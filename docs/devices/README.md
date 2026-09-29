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
(`iot-ap`, SSID `OpenWrt`) on switch port 6. Identified via a mix of MAC
vendor lookup (`api.macvendors.com`) and ground-truth checks in each device's
companion app — vendor lookup alone caused one mislabel (see note below), so
app-based confirmation is the more reliable method going forward.

| Name | MAC | IP | Notes |
|---|---|---|---|
| Galaxy-A71-5G | BA:AD:F9:BE:0C:BB | 192.168.30.117 | Test phone |
| RingDoorbell-b1 | 90:48:6C:04:72:B1 | 192.168.30.151 | Ring Video Doorbell |
| HS105 | 00:5F:67:FB:83:A4 | 192.168.30.216 | Kasa Smart Plug |
| Nest-Cam-indoor | 20:1F:3B:21:93:74 | 192.168.30.110 | Google Home Cam |
| **Amazon-Echo-Dot** | A8:E6:21:3E:26:01 | 192.168.30.142 | Amazon Echo Dot (5th Gen) — confirmed via Alexa app, doesn't respond to ICMP even when online (expected Echo behavior) |
| Roborock-K2-Vacuum | B0:4A:39:55:B1:76 | 192.168.30.181 | Self-identified via DHCP hostname `roborock-vacuum-a34` |
| OKP-K2-Vacuum | 10:D5:61:A4:B8:92 | 192.168.30.188 | Inferred by elimination (plugged in alongside the Roborock, only 2 new leases appeared) |
| `amazon-unknown-1` | 00:F6:20:4E:22:FB | 192.168.30.203 | **Was mislabeled `Google-Home-Mini`** — vendor lookup said Amazon, not Google, and it's confirmed NOT the Echo Dot (different MAC, responds to ping unlike the real Echo Dot). Not in the Alexa app either. Still unidentified — worth physically tracking down |
| `iot-unknown-2` | 72:28:BA:5F:4E:6C | 192.168.30.229 | Unidentified — locally-administered/randomized MAC, vendor lookup impossible |
| `iot-unknown-3` | 30:4A:26:2B:BA:87 | 192.168.30.220 | Unidentified — vendor: Shenzhen Trolink Technology Co. (generic OEM). Candidates from the owner's device list: LongPlus baby monitor, NiteBird smart bulb, Philips Hue Hub |
| `iot-unknown-4` | CA:70:A3:B6:C7:FB | 192.168.30.237 | Unidentified — locally-administered/randomized MAC. Present in the original TP-Link lease dump from before this migration too — has been on the network unidentified for a while |
| **BLOCKED**: was `ESP_512EA9` | 70:03:9F:51:2E:A9 | 192.168.30.214 | Not on the owner's device list — unrecognized ESP32/8266 dev board. Firewall-blocked (MAC-based DROP, both input and forward-to-wan) rather than just isolated — confirmed actively dropping traffic via `nft` counters (35 packets/7560 bytes at time of blocking) |

**Not yet connected** (known from the owner's device list / companion apps, no current lease):
Google Nest Mini (MAC known: `20:1F:3B:78:FA:4A`, from Google Home app), Philips Hue Hub, LongPlus baby monitor, NiteBird smart bulb.

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
