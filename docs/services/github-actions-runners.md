# Self-hosted GitHub Actions runners

## DFAIR production ARC deployment (2026-11-27)

This section supersedes the historical Docker deployment below for DFAIR.
The production runner is an organization-level Actions Runner Controller
(ARC) scale set on the existing Debian 13 CI VM, not the Proxmox host.
KC-Timing remains a separate Docker runner; do not retire it.

| Property | Production configuration |
|---|---|
| VM | `gha-general-01`, Proxmox VM 101, 6 vCPU, 18 GiB RAM |
| Kubernetes | Single-node K3s v1.37.2+k3s1, containerd |
| Storage | Dedicated 200 GiB SSD, ext4 at `/var/lib/rancher/k3s` |
| ARC controller | Chart 0.15.1, namespace `dfair-arc-system` |
| Scale set | `dfair-gha-runner-arc`, namespace `dfair-arc-runners` |
| Scaling | Minimum 0, maximum 3 ephemeral runners |
| Per-runner CPU | Request 1, limit 2 |
| Per-runner memory | Request 3 GiB, limit 4 GiB |
| Per-runner ephemeral storage | Request 15 GiB, limit 40 GiB |
| Image | Digest-pinned research image with LaTeX and Python tooling |
| Authentication | GitHub App and separate registry pull secret |

### Node setup and recovery

VM 108 was gracefully shut down (already configured not to start at boot).
VM 101 was shut down, its configuration backed up, and resized from 4 vCPU
and 12 GiB to 6 vCPU and 18 GiB (ballooning disabled). Its original 100 GiB
root disk was retained. The added SSD is mounted by UUID with
`defaults,noatime`; K3s has a systemd mount dependency and mount-point
condition to avoid writing to the root filesystem when storage is absent.
The single-node control plane reserves 1 CPU and 3 GiB for system/Kubernetes
components. After reboot the node reported 5 allocatable CPUs and
15,207,888 KiB allocatable memory; API readiness and metrics passed.

K3s uses separate pod/service networks, secrets encryption, and containerd.
Docker remains installed for KC-Timing and monitoring. The guest swap
partition was reactivated on reboot despite its commented fstab entry;
swap was disabled again and `dev-sda3.swap` masked. Persistence is not
yet verified. Preserve the swap partition and investigate auto-discovery
if it reappears.

### Deployment operations

Use the existing authenticated kubeconfig and Helm context. Never commit
GitHub App keys, tokens, kubeconfigs, or secret manifests. Keep the exact
image digest and credentials in the authorized deployment configuration.

```bash
kubectl get nodes -o wide
kubectl get --raw='/readyz?verbose'
findmnt /var/lib/rancher/k3s
kubectl get autoscalingrunnersets -A
kubectl get pods -A
kubectl top nodes
```

To change capacity during an idle maintenance window, explicitly supply
both numeric values (reusing only one caused a Helm float/int template
comparison failure):

```bash
helm upgrade dfair-gha-runner-arc \
    oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set \
    --version 0.15.1 \
    --namespace dfair-arc-runners \
    --kube-context dfair-pilot \
    --reuse-values \
    --set minRunners=0 \
    --set maxRunners=3 \
    --wait --timeout 5m
```

Revision 2 deployed successfully. Three ephemeral runner objects were
observed concurrently (one running and two pending at that snapshot).
The operator reports the subsequent workload test worked well; peak
three-job memory and sustained throughput have not been formally recorded.
Keep concurrency at three until heavier workloads are measured.

### Repository migration and performance

The four repository migration PRs merged into dev and their post-merge
CI passed. CAPEX, XSecIoT and the LaTeX proposal repository were also
promoted to main. SOC Email Collab's main promotion remained a draft
at the last inspection; its legacy workflow references must be reconciled.
All-branch test trigger changes were submitted for CAPEX, XSecIoT and SOC;
merge and main promotion are not established by opening a PR.

Private trusted workflows use `runs-on: dfair-gha-runner-arc`. Public
repositories retain GitHub-hosted fallback; do not grant untrusted PRs
access to the homelab. A YAML condition alone is not an authorization
boundary. Old feature branches need to incorporate updated workflow files.

