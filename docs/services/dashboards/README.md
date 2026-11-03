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

These checks are **not** live Grafana server-side validation. Live rendering of the PR revision has not been verified.

## Lenovo CI row (prepared 2026-11-03)

The fifth row groups 13 panels: host up, CPU, memory, root disk; runner
exporter health; backend and infrastructure container running indicators;
current log-inferred job names; and each container's CPU and RAM percentage
of host capacity. All metrics originate from the three live Prometheus
scrape jobs on monitor-01: `lenovo-lap-node`, `lenovo-lap-containers`,
and `lenovo-lap-runners`.

**Deploy deliberately:** export/backup the live Grafana dashboard model
before applying this repository version. Its structure is the Grafana 13
V2 / Scenes model, not an importable classic `panels` JSON. If live-only
changes have been made since the last committed export, reconcile them
instead of overwriting them. After updating in the Grafana editor, inspect
the fifth row; verify both runner gauges, and test a live job without
restarting any runner. Changes to GitHub Actions registration are
not required.

The current-job panels show `None running` when the log observer is healthy
and has observed an idle state. They show no data if the Prometheus scrape
itself fails. They are **not** authoritative GitHub online/busy telemetry.
Container-CPU and RAM panels depend on cAdvisor retaining the Docker
container `name` label; inspect exported metric labels if they show no data.
