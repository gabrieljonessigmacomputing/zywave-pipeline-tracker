#!/usr/bin/env python3
"""Pipeline Tracker FY2026 — layered data model (clear lineage + fast).

Architecture (each node is intentionally small / purpose-built):

  Snowflake
    ├─ OPPORTUNITY_ACV_METRICS ──► kpi_open (1 row)         ROTB / Open KPIs
    │                           ──► kpi_created (1 row)     Creation pace KPIs
    │                           ──► funnel_q4 (~6 rows)     Open funnel
    │                           ──► open_by_month_stage     Close×Stage chart
    │                           ──► created_by_month        Created chart
    ├─ VW_PIPELINE ─────────────► kpi_sourcing (few rows)   Mkt/Sales mix
    │                           ──► kpi_closed_q4 (1 row)   Won / Lost
    ├─ SNAPSHOT.VW_PIPELINE ────► kpi_walkin (1 row)        Walk-in frozen
    │                           ──► snap_daily              Movement trend
    └─ literals ────────────────► dim_goals / dim_seg_tgt   Hand-entry

NO full-table VW_PIPELINE bind. NO mega cross-join CTE.
Workbook must source these DM elements (no duplicate-named wrappers).
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

CONN = "e2b90d0c-34fd-4423-a4c3-0569c58f33df"
FOLDER = "5EFLG4WW7cjvngI0kCudpF"
YEAR_GOAL, Q4_GOAL = 94_600_000, 26_700_000
OUT = "/tmp/zywave-pt-dm.json"


def api(method: str, path: str, body: dict | None = None):
    base = os.environ.get("SIGMA_BASE_URL") or os.environ["ZYWAVE_BASE_URL"]
    token = os.environ.get("SIGMA_API_TOKEN") or os.environ["ZYWAVE_API_TOKEN"]
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        f"{base}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            raw = r.read()
            return json.loads(raw) if raw else {"ok": True}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{e.code}: {e.read().decode()[:10000]}") from e


def money():
    return {"kind": "number", "formatString": "$,.0f"}


def pct():
    return {"kind": "number", "formatString": ".1%"}


def sql_table(tid: str, name: str, statement: str, cols: list[tuple]):
    """cols: (id, name, format|None)."""
    columns = []
    for cid, cname, fmt in cols:
        c = {"id": cid, "name": cname, "formula": f"[Custom SQL/{cname}]"}
        if fmt:
            c["format"] = fmt
        columns.append(c)
    return {
        "id": tid,
        "kind": "table",
        "name": name,
        "source": {"kind": "sql", "connectionId": CONN, "statement": statement.strip()},
        "columns": columns,
    }


def build() -> dict:
    # ── 1-row KPI: Open horizons (ACV metrics only, STAGE_GROUP pushdown) ──
    kpi_open = sql_table(
        "kpi-open",
        "KPI · Open Horizons",
        """
SELECT
  COUNT(DISTINCT OPPORTUNITY_ID) AS TOTAL_OPPS,
  COALESCE(SUM(METRIC_VALUE),0) AS TOTAL_ACV,
  COUNT(DISTINCT CASE WHEN CLOSE_DATE >= DATE '2026-10-01' AND CLOSE_DATE < DATE '2027-01-01'
    THEN OPPORTUNITY_ID END) AS Q4_OPPS,
  COALESCE(SUM(CASE WHEN CLOSE_DATE >= DATE '2026-10-01' AND CLOSE_DATE < DATE '2027-01-01'
    THEN METRIC_VALUE ELSE 0 END),0) AS Q4_ACV,
  COUNT(DISTINCT CASE WHEN CLOSE_DATE >= DATE '2027-01-01' AND CLOSE_DATE < DATE '2027-04-01'
    THEN OPPORTUNITY_ID END) AS NQ_OPPS,
  COALESCE(SUM(CASE WHEN CLOSE_DATE >= DATE '2027-01-01' AND CLOSE_DATE < DATE '2027-04-01'
    THEN METRIC_VALUE ELSE 0 END),0) AS NQ_ACV,
  COUNT(DISTINCT CASE WHEN CLOSE_DATE >= DATE '2027-04-01' AND CLOSE_DATE < DATE '2027-07-01'
    THEN OPPORTUNITY_ID END) AS Q2OUT_OPPS,
  COALESCE(SUM(CASE WHEN CLOSE_DATE >= DATE '2027-04-01' AND CLOSE_DATE < DATE '2027-07-01'
    THEN METRIC_VALUE ELSE 0 END),0) AS Q2OUT_ACV,
  COALESCE(SUM(CASE WHEN YEAR(CLOSE_DATE) = 2026 THEN METRIC_VALUE ELSE 0 END),0) AS CLOSE_CY_ACV,
  COALESCE(SUM(CASE WHEN YEAR(CLOSE_DATE) = 2027 THEN METRIC_VALUE ELSE 0 END),0) AS CLOSE_NY_ACV,
  COALESCE(SUM(CASE WHEN YEAR(CLOSE_DATE) >= 2028 THEN METRIC_VALUE ELSE 0 END),0) AS CLOSE_FY_ACV
