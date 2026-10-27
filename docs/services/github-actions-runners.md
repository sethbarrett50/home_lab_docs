# Self-hosted GitHub Actions runners

## Deployment and inventory

Three self-hosted runners operate as Docker containers on
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

Update DFAIR independently:

```bash
git -C /opt/gha-runners/dfair pull --ff-only origin main
make -C /opt/gha-runners/dfair build
sudo systemctl restart gha-runner-dfair.service
sudo systemctl status gha-runner-dfair.service --no-pager
docker logs --tail 40 dfair-gha-runner-local
```

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
