# Services

All services run on or through the **Dell Precision 3620 Proxmox node**
unless noted — `research-output-scraper` is the one exception, running
directly on `dell-mini` instead.

## Contents

- [Proxmox](proxmox.md) — hypervisor setup, VMs, GitHub Actions runner
- [NAS & Storage](nas.md) — qBittorrent, NAS software, HDD setup
- [GitHub Actions Runners](github-actions-runners.md) — KC/DFAIR/KC-Timing setup, safe restarts, manual deployment and nightly update checks
- [Monitoring](monitoring.md) — current and planned monitoring stack
- [Internal HTTPS / Caddy](caddy.md) — reverse proxy, internal CA, metrics and trust
- [Local GPU LLM](local-llm.md) — VM108, Quadro P4000 passthrough, Qwen3 8B, private HTTPS API and reboot recovery
- [IDS Research](ids-research.md) — dissertation research (FIRCE/FADES),
  likely uses this network's IoT VLAN as its real-world testbed
- [research-output-scraper](research-output-scraper.md) — CS researcher
  publication leaderboard, the one service that runs on `dell-mini`
  instead of Proxmox

## Services Overview

```mermaid
graph TD
    PVE[Proxmox VE\nDell Precision 3620]

    subgraph "VMs (Planned)"
        DEBIAN[Debian VM\nGeneral purpose]
        MACOS[macOS VM\nDevelopment]
        WIN[Windows VM\nCompatibility]
        FW[Firewall VM\ne.g. OPNsense]
    end

    subgraph "VM 101 - gha-general-01"
        GHA1[dfair runner]
        GHA3[kc runner]
        GHA4[KC-Timing runner]
        BK[Buildkit]
    end

    subgraph "VM 102 - monitor-01"
        PROM[Prometheus]
        GRAF[Grafana]
        LOKI[Loki]
        KUMA[Uptime Kuma]
    end

    subgraph "VM 108 - llm-01"
        LLM[Qwen3 8B / llama.cpp\nNVIDIA P4000 passthrough]
    end

    subgraph "LXC 106 - certs-01"
        CADDY[Caddy / internal CA\nHTTPS reverse proxy and metrics]
    end

    subgraph "LXC 105 - nas"
        QB[qBittorrent - planned]
    end

    PVE --> DEBIAN
    PVE --> MACOS
    PVE --> WIN
    PVE --> FW
    PVE --> GHA1
    PVE --> GHA3
    PVE --> GHA4
    GHA1 --> BK
    GHA3 --> BK
    GHA4 --> BK
    PVE --> PROM
    PVE --> QB
    PVE --> CADDY
    PVE --> LLM
    CADDY -->|Trusted VLAN HTTPS / API key| LLM
    CADDY -->|HTTPS reverse proxy| GRAF
    CADDY -->|HTTPS reverse proxy| KUMA
    LEADERBOARD[research-output-scraper\nnginx on dell-mini] 
    CADDY -->|HTTPS frontend, HTTP backend| LEADERBOARD

    IDS["IDS Research (FIRCE/FADES)\nlikely uses VLAN 30 as testbed"]
    IDS -.-> PVE
```

## Internal DNS

| Property | Value |
|---|---|
| Status | Operational |
| Host | GL.iNet Flint 2 |
| Software | OpenWrt dnsmasq |
| Namespace | `home.arpa` |
| Deployment | Router-native |
| Dependencies | Router availability |
| Primary clients | VLAN 10 and VLAN 20 |

DNS resolution and DHCP are managed directly by OpenWrt rather than a Proxmox VM or LXC.

The router maintains hostname records from DHCP leases and reservations, with explicit DNS records for statically addressed infrastructure.

### Infrastructure Services

| Service | Hostname | Access |
|---|---|---|
| Proxmox VE | `pve.home.arpa` | HTTPS port 8006 |
| Grafana host | `monitor.home.arpa` | Port 3000 |
| Uptime Kuma host | `monitor.home.arpa` | Port 3001 |
| CS publication leaderboard | `cs-leaderboard.home.arpa` | HTTPS 443 via Caddy → `dell-mini:80` |
| NAS LXC | `nas.home.arpa` | Service-dependent |
| GitHub Actions VM | `gha-general-01.home.arpa` | SSH port 22 |
| Local LLM API | `llm.home.arpa` | HTTPS port 443, Trusted VLAN + Bearer API key |

The NAS currently uses DHCP at `192.168.10.170`. A permanent reservation is recommended but has not yet been configured.

DNS resolution does not grant access between VLANs; OpenWrt firewall policies remain enforced.

For the full configuration, verified inventory, and troubleshooting procedures, see [Internal DNS](../networking/dns.md).

## Service Status

| Service | Type | Status | Priority |
|---|---|---|---|
| [GitHub Actions runners (DFAIR/KC/KC-Timing)](github-actions-runners.md) | 3x Docker containers on `gha-general-01` (VM 101, separate from proxmox itself) | ✅ Running | High |
| Monitoring (Prometheus/Grafana) | Docker, on `monitor-01` (VM 102) | ✅ Running | High |
| [Internal HTTPS / Caddy](caddy.md) | Caddy 2.6.2 on `certs-01` (LXC 106) | ✅ Running; hardening and dashboards pending | High |
| [research-output-scraper](research-output-scraper.md) | nginx + systemd on `dell-mini`; HTTPS via Caddy | ✅ Running; HTTPS verified 2026-10-21 | Medium |
| [qBittorrent](nas.md) | qBittorrent-nox 4.5.2 in NAS CT 105 | ✅ Running via Mullvad, HTTPS `torrent.home.arpa` | Medium |
| [NAS storage](nas.md) | CT 105 with bind-mounted HDD | ✅ CT/storage running; SMB/NFS management stack pending | Medium |
| Firewall VM | VM | 🔲 Planned | Low |
| Debian VM | VM | 🔲 Planned | Low |
| macOS VM | VM | 🔲 Planned | Low |
| Windows VM | VM | 🔲 Planned | Low |

## Mullvad-dependent services (2026-10-25)

- [NAS / qBittorrent](nas.md): CT 105, Mullvad-only PBR and WAN guard; Web UI via `torrent.home.arpa`.
- [Telegram proxy and DNS](telegram-proxy.md): CT 107, Tinyproxy allowlisting `api.telegram.org`, plus VPN-mode DNS for Trusted VLAN.
- [Monitoring](monitoring.md): Kuma upgraded to 2.5.7, Telegram DOWN/recovery alerts verified via CT 107.

See [Mullvad router operations](../networking/mullvad.md) for subnet-level routing and toggle details.