FROM BI_STAGING.DATA.OPPORTUNITY_ACV_METRICS
WHERE METRIC_NAME = 'Forecasted Net ACV'
  AND STAGE_GROUP = '2-7'
""",
        [
            ("ko-to", "TOTAL_OPPS", None),
            ("ko-ta", "TOTAL_ACV", money()),
            ("ko-qo", "Q4_OPPS", None),
            ("ko-qa", "Q4_ACV", money()),
            ("ko-no", "NQ_OPPS", None),
            ("ko-na", "NQ_ACV", money()),
            ("ko-2o", "Q2OUT_OPPS", None),
            ("ko-2a", "Q2OUT_ACV", money()),
            ("ko-cy", "CLOSE_CY_ACV", money()),
            ("ko-ny", "CLOSE_NY_ACV", money()),
            ("ko-fy", "CLOSE_FY_ACV", money()),
        ],
    )

    # ── 1-row KPI: Created (Stage2 attained) + pace maths ──
    kpi_created = sql_table(
        "kpi-created",
        "KPI · Pipeline Created",
        f"""
SELECT
  COALESCE(SUM(CASE WHEN STAGE_2_DATETIME >= DATE '2026-01-01' AND STAGE_2_DATETIME < DATE '2027-01-01'
    THEN METRIC_VALUE ELSE 0 END),0) AS YTD_ACV,
  COALESCE(SUM(CASE WHEN STAGE_2_DATETIME >= DATE '2026-10-01' AND STAGE_2_DATETIME < DATE '2027-01-01'
    THEN METRIC_VALUE ELSE 0 END),0) AS Q4_ACV,
  COALESCE(SUM(CASE WHEN STAGE_2_DATETIME >= DATEADD(day, -7, CURRENT_DATE())
    THEN METRIC_VALUE ELSE 0 END),0) AS WEEK_ACV,
  COUNT(DISTINCT CASE WHEN STAGE_2_DATETIME >= DATEADD(day, -7, CURRENT_DATE())
    THEN OPPORTUNITY_ID END) AS WEEK_OPPS,
  COALESCE(SUM(CASE
    WHEN STAGE_2_DATETIME >= DATE '2026-10-01' AND STAGE_2_DATETIME < DATE '2027-01-01'
     AND CLOSE_DATE >= DATE '2026-10-01' AND CLOSE_DATE < DATE '2027-01-01'
    THEN METRIC_VALUE ELSE 0 END),0) AS CREATED_CLOSING_ACV,
  COUNT(DISTINCT CASE
    WHEN STAGE_2_DATETIME >= DATE '2026-10-01' AND STAGE_2_DATETIME < DATE '2027-01-01'
     AND CLOSE_DATE >= DATE '2026-10-01' AND CLOSE_DATE < DATE '2027-01-01'
    THEN OPPORTUNITY_ID END) AS CREATED_CLOSING_OPPS,
  {YEAR_GOAL}::FLOAT AS YEAR_GOAL,
  {Q4_GOAL}::FLOAT AS Q4_GOAL,
  DATEDIFF(day, DATE '2026-01-01', CURRENT_DATE()) / 365.0 AS YEAR_ELAPSED,
  DATEDIFF(day, DATE '2026-10-01', CURRENT_DATE()) / 92.0 AS Q4_ELAPSED
