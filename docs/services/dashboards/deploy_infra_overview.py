#!/usr/bin/env python3
"""Safely update an existing Grafana dashboard with this repo's Classic JSON.

Runs on monitor-01 against localhost only. Does not create dashboards.
"""
import argparse
import base64
import getpass
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_FILE = Path(__file__).with_name("infra-overview.json")
BASE = "http://127.0.0.1:3000"


def api(method, path, authorization, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={"Authorization": authorization,
                 "Accept": "application/json",
                 "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        # Error text is useful; authorization header is not included.
        raise RuntimeError(f"Grafana HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:1000]}") from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE)
    parser.add_argument("--apply", action="store_true", help="Backup existing dashboard and overwrite it")
    args = parser.parse_args()
    model = json.loads(args.file.read_text())
    assert isinstance(model.get("panels"), list) and len(model["panels"]) == 46, "Expected 42 visualizations + 4 rows"
    assert model.get("title") == "Infra Overview", "Unexpected dashboard title"
    assert len({p["id"] for p in model["panels"]}) == 46, "Duplicate panel IDs"

    token = os.environ.get("GRAFANA_API_TOKEN")
    if token:
        authorization = "Bearer " + token
    else:
        username = input("Grafana username: ")
        password = getpass.getpass("Grafana password (not echoed): ")
        authorization = "Basic " + base64.b64encode(f"{username}:{password}".encode()).decode()

    matches = api("GET", "/api/search?type=dash-db&query=" + urllib.parse.quote(model["title"]), authorization)
    candidates = [item for item in matches if item.get("title") == model["title"]]
    if len(candidates) != 1:
        raise RuntimeError(f"Expected exactly one existing dashboard titled {model['title']!r}; found {len(candidates)}. Nothing changed.")
    uid = candidates[0]["uid"]
    original = api("GET", "/api/dashboards/uid/" + urllib.parse.quote(uid, safe=""), authorization)
    live = original["dashboard"]
    if live.get("title") != model["title"]:
        raise RuntimeError("Live dashboard title mismatch; nothing changed")
    print(f"Existing dashboard UID: {uid}")
    print(f"Live version: {live.get('version')}")
    print(f"Proposed visualization panels: {sum(p['type'] != 'row' for p in model['panels'])}")
    if not args.apply:
        print("Dry run only. Re-run with --apply to update the existing dashboard.")
        return

    backup_dir = args.file.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(backup_dir, 0o700)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = backup_dir / f"infra-overview-live-{timestamp}.json"
    with backup.open("x") as handle:
        json.dump(original, handle, indent=2)
        handle.write("\n")
    os.chmod(backup, 0o600)
    print(f"Live dashboard backup: {backup}")
    model["id"] = live["id"]
    model["uid"] = uid
    model["version"] = live.get("version", 0)
    payload = {"dashboard": model, "folderUid": original["meta"].get("folderUid", ""), "overwrite": True, "message": "Add llm-01 GPU telemetry (home_lab_docs PR #95)"}
    result = api("POST", "/api/dashboards/db", authorization, payload)
    check = api("GET", "/api/dashboards/uid/" + urllib.parse.quote(uid, safe=""), authorization)
    panels = check["dashboard"].get("panels", [])
    if len(panels) != 46 or check["dashboard"].get("uid") != uid:
        raise RuntimeError("API returned success but dashboard read-back did not match expected panel count; inspect backup")
    print(f"Updated existing dashboard: {result.get('url', uid)}")
    print(f"Verified read-back: {len(panels)} panel objects including 4 rows.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, RuntimeError, AssertionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
