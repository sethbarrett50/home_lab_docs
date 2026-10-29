# Infra Overview dashboard

One authoritative dashboard file: [infra-overview.json](infra-overview.json).

The JSON is in **Classic Grafana dashboard format** (`schemaVersion`, `panels`, `targets`, `gridPos`) for compatibility with the **Dashboards → New → Import** workflow. It replaces the earlier V2 spec-only export, which was unsuitable for that import path. All 34 original visualization panels, 8 NVIDIA GPU visualization panels, and four organizational row headings remain.

## Import into existing Grafana dashboard

1. Back up your live **Infra Overview** dashboard using Grafana's Export function. Any edits made directly in Grafana after the repo's previous snapshot may not be represented here.
2. Open **Dashboards → New → Import** in Grafana and upload the latest `infra-overview.json` from this feature branch (or `dev` after PR merge). **The old `dev` file does not have the new format until this PR is merged.**
3. In Grafana's import workflow, choose the existing dashboard's UID/overwrite option where offered to avoid a duplicate. The JSON uses `uid: null`, because the live dashboard UID was not available from the repository export. If Grafana cannot replace by selection, retrieve the existing UID from the dashboard URL, insert it in `uid`, and back up the existing dashboard before import.
4. Confirm the existing Infrastructure, GHA Runners, and Internal HTTPS / Caddy rows plus **LLM / GPU (llm-01)** row. Verify the GPU exporter is up: `up{job="llm-01-gpu"} == 1`.

The dashboard uses the original Prometheus datasource UID `PBFA97CFB590B2093`. If the target Grafana instance has a different UID, select or edit the datasource after import. This JSON **does not automatically deploy** via the Grafana bind-mounted datasource provisioning directory.

## Local static verification

```bash
python3 -m json.tool docs/services/dashboards/infra-overview.json >/dev/null
python3 - <<'PY'
import json
from pathlib import Path
d = json.loads(Path("docs/services/dashboards/infra-overview.json").read_text())
assert "panels" in d and "elements" not in d
assert d["schemaVersion"] >= 40
viz = [p for p in d["panels"] if p["type"] != "row"]
assert len(viz) == 42
assert len([p for p in d["panels"] if p["type"] == "row"]) == 4
ids = [p["id"] for p in d["panels"]]
assert len(ids) == len(set(ids))
assert all(p["targets"] and p["targets"][0]["expr"] for p in viz)
print("Classic JSON structurally valid, 42 visualizations + 4 rows")
PY
```

**Status:** Static structure confirmed in the PR. A live Grafana server-side import/validation and render check has **not** yet been completed; an exact error message would be necessary to debug any remaining failure.
