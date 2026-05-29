# Physical Infrastructure

Overview of rack hardware, device placement, and power infrastructure.

## Contents

- [Rack Layout](rack-layout.md) — visual diagram and unit assignments
- [Power](power.md) — UPS, PDU, capacity planning

## Hardware Inventory

### Networking

| Device | Model | Role | Location |
|---|---|---|---|
| Router | GL.iNet GL-MT6000 (Flint 2) | Edge router, WiFi 6, 2× 2.5G ports | Rack |
| Switch | TP-Link TL-SG108E | 8-port smart managed switch (QoS/VLAN/IGMP/LAG) | Rack |
| Patch Panel | Cable Matters 12-Port Cat6 1U | Cable management | Rack |
| IoT AP | TP-Link (OpenWrt) | Isolated IoT wireless | Rack/shelf |

### Compute

| Device | Model | Role | Location |
|---|---|---|---|
| Proxmox node | Dell Precision 3620 | Hypervisor, GitHub Actions runner, monitoring | Rack |
| SBC × 3 | Raspberry Pi 3B | Various lab tasks | Rack shelf |

### Power

| Device | Model | Location |
|---|---|---|
| UPS | CyberPower CP1500PFCLCD (1500VA/1000W, 12 outlets) | Rack / floor |
| PDU | VEVOR 8-outlet 1U rackmount (15A, 110-125V) | Rack 1U |

### Rack

| Item | Model | Notes |
|---|---|---|
| Rack | Eastrexon 15U open frame, wall-mountable | 19.7"L × 18.8"W × 32.3"H, swivel casters |
| Shelf | Tecmojo 1U 4-post vented, 21.7" deep, adjustable 13.5–31.8" | Up to 242 lbs |

### Mobile / Off-rack Devices

| Device | OS | Notes |
|---|---|---|
| Dell XPS 16 | Debian | Primary dev laptop, leaves lab |
| MacBook M1 Pro Max | macOS | Primary portable, leaves lab |
| Acer Aspire (8GB) | Debian headless | Leaves lab |
| HP laptop | Debian + XFCE | Stays in lab area |
| Pixel 6 | GrapheneOS | Leaves lab |
| iPhone 7 | iOS | Leaves lab |
| Samsung (old) | Android | IoT VLAN testing, stays in lab |
