# Infra Overview dashboard deployment (Grafana 13)

The authoritative dashboard **spec** is [infra-overview.json](infra-overview.json). It uses Grafana's V2 dashboard JSON model with an `elements` map and `RowsLayout`, **not** the older classic `panels` array. The file retains all 34 preexisting panels and adds 8 GPU gauges in a fourth row, `LLM / GPU (llm-01)`.

**Important:** The Grafana 13 **JSON Model editor** works with a dashboard spec, while API operations expecting a full V2 resource require `apiVersion`, `kind`, `metadata`, and `spec`. A complete resource-shaped example is [infra-overview-resource.json](infra-overview-resource.json). For updates to an **existing** dashboard through the API, retain its real UID, namespace, resourceVersion and metadata obtained from Grafana; do **not** blindly create a second dashboard with the example metadata. Grafana's classic legacy `/api/dashboards/db` endpoint and legacy file provisioning may reject V2 dashboards. Avoid using that path with this file.

## Update the existing live dashboard (preferred)

1. Open the existing **Infra Overview** dashboard in Grafana, select **Edit**, open dashboard settings → **JSON Model**.
2. Back up the live JSON model locally before editing. Compare with the version in Git; if live changes were made since the repo snapshot, merge those changes first.
3. Replace the **spec** in the JSON model editor with the contents of `infra-overview.json` (do not paste the wrapped resource into a spec-only editor). Save changes and verify the original three sections plus the new fourth section. If the UI expects the full resource instead, use the full V2 resource shape, preserving the live metadata/UID.
4. Confirm that `up{job="llm-01-gpu"} == 1` and that the new gauges display readings. Return to edit if the dashboard shows a schema validation message; save the **exact validation error** to debug fields, not merely JSON syntax.

## Automated structural checks (repository)

```bash
python3 -m json.tool docs/services/dashboards/infra-overview.json >/dev/null
python3 -m json.tool docs/services/dashboards/infra-overview-resource.json >/dev/null
python3 - <<'PY'
import json
from pathlib import Path
p = Path('docs/services/dashboards')
spec = json.loads((p / 'infra-overview.json').read_text())
resource = json.loads((p / 'infra-overview-resource.json').read_text())
assert resource['apiVersion'] == 'dashboard.grafana.app/v2'
assert resource['kind'] == 'Dashboard'
assert resource['spec'] == spec
assert len(spec['elements']) == 42
ids = [v['spec']['id'] for v in spec['elements'].values()]
assert len(ids) == len(set(ids))
for row in spec['layout']['spec']['rows']:
    for item in row['spec']['layout']['spec']['items']:
        assert item['spec']['element']['name'] in spec['elements']
print('JSON, panel IDs and layout references valid')
PY
```

These checks verify JSON syntax and dashboard references but **do not substitute for a Grafana server-side schema check**. Grafana rendering/import of the PR revision is not yet verified, and the exact UI error that prompted this change was not supplied.

## Source and live configuration

- Grafana container: `grafana`, `monitor-01:3000` via `https://grafana.home.arpa`.
- Grafana datasource config bind mount: `/opt/monitoring/grafana/provisioning` → `/etc/grafana/provisioning`. No dashboard-provider provisioning has been configured.
- Prometheus datasource used by this dashboard: `PBFA97CFB590B2093`, copied from original panels.
- Prometheus scrape job: `llm-01-gpu` at `192.168.10.162:9835`, confirmed up on 2026-10-29.

**Do not** copy V2 spec JSON into a classic dashboard provider and assume Grafana will pick it up; existing dashboard remains database-managed until an explicit compatible deployment mechanism is installed.
