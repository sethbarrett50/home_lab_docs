# Internal DNS — OpenWrt dnsmasq

**Status:** Deployed and validated on 2026-10-20
**DNS namespace:** `home.arpa` (RFC 8375)
**Platform:** GL.iNet Flint 2 / OpenWrt 23.05.5, dnsmasq
**Scope:** Internal lab hostnames; the router continues to serve DNS and DHCP. HTTPS certificates are provided separately by Caddy on `certs-01`.

## WireGuard remote DNS note (2026-10-25)

The VPS-relayed remote VPN allows XPS `10.100.0.10` to query the Flint 2 DNS service at `192.168.10.1:53` over TCP and UDP. When the WireGuard /32 client was rejected by dnsmasq's local-subnet guard, `dhcp.@dnsmasq[0].localservice` was changed from `1` to `0`; DNS resolution through the WireGuard path then succeeded. This increases the importance of verifying that router firewall INPUT rules continue to deny WAN DNS. No router WAN DNS exposure has been demonstrated, but a dedicated exposure audit remains outstanding.

The XPS **retains NetworkManager** and its existing resolver configuration. To resolve key homelab services off-network without changing the laptop's DNS manager, `/etc/hosts` was backed up to `/etc/hosts.pre-homelab` and static entries added: `pve.home.arpa → 192.168.10.10`, `grafana.home.arpa`/`uptime.home.arpa → 192.168.10.50`, `monitor.home.arpa → 192.168.10.158`, `nas.home.arpa → 192.168.10.170`. These host mappings do **not** confer permission to access each destination; remote routing/firewall access is still narrowly allowed. See [VPN](vpn.md).

## Design decision

Use the Flint 2's existing dnsmasq service instead of hosting a DNS LXC on Proxmox. This keeps hostname resolution available even if Proxmox is offline, and avoids unnecessary additional services. DHCP reservations and DHCP-advertised client names produce DNS records automatically; infrastructure with statically configured IP addresses receives explicit records.

The router's VLAN 10 gateway is `192.168.10.1`, and its VLAN 20 gateway is `192.168.20.1`. Clients on VLAN 20 were verified to resolve internal records via the router. DNS resolution does **not** grant access across VLANs; existing firewall rules still govern connectivity to each host and port.

`home.arpa` is reserved for home-network naming. Avoid `.local` (mDNS) and standalone `.arpa` names. Clients should use fully qualified names, such as `pve.home.arpa`; the Proxmox UI still uses HTTPS port `8006`.

## Verified VLAN 10 records

| DNS name | IPv4 address | Source | Verification |
| --- | --- | --- | --- |
| `pve.home.arpa` | `192.168.10.10` | Explicit UCI DNS record; static address on Proxmox `vmbr0` | DNS lookup; web UI reachable |
| `monitor.home.arpa` | `192.168.10.158` | Explicit UCI DNS record | DNS lookup |
| `cs-leaderboard.home.arpa` | `192.168.10.50` | Explicit UCI `config domain` record (2026-10-21) | `dig @192.168.20.1`, `getent`, HTTPS/API validated |
| `dell-mini.home.arpa` | `192.168.10.117` | Existing DHCP reservation | DNS lookup |
| `gha-general-01.home.arpa` | `192.168.10.189` | Existing DHCP reservation | DNS lookup |
| `acer-lap.home.arpa` | `192.168.10.199` | Existing DHCP reservation | DNS lookup |
| `hp-lap.home.arpa` | `192.168.10.147` | Existing DHCP reservation | DNS lookup |
| `nas.home.arpa` | `192.168.10.170` | Active DHCP lease for LXC 105 (`nas`); **no reservation yet confirmed** | DHCP lease verified; DNS lookup pending |

**NAS address verification:** LXC 105 (`hostname: nas`) uses DHCP. The router's `/tmp/dhcp.leases` confirms `192.168.10.170`, hostname `nas`, and MAC `BC:24:11:4D:7E:3A` (matching `pct config 105`). This verifies its **current lease only**, not a permanent reservation or successful `nas.home.arpa` DNS lookup. The router also observed `192.168.10.198` and `.199` with the Acer laptop's MAC, and an unresolved/failed neighbor at `.146`. Do not publish those as additional devices without confirming them.

The `monitor-01` Proxmox VM name differs from its documented `monitor.home.arpa` alias; the alias is intentional.

## Current router configuration

The relevant OpenWrt `/etc/config/dhcp` settings are:

```text
config dnsmasq
    option domain 'home.arpa'
    option local '/home.arpa/'
    option expandhosts '1'
```

