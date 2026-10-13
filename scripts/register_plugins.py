#!/usr/bin/env python3
"""Register Pipeline Tracker plugins with the Zywave Sigma org (idempotent)."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

OUT = os.path.join(os.path.dirname(__file__), "..", "plugins", "plugin-ids.json")

PLUGINS = [
    {
        "key": "pace",
        # New name+URL → new pluginId (PATCH often ignores URL-only updates).
        "name": "Pipeline Tracker · Goal pace bar v3",
        "description": "ROTB creation pace: red/green vs paced tick + dark elapsed marker.",
        "url": "https://gabrieljonessigmacomputing.github.io/zywave-pipeline-tracker/plugins/pace-bullet-v3/",
        "devUrl": "http://localhost:5173",
    },
    {
        "key": "funnel",
        "name": "Pipeline Tracker · Stage funnel",
        "description": "Tapered Stage 2–7 open-pipeline funnel.",
        "url": "https://gabrieljonessigmacomputing.github.io/zywave-pipeline-tracker/plugins/stage-funnel/",
        "devUrl": "http://localhost:5173",
    },
    {
        "key": "tv",
        # New pluginId when URL must change — Sigma often ignores URL PATCH on existing plugins.
        "name": "Pipeline Tracker · Target vs Actual v5",
        "description": "ACV-fast product actuals; segment targets (optional kpiSource for SEG/SRC).",
        "url": "https://gabrieljonessigmacomputing.github.io/zywave-pipeline-tracker/plugins/tv-dual-v5/",
        "devUrl": "http://localhost:5173",
    },
    {
        "key": "openKpis",
        "name": "Pipeline Tracker · Open KPI tiles",
        "description": "Early-stage + sourcing KPI tiles from chart-tv KPI grain (no SumIf re-inline).",
        "url": "https://gabrieljonessigmacomputing.github.io/zywave-pipeline-tracker/plugins/open-kpis/",
        "devUrl": "http://localhost:5173",
    },
]


def api(method, path, body=None):
    base = os.environ.get("SIGMA_BASE_URL") or os.environ["ZYWAVE_BASE_URL"]
    token = os.environ.get("SIGMA_API_TOKEN") or os.environ["ZYWAVE_API_TOKEN"]
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        f"{base}{path}", data=data, method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{e.code}: {e.read().decode()[:4000]}") from e


def main():
    entries = api("GET", "/v2/plugins").get("entries") or []
    ids = {}
    for p in PLUGINS:
        hit = next(
            (e for e in entries
             if e.get("name") == p["name"]
             or (e.get("url") or "").rstrip("/") == p["url"].rstrip("/")),
            None,
        )
        if hit:
            if (hit.get("url") or "").rstrip("/") != p["url"].rstrip("/"):
                hit = api("PATCH", f"/v2/plugins/{hit['pluginId']}", {
                    "url": p["url"], "description": p["description"], "name": p["name"],
                })
            print("ok", p["key"], hit["pluginId"])
            ids[p["key"]] = hit["pluginId"]
        else:
            created = api("POST", "/v2/plugins", {
                "name": p["name"], "description": p["description"],
                "url": p["url"], "devUrl": p["devUrl"],
            })
            print("created", p["key"], created["pluginId"])
            ids[p["key"]] = created["pluginId"]
    payload = {
        "pace": ids["pace"],
        "funnel": ids["funnel"],
        "tv": ids["tv"],
        "openKpis": ids["openKpis"],
        "urls": {p["key"]: p["url"] for p in PLUGINS},
    }
    path = os.path.abspath(OUT)
    json.dump(payload, open(path, "w"), indent=2)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
