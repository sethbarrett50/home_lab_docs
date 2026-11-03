# Lenovo CI observability deployment (proposed)

**Status:** configuration checked into the repository; **not yet deployed or
verified on either host**. This extends the existing monitor-01 stack without
restarting, rebuilding, or re-registering the GitHub Actions runners.

## Architecture

| Layer | Source | Destination | Intended signal |
|---|---|---|---|
| Uptime Kuma 2.5.7 | `monitor-01` (`192.168.10.158`) | `lenovo-lap:22` | SSH/TCP availability, with existing Telegram DOWN/recovery notifications |
| Prometheus | `monitor-01` | `lenovo-lap:9100` | Native node-exporter: CPU, RAM, disk, network, uptime |
| Prometheus | `monitor-01` | `lenovo-lap:8080` | cAdvisor: Docker container CPU, RAM, network, running metrics |
| Prometheus | `monitor-01` | `lenovo-lap:9119` | Dedicated read-only log observer: job names and Docker running state |
| Grafana 13 | Prometheus data source | new dashboard panels | Both runner states, current job, host and container load |

The metric endpoints use unauthenticated HTTP within VLAN 10. Restrict access
to `192.168.10.158` at the Lenovo host firewall (or an equivalent
enforced network control) **before** exposing these ports. Simply binding to
the Lab address does not restrict other same-VLAN peers. The cAdvisor collector
reads host data and needs privileged access according to its upstream Docker
recipe; treat it as trusted host infrastructure. Keep secrets out of metrics
and job names.

## Step 0 — restrict host monitoring ports before starting listeners

Review `lenovo-metrics-firewall.nft`. It uses a separate `inet
lenovo_observability` table with an **input-hook** chain, not Docker's
iptables-nft-managed tables; port 8080 on cAdvisor uses host networking so
its traffic crosses this hook. The rule permits IPv4 scrapes from
`192.168.10.158` and localhost, drops other IPv4 sources, and drops
network IPv6 access to ports 8080/9100/9119.

```bash
# On lenovo-lap, in a checkout that includes this PR:
sudo nft -c -f docs/services/lenovo-observability/lenovo-metrics-firewall.nft
sudo nft -f docs/services/lenovo-observability/lenovo-metrics-firewall.nft
sudo nft list table inet lenovo_observability
```

Install the separately versioned `lenovo-metrics-firewall.service` to
reapply **only its own table** before Docker and the exporters at boot.
It does not flush or change Docker tables.

```bash
sudo install -d -m 755 /etc/nftables.d
sudo install -m 644 docs/services/lenovo-observability/lenovo-metrics-firewall.nft \
  /etc/nftables.d/lenovo-metrics-firewall.nft
sudo install -m 644 docs/services/lenovo-observability/lenovo-metrics-firewall.service \
  /etc/systemd/system/lenovo-metrics-firewall.service
sudo nft -c -f /etc/nftables.d/lenovo-metrics-firewall.nft
sudo systemctl daemon-reload
sudo systemctl enable --now lenovo-metrics-firewall.service
systemctl is-enabled lenovo-metrics-firewall.service
systemctl is-active lenovo-metrics-firewall.service
sudo nft list table inet lenovo_observability
```

Review existing `/etc/nftables.conf` and `nftables.service` first and
ensure no other service subsequently flushes the ruleset. Keep SSH connected
while applying firewall rules. Confirm persistence after a scheduled reboot;
do **not** reboot or restart existing CI runners during jobs.

## Step 1 — install collectors on lenovo-lap

From an SSH session on `lenovo-lap`, **not** on `monitor-01`:

```bash
sudo apt-get update
sudo apt-get install -y prometheus-node-exporter

# Bind node exporter to the wired Lab interface.
sudo mkdir -p /etc/systemd/system/prometheus-node-exporter.service.d
sudo tee /etc/systemd/system/prometheus-node-exporter.service.d/10-lab-address.conf >/dev/null <<'UNIT'
[Service]
ExecStart=
ExecStart=/usr/bin/prometheus-node-exporter --web.listen-address=192.168.10.193:9100
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now prometheus-node-exporter
sudo systemctl restart prometheus-node-exporter
sudo systemctl is-active prometheus-node-exporter
curl -fsS http://192.168.10.193:9100/metrics | grep -m 1 '^node_uname_info'
```

Review any existing security policy first: `sudo nft list ruleset`.
Use existing firewall management so local rules survive reboot. Confirm that
`monitor-01` can reach TCP 9100/8080/9119 but unapproved hosts cannot.
Avoid changing the default input policy or flushing unrelated firewall rules.

The runner observer uses the checked-in `exporter.py` and
`gha-runner-exporter.service` in this folder:

