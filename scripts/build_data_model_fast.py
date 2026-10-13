#!/usr/bin/env python3
"""Ultra-fast layered DM: ONE Snowflake round-trip for all ROTB KPIs.

Was: 14 independent SQL elements → 14 warehouse queries per load.
Now: 1× rotb_pack (1 row) + 6 tiny chart grains + 2 dims.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

CONN = "e2b90d0c-34fd-4423-a4c3-0569c58f33df"
FOLDER = "5EFLG4WW7cjvngI0kCudpF"
YEAR_GOAL, Q4_GOAL = 94_600_000, 26_700_000
# Prefer updating this model in place
DM = "e9511cff-4ab8-48c4-96e0-fbf2b3b96f10"
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
        raise RuntimeError(f"{e.code}: {e.read().decode()[:12000]}") from e


def money():
    return {"kind": "number", "formatString": "$,.0f"}


def pct():
    return {"kind": "number", "formatString": ".1%"}


def sql_table(tid, name, statement, cols):
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


# Single scan of ACV for open + single scan for created + tiny walkin/closed/src
ROTB_PACK = f"""
WITH open_acv AS (
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
  WHERE METRIC_NAME = 'Forecasted Net ACV' AND STAGE_GROUP = '2-7'
),
created AS (
  SELECT
    COALESCE(SUM(CASE WHEN STAGE_2_DATETIME >= DATE '2026-01-01' AND STAGE_2_DATETIME < DATE '2027-01-01'
      THEN METRIC_VALUE ELSE 0 END),0) AS YTD_ACV,
    COALESCE(SUM(CASE WHEN STAGE_2_DATETIME >= DATE '2026-10-01' AND STAGE_2_DATETIME < DATE '2027-01-01'
      THEN METRIC_VALUE ELSE 0 END),0) AS Q4_CREATED_ACV,
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
      THEN OPPORTUNITY_ID END) AS CREATED_CLOSING_OPPS
  FROM BI_STAGING.DATA.OPPORTUNITY_ACV_METRICS
  WHERE METRIC_NAME = 'Forecasted Net ACV' AND STAGE_2_ATTAINED = TRUE
    AND STAGE_2_DATETIME >= DATE '2025-01-01'
),
walkin AS (
  SELECT COUNT(*) AS WALKIN_OPPS, COALESCE(SUM(v),0) AS WALKIN_ACV
  FROM (
    SELECT OPPORTUNITYID, MAX(FCST_NETACV) AS v
    FROM BI_STAGING.SNAPSHOT.VW_PIPELINE
    WHERE SNAPSHOTDATE = DATE '2026-10-01'
      AND LEFT(STAGE_NAME,1) IN ('2','3','4','5','6','7')
      AND CLOSE_DATE >= DATE '2026-10-01' AND CLOSE_DATE < DATE '2027-01-01'
    GROUP BY 1
    HAVING MAX(FCST_NETACV) BETWEEN 0 AND 2000000
  )
),
closed AS (
  SELECT
    COALESCE(SUM(CASE WHEN "Is Won" THEN NETACV__C ELSE 0 END),0) AS WON_ACV,
    COUNT(DISTINCT CASE WHEN "Is Won" THEN ID END) AS WON_OPPS,
    COALESCE(SUM(CASE WHEN NOT "Is Won" AND NETACV__C BETWEEN 0 AND 50000 THEN NETACV__C ELSE 0 END),0) AS LOST_ACV,
    COUNT(DISTINCT CASE WHEN NOT "Is Won" AND NETACV__C BETWEEN 0 AND 50000 THEN ID END) AS LOST_OPPS
  FROM BI_PRESENTATION.REPORT.VW_PIPELINE
  WHERE "Is Closed" = TRUE
    AND "Close Date" >= DATE '2026-10-01' AND "Close Date" < DATE '2027-01-01'
),
src AS (
  SELECT
    COALESCE(SUM(CASE WHEN "Lead Source" = 'Marketing' AND FCST_NETACV BETWEEN 0 AND 5000000
      THEN FCST_NETACV ELSE 0 END),0) AS MKT_ACV,
    COALESCE(SUM(CASE WHEN "Lead Source" = 'Sales Generated' AND FCST_NETACV BETWEEN 0 AND 5000000
      THEN FCST_NETACV ELSE 0 END),0) AS SALES_ACV
  FROM BI_PRESENTATION.REPORT.VW_PIPELINE
  WHERE "Is Closed" = FALSE
    AND LEFT("Stage Name",1) IN ('2','3','4','5','6','7')
)
SELECT
  o.*,
  c.YTD_ACV, c.Q4_CREATED_ACV, c.WEEK_ACV, c.WEEK_OPPS, c.CREATED_CLOSING_ACV, c.CREATED_CLOSING_OPPS,
  w.WALKIN_OPPS, w.WALKIN_ACV,
  z.WON_ACV, z.WON_OPPS, z.LOST_ACV, z.LOST_OPPS,
  s.MKT_ACV, s.SALES_ACV,
  {YEAR_GOAL}::FLOAT AS YEAR_GOAL,
  {Q4_GOAL}::FLOAT AS Q4_GOAL,
  LEAST(1, DATEDIFF(day, DATE '2026-01-01', CURRENT_DATE()) / 365.0) AS YEAR_ELAPSED,
  LEAST(1, GREATEST(0, DATEDIFF(day, DATE '2026-10-01', CURRENT_DATE()) / 92.0)) AS Q4_ELAPSED,
  c.YTD_ACV / {YEAR_GOAL} AS YEAR_PCT_GOAL,
  c.Q4_CREATED_ACV / {Q4_GOAL} AS Q4_PCT_GOAL
