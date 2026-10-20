# Firewall

The GL.iNet Flint 2 runs OpenWrt, giving full nftables/iptables access alongside the LuCI GUI. Firewall rules are applied at the router level between VLAN interfaces.

## Zone Model

```mermaid
flowchart LR
    WAN[wan\nzone]
    LAB[lan_lab\nVLAN 10]
    TRUST[lan_trusted\nVLAN 20]
    IOT[lan_iot\nVLAN 30]

    WAN -->|"DNAT — VPN tunnel\n& homelab ingress"| LAB
    WAN -->|"DNAT — VPN tunnel"| TRUST
    LAB -->|"allow outbound"| WAN
    TRUST -->|"via Mullvad only"| WAN
    IOT -->|"restricted outbound"| WAN

    LAB -. blocked .- TRUST
    LAB -. blocked .- IOT
    TRUST -. blocked .- IOT
    TRUST -->|"selective rules"| LAB
```

## Default Zone Policies

| Zone | INPUT | OUTPUT | FORWARD |
|---|---|---|---|
| wan | DROP | ACCEPT | DROP |
| lan_lab | ACCEPT | ACCEPT | ACCEPT |
| lan_trusted | ACCEPT | ACCEPT | ACCEPT |
| lan_iot | DROP | ACCEPT | DROP |

## Planned Firewall Rules

### WAN → Router (INPUT)
| # | Protocol | Port | Action | Notes |
|---|---|---|---|---|
| 1 | UDP | 51820 | ACCEPT | WireGuard inbound (homelab VPN) |
| 2 | TCP | 22 | DROP | No SSH from WAN — use VPN |
| — | * | * | DROP | Default deny |

### Trusted VLAN → Internet
All traffic from VLAN 20 is policy-routed to the Mullvad WireGuard interface. A kill switch rule drops traffic if the VPN interface is down:

```text
# Conceptual nftables kill switch
chain forward {
    iifname "br-trusted" oifname != "mullvad0" drop
}
```

### IoT VLAN — Restricted Outbound
Allow only what research devices need; deny everything else by default.

| Protocol | Destination | Action | Notes |
|---|---|---|---|
| UDP/TCP | 53 | ACCEPT | DNS (router only) |
| TCP | 80, 443 | ACCEPT | HTTP/HTTPS if needed |
| * | RFC1918 | DROP | No lateral movement |
| * | * | DROP | Default deny |

### Selective Trusted → Lab Access
Add rules as needed. Starting point — only Proxmox UI:

| Protocol | Destination | Port | Action |
|---|---|---|---|
| TCP | 192.168.10.10 | 8006 | ACCEPT (Proxmox web UI) |
| TCP | 192.168.10.10 | 22 | ACCEPT (SSH to Proxmox) |
| * | 192.168.10.0/24 | * | DROP |

## Internal HTTPS access (deployed 2026-10-20)

The existing broad section above documents the planned baseline, **not a fully audited live firewall ruleset**. During the internal HTTPS deployment, selective Trusted (VLAN 20) → `certs-01` (`192.168.10.50`) TCP access was configured for SSH **22** and web **80/443**. Grafana and Uptime Kuma are reached through Caddy on port 443. Proxmox's CA-signed UI still uses direct `192.168.10.10:8006` access.

The Caddy metrics endpoint `192.168.10.50:9180` is for `monitor-01` (`192.168.10.158`) within VLAN 10. Caddy currently uses a source-IP matcher to reject other clients, but a cross-client test and additional Proxmox/LXC firewall restriction remain outstanding. The admin endpoint `127.0.0.1:2019` **must never be exposed on the network**. Same-VLAN traffic is not secured by OpenWrt's inter-VLAN rules alone.

## TODO

- [ ] Implement zone config in OpenWrt UCI / LuCI
- [ ] Configure Mullvad WireGuard interface + kill switch
- [ ] Test VLAN isolation with `nmap` cross-VLAN scans
- [ ] Set up firewall logging for dropped packets (helps with debugging IoT devices)
- [ ] Consider running a dedicated firewall VM on Proxmox (e.g. pfSense/OPNsense) in the future for more granular control
