# Telegram notification proxy and Mullvad DNS (CT 107)

**Deployed and validated 2026-10-25.** `telegram-proxy-01` is Debian 13.6 in unprivileged Proxmox LXC **107**, at `192.168.10.171/24` (gateway `192.168.10.1`) on VLAN 10. It is a narrow HTTPS CONNECT proxy for Uptime Kuma's Telegram notification provider **and** a Mullvad-backed DNS resolver for Trusted VLAN 20 when VPN mode is enabled. Do not put the Telegram bot token in files tracked by Git.

## Architecture

| Service | Configuration | Purpose |
|---|---|---|
| Tinyproxy 1.11.2 | `/etc/tinyproxy/tinyproxy.conf`, listen `192.168.10.171:3128` | Only source `192.168.10.158` (monitor-01) and loopback allowed; `ConnectPort 443` |
| Tinyproxy filter | `/etc/tinyproxy/telegram-allowed-domains` containing `api.telegram.org` | `FilterType fnmatch`, `FilterDefaultDeny Yes`, `FilterURLs No`; other CONNECT domains blocked |
| dnsmasq | `/etc/dnsmasq.d/mullvad-split-dns.conf` | Public requests → `10.64.0.1`; `home.arpa` → router `192.168.10.1`; cache-size 300 |
| Container resolver | `/etc/resolv.conf` managed by Proxmox | `nameserver 127.0.0.1`, search `home.arpa` |
| DNS destination guard | `telegram_dns_guard` nft table; enabled systemd unit | Permits dnsmasq uid DNS upstream only to Mullvad or homelab router; blocks other classic port-53 outbound DNS |
| Trusted DNS listener access | `/root/trusted-dns-access.nft` with `trusted-dns-access.service` enabled | Allow VLAN 20 DNS TCP/UDP 53; drop other inbound DNS, with loopback permitted |
| Router inter-VLAN rule | `firewall.trusted_telegram_dns` | `trusted` `192.168.20.0/24` → `lab` `192.168.10.171:53` UDP/TCP |
| Router PBR and kill switch | `pbr.telegram_local`, `pbr.telegram_mullvad`, `/etc/nftables.d/31-telegram-mullvad-guard.nft` | CT 107 public egress via Mullvad; forwarding out university `eth1` blocked |

Tinyproxy uses `Allow 192.168.10.158`, `Allow 127.0.0.1`, `ConnectPort 443`, and filter `api.telegram.org`. **Use `fnmatch`, not `ere` for that literal filter file**; an earlier mismatch returned HTTP 403 for valid Telegram requests. Proxy is not a generic open Internet proxy.

The dnsmasq service listens on loopback and `192.168.10.171:53` (both TCP and UDP). A previous `interface=lo`/`listen-address=127.0.0.1` was extended to `interface=lo,eth0` and `listen-address=127.0.0.1,192.168.10.171`. It also opened IPv6 link-local listeners; additional listener hardening remains on the task list. Keep the input filter active before exposing port 53 remotely.

### Uptime Kuma integration

Kuma is on `monitor-01` (`192.168.10.158`) in Docker and was upgraded to **`louislam/uptime-kuma:2.5.7`**. Compose sets `NOTIFICATION_PROXY=http://192.168.10.171:3128`, while retaining `NODE_EXTRA_CA_CERTS`, the mounted public homelab CA, and `uptime-kuma-data` volume. Only provider requests using Kuma's shared notification proxy helper are proxied; ordinary monitor health checks remain on normal routing. The Telegram provider uses the default server URL `https://api.telegram.org` (do **not** put the proxy URL in Telegram Server URL). A Telegram **Test** message arrived and a real temporary monitor DOWN/UP workflow was tested after explicitly assigning the notification to that monitor; notification is configured for existing monitors.

The pre-upgrade Kuma 1.x data archive was verified at `/opt/monitoring/backups/kuma-v1-20261025-130228/uptime-kuma-v1-data.tar.gz` (on monitor-01), with a Compose backup. Migration finished, existing monitors persisted. See [Monitoring](monitoring.md).

### Verification / troubleshooting

Run on **monitor-01** (not PVE: Tinyproxy only allows its IP):

```bash
curl -4 -sS -o /dev/null -w '%{http_code}\n' \
  --max-time 10 --proxy http://192.168.10.171:3128 \
  https://api.telegram.org/
# Expected 302; proxy CONNECT succeeds, then Telegram root redirects.
curl -sS -o /dev/null -w '%{http_code}\n' \
  --max-time 10 --proxy http://192.168.10.171:3128 \
  https://example.com/
# Expected 403 from Tinyproxy filter.
docker exec uptime-kuma printenv NOTIFICATION_PROXY
docker logs uptime-kuma --since 30m 2>&1 | tail -60
```

Run on **XPS in VLAN 20**:

```bash
dig @192.168.10.171 api.telegram.org A +short
dig @192.168.10.171 pve.home.arpa A +short
dig +tcp @192.168.10.171 pve.home.arpa A +short
# Expected Telegram 149.154.166.110; internal pve 192.168.10.10 at deployment.
```

Run on **PVE**:

```bash
pct exec 107 -- systemctl is-active tinyproxy dnsmasq trusted-dns-access.service
pct exec 107 -- nft list table inet trusted_dns_access
pct exec 107 -- ss -lntup
```

**Do not** paste bot tokens or run commands that dump private UCI interface keys. For `getUpdates`, users must message the bot first; the chat ID is not the bot token. Telegram notification must actually be enabled on each monitor (or apply-to-existing-monitors option used); a successful provider test alone doesn't attach a notification to monitors.

### Open checks

- [ ] Verify CT 107 DNS input and output nft guards after a container reboot; check unit ordering and whether firewall state is preserved at startup.
- [ ] Verify DNS listening on IPv4 only where intended, or filter IPv6 DNS listeners explicitly.
- [ ] Confirm DNS access is restricted across other VLAN 10 peers and unapproved network sources.
- [ ] Add monitoring of CT 107 proxy/DNS availability and ensure alert delivery does not depend exclusively on an unavailable path.