FROM open_acv o
CROSS JOIN created c
CROSS JOIN walkin w
CROSS JOIN closed z
CROSS JOIN src s
"""


def build_elements():
    m, p = money, pct
    rotb_cols = [
        ("TOTAL_OPPS", None), ("TOTAL_ACV", m()), ("Q4_OPPS", None), ("Q4_ACV", m()),
        ("NQ_OPPS", None), ("NQ_ACV", m()), ("Q2OUT_OPPS", None), ("Q2OUT_ACV", m()),
        ("CLOSE_CY_ACV", m()), ("CLOSE_NY_ACV", m()), ("CLOSE_FY_ACV", m()),
        ("YTD_ACV", m()), ("Q4_CREATED_ACV", m()), ("WEEK_ACV", m()), ("WEEK_OPPS", None),
        ("CREATED_CLOSING_ACV", m()), ("CREATED_CLOSING_OPPS", None),
        ("WALKIN_OPPS", None), ("WALKIN_ACV", m()),
        ("WON_ACV", m()), ("WON_OPPS", None), ("LOST_ACV", m()), ("LOST_OPPS", None),
        ("MKT_ACV", m()), ("SALES_ACV", m()),
        ("YEAR_GOAL", m()), ("Q4_GOAL", m()),
        ("YEAR_ELAPSED", p()), ("Q4_ELAPSED", p()),
        ("YEAR_PCT_GOAL", p()), ("Q4_PCT_GOAL", p()),
    ]
    els = [
        sql_table(
            "kpi-rotb",
            "KPI ROTB Pack",
            ROTB_PACK,
            [(f"r{i}", n, f) for i, (n, f) in enumerate(rotb_cols)],
        ),
        # Pace strip long — same WITH body reused but only 4 rows (tiny)
        sql_table(
            "pace-long",
            "Chart Pace Strip",
            f"""
WITH created AS (
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
  SELECT 'Year' AS METRIC, 'Actual' AS PART, LEAST(1, YTD/{YEAR_GOAL}) AS VAL,
    LEAST(1, DATEDIFF(day, DATE '2026-01-01', CURRENT_DATE())/365.0) AS PACED FROM created
  UNION ALL SELECT 'Year','Remain', GREATEST(0,1-LEAST(1,YTD/{YEAR_GOAL})),
    LEAST(1, DATEDIFF(day, DATE '2026-01-01', CURRENT_DATE())/365.0) FROM created
  UNION ALL SELECT 'Q4','Actual', LEAST(1, Q4/{Q4_GOAL}),
    LEAST(1, GREATEST(0, DATEDIFF(day, DATE '2026-10-01', CURRENT_DATE())/92.0)) FROM created
  UNION ALL SELECT 'Q4','Remain', GREATEST(0,1-LEAST(1,Q4/{Q4_GOAL})),
    LEAST(1, GREATEST(0, DATEDIFF(day, DATE '2026-10-01', CURRENT_DATE())/92.0)) FROM created
)
""",
            [("a", "METRIC", None), ("b", "PART", None), ("c", "VAL", p()), ("d", "PACED", p())],
        ),
        sql_table(
            "funnel-q4",
            "Chart Q4 Funnel",
            """