```bash
# Run from a checkout of home_lab_docs containing this PR:
sudo install -d -m 755 /opt/lenovo-observability
sudo install -m 755 docs/services/lenovo-observability/exporter.py /opt/lenovo-observability/exporter.py
sudo install -m 644 docs/services/lenovo-observability/gha-runner-exporter.service /etc/systemd/system/gha-runner-exporter.service
python3 -m py_compile /opt/lenovo-observability/exporter.py
sudo systemctl daemon-reload
sudo systemctl enable --now gha-runner-exporter.service
curl -fsS http://192.168.10.193:9119/metrics
```

Expected series for both `kc_backend` and `kc_infra`:
`gha_runner_container_running`,
`gha_runner_job_observer_up`,
`gha_runner_job_observer_initialized`. `gha_runner_current_job`
appears only when a running job can be inferred from the logs. The metrics
**do not** prove GitHub online/busy status; use `gh api` for authoritative
runner registration.

For cAdvisor (host networking so the host INPUT firewall applies), the pinned image in `cadvisor-compose.yml` is
`ghcr.io/google/cadvisor:v0.53.0`; verify its digest before deployment.
Because this is a privileged monitoring container, review the Compose file
and any security implications before running it:

```bash
sudo install -d -m 755 /opt/lenovo-observability
sudo install -m 644 docs/services/lenovo-observability/cadvisor-compose.yml /opt/lenovo-observability/compose.yml
docker compose -f /opt/lenovo-observability/compose.yml config -q
docker compose -f /opt/lenovo-observability/compose.yml up -d
docker ps --filter name=lenovo-cadvisor
curl -fsS http://192.168.10.193:8080/metrics | grep -m 1 '^container_cpu_usage_seconds_total'
```

The Compose project is separate from the existing runner containers. None of
these collector commands invokes `make r.up` or restarts either CI runner.
If `/dev/kmsg` is absent on this hardware, inspect that before starting
cAdvisor instead of creating arbitrary device nodes.

## Step 2 — add Prometheus scrapes on monitor-01

The Prometheus container uses the **host file**
`/opt/monitoring/prometheus/prometheus.yml`, mounted read-only inside the
container. Back it up. Then merge the three scrape jobs from
`prometheus-scrape.yml` in this folder **under the existing
`scrape_configs:` key**. Do not replace the whole configuration or introduce
a second `scrape_configs:` mapping.

```bash
# On monitor-01:
sudo cp -a /opt/monitoring/prometheus/prometheus.yml \
  /opt/monitoring/prometheus/prometheus.yml.bak-$(date +%Y%m%d-%H%M%S)
sudo docker exec prometheus promtool check config /etc/prometheus/prometheus.yml
# After editing and validating the host config:
sudo docker exec prometheus promtool check config /etc/prometheus/prometheus.yml
curl -fsS -X POST http://127.0.0.1:9090/-/reload
sleep 20
for job in lenovo-lap-node lenovo-lap-containers lenovo-lap-runners; do
  curl -fsSG http://127.0.0.1:9090/api/v1/query \
    --data-urlencode "query=up{job=\"$job\"}" | jq -r '.data.result[]? | [.metric.job,.value[1]] | @tsv'
done
```

Expected `up=1` for all three after successful scrape, with other
existing Prometheus targets unchanged. The reload endpoint may be disabled:
if it fails, check Prometheus launch flags and use its documented signal-based
reload without deleting the persistent container/volumes.

## Step 3 — configure Uptime Kuma

In the existing Uptime Kuma 2.5.7 UI on `monitor-01`, add one **TCP Port**
monitor for the CI host:

- Friendly name: `Lenovo CI host - SSH`
- Hostname: `192.168.10.193`
- Port: `22`
- Interval: 60 seconds; retries: 3
- Notification: enable the existing **Homelab Telegram Alerts** provider

This detects network/SSH availability but does **not** establish that both
Docker runners are online. For the observer, a second optional HTTP monitor
can request `http://192.168.10.193:9119/metrics`; HTTP 200 confirms the
exporter is serving, **not** that it correctly sees either runner. Prometheus
queries are the appropriate checks for individual `gha_runner_container_running`
series. Avoid a deployment-triggering GitHub workflow just to generate traffic.
Test notification delivery through a safe, explicitly controlled monitor test.

### Additional Uptime Kuma monitors for runner health

The operator has created the `Lenovo CI host - SSH` TCP port 22 monitor.
Suggested additional checks in Kuma's existing UI (all target the Lenovo
Lab IP; enable the existing Telegram notification on each):