FROM BI_STAGING.DATA.OPPORTUNITY_ACV_METRICS
WHERE METRIC_NAME = 'Forecasted Net ACV'
  AND STAGE_2_ATTAINED = TRUE
  AND STAGE_2_DATETIME >= DATE '2025-01-01'
""",
        [
            ("kc-y", "YTD_ACV", money()),
            ("kc-q", "Q4_ACV", money()),
            ("kc-w", "WEEK_ACV", money()),
            ("kc-wo", "WEEK_OPPS", None),
            ("kc-cc", "CREATED_CLOSING_ACV", money()),
            ("kc-cco", "CREATED_CLOSING_OPPS", None),
            ("kc-yg", "YEAR_GOAL", money()),
            ("kc-qg", "Q4_GOAL", money()),
            ("kc-ye", "YEAR_ELAPSED", pct()),
            ("kc-qe", "Q4_ELAPSED", pct()),
        ],
    )

    # ── 1-row: Walk-in (snapshot, already tiny agg) ──
    kpi_walkin = sql_table(
        "kpi-walkin",
        "KPI · Walk-in Q4",
        """
SELECT COUNT(*) AS OPPS, COALESCE(SUM(v),0) AS ACV
FROM (
  SELECT OPPORTUNITYID, MAX(FCST_NETACV) AS v
  FROM BI_STAGING.SNAPSHOT.VW_PIPELINE
  WHERE SNAPSHOTDATE = DATE '2026-10-01'
    AND LEFT(STAGE_NAME,1) IN ('2','3','4','5','6','7')
    AND CLOSE_DATE >= DATE '2026-10-01' AND CLOSE_DATE < DATE '2027-01-01'
  GROUP BY 1
  HAVING MAX(FCST_NETACV) BETWEEN 0 AND 2000000
)
""",
        [("kw-o", "OPPS", None), ("kw-a", "ACV", money())],
    )

    # ── 1-row: Closed won/lost Q4 — filtered VW only (not full history) ──
    kpi_closed = sql_table(
        "kpi-closed",
        "KPI · Closed Q4",
        """
SELECT
  COALESCE(SUM(CASE WHEN "Is Won" THEN NETACV__C ELSE 0 END),0) AS WON_ACV,
  COUNT(DISTINCT CASE WHEN "Is Won" THEN ID END) AS WON_OPPS,
  COALESCE(SUM(CASE WHEN NOT "Is Won" AND NETACV__C BETWEEN 0 AND 50000 THEN NETACV__C ELSE 0 END),0) AS LOST_ACV,
  COUNT(DISTINCT CASE WHEN NOT "Is Won" AND NETACV__C BETWEEN 0 AND 50000 THEN ID END) AS LOST_OPPS
FROM BI_PRESENTATION.REPORT.VW_PIPELINE
WHERE "Is Closed" = TRUE
  AND "Close Date" >= DATE '2026-10-01' AND "Close Date" < DATE '2027-01-01'
""",
        [
            ("kz-wa", "WON_ACV", money()),
            ("kz-wo", "WON_OPPS", None),
            ("kz-la", "LOST_ACV", money()),
            ("kz-lo", "LOST_OPPS", None),
        ],
    )

    # ── Few rows: Sourcing mix — open Stage2+ only, sane FCST ──
    kpi_sourcing = sql_table(
        "kpi-sourcing",
        "KPI · Sourcing Mix",
        """
SELECT
  CASE
    WHEN "Lead Source" = 'Marketing' THEN 'Marketing'
    WHEN "Lead Source" = 'Sales Generated' THEN 'Sales'
    ELSE 'Other'
  END AS SOURCE_BUCKET,
  COUNT(DISTINCT ID) AS OPPS,
  COALESCE(SUM(CASE WHEN FCST_NETACV BETWEEN 0 AND 5000000 THEN FCST_NETACV ELSE 0 END),0) AS ACV