A controlled XSecIoT CPU-only PyTorch benchmark passed 242 tests with
9 skips, matching the CUDA-wheel baseline. Cold dependency setup fell
from 120.78 s to 19.41 s and environment size from 6.1 G to 1.7 G.
This is a single paired benchmark, not a production CPU-only rollout
or evidence of GPU equivalence. Retain full LaTeX dependencies and
reuse immutable image layers.

### Retire the legacy DFAIR container

The legacy service used a foreground helper, `Restart=always` and a
15-second restart delay. Stopping Docker alone caused it to recreate the
container and register again. The operator disabled and stopped
`gha-runner-dfair.service` and verified that the container was absent.
Masking initially failed because the custom unit occupied the mask path.
The operator then archived the unit under `/root/retired-services/`,
masked it, and verified `masked` / `inactive`. The recreated registration
(ID 133) was verified offline and idle, then deleted. Do not delete
ephemeral runners.

The nightly update-check unit and timer remain enabled. The installed
checker was confirmed fetch-only, with KC and DFAIR entries (not KC-Timing).
The operator backed it up, removed the DFAIR entry and passed `bash -n`.
The versioned checker also includes KC-Timing; deploying that version and
validating its credentials remain optional follow-up steps.
Keep KC-Timing, Docker, job exporter, Alloy, cAdvisor and node-exporter.
The old Docker image and source checkout can be retained for rollback;
do not start the legacy service routinely.

The existing Docker log exporter does not observe ARC pods. Use
`kubectl get ephemeralrunners -A`, `kubectl top pods -n dfair-arc-runners`
and GitHub Actions job results for ARC. Dashboard/alert changes to reflect
the new architecture remain a separate unverified deployment task.

## Dedicated physical Lenovo host (2026-11-03)

`lenovo-lap` is a **physical Lenovo ThinkBook 15 G4 IAP** running Debian 13.7 on
Lab VLAN 10 at `192.168.10.193` (`lenovo-lap.home.arpa`). It runs two
**repository-scoped** runners, each in its own Docker container. This host is
separate from `gha-general-01`, which remains in service for other workloads.

| GitHub repository served | Runner source | Container / image | Workspace | systemd instance |
|---|---|---|---|---|
| `Kart-Chaser/kc-backend-core` | `kc-backend-runner` (private) | `kc-backend-runner-local` / `kc-backend-runner:dev` | `/workspace-backend` | `gha-runner@kc-backend-runner-local.service` |
| `Kart-Chaser/kartchaser-infrastructure` | `kc-infra-runner` (private) | `kc-infra-runner-local` / `kc-infra-runner:dev` | `/workspace-infra` | `gha-runner@kc-infra-runner-local.service` |

Both runners were registered online and observed executing real GitHub Actions jobs.
The infrastructure repository's `RUNNER_LABELS` variable was changed to
`["self-hosted","kc-infra-runner"]`; workflows with hard-coded labels are
not automatically migrated. The backend runner successfully executed several
jobs during PR #233 validation; CI failures were being investigated separately.
The systemd instances were confirmed `enabled` and `active`, with both Docker
containers `running` using `unless-stopped` restart policies.

Unlike the older VM runner services, the Lenovo's template service uses a
`Type=oneshot` helper that **starts only an existing container**, never
rebuilds or registers it. Explicit updates/re-registration use each checkout's
`make r.up` only during maintenance, after jobs are drained. Both containers
mount `/var/run/docker.sock`, granting workflows powerful control of the
physical host. See the [Lenovo CI host runbook](lenovo-github-runners.md).

## Legacy Docker deployment and inventory (historical)

The legacy self-hosted runners below operate as Docker containers on
**`gha-general-01`** (Debian 13, Proxmox VM 101, `192.168.10.189`, VLAN 10).
These are **not** installed on the Proxmox host. The repository-specific
Docker images are built on the VM and registered using GitHub CLI tokens.

