# Physical Infrastructure

Overview of rack hardware, device placement, and power infrastructure.

## Contents

- [Rack Layout](rack-layout.md) — visual diagram and unit assignments
- [Power](power.md) — UPS, PDU, capacity planning

## Hardware Inventory

### Networking

| Device | Model | Role | Location |
|---|---|---|---|
| Router | GL.iNet GL-MT6000 (Flint 2) | Edge router, WiFi 6, 2× 2.5G ports | Rack, front short shelf |
| Switch | TP-Link TL-SG108E | 8-port smart managed switch (QoS/VLAN/IGMP/LAG) | Rack, back short shelf (shares with dell-mini) |
| Patch Panel | Cable Matters 12-Port Cat6 1U | Cable management | Rack, back (above PDU) |
| IoT AP | TP-Link (OpenWrt) | Isolated IoT wireless | On top of rack frame (not rack-mounted), front — see [Top of Rack](#top-of-rack-not-rack-mounted) |

### Compute

| Device | Model | Role | Location |
|---|---|---|---|
| Proxmox node | Dell Precision 3620 | Hypervisor, GitHub Actions runner, monitoring | Rack, full-depth shelf (shared front+back) |
| `dell-mini` | Dell OptiPlex 3050 Micro | Debian, runs research-output-scraper — see [devices/README.md](../devices/README.md) | Rack, back short shelf (shares with switch) |
| `acer-lap` | Acer Aspire (laptop) | Debian, networked — see [devices/README.md](../devices/README.md) | Rack, back half-depth shelf |
| HP laptop | HP (laptop) | Debian, networking not yet configured | Rack, front half-depth shelf |

### Top of Rack (not rack-mounted)

Sitting on top of the rack frame itself, front side — not in a rack-mount
slot:

| Device | Notes |
|---|---|
| Lenovo ThinkPad Mini Dock 3 | Dock for the T420 below |
| Lenovo ThinkPad T420 | Personal/legacy laptop |
| TP-Link (OpenWrt) | Same physical unit as the IoT AP listed above |

### Power

| Device | Model | Location |
|---|---|---|
| UPS | CyberPower CP1500PFCLCD (1500VA/1000W, 12 outlets) | Rack's own base tray (above casters) |
| PDU | VEVOR 8-outlet 1U rackmount (15A, 110-125V) | Rack 1U |

### Rack

| Item | Model | Notes |
|---|---|---|
| Rack | Eastrexon 15U open frame, wall-mountable | 19.7"L × 18.8"W × 32.3"H, swivel casters |
| Shelves | Multiple — full-depth (Proxmox), half-depth ×2 (HP/Acer), short ×2 (dell-mini+switch, router) | Exact per-shelf models/part numbers not yet reconciled post-move — originally a single Tecmojo 1U 4-post vented shelf was planned, actual shelf count grew with it |

### Mobile / Off-rack Devices

| Device | OS | Notes |
|---|---|---|
| Dell XPS 16 | Debian | Primary dev laptop, leaves lab |
| MacBook M1 Pro Max | macOS | Primary portable, leaves lab |
| Pixel 6 | GrapheneOS | Leaves lab |
| iPhone 7 | iOS | Leaves lab |
| Samsung (old) | Android | IoT VLAN testing, stays in lab |
