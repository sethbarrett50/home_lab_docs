# VLANs

## Design Philosophy

Three VLANs segment traffic by trust level and use case. IoT devices get the strictest isolation since they run unknown/research firmware. Trusted devices get full internet access through Mullvad VPN. Lab devices can communicate freely within the VLAN and have controlled outbound access.

## VLAN Definitions

### VLAN 10 — Lab

**Purpose:** Infrastructure and compute devices that stay in (or near) the lab.

| Property | Value |
|---|---|
| Subnet | 192.168.10.0/24 |
| Gateway | 192.168.10.1 |
| DNS | 192.168.10.1 (router) |
| Internet | Direct (no VPN) |
| Inter-VLAN | → Trusted: blocked. → IoT: blocked. |

**Devices:** Proxmox node, Raspberry Pis, HP laptop (Debian/XFCE), Acer Aspire (when present)

---

### VLAN 20 — Trusted

**Purpose:** Personal devices — phones, laptops, daily drivers.

| Property | Value |
|---|---|
| Subnet | 192.168.20.0/24 |
| Gateway | 192.168.20.1 |
| DNS | 192.168.20.1 (router) |
| Internet | **Routed through Mullvad VPN** |
| Inter-VLAN | → Lab: blocked by default (allow specific services as needed). → IoT: blocked. |

**Devices:** MacBook M1 Pro, Dell XPS 16, Pixel 6, iPhone 7

> All outbound traffic from VLAN 20 exits via Mullvad. If the VPN tunnel drops, implement a **kill switch** so traffic doesn't fall back to plain internet.

---

### VLAN 30 — IoT

**Purpose:** Research IoT devices with untrusted/experimental firmware.

| Property | Value |
|---|---|
| Subnet | 192.168.30.0/24 |
| Gateway | 192.168.30.1 |
| DNS | 192.168.30.1 (router) or dedicated resolver |
| Internet | Restricted (allow only what's needed) |
| Inter-VLAN | Fully isolated — no access to Lab or Trusted. |

**Devices:** Research IoT hardware, Samsung phone (for IoT testing), TP-Link OpenWrt AP

> IoT devices connect wirelessly to the OpenWrt AP on a dedicated SSID. This AP uplinks to the switch on a VLAN 30 access port.

---

## Inter-VLAN Traffic Policy

```mermaid
flowchart LR
    L10[VLAN 10\nLab]
    L20[VLAN 20\nTrusted]
    L30[VLAN 30\nIoT]
    WAN[🌐 Internet]
    VPN[Mullvad VPN]

    L10 -->|Direct| WAN
    L20 -->|Tunneled| VPN --> WAN
    L30 -->|Restricted| WAN

    L10 -. blocked .- L20
    L10 -. blocked .- L30
    L20 -. blocked .- L30
    L20 -.->|"selective allow\n(e.g. Proxmox UI)"| L10
```

| Source | Destination | Policy |
|---|---|---|
| Lab | Trusted | ❌ Blocked |
| Lab | IoT | ❌ Blocked |
| Trusted | Lab | ⚠️ Selective (e.g. allow :8006 for Proxmox) |
| Trusted | IoT | ❌ Blocked |
| IoT | Lab | ❌ Blocked |
| IoT | Trusted | ❌ Blocked |
| Any | Internet | See per-VLAN policy above |

## Rollout Plan (Phased)

Earlier attempt at doing all VLANs in one pass on the Flint 2 failed at the
switch/router VLAN tagging step. Flint 2 runs **stock OpenWrt** (not GL.iNet's
own firmware), which uses DSA + bridge-vlan-filtering rather than classic
swconfig — tagging must be done via `br-lan` VLAN filtering + per-port
tagged/untagged bridge-vlan members, not per-interface `.VLANID` subinterfaces.
Rolling out incrementally to isolate failures to one layer at a time:

- [x] **Phase 1** — Flint 2 as plain main router (flat LAN, no VLANs). Replaces
      TP-Link as the WAN-facing device. Confirms WAN/NAT/DHCP works before any
      switch complexity is introduced.
      Notes: TL-SG108E needed a factory reset (leftover VLAN config from the
      earlier failed attempt was blocking L2 forwarding entirely — 802.1Q mode
      is currently `Disable`). Proxmox is reachable via static `192.168.1.197`
      (falls inside the `.100`–`.249` DHCP pool — flag for exclusion/reservation
      later). Acer/HP/Dell-mini debian boxes skipped for now (no network
      config done on them yet, not blocking).
- [ ] **Phase 2** — Add VLAN 30 (IoT) only. Enable bridge-vlan-filtering on
      `br-lan`, tag the 2.5G LAN uplink port for VLAN 30, configure one switch
      access port for VLAN 30, repurpose the old TP-Link as a dedicated IoT AP
      on that port. This is the highest-priority isolation goal.
- [ ] **Phase 3** — Add VLAN 10 (Lab) and VLAN 20 (Trusted), full 802.1Q trunk
      on switch port 1, per-VLAN SSIDs, firewall zones per
      [firewall.md](firewall.md), Mullvad WireGuard for VLAN 20 + kill switch.

## TODO / Implementation Notes

- [ ] Configure 802.1Q VLAN tagging on TL-SG108E
- [ ] Create VLAN interfaces on GL.iNet Flint 2 (stock OpenWrt — DSA bridge-vlan-filtering via LuCI or UCI)
- [ ] Create separate SSIDs per VLAN on Flint 2 WiFi
- [ ] Configure DHCP server per VLAN on router
- [ ] Set up Mullvad WireGuard interface on router, policy-route VLAN 20 traffic through it
- [ ] Configure kill switch (nftables/iptables) for Mullvad on VLAN 20
- [ ] Set up OpenWrt IoT AP with VLAN 30 SSID, trunk to switch
