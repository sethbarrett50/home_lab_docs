# Networking

## Contents

- [VLANs](vlans.md) — design, IP scheme, inter-VLAN policy
- [Firewall](firewall.md) — rules and segmentation strategy
- [VPN](vpn.md) — inbound remote access + Mullvad on Trusted VLAN

## Hardware

| Device | Role |
|---|---|
| GL.iNet GL-MT6000 Flint 2 | Edge router, DHCP, firewall, WiFi. Stock OpenWrt 23.05.5 (not GL.iNet firmware) |
| TP-Link TL-SG108E | Layer 2 smart switch (802.1Q VLAN tagging, QoS, IGMP, LAG) |
| Old TP-Link (unknown model) | OpenWrt 15.05.1 "Chaos Calmer", dumb AP for IoT VLAN — no routing/DHCP of its own |

## Network Topology

```mermaid
graph TD
    WAN[🌐 Home ISP]

    subgraph Edge
        Router["GL.iNet Flint 2\nstock OpenWrt 23.05.5\n192.168.1.1 (lan) + br-lan.10/.20/.30\nFirewall · DHCP"]
    end

    subgraph "Rack — Layer 2"
        Switch["TP-Link TL-SG108E\n8-port Smart Switch\n802.1Q, native VLAN 1 + tagged 10/20/30"]
        Patch["12-port Patch Panel"]
    end

    subgraph "VLAN 10 — Lab (192.168.10.0/24)"
        PVE["Dell Precision 3620\nProxmox host\n.10 static"]
        NAS["nas (LXC 105)\n.170 DHCP"]
        GHA["gha-general-01 (VM 101)\n.189 DHCP-pinned"]
        MON["monitor-01 (VM 102)\n.158 DHCP\nGrafana :3000 / Prometheus :3001"]
        DEBIAN["Dell Micro / Acer / HP\nswitch-migrated, OS networking pending"]
    end

    subgraph "VLAN 20 — Trusted (192.168.20.0/24)"
        SSID["WiFi SSID: dfair_lab\n(radio0 2.4GHz + radio1 5GHz)"]
        PHONE["Phone"]
        MBP["MacBook Pro"]
    end

    subgraph "VLAN 30 — IoT (192.168.30.0/24)"
        IoTAP["Old TP-Link\nOpenWrt 15.05.1, dumb AP\n192.168.30.2 static"]
        IOTDEV["Cameras, smart plugs, doorbell,\nresearch devices — all DHCP-pinned"]
    end

    WAN -->|"2.5G WAN port"| Router
    Router -->|"2.5G LAN port — native VLAN 1, tagged 10/20/30"| Switch
    Switch --> Patch
    Patch --> PVE
    Switch --> PVE
    Switch --> DEBIAN
    PVE -.-> NAS
    PVE -.-> GHA
    PVE -.-> MON
    Switch -->|"Access port 6 — VLAN 30"| IoTAP
    IoTAP --> IOTDEV
    Router -.->|"WiFi"| SSID
    SSID -.-> PHONE
    SSID -.-> MBP
```

## IP Addressing Scheme

| VLAN | Name | Subnet | Gateway | DHCP Range |
|---|---|---|---|---|
| 1 | Management | 192.168.1.0/24 | 192.168.1.1 | `.100`–`.249` (DHCP active — not static-only as originally planned; switch mgmt and a few misc devices use it) |
| 10 | Lab | 192.168.10.0/24 | 192.168.10.1 | `.100`–`.200` |
| 20 | Trusted | 192.168.20.0/24 | 192.168.20.1 | `.100`–`.200` |
| 30 | IoT | 192.168.30.0/24 | 192.168.30.1 | `.100`–`.200` |

### Static / Pinned Assignments

Superseded the original RPi-era plan. Full current list, including all IoT
device reservations, lives in [devices/README.md](../devices/README.md) —
kept there rather than duplicated here since it changes more often than the
network design itself.

| Host | IP | Notes |
|---|---|---|
| Proxmox host | 192.168.10.10 | Static (in-guest, `/etc/network/interfaces`) |
| gha-general-01 | 192.168.10.189 | DHCP host reservation |
| Old TP-Link (IoT AP) | 192.168.30.2 | Static (in-guest) |
| 10 IoT devices | 192.168.30.x | DHCP host reservations — see devices/README.md |

## Switch Port Assignment

Updated to match actual current hardware (post-move) and the phased rollout —
see [vlans.md](vlans.md) for phase status. Only ports 1 and 6 required changes
from switch factory default; 2-5, 7-8 are untouched (Untagged VLAN 1, PVID 1).

| Port | VLAN Mode | VLAN 1 | VLAN 30 | PVID | Device |
|---|---|---|---|---|---|
| 1 | Trunk (native VLAN 1) | Untagged (unchanged) | Tagged | 1 | GL.iNet Flint 2 uplink (`lan1`) |
| 2 | Access | Untagged | Not Member | 1 | Proxmox (Dell Precision 3620) — moves to VLAN 10 in Phase 3 |
| 3 | Access | Untagged | Not Member | 1 | Dell Micro (debian) — moves to VLAN 10 in Phase 3 |
| 4 | Access | Untagged | Not Member | 1 | Acer Aspire (debian) — moves to VLAN 10 in Phase 3 |
| 5 | Access | Untagged | Not Member | 1 | HP Laptop (debian) — moves to VLAN 10 in Phase 3 |
| 6 | Access | Not Member | Untagged | 30 | Old TP-Link (OpenWrt) — dedicated IoT AP |
| 7 | — | Untagged | Not Member | 1 | Empty |
| 8 | — | Untagged | Not Member | 1 | Reserved / maintenance |

> TL-SG108E gotcha: VLAN membership (tagged/untagged/not member) and PVID are
> **two separate pages** (`VLAN > 802.1Q VLAN` and `VLAN > 802.1Q VLAN PVID
> Setting`) — easy to configure one and forget the other, leaving a port
> half-configured.
>
> **Lesson learned (caused a real outage during Phase 2):** originally tagged
> `lan1` for VLAN 1 on the router before the switch had any 802.1Q config —
> this cut off everything through the switch (proxmox, the switch's own mgmt
> UI at 192.168.1.160) since the router started sending/expecting tagged
> frames on a link the switch was still treating as flat. Full loss of
> reachability to the switch's management page, confirmed via `ping` timing
> out even from the router itself — not a browser/cache issue.
>
> **Fix, and the pattern going forward:** use **native VLAN 1** on the trunk —
> VLAN 1 stays **untagged** on `lan1` (`lan1:u*`), matching the switch's
> untouched factory-default state exactly, so it needs **zero changes** to
> keep working. Only the *new* VLAN (30) is tagged on the trunk. This means
> adding a VLAN never risks breaking existing traffic — the router and switch
> only need to agree on the newly-added tagged VLAN, not renegotiate the
> already-working native one. Apply this same pattern in Phase 3 for VLANs 10
> and 20.
