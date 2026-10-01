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

**Devices:** Proxmox node, Raspberry Pis, dell-mini, acer-lap, HP laptop (Debian/XFCE, when present)

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
- [x] **Phase 2a** — VLAN 30 (IoT) interface live on the Flint 2. Enabled
      `vlan_filtering` on `br-lan`, tagged `lan1` (2.5G uplink) for VLAN 1 + 30,
      left `lan2`-`lan5` untagged/PVID in VLAN 1. `br-lan.1` (192.168.1.1) and
      `br-lan.30` (192.168.30.1) both up, SSH survived the reload.
      **Root cause of every prior lockout on this exact router (GL-MT6000):**
      once `vlan_filtering` is enabled, the `lan` interface must bind to the
      VLAN 1 subinterface (`option device 'br-lan.1'`), not the raw bridge
      device (`br-lan`). Binding to the raw bridge while filtering is active
      is what caused the "changes apply, device goes unreachable" failure that
      led to repeated reflashes in the earlier attempt — confirmed as a known
      GL-MT6000-specific gotcha via the OpenWrt forum, not user error.
      (See: forum.openwrt.org/t/vlan-config-problems-on-gl-inet-gl-mt6000/200882
      and forum.openwrt.org/t/gl-inet-flint-2-gl-mt6000-vlan-best-practices-on-openwrt-snapshot/251673)
- [x] **Phase 2b** — DHCP server on `iot` interface (`.100`-`.249`, 12h lease),
      firewall zone (`input`/`forward` DROP by default, explicit allow only for
      DHCP/DNS-to-router and forwarding to `wan`). Switch VLAN 30 added via
      native-VLAN-1 pattern (see above) — zero disruption to existing traffic.
      Switch port 6 is now VLAN 30 untagged/PVID 30, ready for the IoT AP.
      Old TP-Link (15.05.1 "Chaos Calmer", ar71xx — its own switch/VLAN config
      untouched, only became a dumb AP) reconfigured: LAN static
      `192.168.30.2`, own DHCP server disabled (`dhcp.lan.ignore=1`), WAN
      disabled (`proto=none`), wired into switch port 6. Verified end-to-end:
      phone joined its `OpenWrt` SSID, got a `192.168.30.x` lease from the
      Flint 2, has internet access.
      **Phase 2 complete.**
- [x] **Phase 3a** — VLAN 10 (Lab) and VLAN 20 (Trusted) router-side infra
      live: `br-lan.10` (192.168.10.1), `br-lan.20` (192.168.20.1), DHCP
      scopes (`.100`-`.200`), firewall zones (ACCEPT/ACCEPT/ACCEPT, forward
      to `wan` only, no cross-zone rules yet). Hostname set to `flint2` (was
      causing tab mix-ups with the identically-prompted TP-Link). No devices
      migrated yet, no switch access ports assigned — infra only, per the
      decision to stand up VLANs before moving working devices.
- [x] **Phase 3b** — Switch: VLAN 10 + 20 added to 802.1Q table, tagged port 1
      only (trunk), no access ports assigned. Verified zero disruption — VLAN
      1 and VLAN 30 traffic unaffected.
- [x] **Phase 3c** — Device migration done for core infra. `dfair_lab` SSID
      live on both radios, bound to VLAN 20. Idle debian boxes (Dell
      Micro/Acer/HP) switch-migrated to VLAN 10 (no OS network config on them
      yet — not blocking). Proxmox host + its VM/LXC guests migrated to VLAN
      10 — **key lesson**: the Proxmox host's own `vmbr0` IP is independent of
      each VM/LXC's *guest-level* network config; migrating the host doesn't
      migrate the guests. LXCs on `ip=dhcp` (nas) picked up new leases on
      reboot automatically; VMs (gha-general-01, monitor-01) needed the same
      via their own guest OS, reachable only through the Proxmox noVNC console
      once the host itself was unreachable over the network.
      Scoped `lan`/`trusted` → Lab firewall rules added per-host as needed
      (proxmox :8006/:22, monitor-01 :3000/:3001 for Grafana/Prometheus,
      gha-general-01 :22) — see [devices/README.md](../devices/README.md) for
      the full table. gha-general-01 given a static DHCP reservation (was
      floating DHCP, now pinned to its MAC).
      MacBook Pro reconnected to `dfair_lab` (VLAN 20), confirmed. All 10
      current IoT devices given static DHCP host reservations (MAC-pinned) so
      addresses don't drift — see [devices/README.md](../devices/README.md).
      **Remaining:** Mullvad WireGuard + kill switch for VLAN 20 — separate
      follow-up task, not started.
- [ ] **Phase 3d** — OS-level networking for the 3 idle debian boxes (Dell
      Micro/Acer/HP), tracked in [issue #19](https://github.com/sethbarrett50/home_lab_docs/issues/19).
      `dell-mini` and `acer-lap` done: `systemd-networkd` (chosen for a config
      method that works the same whether a box is headless or running a
      desktop env like HP's XFCE, instead of per-box ifupdown/NetworkManager),
      DHCP host reservations pinned to `192.168.10.117`/`.199`, `lan`/`trusted`
      → `:22` firewall rules added. `acer-lap` is run closed-lid (rack-mounted
      laptop) — needed `HandleLidSwitch=ignore` (+ `ExternalPower`/`Docked`
      variants) in `/etc/systemd/logind.conf` to stop it suspending on lid
      close; HP will need the same since it's also a laptop. HP not yet
      started.

## TODO / Implementation Notes

- [x] Configure 802.1Q VLAN tagging on TL-SG108E
- [x] Create VLAN interfaces on GL.iNet Flint 2 (stock OpenWrt — DSA bridge-vlan-filtering via UCI, not LuCI — see Phase 2a note on the GL-MT6000 lockout bug)
- [x] Create SSID for VLAN 20 on Flint 2 WiFi (`dfair_lab`, both radios). VLAN 30 uses the old TP-Link's own AP instead of a Flint 2 radio SSID; VLAN 10 is wired-only per design, no SSID needed.
- [x] Configure DHCP server per VLAN on router (10, 20, 30 all live; static host reservations for known devices)
- [ ] Set up Mullvad WireGuard interface on router, policy-route VLAN 20 traffic through it
- [ ] Configure kill switch (nftables/iptables) for Mullvad on VLAN 20
- [x] Set up OpenWrt IoT AP with VLAN 30 (simplified from the original "SSID + trunk" plan to a dumb-AP-on-a-single-access-port — no trunking needed on the AP itself since it only ever serves one VLAN)
