# Infra Overview dashboard

The repository contains **one dashboard JSON**: [infra-overview.json](infra-overview.json).

This file retains the **original Grafana 13 dashboard V2 JSON model** from `dev` / `main`, with its existing `elements`, `layout`, `annotations`, `timeSettings`, and other top-level fields. It preserves the original 42 panel elements (including the eight NVIDIA P4000 panels) and their queries unchanged, and adds 13 Lenovo host/CI runner panels under `Lenovo CI (lenovo-lap)`. There is no Classic-format conversion and no second dashboard JSON or deployment script.

The preexisting dashboard is managed inside Grafana, not file-provisioned. If editing the existing dashboard's JSON Model, use this spec-only JSON in the **same editor/workflow that successfully handled the original exported JSON**. Back up any live-only edits before replacing the model; a merge may be necessary if the live database diverged from the repo. The PR does not deploy Grafana changes by itself.

## Local structural check

```bash
python3 -m json.tool docs/services/dashboards/infra-overview.json >/dev/null
python3 - <<'PY'
import json
from pathlib import Path
d = json.loads(Path("docs/services/dashboards/infra-overview.json").read_text())
assert "elements" in d and "layout" in d and "panels" not in d
assert len(d["elements"]) == 55
assert len(d["layout"]["spec"]["rows"]) == 5
for row in d["layout"]["spec"]["rows"]:
    for item in row["spec"]["layout"]["spec"]["items"]:
        assert item["spec"]["element"]["name"] in d["elements"]
ids = [p["spec"]["id"] for p in d["elements"].values()]
assert len(ids) == len(set(ids))
assert d["layout"]["spec"]["rows"][-1]["spec"]["title"] == "Lenovo CI (lenovo-lap)"
assert len(d["layout"]["spec"]["rows"][-1]["spec"]["layout"]["spec"]["items"]) == 13
print("Grafana V2 structural checks passed")
PY
```

These structural checks are **not** Grafana server-side tests. On
2026-11-03 the operator separately confirmed the live Grafana 13 V2 dashboard
renders correctly, including Caddy/GPU panels, Lenovo host metrics, runner
CPU/RAM host percentages, and job transitions. No exported post-validation
live dashboard JSON was provided for comparison with this repository file.

## Lenovo CI row (deployed and operator-reviewed 2026-11-03)

The fifth row groups 13 panels: host up, CPU, memory, root disk; runner
exporter health; backend and infrastructure container running indicators;
current log-inferred job names; and each container's CPU and RAM percentage
of host capacity. All metrics originate from the three live Prometheus
scrape jobs on monitor-01: `lenovo-lap-node`, `lenovo-lap-containers`,
and `lenovo-lap-runners`.

**For future changes:** export/backup the live Grafana dashboard model
before applying a revised repository version. Its structure is the Grafana 13
V2 / Scenes model, not an importable classic `panels` JSON. If live-only
changes have been made since the last committed export, reconcile them
instead of overwriting them. After updating in the Grafana editor, inspect
the fifth row; verify both runner gauges, and test a live job without
restarting any runner. Changes to GitHub Actions registration are
not required.

The current-job panels show `None running` when the log observer is healthy
and has observed an idle state. They show no data if the Prometheus scrape
itself fails. They are **not** authoritative GitHub online/busy telemetry.
Container-CPU and RAM panels use the dedicated Lenovo exporter’s
`gha_runner_container_cpu_host_percent` and
`gha_runner_container_memory_host_percent` gauges, not cAdvisor's
container-name labels. Both require deployment of the updated exporter and
`gha_runner_container_stats_up=1` for the corresponding runner.
Container status panels use `or on() vector(0)` to produce a single 0/1
series, rather than displaying simultaneous UP and DOWN values.