SELECT STAGE,
  CASE STAGE
    WHEN '2 - Analysis' THEN 2 WHEN '3 - Executive Alignment' THEN 3
    WHEN '4 - Solution Validation' THEN 4 WHEN '5 - Negotiate' THEN 5
    WHEN '6 - Finance Hold' THEN 6 WHEN '7 - Finance Review' THEN 7 ELSE 99 END AS ORD,
  COUNT(DISTINCT OPPORTUNITY_ID) AS OPPS,
  COALESCE(SUM(METRIC_VALUE),0) AS ACV
FROM BI_STAGING.DATA.OPPORTUNITY_ACV_METRICS
WHERE METRIC_NAME = 'Forecasted Net ACV' AND STAGE_GROUP = '2-7'
  AND CLOSE_DATE >= DATE '2026-10-01' AND CLOSE_DATE < DATE '2027-01-01'
GROUP BY 1, 2
""",
            [("a", "STAGE", None), ("b", "ORD", None), ("c", "OPPS", None), ("d", "ACV", m())],
        ),
        sql_table(
            "chart-open-month",
            "Chart Open Month Stage",
            """
SELECT DATE_TRUNC('month', CLOSE_DATE) AS CLOSE_MONTH, STAGE, COALESCE(SUM(METRIC_VALUE),0) AS ACV
FROM BI_STAGING.DATA.OPPORTUNITY_ACV_METRICS
WHERE METRIC_NAME = 'Forecasted Net ACV' AND STAGE_GROUP = '2-7'
  AND CLOSE_DATE >= DATE '2026-07-01' AND CLOSE_DATE < DATE '2028-01-01'
GROUP BY 1, 2
""",
            [
                ("a", "CLOSE_MONTH", {"kind": "datetime", "formatString": "%b %Y"}),
                ("b", "STAGE", None),
                ("c", "ACV", m()),
            ],
        ),
        sql_table(
            "chart-open-prod",
            "Chart Open Product",
            """
SELECT COALESCE(NULLIF(PRODUCT_CATEGORY,''),'Uncategorized') AS PRODUCT_CATEGORY,
  COALESCE(SUM(METRIC_VALUE),0) AS ACV
FROM BI_STAGING.DATA.OPPORTUNITY_ACV_METRICS
WHERE METRIC_NAME = 'Forecasted Net ACV' AND STAGE_GROUP = '2-7'
GROUP BY 1 ORDER BY 2 DESC LIMIT 20
""",
            [("a", "PRODUCT_CATEGORY", None), ("b", "ACV", m())],
        ),
        sql_table(
            "chart-created-month",
            "Chart Created Month",
            """
SELECT DATE_TRUNC('month', STAGE_2_DATETIME) AS MONTH,
  COALESCE(SUM(METRIC_VALUE),0) AS ACV
FROM BI_STAGING.DATA.OPPORTUNITY_ACV_METRICS
WHERE METRIC_NAME = 'Forecasted Net ACV' AND STAGE_2_ATTAINED = TRUE
  AND STAGE_2_DATETIME >= DATE '2025-01-01'
GROUP BY 1
""",
            [
                ("a", "MONTH", {"kind": "datetime", "formatString": "%b %Y"}),
                ("b", "ACV", m()),
            ],
        ),
        sql_table(
            "snap-daily",
            "Chart Snapshot Trend",
            """
SELECT SNAPSHOTDATE,
  SUM(CASE WHEN FCST_NETACV BETWEEN 0 AND 2000000 THEN FCST_NETACV ELSE 0 END) AS FCST_NETACV
FROM BI_STAGING.SNAPSHOT.VW_PIPELINE
WHERE SNAPSHOTDATE >= DATE '2026-07-01'
  AND LEFT(STAGE_NAME,1) IN ('2','3','4','5','6','7')
GROUP BY 1
""",
            [
                ("a", "SNAPSHOTDATE", {"kind": "datetime", "formatString": "%b %d"}),
                ("b", "FCST_NETACV", m()),
            ],
        ),
        # Target vs Actual melted — Total Company still
        sql_table(
            "chart-seg-tv",
            "Chart Segment Target vs Actual",
            """
