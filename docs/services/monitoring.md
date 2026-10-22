# Monitoring

## Current State

Deployed via Docker on two VMs, plus a native (non-Docker) node-exporter
on `dell-mini`, and Caddy metrics from `certs-01`. The Infrastructure
Overview dashboard has been rebuilt; an updated repository dashboard JSON now
includes a proposed Caddy row, but its import/rendering in live Grafana has not
yet been verified. Related work is tracked in issues
[#3](https://github.com/sethbarrett50/home_lab_docs/issues/3)–[#8](https://github.com/sethbarrett50/home_lab_docs/issues/8),
[#43](https://github.com/sethbarrett50/home_lab_docs/issues/43) for
dell-mini specifically.

## Actual Stack

```mermaid
graph TD
    subgraph "gha-general-01 (192.168.10.189)"
        NE1[node-exporter]
        CB1[cAdvisor :8080]
        AL1[Grafana Alloy :12345]
        R1[2x GHA runner containers\ndfair / kc]
        BK[Buildkit builder]
        EX[Runner job exporter :9119]
    end

    subgraph "monitor-01 (192.168.10.158)"
        NE2[node-exporter]
        CB2[cAdvisor :8080]
        AL2[Grafana Alloy :12345]
        PROM[Prometheus :9090]
        LOKI[Loki :3100]
        GF[Grafana :3000]
        KUMA[Uptime Kuma :3001]
    end

    subgraph "certs-01 (LXC 106; 192.168.10.50)"
        CADDY[Caddy :443 / metrics :9180]
    end

    subgraph "dell-mini (192.168.10.117)"
        NE3[node-exporter\nnative systemd, no Docker]
    end

    NE1 --> AL1
    CB1 --> AL1
    EX -->|direct scrape :9119| PROM
    AL1 -->|remote_write| PROM
    NE2 --> PROM
    CB2 --> PROM
    NE3 -->|direct scrape| PROM
    CADDY -->|metrics scrape :9180| PROM
    CADDY -->|HTTPS proxy| GF
    CADDY -->|HTTPS proxy| KUMA
    AL2 --> LOKI
    PROM --> GF
    LOKI --> GF
```

## Components (as deployed)

| Container | Host | Port | Role |
|---|---|---|---|
| `grafana` | monitor-01 | 3000 | Visualization — Infrastructure Overview dashboard has been rebuilt; see [Dashboard Rebuild Status](#dashboard-rebuild-status) |
| `prometheus` | monitor-01 | 9090 | Metrics store. **Not** 3001 — that's Kuma (see below, was documented wrong) |
| `uptime-kuma` | monitor-01 | 3001 | Uptime/status checks; existing research-output-scraper monitors documented in [research-output-scraper.md](research-output-scraper.md#monitoring). Docker DNS pinned to `192.168.10.1`. Added internal-CA trust via `NODE_EXTRA_CA_CERTS` and read-only certificate mount (2026-10-20); new Grafana/Proxmox HTTPS monitor status not yet verified. |
| `loki` | monitor-01 | 3100 | Log aggregation |
| `alloy` | monitor-01 + gha-general-01 | 12345 | Unified telemetry collector — ships node-exporter/cAdvisor data to Prometheus/Loki |
| `cadvisor` | monitor-01 + gha-general-01 | 8080 | Per-container CPU/mem/network metrics |
| `node-exporter` | monitor-01 + gha-general-01 | — | Host-level CPU/mem/disk metrics |
| `node_exporter` (native, not a container) | dell-mini | 9100 | Host-level CPU/mem/disk metrics — scraped directly by Prometheus, no Alloy (dell-mini doesn't run Docker) |
| `dfair-gha-runner-local`, `kc-gha-runner-local` | gha-general-01 | — | The 2 active self-hosted GitHub Actions runners; PL retired 2026-10-22 |
| `gha-runner-job-exporter.service` (systemd/Python) | gha-general-01 | 9119 | Read-only Docker runner log observer; exported metrics for current job names |
| `buildx_buildkit_builder-*` | gha-general-01 | — | Buildkit builder for the runners |

**Fixed (was issue #3):** all scrape targets were still pointed at
pre-migration `192.168.1.x` IPs (proxmox's target was literally still
`192.168.1.197`, its old flat-network address) — a direct side effect of the
VLAN migration earlier this session. Fixed by updating
`/opt/monitoring/prometheus/prometheus.yml` on monitor-01 to the current
`192.168.10.x` addresses and restarting the `prometheus` container. All 7
configured targets (prometheus, monitor-01-node/-containers,
gha-general-01-node/-containers, proxmox-node, dell-mini-node) are now
healthy.

## Caddy and internal HTTPS monitoring (2026-10-20)

Caddy runs on `certs-01` (LXC 106, `192.168.10.50`); full configuration and CA handling are documented in [Internal HTTPS / Caddy](caddy.md). Prometheus runs in Docker on `monitor-01` and reads `/opt/monitoring/prometheus/prometheus.yml` (bind-mounted read-only to `/etc/prometheus/prometheus.yml`). Added one scrape job alongside existing jobs:

```yaml
  - job_name: "caddy"
    scrape_interval: 15s
    metrics_path: /metrics
    static_configs:
      - targets:
          - "192.168.10.50:9180"
```

`promtool check config` passed, the lifecycle reload succeeded, and the target API reported `health: up` with `up{job="caddy"} = 1` and no scrape error. Existing seven targets remain configured; **eight** targets are now configured including Caddy. Caddy exposes upstream health and HTTP metrics. The Prometheus API was rechecked on 2026-10-20: `up{job="caddy"} = 1`, and both `caddy_reverse_proxy_upstreams_healthy` series (`192.168.10.158:3000` and `192.168.10.158:3001`) returned `1`. The values show successful scraping and Caddy-reported upstream state, not verified end-to-end application health.

**Uptime Kuma** (Docker Compose at `/opt/monitoring/compose.yml`) retains its named `/app/data` volume and router DNS (`192.168.10.1`). The service additionally sets:

```yaml
    environment:
      NODE_EXTRA_CA_CERTS: /etc/homelab-ca/root.crt
    volumes:
      # Existing uptime-kuma-data:/app/data mount is retained
      - /opt/monitoring/certs/homelab-root-ca.crt:/etc/homelab-ca/root.crt:ro
```

`/opt/monitoring/certs/homelab-root-ca.crt` is a verified copy of the **public** internal CA certificate; `NODE_EXTRA_CA_CERTS` and the mount were confirmed inside the running Uptime Kuma **1.23.17** container following `docker compose up -d --no-deps uptime-kuma`. Its SQLite database loaded successfully. Adding/verifying HTTPS probes for `https://grafana.home.arpa/login` and `https://pve.home.arpa:8006/`, retaining TLS verification, and testing actual alert delivery are **still to be confirmed**. Do not count those checks as verified until Kuma reports them UP.

**Not yet instrumented:** `nas` (LXC 105) has no node-exporter and isn't in
the scrape config at all — genuine gap, not a stale-IP issue. Needed before
the Infrastructure Overview dashboard (issue #5) can include it.

## GitHub Actions runner observability (2026-10-22)

The deployed `gha-general-01` runner inventory is **KC + DFAIR only**.
PL was removed from Docker and its dedicated systemd unit was disabled and
removed on 2026-10-22; its old `pl-gha-runner.service` alias is masked.
Removing PL from GitHub's organization-level runner registration is still
not independently verified. The retired runner must not be reintroduced by
backup restore or service automation.

| Runner | Private source repo | Container | Service |
|---|---|---|---|
| KC | [KC-GHA-Runner](https://github.com/Kart-Chaser/KC-GHA-Runner) | `kc-gha-runner-local` | `gha-runner-kc.service` |
| DFAIR | [dfair_runner](https://github.com/DFAIR-LAB-Augusta/dfair_runner) | `dfair-gha-runner-local` | `gha-runner-dfair.service` |

The repos are private. Their *exact* GitHub URLs are excluded from the
unauthenticated lychee link checker in `.lycheeignore`. Other links remain
checked as usual.

A Python HTTP exporter runs as `gha-runner-job-exporter.service` on
`gha-general-01` (`192.168.10.189:9119`) and reads local Docker runner logs.
Its repository copy and systemd unit are under
[`runner-observability/`](runner-observability/).
It exposes:

- `gha_runner_job_observer_up{runner="kc|dfair"}`: `1` when Docker logs can be read;
  **not** proof GitHub has registered or marked the runner online.
- `gha_runner_job_observer_initialized`: whether a recognizable log marker was seen.
- `gha_runner_current_job{runner="...",job="..."} 1`: inferred unfinished job;
  **absent** when no active job is inferred. Grafana maps absence to
  `None running` when the observer is healthy.

This observer does not use GitHub APIs or expose the originating repository.
It can miss very short jobs or infer stale status if log history rolls over.
A live running-job test against GitHub has **not yet been verified**.
Do not confuse `None running` with a failed exporter: first inspect the
observer metrics and actual `docker logs`.

The Prometheus config on `monitor-01` is bind-mounted from
`/opt/monitoring/prometheus/prometheus.yml` and includes:

```yaml
  - job_name: gha-runner-jobs
    scrape_interval: 15s
    static_configs:
      - targets:
          - '192.168.10.189:9119'
```

On 2026-10-22 `promtool check config` passed, Prometheus was HUP-reloaded,
`curl` from `monitor-01` reached the exporter, and the Prometheus API returned
`gha_runner_job_observer_up=1` for both `kc` and `dfair`. This verifies the
exporter-to-Prometheus path, not a running-job capture or alert notification.
Limit port 9119 to the monitoring host; it has no authentication and Docker
access held by the exporter service is privileged.

### Diagnostic commands

On `gha-general-01`:

```bash
sudo systemctl status gha-runner-job-exporter.service --no-pager
curl -fsS http://127.0.0.1:9119/metrics
docker logs --tail 30 kc-gha-runner-local
docker logs --tail 30 dfair-gha-runner-local
```

On `monitor-01`:

```bash
sudo docker exec prometheus promtool check config /etc/prometheus/prometheus.yml
curl -fsSG http://localhost:9090/api/v1/query \
  --data-urlencode 'query=gha_runner_job_observer_up' | jq '.data.result'
```

The versioned
[Infrastructure Overview dashboard JSON](dashboards/infra-overview.json)
is a **Grafana 13 Scenes-based JSON**, based on the supplied dashboard and
updated with two runners, current-job stat panels, and corrected single-value
container-health queries. CPU and RAM gauges use actual host capacity;
network gauges show throughput without an assumed link maximum. Because KC
uses host networking, its per-container network metric may be absent.
The user reported importing/updating a Grafana dashboard with the job panels
showing `None running` while both runners' latest observed jobs had completed.
Import of this *exact version-controlled revision* into live Grafana has
not been independently re-exported and compared. Treat live dashboard
synchronization as a verification step.

Existing Caddy scrape (`:9180`) and other infrastructure panels are retained.
Outstanding work includes verifying a running workflow appears while active,
reviewing alerts, and deploying authoritative GitHub API runner status if needed.
Related tracking: [#7](https://github.com/sethbarrett50/home_lab_docs/issues/7)
(job-level monitoring), [#8](https://github.com/sethbarrett50/home_lab_docs/issues/8)
(router telemetry).

## Alerting — separate follow-up issue (not part of this deployment)

Grafana alerting and Uptime Kuma notification/expiry alert setup and
validation will be tracked in a **separate GitHub issue**. No new alerts were
configured in the October 20, 2026 Caddy monitoring session.

### Ideas (not configured)

| Alert | Condition | Severity |
|---|---|---|
| Host down | Node exporter unreachable >2m | Critical |
| High CPU | >90% for >10m | Warning |
| High RAM | >85% | Warning |
| Disk full | >80% on any mount | Warning |
| GHA runner container down | cAdvisor shows container not running | Warning |

No Alertmanager or notification routing exists yet for Prometheus/Grafana —
they're collection + visualization only, nothing pages/notifies on these
thresholds. Uptime Kuma *does* notify (its own notification channel, separate
from this), but only for its up/down checks.
