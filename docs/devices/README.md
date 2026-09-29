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

| Device | VLAN | Notes |
|---|---|---|
| Phone (tested) | 20 | Confirmed working on `dfair_lab` SSID |
| MacBook Pro | 30 (should be 20) | Still on old `OpenWrt` SSID (now the IoT AP) — needs reconnecting to `dfair_lab` |
| Everything else from the original PhD-lab device list (XPS16, Pixel 6, iPhone 7, Samsung) | — | Not yet reconnected post-move; re-add here as they come online |

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