WITH act AS (
  SELECT
    CASE
      WHEN CONTAINS("Segment",'Core') THEN 'Core'
      WHEN CONTAINS("Segment",'Mid') OR "Segment"='MM' THEN 'Mid-Market'
      WHEN CONTAINS("Segment",'Enterprise') OR CONTAINS("Segment",'Up-Market') THEN 'Enterprise'
      ELSE 'Other'
    END AS SEG,
    COALESCE(SUM(CASE WHEN FCST_NETACV BETWEEN 0 AND 5000000 THEN FCST_NETACV ELSE 0 END),0) AS ACTUAL
  FROM BI_PRESENTATION.REPORT.VW_PIPELINE
  WHERE "Is Closed"=FALSE AND LEFT("Stage Name",1) IN ('2','3','4','5','6','7')
  GROUP BY 1
),
tgt AS (
  SELECT * FROM (
    SELECT 'Core' AS SEG, 18000000::FLOAT AS TARGET
    UNION ALL SELECT 'Mid-Market', 16000000
    UNION ALL SELECT 'Enterprise', 20000000
  )
)
SELECT t.SEG AS SEG, 'Target' AS SERIES, t.TARGET AS VAL
FROM tgt t WHERE t.SEG <> 'Other'
UNION ALL
SELECT a.SEG, 'Actual', a.ACTUAL FROM act a WHERE a.SEG <> 'Other'
""",
            [("a", "SEG", None), ("b", "SERIES", None), ("c", "VAL", m())],
        ),
        sql_table(
            "chart-prod-tv",
            "Chart Product Target vs Actual",
            """
WITH act AS (
  SELECT
    CASE
      WHEN CONTAINS("Product Category",'Analytics') OR CONTAINS("Product Category",'Marketing')
        OR CONTAINS("Product Category",'Client') OR CONTAINS("Product Category",'Content')
        THEN 'Insurance Intelligence'
      WHEN CONTAINS("Product Category",'RQC') OR CONTAINS("Product Category",'AMS')
        OR CONTAINS("Product Category",'Service') THEN 'RQC & AMS'
      ELSE 'Platform Sales'
    END AS PGRP,
    COALESCE(SUM(CASE WHEN FCST_NETACV BETWEEN 0 AND 5000000 THEN FCST_NETACV ELSE 0 END),0) AS ACTUAL
  FROM BI_PRESENTATION.REPORT.VW_PIPELINE
  WHERE "Is Closed"=FALSE AND LEFT("Stage Name",1) IN ('2','3','4','5','6','7')
  GROUP BY 1
),
tgt AS (
  SELECT * FROM (
    SELECT 'Insurance Intelligence' AS PGRP, 31000000::FLOAT AS TARGET
    UNION ALL SELECT 'RQC & AMS', 22000000
    UNION ALL SELECT 'Platform Sales', 1000000
  )
)
SELECT t.PGRP AS PGRP, 'Target' AS SERIES, t.TARGET AS VAL FROM tgt t
UNION ALL
SELECT a.PGRP, 'Actual', a.ACTUAL FROM act a
""",
            [("a", "PGRP", None), ("b", "SERIES", None), ("c", "VAL", m())],
        ),
        sql_table(
            "kpi-sourcing",
            "KPI Sourcing Mix",
            """
SELECT
  CASE WHEN "Lead Source"='Marketing' THEN 'Marketing'
       WHEN "Lead Source"='Sales Generated' THEN 'Sales' ELSE 'Other' END AS SOURCE_BUCKET,
  COUNT(DISTINCT ID) AS OPPS,
  COALESCE(SUM(CASE WHEN FCST_NETACV BETWEEN 0 AND 5000000 THEN FCST_NETACV ELSE 0 END),0) AS ACV
FROM BI_PRESENTATION.REPORT.VW_PIPELINE
WHERE "Is Closed"=FALSE AND LEFT("Stage Name",1) IN ('2','3','4','5','6','7')
GROUP BY 1
""",
            [("a", "SOURCE_BUCKET", None), ("b", "OPPS", None), ("c", "ACV", m())],
        ),
    ]
    return els


def main():
    els = build_elements()
    body = {
        "name": "Pipeline Tracker FY2026 · Model",
        "folderId": FOLDER,
        "schemaVersion": 1,
        "pages": [
            {"id": "page-kpis", "name": "01 KPIs", "elements": [e for e in els if e["id"].startswith("kpi")]},
            {
                "id": "page-charts",
                "name": "02 Charts",
                "elements": [e for e in els if not e["id"].startswith("kpi")],
            },
        ],
    }
    sql_chars = sum(len(e["source"]["statement"]) for e in els)
    print(f"elements={len(els)} sql_chars={sql_chars}")
    with open("/tmp/zywave-pt-dm-fast.json", "w") as f:
        json.dump(body, f)

    # PUT replace existing model (full replace)
    try:
        print("PUT", api("PUT", f"/v2/dataModels/{DM}/spec", body))
        dm_id = DM
    except RuntimeError as e:
        print("PUT failed, POST new", str(e)[:2000])
        resp = api("POST", "/v2/dataModels/spec", body)
        dm_id = resp["dataModelId"]
        print("created", dm_id)

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
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