FROM BI_PRESENTATION.REPORT.VW_PIPELINE
WHERE "Is Closed" = FALSE
  AND LEFT("Stage Name",1) IN ('2','3','4','5','6','7')
GROUP BY 1
""",
        [
            ("ks-b", "SOURCE_BUCKET", None),
            ("ks-o", "OPPS", None),
            ("ks-a", "ACV", money()),
        ],
    )

    # ── Funnel grain: Q4 open by stage (~6 rows) ──
    funnel = sql_table(
        "funnel-q4",
        "Chart · Q4 Funnel by Stage",
        """
SELECT
  STAGE,
  CASE STAGE
    WHEN '2 - Analysis' THEN 2
    WHEN '3 - Executive Alignment' THEN 3
    WHEN '4 - Solution Validation' THEN 4
    WHEN '5 - Negotiate' THEN 5
    WHEN '6 - Finance Hold' THEN 6
    WHEN '7 - Finance Review' THEN 7
    ELSE 99
  END AS ORD,
  COUNT(DISTINCT OPPORTUNITY_ID) AS OPPS,
  COALESCE(SUM(METRIC_VALUE),0) AS ACV
FROM BI_STAGING.DATA.OPPORTUNITY_ACV_METRICS
WHERE METRIC_NAME = 'Forecasted Net ACV'
  AND STAGE_GROUP = '2-7'
  AND CLOSE_DATE >= DATE '2026-10-01' AND CLOSE_DATE < DATE '2027-01-01'
GROUP BY 1, 2
""",
        [
            ("fn-s", "STAGE", None),
            ("fn-o", "ORD", None),
            ("fn-p", "OPPS", None),
            ("fn-a", "ACV", money()),
        ],
    )

    # ── Chart: open by close month × stage ──
    open_month = sql_table(
        "chart-open-month",
        "Chart · Open by Close Month × Stage",
        """
SELECT
  DATE_TRUNC('month', CLOSE_DATE) AS CLOSE_MONTH,
  STAGE,
  COALESCE(SUM(METRIC_VALUE),0) AS ACV
FROM BI_STAGING.DATA.OPPORTUNITY_ACV_METRICS
WHERE METRIC_NAME = 'Forecasted Net ACV'
  AND STAGE_GROUP = '2-7'
  AND CLOSE_DATE >= DATE '2026-07-01'
  AND CLOSE_DATE < DATE '2028-01-01'
GROUP BY 1, 2
""",
        [
            ("om-m", "CLOSE_MONTH", {"kind": "datetime", "formatString": "%b %Y"}),
            ("om-s", "STAGE", None),
            ("om-a", "ACV", money()),
        ],
    )

    # ── Chart: open by product ──
    open_prod = sql_table(
        "chart-open-prod",
        "Chart · Open by Product",
        """
SELECT
  COALESCE(NULLIF(PRODUCT_CATEGORY,''), 'Uncategorized') AS PRODUCT_CATEGORY,
  COALESCE(SUM(METRIC_VALUE),0) AS ACV
FROM BI_STAGING.DATA.OPPORTUNITY_ACV_METRICS
WHERE METRIC_NAME = 'Forecasted Net ACV'
  AND STAGE_GROUP = '2-7'
GROUP BY 1
ORDER BY 2 DESC
LIMIT 25
""",
        [("op-p", "PRODUCT_CATEGORY", None), ("op-a", "ACV", money())],
    )

    # ── Chart: created by month ──
    created_month = sql_table(
        "chart-created-month",
        "Chart · Created by Month",
        """
SELECT
  DATE_TRUNC('month', STAGE_2_DATETIME) AS MONTH,
  COALESCE(SUM(METRIC_VALUE),0) AS ACV,
  COUNT(DISTINCT OPPORTUNITY_ID) AS OPPS
