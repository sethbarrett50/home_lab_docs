# Devices

Full inventory of all devices in the homelab ecosystem.

## Infrastructure (Rack)

Superseded the original PhD-lab RPi-based plan — actual hardware post-move is
Proxmox host + LXC/VM services + 3 debian boxes not yet networked.

| Hostname | Device | OS/Firmware | VLAN | IP | Notes |
|---|---|---|---|---|---|
| `flint2` | GL.iNet GL-MT6000 Flint 2 | stock OpenWrt 23.05.5 (not GL.iNet fw) | mgmt (all, trunk) | 192.168.1.1 | Edge router, DHCP filtering + `br-lan.X` per VLAN |
| `switch` | TP-Link TL-SG108E | — | mgmt | 192.168.1.160 | L2 only, DHCP (not static) |
| `proxmox` (pve) | Dell Precision 3620 | Proxmox VE | 10 | 192.168.10.10 | Static, host for VMs/LXCs below |
| `nas` (LXC 105) | — | — | 10 | 192.168.10.170 | DHCP (not pinned) |
| `gha-general-01` (VM 101) | — | Debian Trixie | 10 | 192.168.10.189 | DHCP host reservation (pinned to MAC) |
| `monitor-01` (VM 102) | — | — | 10 | 192.168.10.158 | Prometheus `:3001` + Grafana `:3000`. DHCP (not pinned) |
| `iot-ap` (old TP-Link) | TP-Link (unknown model) | OpenWrt 15.05.1 "Chaos Calmer" | 30 | 192.168.30.2 | Dumb AP, SSID `OpenWrt`, own DHCP/WAN disabled |
| Dell Micro / Acer / HP laptop | — | Debian, base install only | 10 (switch ports 3-5) | — | Switch-side migrated to VLAN 10; OS networking not yet configured on any of the three |

## Personal Devices (Mobile / Off-rack)

WiFi: SSID `dfair_lab` (both 2.4GHz/`radio0` and 5GHz/`radio1`), bound to
VLAN 20 (Trusted), on the Flint 2 itself.

| Device | VLAN | Notes |
|---|---|---|
| Phone (tested) | 20 | Confirmed working on `dfair_lab` |
| MacBook Pro | 20 | Reconnected from the old IoT `OpenWrt` SSID to `dfair_lab` |
| Everything else from the original PhD-lab device list (XPS16, Pixel 6, iPhone 7, Samsung) | — | Not yet reconnected post-move; re-add here as they come online |

## IoT Devices (VLAN 30)

All static DHCP host reservations on the Flint 2 (`/etc/config/dhcp`), pinned
to current MAC/IP so they don't drift. Bridged in via the old TP-Link AP
(`iot-ap`, SSID `OpenWrt`) on switch port 6.

| Name | MAC | IP | Notes |
|---|---|---|---|
| Galaxy-A71-5G | BA:AD:F9:BE:0C:BB | 192.168.30.117 | |
| RingDoorbell-b1 | 90:48:6C:04:72:B1 | 192.168.30.151 | |
| ESP_512EA9 | 70:03:9F:51:2E:A9 | 192.168.30.214 | Dev board |
| HS105 | 00:5F:67:FB:83:A4 | 192.168.30.216 | Kasa smart plug |
| Nest-Cam-indoor | 20:1F:3B:21:93:74 | 192.168.30.110 | |
| Google-Home-Mini | 00:F6:20:4E:22:FB | 192.168.30.203 | |
| `iot-unknown-1` | A8:E6:21:3E:26:01 | 192.168.30.142 | Unidentified — rename once physically confirmed |
| `iot-unknown-2` | 72:28:BA:5F:4E:6C | 192.168.30.229 | Unidentified — locally-administered MAC (likely a phone/tablet with MAC randomization) |
| `iot-unknown-3` | 30:4A:26:2B:BA:87 | 192.168.30.220 | Unidentified |
| `iot-unknown-4` | CA:70:A3:B6:C7:FB | 192.168.30.237 | Unidentified |

## Cross-VLAN Firewall Rules (Lab access from mgmt/Trusted)

Scoped, least-privilege — only these host:port combos are reachable from
`lan`/`trusted` into VLAN 10, everything else in Lab stays unreachable from
outside it:

| Dest host | Port(s) | From |
|---|---|---|
| proxmox (192.168.10.10) | 8006, 22 | lan, trusted |
| monitor-01 (192.168.10.158) | 3000, 3001 | lan, trusted |
| gha-general-01 (192.168.10.189) | 22 | lan, trusted |

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
