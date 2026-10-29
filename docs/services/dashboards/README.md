# Infra Overview dashboard

The repository contains **one dashboard JSON**: [infra-overview.json](infra-overview.json).

This file retains the **original Grafana 13 dashboard V2 JSON model** from `dev` / `main`, with its existing `elements`, `layout`, `annotations`, `timeSettings`, and other top-level fields. It preserves the 34 original panel elements and their queries unchanged, and adds eight NVIDIA P4000 panels in a new `LLM / GPU (llm-01)` row. There is no Classic-format conversion and no second dashboard JSON or deployment script.

The preexisting dashboard is managed inside Grafana, not file-provisioned. If editing the existing dashboard's JSON Model, use this spec-only JSON in the **same editor/workflow that successfully handled the original exported JSON**. Back up any live-only edits before replacing the model; a merge may be necessary if the live database diverged from the repo. The PR does not deploy Grafana changes by itself.

## Local structural check

```bash
python3 -m json.tool docs/services/dashboards/infra-overview.json >/dev/null
python3 - <<'PY'
import json
from pathlib import Path
d = json.loads(Path("docs/services/dashboards/infra-overview.json").read_text())
assert "elements" in d and "layout" in d and "panels" not in d
assert len(d["elements"]) == 42
assert len(d["layout"]["spec"]["rows"]) == 4
for row in d["layout"]["spec"]["rows"]:
    for item in row["spec"]["layout"]["spec"]["items"]:
        assert item["spec"]["element"]["name"] in d["elements"]
ids = [p["spec"]["id"] for p in d["elements"].values()]
assert len(ids) == len(set(ids))
print("Grafana V2 structural checks passed")
PY
```

These checks are **not** live Grafana server-side validation. Live rendering of the PR revision has not been verified.
