# Lenovo dedicated GitHub Actions runners

**Deployed:** 2026-11-03. **Host:** physical Lenovo ThinkBook 15 G4 IAP (`lenovo-lap`), Debian 13.7, Lab VLAN 10, switch port 7, `192.168.10.193` / `lenovo-lap.home.arpa`. This deployment is **not** a Proxmox VM and does not replace the existing `gha-general-01` runner VM.

## Inventory

| Purpose | GitHub repository served | Runner source checkout | Container / image | Workspace | Runner label |
|---|---|---|---|---|---|
| Backend | `Kart-Chaser/kc-backend-core` (private) | `/opt/gha-runners/kc-backend-runner` | `kc-backend-runner-local` / `kc-backend-runner:dev` | `/workspace-backend` | `kc-backend-runner` |
| Infrastructure | `Kart-Chaser/kartchaser-infrastructure` (private) | `/opt/gha-runners/kc-infra-runner` | `kc-infra-runner-local` / `kc-infra-runner:dev` | `/workspace-infra` | `kc-infra-runner` |

Runner source: `kc-backend-runner` (private) and `kc-infra-runner` (private). Both images built and passed `make r.preflight` and `make smoke` on 2026-11-02. The runners registered successfully and executed real CI jobs on 2026-11-03. Workspaces are host bind mounts at the **same absolute path** in the container, owned by UID/GID `1001:1001`, to support Docker-outside-of-Docker bind mounts. The host Docker group GID was `989` during image builds; the Makefiles discover it dynamically.

The infrastructure repository's `RUNNER_LABELS` GitHub Actions variable was updated to `["self-hosted","kc-infra-runner"]`. Backend migration was tested under PR #233; check the current merge/CI state before claiming it fully migrated. Do not change workflows with hard-coded labels without reviewing them.

## Networking and SSH

- Ethernet: `enp0s31f6`, Intel I219-V (`e1000e`), MAC `e4:a8:df:dd:bd:29`; switch TL-SG108E **port 7**, VLAN 10 **untagged**, PVID **10**, VLAN 1 **not member**.
- `ifupdown`: `/etc/network/interfaces` includes `/etc/network/interfaces.d/*`; `/etc/network/interfaces.d/enp0s31f6` contains `auto enp0s31f6` and `iface enp0s31f6 inet dhcp`. `dhcpcd-base` provides DHCP. Wired DHCP and SSH successfully returned after reboot.
- Router: Flint 2 gateway `192.168.10.1`. `lenovo-lap.home.arpa` resolved to `192.168.10.193` and SSH connected from the XPS at `192.168.20.173`.
- Flint 2 firewall UCI section `firewall.allow_xps_to_lenovo_ssh`: `src=trusted`, `src_ip=192.168.20.173`, `dest=lab`, `dest_ip=192.168.10.193`, `proto=tcp`, `dest_port=22`, `family=ipv4`, `target=ACCEPT`. `fw4 check` and reload passed. This rule does **not** grant all Trusted clients Lab access.
- **Open verification:** DHCP host reservation for MAC `e4:a8:df:dd:bd:29` / `192.168.10.193` was not independently shown in router output. Verify it before relying on this fixed-IP firewall rule long term.

```bash
ssh pooltab@lenovo-lap.home.arpa
ip -4 addr show enp0s31f6
ip -4 route
systemctl is-active networking ssh docker containerd
```

## Systemd and Docker startup

Docker Engine 29.9.2 and `containerd` are enabled. Both containers use Docker `--restart unless-stopped`. The services are:

- `gha-runner@kc-backend-runner-local.service`
- `gha-runner@kc-infra-runner-local.service`

Both instances are **enabled** and were observed **active** on 2026-11-03. The shared template lives at `/etc/systemd/system/gha-runner@.service`; the executable helper is `/usr/local/libexec/gha-runner-start`.