| Runner | Private image repository | Local checkout | Container / image | systemd unit |
|---|---|---|---|---|
| KC | [KC-GHA-Runner](https://github.com/Kart-Chaser/KC-GHA-Runner) | `/opt/gha-runners/kc/KC-GHA-Runner` | `kc-gha-runner-local` / `kc-gha-runner:dev` | `gha-runner-kc.service` |
| DFAIR | [dfair_runner](https://github.com/DFAIR-LAB-Augusta/dfair_runner) | `/opt/gha-runners/dfair` | `dfair-gha-runner-local` / `dfair-gha-runner:dev` | `gha-runner-dfair.service` |
| KC-Timing (repo-scoped) | [KC-Timing-Runner](https://github.com/Kart-Chaser/KC-Timing-Runner) | `/opt/gha-runners/kc-timing/KC-Timing-Runner` | `kc-timing-runner-local` / `kc-timing-runner:dev` | `gha-runner-kc-timing.service` |

All three runner repositories use `main` for deployed source and `make build` for local
image builds. KC and KC-Timing use Docker **host networking** and a mounted Docker socket;
DFAIR uses Docker's default bridge network. KC-Timing uses a host-backed `/workspace-timing` mount (UID/GID 1001:1001), separate from KC's `/workspace` bind mount, so Docker-outside-of-Docker Compose bind sources resolve on the VM host. KC-Timing is registered specifically to `Kart-Chaser/KC-Timing` with the `kc-timing-runner,linux,x64` labels. KC image builds pass the host
Docker group GID. Treat runner access to Docker as privileged: untrusted
workflows may compromise the host VM. Restrict GitHub organization access,
runner groups, and workflow permissions appropriately.

**Retired:** PrivateLingua (PL) container/image and dedicated unit were
removed on 2026-10-22. The former `pl-gha-runner.service` alias is masked.
PL is excluded from update automation. Its remote GitHub runner-registration
removal was not independently verified; the source directory may remain on
disk. Do not run PL as part of normal maintenance.

## How services start

The original systemd services use `User=seth`, `Restart=always`, and a
foreground log follower. The shared `/usr/local/bin/gha-runner-start` helper
performs `make r.down`, `make r.up`, then `make r.log`. `r.up` depends on
`build` for **both** repositories, so a restart rebuilds the local image.

**KC has a host-only safety override.** Its upstream `r.down` target also
prunes unrelated stopped containers, networks, volumes, and PostgreSQL/Redis
service containers. Rather than edit the private repository Makefile, the
local override replaces `ExecStart` with a wrapper that calls only `make r.up`
and `make r.log`; its `ExecStop` removes only the named KC container. The
versioned examples are:

- [KC safe startup wrapper](runner-observability/gha-runner-kc-safe-start)
- [KC systemd drop-in](runner-observability/gha-runner-kc-override.conf)

Deployed paths on `gha-general-01`:

```text
/usr/local/bin/gha-runner-kc-safe-start
/etc/systemd/system/gha-runner-kc.service.d/override.conf
```

To check the *effective* config, not just the base unit:

```bash
sudo systemctl cat gha-runner-kc.service
sudo systemctl show gha-runner-kc.service -p ExecStart -p ExecStop
sudo systemctl status gha-runner-kc.service gha-runner-dfair.service gha-runner-kc-timing.service --no-pager
```

The KC override was installed and loaded on **2026-10-22**; KC was already
running the rebuilt image, so the new wrapper did **not** need an immediate
restart. It will apply at the next service start. KC's `r.up` still replaces
the named KC container and is disruptive; neither service is job-aware.
DFAIR retains the original helper because its `r.down` only removes its own
container.

## KC-Timing deployment (2026-10-27)

KC-Timing is deployed, enabled, and was confirmed **Online / Idle** in GitHub on 2026-10-27. The VM build, `make r.preflight`, and `make smoke` succeeded. The runner has its own `/workspace-timing` bind mount and `/var/run/docker.sock` mount. GitHub Actions *real-job execution* remains to be tested.

The deployed systemd unit is versioned as [gha-runner-kc-timing.service](runner-observability/gha-runner-kc-timing.service); copy to `/etc/systemd/system/gha-runner-kc-timing.service` when rebuilding the VM. It runs `make r.up` from `ExecStartPre` and follows `make r.log`, and uses a 45-second `docker stop` on shutdown. `make r.up` replaces the container, so only restart while idle and when no new jobs can be assigned. It reacquires a GitHub registration token using the `seth` account's GitHub CLI authentication; do not log or commit this token.

```bash
# On gha-general-01; the checkout already exists
cd /opt/gha-runners/kc-timing/KC-Timing-Runner
git status --short
git pull --ff-only origin main
make r.preflight
make smoke
# ONLY WHEN IDLE: sudo systemctl restart gha-runner-kc-timing.service
sudo systemctl status gha-runner-kc-timing.service --no-pager
sudo docker logs --tail 50 kc-timing-runner-local
sudo docker inspect kc-timing-runner-local --format '{{range .Mounts}}{{println .Source " -> " .Destination}}{{end}}'
```

Preflight/smoke test tooling and workspace writability; neither proves GitHub job execution. For a real job in `Kart-Chaser/KC-Timing`, target `runs-on: [self-hosted, kc-timing-runner]` and compare live runner logs with `gha_runner_current_job{runner="kc_timing"}` in Prometheus.

## Manual updates (controlled deployments)

**Do not restart a runner with an active GitHub Actions job.** Verify its
current state in GitHub's organization runner settings, as well as recent
Docker logs. A log-based idle indication cannot guarantee that a new job is
not being assigned. Ideally pause or disable assignment during maintenance.
Update runners **one at a time** and verify registration between changes.

Check remote source changes without changing files or running containers:

```bash
/usr/local/sbin/gha-runner-update-check
```

When the target runner is idle, update KC:

```bash
git -C /opt/gha-runners/kc/KC-GHA-Runner pull --ff-only origin main
make -C /opt/gha-runners/kc/KC-GHA-Runner build
sudo systemctl restart gha-runner-kc.service
sudo systemctl status gha-runner-kc.service --no-pager
docker logs --tail 40 kc-gha-runner-local
```

Update KC-Timing independently when idle:

```bash
git -C /opt/gha-runners/kc-timing/KC-Timing-Runner pull --ff-only origin main
make -C /opt/gha-runners/kc-timing/KC-Timing-Runner r.preflight
sudo systemctl restart gha-runner-kc-timing.service
sudo systemctl status gha-runner-kc-timing.service --no-pager
docker logs --tail 40 kc-timing-runner-local
```

DFAIR now uses the ARC deployment above. Do not restart its retired Docker service.

`make build` builds the new image without replacing the current container;
`systemctl restart` activates it. The service's `r.up` also builds, so this
usually builds a cached second time. **There is no automatic rollback.**
A build, token acquisition, or runner-registration failure can cause downtime.
An initial `A session for this runner already exists` conflict was observed
on both runners after 2026-10-22 restarts. Both eventually reconnected;
wait for `Listening for Jobs` rather than repeatedly restarting blindly.

Verify the container runs the intended image:

```bash
docker inspect kc-gha-runner-local --format 'Container: {{.Image}}'
docker image inspect kc-gha-runner:dev --format 'Built: {{.Id}}'
docker inspect dfair-gha-runner-local --format 'Container: {{.Image}}'
docker image inspect dfair-gha-runner:dev --format 'Built: {{.Id}}'
```

Each pair of image IDs should match. Also verify `Connected to GitHub` and
`Listening for Jobs`, then run a suitable workflow for functional confidence.
GitHub Actions runner binary auto-updates inside the container are separate
from source-code/image updates. After deployment on 2026-10-22, KC reported
runner version `2.338.1`; DFAIR's connection was later confirmed but its
post-update binary version was not recorded here.

## Nightly source update check

A **read-only systemd timer** checks each configured private repository's `origin/main`
every night around **03:00 host-local time** with up to 15 minutes of random
delay. The timer was enabled and its service run succeeded on **2026-10-22**.
Its first scheduled run was **2026-10-23 03:03:51 EDT**, according to
`systemctl list-timers` at setup time. The KC and DFAIR repositories use SSH aliases under `seth` (`github-kc`, `github-dfair`); KC-Timing is cloned with an HTTPS remote authenticated by `gh auth setup-git` as `seth`. The oneshot unit runs as `seth`. The versioned script now includes KC-Timing, but updating the **deployed** `/usr/local/sbin/gha-runner-update-check` and testing its HTTPS credentials remains a separate deployment step.

| Installed component | Path | Versioned example |
|---|---|---|
| Checker | `/usr/local/sbin/gha-runner-update-check` | [Script](runner-observability/gha-runner-update-check) |
| Service | `/etc/systemd/system/gha-runner-update-check.service` | [Service unit](runner-observability/gha-runner-update-check.service) |
| Timer | `/etc/systemd/system/gha-runner-update-check.timer` | [Timer unit](runner-observability/gha-runner-update-check.timer) |

The checker runs `git fetch origin main`, compares `HEAD` with
`refs/remotes/origin/main`, and prints `UP TO DATE`, `UPDATE AVAILABLE`
(with incoming commit subjects), or a divergence warning. A failed fetch
fails the oneshot service. **It does not** pull into the working tree, deploy
containers, install dependencies, or emit notifications. The deployed version
logs a diverged branch but exits successfully; investigate divergence
manually before any `pull --ff-only`.

```bash
# Verify unit files and next execution
sudo systemd-analyze verify \
  gha-runner-update-check.service gha-runner-update-check.timer
systemctl list-timers --all gha-runner-update-check.timer

# Run an unscheduled check and inspect logs
sudo systemctl start gha-runner-update-check.service
journalctl -u gha-runner-update-check.service -n 60 --no-pager

# History and timer state
journalctl -u gha-runner-update-check.service --since '7 days ago' --no-pager
systemctl status gha-runner-update-check.timer --no-pager

# Disable scheduled checks without removing the files
sudo systemctl disable --now gha-runner-update-check.timer
```

Timer uses the host timezone, **not** automatically America/New_York. Confirm
`timedatectl` before interpreting 03:00 as Eastern time. `Persistent=true`
runs a missed check after the host comes back online.

### Reinstalling the versioned check files

From this documentation repository root **on the target VM**, copy the
checked-in examples to their configured locations and enable the timer:

```bash
sudo install -m 755 docs/services/runner-observability/gha-runner-update-check \
  /usr/local/sbin/gha-runner-update-check
sudo install -m 644 docs/services/runner-observability/gha-runner-update-check.service \
  /etc/systemd/system/gha-runner-update-check.service
sudo install -m 644 docs/services/runner-observability/gha-runner-update-check.timer \
  /etc/systemd/system/gha-runner-update-check.timer
sudo systemctl daemon-reload
sudo systemctl enable --now gha-runner-update-check.timer
```

The KC override is a **separate** change; do not replace a running service
blindly. Review and apply the versioned wrapper/drop-in during a maintenance
window if the VM is rebuilt. Keep all repository Makefiles untouched.

## Health and troubleshooting

```bash
# Check Docker/systemd status
docker ps --filter name=gha-runner-local
sudo systemctl status gha-runner-kc.service gha-runner-dfair.service gha-runner-kc-timing.service --no-pager

# Recent registration/job activity
docker logs --tail 50 kc-gha-runner-local
docker logs --tail 50 dfair-gha-runner-local
docker logs --tail 50 kc-timing-runner-local

# Log-based current-job observer (bound to VM lab address, not loopback)
curl -fsS http://192.168.10.189:9119/metrics
sudo systemctl status gha-runner-job-exporter.service --no-pager
```

The exporter now emits `kc`, `dfair`, and `kc_timing` observer metrics. The 2026-10-27 VM-local scrape showed `gha_runner_job_observer_up=1` and `gha_runner_job_observer_initialized=1` for all three (this is **not** a live job test). The exporter listens on `192.168.10.189:9119`, so a request to
`127.0.0.1:9119` fails even when it is healthy. Prometheus on
`monitor-01` (`192.168.10.158`) successfully scrapes the exporter every
15 seconds. Metrics report log visibility/current inferred job, **not**
authoritative GitHub runner availability or queued jobs. See
[Monitoring](monitoring.md#github-actions-runner-observability-2026-10-22).

### Open work

- Add alerting or Prometheus metrics for source updates; the nightly
  check presently logs to journald only.
- Validate a deliberately long-running workflow against the current-job
  exporter while it executes.
- Consider coordinated job-draining/disablement, safer image validation,
  and rollback before permitting unattended deployment.
- Confirm retired PL's remote GitHub organization registration is removed.
