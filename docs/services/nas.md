# NAS & Storage — CT 105

**Status (2026-10-25):** Debian 12 LXC CT 105, `nas.home.arpa` / `192.168.10.170`, in VLAN 10 on Proxmox. qBittorrent-nox 4.5.2 and selective Mullvad egress are deployed and tested. Samba/NFS, a NAS management UI, and redundant storage are not claimed deployed.

## Storage and shares

The container root is on Proxmox `local-lvm`. PVE host `/mnt/pve/hdd-1tb/nas-share` is bind-mounted as `/mnt/nas-share` (`mp0`) in CT 105. This data mount is **not included** in ordinary LXC guest backups; preserve host-volume backups separately. Other PVE storage includes the 500 GB WD Blue `hdd-500gb` and ~906 GiB Silicon Power `ssd-1tb` LVM-thin pool. These are not a mirrored NAS array.

## qBittorrent and HTTPS

- qBittorrent-nox **4.5.2** runs directly inside CT 105. Its Web UI is exposed via Caddy as `https://torrent.home.arpa` through the router DNS and the `certs-01` reverse proxy. Auth remains required; do not publish credentials here.
- qBittorrent downloads and seeding were observed to work over selective Mullvad routing. The deployment **does not** rely on binding qBittorrent to a hypothetical `wg0` device inside CT 105; tunnel and PBR live on Flint 2.
- Container autostart and VPN-availability guards/dependencies were configured and tested during setup, but their exact unit names and definitions were not included in this documentation handoff. Capture their live definitions before adding a reproducible unit-file listing; do not invent them.

## Mullvad egress and fail-closed policy

Router PBR rules `pbr.nas_local` (ignore internal destinations) and `pbr.nas_mullvad` (source `192.168.10.170/32` via `wg_mullvad`) are always enabled, regardless of the Trusted VLAN toggle. fw4 permits NAS→Mullvad and a separate `/etc/nftables.d/30-nas-mullvad-guard.nft` hooked forward chain blocks forwarded NAS traffic out university WAN `eth1`. The NAS uses local dnsmasq with public requests through Mullvad DNS `10.64.0.1` and `home.arpa` forwarded to the Flint 2 router; an outbound classic DNS guard prevents normal upstream port-53 fallback. See [Mullvad](../networking/mullvad.md).

Controlled loss of Mullvad was tested without WAN fallback; reconnection and downloads/seeding succeeded. Router reboot persistence, more extensive DNS bypass tests, and startup ordering remain open.

## Operational verification

**On Proxmox:**

```bash
pct status 105
pct config 105 | grep -E '^(net0|mp0|onboot):'
pct exec 105 -- systemctl --failed
```

**On Flint 2:**

```sh
uci show pbr.nas_local
uci show pbr.nas_mullvad
nft list chain inet fw4 nas_mullvad_guard
/etc/init.d/pbr status | grep 'NAS Internet via Mullvad'
```

**From an authorized client:** open `https://torrent.home.arpa` and confirm the qBittorrent Web UI is reachable and authenticated. Do not expose the Web UI directly on WAN.

## Remaining work

- [x] CT 105 bind-mounted storage and qBittorrent-nox operational.
- [x] Router-side Mullvad policy, DNS split and tested WAN kill switch.
- [ ] Confirm router-reboot/startup ordering, CT autostart dependencies and recovery.
- [ ] Capture exact qBittorrent service and guard unit files for reproducibility.
- [ ] Deploy SMB/NFS/file-sharing only after choosing a NAS access model.
- [ ] Implement off-host backups for bind-mounted data.
- [ ] Decide on redundant disks / recovery strategy; current storage is not redundant.
