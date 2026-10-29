# Infra Overview dashboard

The repository maintains exactly **one** Grafana dashboard JSON: [infra-overview.json](infra-overview.json). It contains 34 original visualizations, eight llm-01 GPU visualizations and four section rows.

## Preferred deployment: update the existing dashboard through Grafana's API

**Do not paste the entire JSON into the Grafana 13 V2 JSON Model editor.** That editor may validate V2 resources while the repo contains Classic JSON. Use [deploy_infra_overview.py](deploy_infra_overview.py) to apply the Classic model through the legacy dashboard API instead. This command runs only against Grafana on `127.0.0.1:3000` from `monitor-01`. It refuses to create a new dashboard, requires exactly one existing dashboard titled `Infra Overview`, preserves its UID and folder, backs up the live version outside the repo and reads back the update to verify panel count.

```bash
# On monitor-01: copy the file and script from this PR checkout onto the host
# e.g. after fetching this branch from home_lab_docs:
cd ~/code/home_lab_docs
git fetch origin
git switch feat/grafana-llm-gpu-panels-20261029
git pull --ff-only
python3 docs/services/dashboards/deploy_infra_overview.py
# Inspect target UID/version from the dry run, then:
python3 docs/services/dashboards/deploy_infra_overview.py --apply
```

The script prompts for Grafana username and password without echoing the password. Alternatively supply `GRAFANA_API_TOKEN` as a protected environment variable (do not commit it, paste it into shell history, or print it). Backups are written to `~/.local/share/grafana-dashboard-backups/` with mode 0600, outside Git.

If the API reports HTTP 400, the error body identifies the server-side validation issue directly. If Grafana authentication disallows Basic Auth, use a scoped Grafana service-account token. The script does not restart Grafana, Prometheus or either LLM.

## Static verification

```bash
python3 -m json.tool docs/services/dashboards/infra-overview.json >/dev/null
python3 - <<'PY'
import json
from pathlib import Path
d = json.loads(Path("docs/services/dashboards/infra-overview.json").read_text())
assert isinstance(d["panels"], list) and len(d["panels"]) == 46
assert len([p for p in d["panels"] if p["type"] == "row"]) == 4
assert len([p for p in d["panels"] if p["type"] != "row"]) == 42
assert len({p["id"] for p in d["panels"]}) == 46
print("Dashboard structure OK")
PY
```

The source JSON structure was checked; a successful deployment to the user's live Grafana API has **not yet been observed**.