| Name | Type | URL | Expected |
|---|---|---|---|
| Lenovo Node Exporter | HTTP(s) | `http://192.168.10.193:9100/metrics` | HTTP 200 |
| Lenovo cAdvisor | HTTP(s) | `http://192.168.10.193:8080/metrics` | HTTP 200 |
| Lenovo Backend Runner | HTTP(s) - Keyword | `http://192.168.10.193:9119/metrics` | Exact keyword `gha_runner_container_running{runner="kc_backend"} 1` |
| Lenovo Infra Runner | HTTP(s) - Keyword | `http://192.168.10.193:9119/metrics` | Exact keyword `gha_runner_container_running{runner="kc_infra"} 1` |

Use a 60-second interval and three retries initially. These keyword
checks test whether Docker reports the specific container running, not
whether GitHub has marked it online or whether its jobs succeed. The
metrics endpoint is intentionally protected by Lenovo's nftables rule,
allowing access from `monitor-01`.

Only configure keyword matching when Uptime Kuma offers it in the current
version; do not substitute the generic HTTP 200 check for runner status.
A separate authenticated GitHub Actions API monitor would be needed for
authoritative registration/queue health; do not place API tokens into
URLs or version-controlled Kuma settings.

## Step 4 — Grafana dashboard

The versioned [Infrastructure Overview dashboard](../dashboards/infra-overview.json)
now includes 13 Lenovo panels in a fifth row, preserving the previous panels.
Use [dashboard deployment guidance](../dashboards/README.md) to back up
and reconcile any live-only edits. Representative queries:

| Panel | PromQL |
|---|---|
| Lenovo host reachable | `up{job="lenovo-lap-node"}` |
| Lenovo CPU usage (%) | `100 * (1 - avg(rate(node_cpu_seconds_total{job="lenovo-lap-node",mode="idle"}[5m])))` |
| Lenovo memory usage (%) | `100 * (1 - node_memory_MemAvailable_bytes{job="lenovo-lap-node"} / node_memory_MemTotal_bytes{job="lenovo-lap-node"})` |
| Lenovo root filesystem used (%) | `100 * (1 - node_filesystem_avail_bytes{job="lenovo-lap-node",mountpoint="/",fstype!="tmpfs",fstype!="overlay"} / node_filesystem_size_bytes{job="lenovo-lap-node",mountpoint="/",fstype!="tmpfs",fstype!="overlay"})` |
| Backend container running | `gha_runner_container_running{job="lenovo-lap-runners",runner="kc_backend"} or on() vector(0)` |
| Infrastructure container running | `gha_runner_container_running{job="lenovo-lap-runners",runner="kc_infra"} or on() vector(0)` |
| Runner log observers healthy | `gha_runner_job_observer_up{job="lenovo-lap-runners"}` |
| Current backend job | `gha_runner_current_job{job="lenovo-lap-runners",runner="kc_backend"}` |
| Current infrastructure job | `gha_runner_current_job{job="lenovo-lap-runners",runner="kc_infra"}` |

For the four runner CPU/RAM gauges, the updated dedicated runner exporter
supplies stable `gha_runner_container_cpu_host_percent` and
`gha_runner_container_memory_host_percent` metrics. CPU percentage divides
Docker's per-core CPU percentage by the Lenovo's logical CPU count; RAM
percentage divides Docker-reported container memory usage by physical host
memory from `/proc/meminfo`. Unlike cAdvisor metrics, these series do not
depend on Docker container `name` labels. Validate
`gha_runner_container_stats_up{runner="kc_backend"}` and
`gha_runner_container_stats_up{runner="kc_infra"}` are both 1 after
updating the exporter; the stats collection takes an additional short Docker
read per Prometheus scrape. **The previous dashboard version had no data for
container CPU/RAM and displayed UP/DOWN simultaneously due to an incorrect
unmatched zero fallback.** Both are corrected in the source dashboard.

A missing `gha_runner_current_job` series should show “none inferred”,
not “runner offline”. A log-derived current-job gauge isn't a counter or a
complete job history. For host availability also inspect
`up{job="lenovo-lap-runners"}`; a healthy observer with a missing current-job
series is normal at idle.

Do not import a replacement dashboard until the live Grafana dashboard has
been exported/backed up; this repo uses a Grafana 13 dashboard V2/Scenes model.
Dashboard import/render verification remains necessary.

## Validation and follow-ups

Confirm the following before claiming observability is deployed:
node-exporter, cAdvisor, and observer HTTP endpoints reachable **from
monitor-01**, Prometheus targets `UP`, a live CI job appears and disappears
correctly in the observer, Grafana panels render, Kuma TCP monitor turns
green, and a notification test reaches Telegram. Verify an unauthorized
Lab peer cannot read ports 8080, 9100, or 9119.

The observation exporter currently runs Docker CLI under `pooltab`
with the supplementary `docker` group and thus has privileged host access;
restrict filesystem modification and its HTTP listener accordingly.
