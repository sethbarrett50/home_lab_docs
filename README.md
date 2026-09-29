# 🏠 Homelab Documentation

> Personal homelab documentation — migrated from the PhD lab environment to home. GL.iNet Flint 2 + TL-SG108E + VLAN segmentation now live.

## Quick Links

| Section | Description |
|---|---|
| [Physical Infrastructure](docs/physical/README.md) | Rack layout, hardware inventory, power |
| [Networking](docs/networking/README.md) | Topology, VLANs, firewall, VPN |
| [Services](docs/services/README.md) | Proxmox VMs, NAS, monitoring, self-hosted apps |
| [Devices](docs/devices/README.md) | All connected endpoints |

## High-Level Overview

```mermaid
graph TD
    WAN[🌐 Home ISP]
    Router[GL.iNet Flint 2<br/>stock OpenWrt · Router / Firewall]
    Switch[TP-Link TL-SG108E<br/>8-Port Smart Switch, 802.1Q]
    PATCH[Patch Panel<br/>12-Port Cat6]
    IoT_AP[Old TP-Link<br/>OpenWrt 15.05.1 · dumb AP]

    VLAN10[VLAN 10 — Lab<br/>Proxmox · nas/gha-runner/monitor VMs+LXCs · debian boxes]
    VLAN20[VLAN 20 — Trusted<br/>WiFi `dfair_lab` · Phone · MacBook Pro]
    VLAN30[VLAN 30 — IoT<br/>Cameras · smart plugs · research devices]

    WAN --> Router
    Router -->|2.5G Uplink, native VLAN 1 + tagged 10/20/30| Switch
    Switch --> PATCH
    Switch -->|access port 6| IoT_AP
    PATCH --> VLAN10
    Switch --> VLAN10
    Router -.->|WiFi| VLAN20
    IoT_AP --> VLAN30
```

## Status

| Item | Status |
|---|---|
| Physical rack build | ✅ Done |
| GL.iNet Flint 2 as main router | ✅ Running |
| VLAN configuration (10 Lab / 20 Trusted / 30 IoT) | ✅ Done — all 3 VLANs live, devices migrated, static reservations set |
| Proxmox setup | ✅ Running |
| NAS / storage | ✅ Done |
| VPN (inbound) | 🔲 Planned |
| Mullvad on Trusted VLAN | 🔲 Planned |
| Monitoring stack | 🔧 Partial |

## Repo Structure

```
homelab-docs/
├── README.md                   ← You are here
├── docs/
│   ├── physical/
│   │   ├── README.md           ← Rack layout & hardware inventory
│   │   ├── power.md            ← UPS, PDU, power planning
│   │   └── rack-layout.md      ← Visual rack diagram & placement
│   ├── networking/
│   │   ├── README.md           ← Network overview & topology
│   │   ├── vlans.md            ← VLAN design & policy
│   │   ├── firewall.md         ← Firewall rules & design
│   │   └── vpn.md              ← Inbound VPN & Mullvad config
│   ├── services/
│   │   ├── README.md           ← Services overview
│   │   ├── proxmox.md          ← Proxmox setup & VMs
│   │   ├── nas.md              ← NAS / storage / qBittorrent
│   │   └── monitoring.md       ← Monitoring stack
│   └── devices/
│       └── README.md           ← Device inventory & notes
└── assets/                     ← Diagrams, screenshots
```