Examples of explicit entries for statically addressed infrastructure and service aliases:

```text
config domain
    option name 'pve.home.arpa'
    option ip '192.168.10.10'

config domain
    option name 'monitor.home.arpa'
    option ip '192.168.10.158'

config domain
    option name 'cs-leaderboard.home.arpa'
    option ip '192.168.10.50'
```

The leaderboard DNS name points to the **Caddy frontend** at `.50`, not the application backend `dell-mini` at `192.168.10.117`. Other Caddy aliases (`grafana.home.arpa`, `uptime.home.arpa`) also point to `.50`; see [networking inventory](README.md#internal-service-dns-homearpa) and [Caddy](../services/caddy.md).

Existing `config host` DHCP reservations are retained. No DHCP reservation was added for Proxmox: its host network configuration uses `192.168.10.10/24` statically on `vmbr0`, gateway `192.168.10.1`.

## Implementation and checks

Changes were backed up, committed with `uci commit dhcp`, syntax-checked with `dnsmasq --test` (`syntax check OK`), and applied using `/etc/init.d/dnsmasq restart`. The dnsmasq process was observed running afterward.

The six DNS-tested records above returned the expected IPv4 addresses when queried against the VLAN 20 gateway (the NAS entry is not yet DNS-tested):

```bash
for host in pve monitor dell-mini gha-general-01 acer-lap hp-lap; do
  printf '%-32s' "$host.home.arpa"
  dig @192.168.20.1 +short "$host.home.arpa"
done
```

From the Debian XPS, standard system name resolution also succeeded for `pve`, `monitor`, and `dell-mini`:

```bash
getent ahostsv4 pve.home.arpa
getent ahostsv4 monitor.home.arpa
getent ahostsv4 dell-mini.home.arpa
```

`https://pve.home.arpa:8006` worked in a browser. Certificate trust warnings are expected until TLS is addressed separately. An HTTP `501` response to `curl -k -I` reflects unsupported HEAD requests and is not evidence of failed name resolution.

### Leaderboard DNS validation (2026-10-21)

Added `cs-leaderboard.home.arpa` on OpenWrt using `uci add dhcp domain`, committed, ran `dnsmasq --test` (OK), and restarted dnsmasq. `dig @192.168.20.1 cs-leaderboard.home.arpa +short` and `getent ahostsv4 cs-leaderboard.home.arpa` both returned `192.168.10.50` from the Trusted VLAN. HTTPS then returned HTTP 200 with trusted TLS, API JSON was returned, and HTTP redirected to HTTPS (308). See [leaderboard](../services/research-output-scraper.md). The dnsmasq restart printed `udhcpc: no lease` messages, but the tested DNS resolution succeeded; this alone does not diagnose other DHCP client interfaces.

### NAS follow-up validation

The active DHCP lease has been confirmed, but DNS resolution and address persistence remain to be checked:

```bash
# On a trusted client
dig @192.168.20.1 +short nas.home.arpa
getent ahostsv4 nas.home.arpa

# On OpenWrt: verify no existing reservation before creating one
uci show dhcp | grep -i -B2 -A2 "bc:24:11:4d:7e:3a"
```

Only after deciding that `.170` should be permanent, add a reservation and document that change separately.

## Operational guidance

- For new DHCP clients, assign meaningful DHCP hostnames; configure static reservations for devices that should retain stable addresses.
- For static-IP systems, create a `config domain` DNS record and document the address in this inventory.
- Keep the router's internal DNS domain and records consistent with this document.
- After changes, run `dnsmasq --test`, restart dnsmasq, and test DNS from a client without explicitly specifying a resolver (`getent`) as well as with `dig @<router-ip>`.
- DNS answers do not bypass VLAN firewall policies. Validate service access separately from hostname resolution.
- Store router configuration backups securely. Avoid committing sensitive full-device exports or credentials into a public repository.

## Remaining work

- Test `nas.home.arpa` from VLAN 20 and with ordinary client resolution. If the NAS should keep `192.168.10.170`, add a DHCP reservation using MAC `BC:24:11:4D:7E:3A`, then retest. Do not treat the currently verified DHCP lease as a permanent reservation.
- Compare the router's active DHCP leases and ARP/neigh table with the VLAN 10 inventory; add entries for other verified hosts if necessary.
- Keep network inventory and diagrams synchronized with new router-hosted DNS names and the `home.arpa` namespace.
- HTTPS was deployed on 2026-10-20 and extended to the leaderboard on 2026-10-21; clients must trust the existing Caddy CA. See [Caddy](../services/caddy.md).