FROM BI_STAGING.DATA.OPPORTUNITY_ACV_METRICS
WHERE METRIC_NAME = 'Forecasted Net ACV'
  AND STAGE_2_ATTAINED = TRUE
  AND STAGE_2_DATETIME >= DATE '2025-01-01'
GROUP BY 1
""",
        [
            ("cm-m", "MONTH", {"kind": "datetime", "formatString": "%b %Y"}),
            ("cm-a", "ACV", money()),
            ("cm-o", "OPPS", None),
        ],
    )

    # ── Daily snapshots (already aggregated) ──
    snap = sql_table(
        "snap-daily",
        "Chart · Snapshot Trend",
        """
SELECT SNAPSHOTDATE,
  COUNT(DISTINCT OPPORTUNITYID) AS OPPS,
  SUM(CASE WHEN FCST_NETACV BETWEEN 0 AND 2000000 THEN FCST_NETACV ELSE 0 END) AS FCST_NETACV
FROM BI_STAGING.SNAPSHOT.VW_PIPELINE
WHERE SNAPSHOTDATE >= DATE '2026-07-01'
  AND LEFT(STAGE_NAME,1) IN ('2','3','4','5','6','7')
GROUP BY 1
""",
        [
            ("sd-d", "SNAPSHOTDATE", {"kind": "datetime", "formatString": "%b %d"}),
            ("sd-o", "OPPS", None),
            ("sd-f", "FCST_NETACV", money()),
        ],
    )

    # ── Pace long-format for stacked strip / plugin (4 rows) ──
    pace_long = sql_table(
        "pace-long",
        "Chart · Pace Strip",
        f"""
WITH c AS (
  SELECT
    COALESCE(SUM(CASE WHEN STAGE_2_DATETIME >= DATE '2026-01-01' AND STAGE_2_DATETIME < DATE '2027-01-01'
      THEN METRIC_VALUE ELSE 0 END),0) AS YTD,
    COALESCE(SUM(CASE WHEN STAGE_2_DATETIME >= DATE '2026-10-01' AND STAGE_2_DATETIME < DATE '2027-01-01'
      THEN METRIC_VALUE ELSE 0 END),0) AS Q4
  FROM BI_STAGING.DATA.OPPORTUNITY_ACV_METRICS
  WHERE METRIC_NAME = 'Forecasted Net ACV' AND STAGE_2_ATTAINED = TRUE
    AND STAGE_2_DATETIME >= DATE '2025-01-01'
)
SELECT * FROM (
  SELECT 'Year' AS METRIC, 'Actual' AS PART, LEAST(1, YTD / {YEAR_GOAL}) AS VAL,
    DATEDIFF(day, DATE '2026-01-01', CURRENT_DATE()) / 365.0 AS PACED
  FROM c
  UNION ALL
  SELECT 'Year', 'Remain', GREATEST(0, 1 - LEAST(1, YTD / {YEAR_GOAL})),
    DATEDIFF(day, DATE '2026-01-01', CURRENT_DATE()) / 365.0 FROM c
  UNION ALL
  SELECT 'Q4', 'Actual', LEAST(1, Q4 / {Q4_GOAL}),
    DATEDIFF(day, DATE '2026-10-01', CURRENT_DATE()) / 92.0 FROM c
  UNION ALL
  SELECT 'Q4', 'Remain', GREATEST(0, 1 - LEAST(1, Q4 / {Q4_GOAL})),
    DATEDIFF(day, DATE '2026-10-01', CURRENT_DATE()) / 92.0 FROM c
)
""",
        [
            ("pl-m", "METRIC", None),
            ("pl-p", "PART", None),
            ("pl-v", "VAL", pct()),
            ("pl-paced", "PACED", pct()),
        ],
    )

    goals = sql_table(
        "dim-goals",
        "Dim · Goals",
        f"""
SELECT * FROM (
  SELECT 'Year' AS METRIC, {YEAR_GOAL}::FLOAT AS GOAL
  UNION ALL SELECT 'Q4', {Q4_GOAL}
)
""",
        [("dg-m", "METRIC", None), ("dg-g", "GOAL", money())],
    )

    seg = sql_table(
        "dim-seg-tgt",
        "Dim · Segment Targets",
        """
