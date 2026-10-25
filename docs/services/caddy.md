# Internal HTTPS and Caddy

Deployed 2026-10-20; leaderboard route added and validated 2026-10-21. Runs on **`certs-01`**, Debian 13 unprivileged Proxmox LXC **CT 106**, VLAN 10, static `192.168.10.50`. Caddy **2.6.2** runs under systemd (`caddy.service`). The router (`flint2`, `192.168.10.1`) provides the `home.arpa` DNS records; Caddy does **not** provide DNS.

## Endpoints and traffic

| Name | Route | Backend or service | Certificate handling |
|---|---|---|---|
| `grafana.home.arpa` | HTTPS 443 → Caddy | `192.168.10.158:3000` | Caddy `tls internal` (automatic leaf renewal) |
| `uptime.home.arpa` | HTTPS 443 → Caddy | `192.168.10.158:3001` | Caddy `tls internal` (automatic leaf renewal) |
| `cs-leaderboard.home.arpa` | HTTPS 443 → Caddy | `192.168.10.117:80` (nginx on `dell-mini`) | Caddy `tls internal` (automatic leaf renewal) |
| `pve.home.arpa:8006` | Direct to Proxmox `192.168.10.10:8006` | Proxmox `pveproxy` (not routed through Caddy) | Manually signed custom certificate; see [Proxmox](proxmox.md#internal-https-certificate) |
| `192.168.10.50:9180/metrics` | HTTP metrics-only listener on `certs-01` | Scraped by Prometheus on `monitor-01` | Plain HTTP, IP-restricted by Caddy matcher; firewall restriction still needs testing |

**Do not expose TCP 2019.** The Caddy administration interface and its local `/metrics` endpoint bind to `127.0.0.1:2019`. The separate port 9180 has only the metrics handler; it is not an administrative proxy. The metrics handler currently permits source `192.168.10.158` and returns 403 otherwise. Its access restrictions have **not yet been tested from another VLAN 10 client**.

## Running Caddyfile

`/etc/caddy/Caddyfile` on **`certs-01`** (updated 2026-10-21; includes leaderboard block):

```caddyfile
{
    servers {
        metrics
    }
}

grafana.home.arpa {
    tls internal
    encode zstd gzip
    reverse_proxy 192.168.10.158:3000
}

uptime.home.arpa {
    tls internal
    encode zstd gzip
    reverse_proxy 192.168.10.158:3001
}

cs-leaderboard.home.arpa {
    tls internal
    encode zstd gzip
    reverse_proxy 192.168.10.117:80
}

http://192.168.10.50:9180 {
    @prometheus remote_ip 192.168.10.158

    handle @prometheus {
        metrics /metrics
    }

    respond 403
}
```

The `servers { metrics }` syntax is intentional for the **installed Caddy 2.6.2**; a top-level `metrics` global option failed validation on this version.

### Validation

**Run on `certs-01` (root):**

```bash
caddy validate --config /etc/caddy/Caddyfile
systemctl reload caddy  # only if validation succeeded
systemctl is-active caddy
curl -fsS http://127.0.0.1:2019/metrics | grep '^caddy_reverse_proxy_upstreams_healthy'
curl -fsS -o /dev/null -w '%{http_code}\n' https://grafana.home.arpa/login
curl -fsS -o /dev/null -w '%{http_code}\n' https://uptime.home.arpa/dashboard
```

**Run on `monitor-01` VM:**

```bash
curl -fsS http://192.168.10.50:9180/metrics | grep '^caddy_reverse_proxy_upstreams_healthy'
```

Both proxy URLs returned HTTP 200 from `certs-01` after installing the internal root CA in its system trust store. Prometheus subsequently reported the `caddy` job **UP** (`up{job="caddy"} = 1`). An upstream-health gauge of 1 is **not** a substitute for an end-to-end HTTPS check.

### Leaderboard acceptance test (2026-10-21)

From an XPS client on VLAN 20, `curl -v https://cs-leaderboard.home.arpa/` returned HTTP/2 200 and `SSL certificate verify ok`; the TLS SAN matched `cs-leaderboard.home.arpa`. `GET /api/universities` returned HTTP/2 200 and nonempty JSON; HTTP port 80 returned a 308 redirect to HTTPS. On `certs-01`, `curl -I http://192.168.10.117/` returned 200. `caddy fmt --overwrite`, configuration validation, and service reload succeeded. The initial leaf certificate was valid for 12 hours; Caddy manages renewal automatically. These checks establish service reachability, not a complete audit of the router firewall rules.

## Internal CA and client trust

Caddy's local CA material lives on **`certs-01`** under:

`/var/lib/caddy/.local/share/caddy/pki/authorities/local/`

- `root.crt`: **public** trust anchor, safe to distribute.
- `root.key`: **private** CA key, do not copy into the repository or distribute to clients.
- `intermediate.crt` and `intermediate.key`: intermediate CA material; protect private key.

Root CA SHA-256 fingerprint (verified on `monitor-01`):

```text
D5:CE:B6:79:57:E5:39:DF:24:A8:59:C0:97:6A:02:A8:D6:AE:E7:EC:B4:6C:4D:53:36:DE:B5:EF:8F:72:A4:2C
```

The public root was installed in Debian's trust store on the **XPS**, **monitor-01**, and **certs-01**. For a Debian machine with a verified copy of the public `root.crt`:

```bash
sudo install -m 0644 root.crt /usr/local/share/ca-certificates/homelab-root-ca.crt
sudo update-ca-certificates
```

On `certs-01`, commands run as root, so omit `sudo` (not installed there). Brave on the XPS also required trust in its NSS database and a full restart; OS trust alone initially did not clear the browser warning.

**Do not commit** root/intermediate private keys, application passwords, copied Compose environment output, or Proxmox TLS private keys. The root CA backup is especially sensitive: anyone with its private key could issue trusted certificates for the homelab.

## Backups and recovery

CT 106 has been included in the Proxmox backup workflow on `hdd-1tb` (see [Proxmox backups](proxmox.md#backups)). An initial manual `vzdump` succeeded. Backups reside on the same host/site and are **not** yet verified off-host disaster-recovery copies.

A restore must preserve Caddy's CA material to keep the existing installed trust anchor valid. After restoring, check DNS resolution, port 443, the `caddy` service, the metrics endpoint, and all three proxied HTTPS URLs. Protect stored backup archives as CA-key-bearing secrets. A restore test is still outstanding.

## Follow-ups

- [ ] Verify port 9180 rejects clients other than `monitor-01`; add host-level/Proxmox firewall restriction as defense in depth.
- [x] Prepare three Caddy/HTTPS status panels in the **version-controlled** Grafana dashboard JSON. Prometheus queries are verified; **live Grafana import and saved-panel verification remain pending**.
- [ ] Import/verify the updated Scenes dashboard in live Grafana and export its final saved JSON back to the repository.
- [ ] Verify Uptime Kuma HTTPS monitors in the UI (container CA trust is configured; monitor health was not demonstrated in the session). Notifications and certificate-expiry alerts are deferred to a **separate issue**.
- [ ] Test restoration and create a secure off-host backup of CA material.
- [ ] Replace password-based root SSH access with appropriate key-based/least-privilege access.
- [ ] Define a safer/automated Proxmox certificate renewal process before October 2027.

## qBittorrent reverse proxy addition (2026-10-25)

The deployed Caddy routing also includes `torrent.home.arpa` for the qBittorrent-nox Web UI in NAS CT 105 (`192.168.10.170`). The configuration block above is a **historical 2026-10-21 snapshot**, not a complete current Caddyfile. Validate the actual live route using `caddy validate --config /etc/caddy/Caddyfile` on `certs-01` and `curl -I https://torrent.home.arpa/` from an authorized CA-trusting client. Backend port and exact current Caddy stanza were not supplied in the handoff and are intentionally not invented. Keep qBittorrent authentication enabled.
