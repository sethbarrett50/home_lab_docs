# Devices

Full inventory of all devices in the homelab ecosystem.

## Infrastructure (Rack)

| Hostname | Device | OS/Firmware | VLAN | IP | Notes |
|---|---|---|---|---|---|
| `proxmox` | Dell Precision 3620 | Proxmox VE | 10 | 192.168.10.10 | Static |
| `rpi1` | Raspberry Pi 3B | TBD | 10 | 192.168.10.20 | Static |
| `rpi2` | Raspberry Pi 3B | TBD | 10 | 192.168.10.21 | Static |
| `rpi3` | Raspberry Pi 3B | TBD | 10 | 192.168.10.22 | Static |
| `router` | GL.iNet GL-MT6000 Flint 2 | OpenWrt (GL.iNet) | mgmt | 192.168.1.1 | Edge |
| `switch` | TP-Link TL-SG108E | — | mgmt | 192.168.1.x | L2 only |
| `iot-ap` | TP-Link (OpenWrt) | OpenWrt | 30 | 192.168.30.x | IoT AP |

## Personal Devices (Mobile / Off-rack)

| Hostname | Device | OS | VLAN | Notes |
|---|---|---|---|---|
| `xps16` | Dell XPS 16 | Debian | 20 | Primary dev laptop, leaves lab |
| `mbp` | MacBook M1 Pro Max | macOS | 20 | Primary portable, leaves lab |
| `acer` | Acer Aspire (8GB) | Debian headless | 10 | Leaves lab |
| `hp-lap` | HP Laptop | Debian + XFCE | 10 | Stays in lab area |
| `pixel6` | Google Pixel 6 | GrapheneOS | 20 | Leaves lab |
| `iphone7` | iPhone 7 | iOS | 20 | Leaves lab |
| `samsung-iot` | Samsung (old) | Android | 30 | IoT testing, stays in lab |

## Raspberry Pi Plans

| Host | Planned Role |
|---|---|
| `rpi1` | TBD |
| `rpi2` | TBD |
| `rpi3` | TBD |

Ideas: network scanner (nmap/Nessus), Pi-hole DNS sinkhole, temperature/environment sensor, build agent.

## Device Naming Convention

```
<type>-<descriptor>
e.g. rpi1, rpi2, proxmox, xps16, mbp
```

Hostnames should be set in `/etc/hostname` and registered in the router's DHCP static leases for consistent DNS resolution.

## Adding a New Device

1. Note MAC address
2. Assign to appropriate VLAN (Lab / Trusted / IoT)
3. Create DHCP reservation on router if static IP needed
4. Add to this table
5. Install node_exporter if it's a Linux device and should be monitored