SELECT * FROM (
  SELECT 'Core' AS SEGMENT, 18000000::FLOAT AS TARGET
  UNION ALL SELECT 'Mid-Market', 12000000
  UNION ALL SELECT 'Enterprise', 10000000
)
""",
        [("ds-s", "SEGMENT", None), ("ds-t", "TARGET", money())],
    )

    # Segment attainment (pre-agg from VW — open stage2+)
    seg_att = sql_table(
        "chart-seg-att",
        "Chart · Attainment by Segment",
        """
SELECT
  CASE
    WHEN CONTAINS("Segment", 'Core') THEN 'Core'
    WHEN CONTAINS("Segment", 'Mid') OR "Segment" = 'MM' THEN 'Mid-Market'
    WHEN CONTAINS("Segment", 'Enterprise') OR CONTAINS("Segment", 'Up-Market') THEN 'Enterprise'
    ELSE 'Other'
  END AS NEW_SEGMENT,
  COUNT(DISTINCT ID) AS OPPS,
  COALESCE(SUM(CASE WHEN FCST_NETACV BETWEEN 0 AND 5000000 THEN FCST_NETACV ELSE 0 END),0) AS ACV
FROM BI_PRESENTATION.REPORT.VW_PIPELINE
WHERE "Is Closed" = FALSE
  AND LEFT("Stage Name",1) IN ('2','3','4','5','6','7')
GROUP BY 1
""",
        [
            ("sa-s", "NEW_SEGMENT", None),
            ("sa-o", "OPPS", None),
            ("sa-a", "ACV", money()),
        ],
    )

    els = [
        kpi_open,
        kpi_created,
        kpi_walkin,
        kpi_closed,
        kpi_sourcing,
        funnel,
        open_month,
        open_prod,
        created_month,
        snap,
        pace_long,
        goals,
        seg,
        seg_att,
    ]

    return {
        "name": "Pipeline Tracker FY2026 · Model",
        "folderId": FOLDER,
        "schemaVersion": 1,
        "pages": [
            {
                "id": "page-kpis",
                "name": "01 KPIs (1-row)",
                "elements": [e for e in els if e["id"].startswith("kpi-")],
            },
            {
                "id": "page-charts",
                "name": "02 Charts",
                "elements": [
                    e
                    for e in els
                    if e["id"].startswith("funnel")
                    or e["id"].startswith("chart")
                    or e["id"].startswith("snap")
                    or e["id"].startswith("pace")
                ],
            },
            {
                "id": "page-dims",
                "name": "03 Dims",
                "elements": [e for e in els if e["id"].startswith("dim-")],
            },
        ],
    }


def main():
    body = build()
    with open("/tmp/zywave-pt-dm-create.json", "w") as f:
        json.dump(body, f)
    sql_chars = sum(
        len(e["source"]["statement"])
        for p in body["pages"]
        for e in p["elements"]
        if e["source"]["kind"] == "sql"
    )
    n = sum(len(p["elements"]) for p in body["pages"])
    print(f"creating DM elements={n} sql_chars={sql_chars}")
    try:
        resp = api("POST", "/v2/dataModels/spec", body)
    except RuntimeError as e:
        print("ERR", str(e)[:6000])
        raise SystemExit(1)
    dm_id = resp.get("dataModelId")
    print("created", resp)
    spec = api("GET", f"/v2/dataModels/{dm_id}/spec")
    by_name = {}
    for p in spec.get("pages", []):
        for e in p.get("elements", []):
            if isinstance(e, dict) and e.get("name"):
                by_name[e["name"]] = e["id"]
    out = {
        "dataModelId": dm_id,
        "url": f"https://app.sigmacomputing.com/zywave/data-model/{dm_id}",
        "byName": by_name,
        "elements": {e["id"]: by_name.get(e["name"], e["id"]) for p in body["pages"] for e in p["elements"]},
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