This is a `Type=oneshot`, `RemainAfterExit=yes` service running as host user `pooltab` with supplementary Docker group. `ExecStart` checks for an existing container and runs `docker start` only when stopped; it does **not** rebuild, replace, or re-register containers. `ExecStop` calls `docker stop -t 120`. An `active (exited)` systemd status is expected and does not itself prove the container or GitHub runner is online. Docker independently handles container process restarts.

```bash
systemctl is-enabled gha-runner@kc-backend-runner-local.service gha-runner@kc-infra-runner-local.service
systemctl status gha-runner@kc-backend-runner-local.service gha-runner@kc-infra-runner-local.service --no-pager
docker ps --filter label=kc.runner
docker inspect kc-backend-runner-local kc-infra-runner-local --format '{{.Name}}: {{.State.Status}}, restart={{.HostConfig.RestartPolicy.Name}}'
docker logs --tail 60 kc-backend-runner-local
docker logs --tail 60 kc-infra-runner-local
```

Query live registration as `pooltab` with GitHub CLI authenticated for both repositories:

```bash
gh api repos/Kart-Chaser/kc-backend-core/actions/runners --jq '.runners[] | select(.name=="kc-backend-runner-local") | {name,status,busy,labels:[.labels[].name]}'
gh api repos/Kart-Chaser/kartchaser-infrastructure/actions/runners --jq '.runners[] | select(.name=="kc-infra-runner-local") | {name,status,busy,labels:[.labels[].name]}'
gh api repos/Kart-Chaser/kartchaser-infrastructure/actions/variables/RUNNER_LABELS --jq '.value'
```

## Safe update procedure

**Never run `make r.up`, stop, restart, or recreate containers while jobs are running.** `make r.up` rebuilds, obtains a new repository registration token and forcibly replaces its named container. Runner labels can immediately receive new jobs; coordinate an assignment pause/drain and verify `busy: false` before maintenance. The systemd service itself is not job-aware.

For the runner being maintained, after draining jobs:

```bash
# BACKEND EXAMPLE ONLY. Never run these while jobs are executing.
sudo systemctl stop gha-runner@kc-backend-runner-local.service
git -C /opt/gha-runners/kc-backend-runner status --short
git -C /opt/gha-runners/kc-backend-runner pull --ff-only origin main
make -C /opt/gha-runners/kc-backend-runner r.preflight
make -C /opt/gha-runners/kc-backend-runner r.up
sudo systemctl start gha-runner@kc-backend-runner-local.service
docker logs --tail 40 kc-backend-runner-local
```

Repeat separately for infrastructure with its checkout, container and service names. Re-verify GitHub registration after updating; do not run Docker-wide pruning commands on this host. GitHub CLI registration requires admin permission on each **served** repository. Do not expose registration tokens or GitHub CLI credential files.

**Security:** The runners mount `/var/run/docker.sock` and use host networking. Docker socket access effectively grants host-level power to executing workflows, even though registration is repository-scoped. Restrict workflow permissions, contributors and secrets appropriately.

## Operational status and follow-ups

- Backend jobs observed as successful on the Lenovo include SDK Package, Label Pull Request and Quality Suite; Container Integration and Workflow Narrator failed during PR #233 testing and were being investigated by another agent. Do not assume they remain failing or have been resolved without checking.
- Backend runner binary version `2.338.1` attempted to self-update to `2.338.2` and failed with `Could not find a part of the path '/workspace-backend/_update/runner1.tar.gz'`. The workspace cleanup hooks may have contributed, but the cause is **unconfirmed**. Investigate/update the runner repository in a PR before changing live deployment.
- Infrastructure runner auto-updated successfully to `2.338.2` and executed Label Pull Request, Trivy misconfiguration scan and Terraform Detect successfully; additional jobs were running at the last captured log. The operator later reported both runners working as expected.
- Add monitoring to the existing `monitor-01` Prometheus/Grafana stack (node-exporter, container metrics, and runner-specific job/online status). These monitors have **not** been shown installed on Lenovo.
- Confirm DHCP reservation, verify lid-closed operation on this host if necessary, and consider a maintenance procedure that drains jobs before Docker/systemd restarts.
