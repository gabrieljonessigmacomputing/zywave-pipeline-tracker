#!/usr/bin/env python3
"""Lean DM: few SQL grains, each meant to run ONCE in the workbook.

Warehouse jobs explode when Sigma re-inlines custom SQL into every Sum()/table.
Keep ≤6 SQL elements; workbook must not fan one grain into many Sum() viz.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

CONN = "e2b90d0c-34fd-4423-a4c3-0569c58f33df"
FOLDER = "5EFLG4WW7cjvngI0kCudpF"
DM = "e9511cff-4ab8-48c4-96e0-fbf2b3b96f10"
YEAR_GOAL, Q4_GOAL = 94_600_000, 26_700_000
OUT = "/tmp/zywave-pt-dm.json"


def api(method, path, body=None):
    base = os.environ.get("SIGMA_BASE_URL") or os.environ["ZYWAVE_BASE_URL"]
    token = os.environ.get("SIGMA_API_TOKEN") or os.environ["ZYWAVE_API_TOKEN"]
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        f"{base}{path}", data=data, method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{e.code}: {e.read().decode()[:12000]}") from e


def money():
    return {"kind": "number", "formatString": "$,.0f"}


def pct():
    return {"kind": "number", "formatString": ".1%"}


def sql_table(tid, name, statement, cols):
    columns = []
    for i, (cname, fmt) in enumerate(cols):
        c = {"id": f"{tid}-{i}", "name": cname, "formula": f"[Custom SQL/{cname}]"}
        if fmt:
            c["format"] = fmt
        columns.append(c)
    return {
        "id": tid, "kind": "table", "name": name,
        "source": {"kind": "sql", "connectionId": CONN, "statement": statement.strip()},
        "columns": columns,
    }


def build():
    m, p = money, pct

    # 1) Pack — ACV metrics only (2 filtered scans, 1 result row)
    pack = f"""
WITH open_acv AS (
  SELECT
    COUNT(DISTINCT OPPORTUNITY_ID) AS TOTAL_OPPS,
    COALESCE(SUM(METRIC_VALUE),0) AS TOTAL_ACV,
    COUNT(DISTINCT IFF(CLOSE_DATE >= '2026-10-01' AND CLOSE_DATE < '2027-01-01', OPPORTUNITY_ID, NULL)) AS Q4_OPPS,
    COALESCE(SUM(IFF(CLOSE_DATE >= '2026-10-01' AND CLOSE_DATE < '2027-01-01', METRIC_VALUE, 0)),0) AS Q4_ACV,
    COUNT(DISTINCT IFF(CLOSE_DATE >= '2027-01-01' AND CLOSE_DATE < '2027-04-01', OPPORTUNITY_ID, NULL)) AS NQ_OPPS,
    COALESCE(SUM(IFF(CLOSE_DATE >= '2027-01-01' AND CLOSE_DATE < '2027-04-01', METRIC_VALUE, 0)),0) AS NQ_ACV,
    COUNT(DISTINCT IFF(CLOSE_DATE >= '2027-04-01' AND CLOSE_DATE < '2027-07-01', OPPORTUNITY_ID, NULL)) AS Q2OUT_OPPS,
    COALESCE(SUM(IFF(CLOSE_DATE >= '2027-04-01' AND CLOSE_DATE < '2027-07-01', METRIC_VALUE, 0)),0) AS Q2OUT_ACV,
    COALESCE(SUM(IFF(YEAR(CLOSE_DATE)=2026, METRIC_VALUE, 0)),0) AS CLOSE_CY_ACV,
    COALESCE(SUM(IFF(YEAR(CLOSE_DATE)=2027, METRIC_VALUE, 0)),0) AS CLOSE_NY_ACV,
    COALESCE(SUM(IFF(YEAR(CLOSE_DATE)>=2028, METRIC_VALUE, 0)),0) AS CLOSE_FY_ACV,
    IFF(COUNT(DISTINCT OPPORTUNITY_ID)>0,
      COALESCE(SUM(METRIC_VALUE),0)/COUNT(DISTINCT OPPORTUNITY_ID), 0) AS AVG_DEAL
  FROM BI_STAGING.DATA.OPPORTUNITY_ACV_METRICS
  WHERE METRIC_NAME = 'Forecasted Net ACV' AND STAGE_GROUP = '2-7'
),
created AS (
  SELECT
    COALESCE(SUM(IFF(STAGE_2_DATETIME >= '2026-01-01' AND STAGE_2_DATETIME < '2027-01-01', METRIC_VALUE, 0)),0) AS YTD_ACV,
    COALESCE(SUM(IFF(STAGE_2_DATETIME >= '2026-10-01' AND STAGE_2_DATETIME < '2027-01-01', METRIC_VALUE, 0)),0) AS Q4_CREATED_ACV,
    COUNT(DISTINCT IFF(STAGE_2_DATETIME >= '2026-10-01' AND STAGE_2_DATETIME < '2027-01-01', OPPORTUNITY_ID, NULL)) AS Q4_CREATED_OPPS,
    COALESCE(SUM(IFF(STAGE_2_DATETIME >= DATE_TRUNC('month', CURRENT_DATE()), METRIC_VALUE, 0)),0) AS MONTH_ACV,
    COUNT(DISTINCT IFF(STAGE_2_DATETIME >= DATE_TRUNC('month', CURRENT_DATE()), OPPORTUNITY_ID, NULL)) AS MONTH_OPPS,
    COALESCE(SUM(IFF(STAGE_2_DATETIME >= DATEADD(day,-7,CURRENT_DATE()), METRIC_VALUE, 0)),0) AS WEEK_ACV,
    COUNT(DISTINCT IFF(STAGE_2_DATETIME >= DATEADD(day,-7,CURRENT_DATE()), OPPORTUNITY_ID, NULL)) AS WEEK_OPPS,
    COALESCE(SUM(IFF(
      STAGE_2_DATETIME >= '2026-10-01' AND STAGE_2_DATETIME < '2027-01-01'
      AND CLOSE_DATE >= '2026-10-01' AND CLOSE_DATE < '2027-01-01', METRIC_VALUE, 0)),0) AS CREATED_CLOSING_ACV,
    COUNT(DISTINCT IFF(
      STAGE_2_DATETIME >= '2026-10-01' AND STAGE_2_DATETIME < '2027-01-01'
      AND CLOSE_DATE >= '2026-10-01' AND CLOSE_DATE < '2027-01-01', OPPORTUNITY_ID, NULL)) AS CREATED_CLOSING_OPPS
  FROM BI_STAGING.DATA.OPPORTUNITY_ACV_METRICS
  WHERE METRIC_NAME = 'Forecasted Net ACV' AND STAGE_2_ATTAINED = TRUE
    AND STAGE_2_DATETIME >= '2025-10-01'
)
SELECT o.*, c.*,
  {YEAR_GOAL}::FLOAT AS YEAR_GOAL, {Q4_GOAL}::FLOAT AS Q4_GOAL,
  LEAST(1, DATEDIFF(day,'2026-01-01',CURRENT_DATE())/365.0) AS YEAR_ELAPSED,
  LEAST(1, GREATEST(0, DATEDIFF(day,'2026-10-01',CURRENT_DATE())/92.0)) AS Q4_ELAPSED,
  c.YTD_ACV/{YEAR_GOAL} AS YEAR_PCT_GOAL,
  c.Q4_CREATED_ACV/{Q4_GOAL} AS Q4_PCT_GOAL,
  IFF(o.TOTAL_ACV>0, o.CLOSE_CY_ACV/o.TOTAL_ACV, 0) AS CLOSE_CY_PCT,
  IFF(o.TOTAL_ACV>0, o.CLOSE_NY_ACV/o.TOTAL_ACV, 0) AS CLOSE_NY_PCT,
  IFF(o.TOTAL_ACV>0, o.CLOSE_FY_ACV/o.TOTAL_ACV, 0) AS CLOSE_FY_PCT
FROM open_acv o CROSS JOIN created c
"""

    # 2) Walk-in — tiny snapshot (date-partitioned)
    walkin = """
SELECT COUNT(*) AS WALKIN_OPPS, COALESCE(SUM(v),0) AS WALKIN_ACV FROM (
  SELECT OPPORTUNITYID, MAX(FCST_NETACV) AS v
  FROM BI_STAGING.SNAPSHOT.VW_PIPELINE
  WHERE SNAPSHOTDATE = '2026-10-01'
    AND LEFT(STAGE_NAME,1) IN ('2','3','4','5','6','7')
    AND CLOSE_DATE >= '2026-10-01' AND CLOSE_DATE < '2027-01-01'
  GROUP BY 1 HAVING MAX(FCST_NETACV) BETWEEN 0 AND 2000000
)"""

    # 3a) Closed Q4 only — tiny date-filtered slice (was drowning in the mega VW OR)
    closed = """
SELECT
  COALESCE(SUM(IFF("Is Won", NETACV__C, 0)),0) AS WON_ACV,
  COUNT(DISTINCT IFF("Is Won", ID, NULL)) AS WON_OPPS,
  COALESCE(SUM(IFF(NOT "Is Won" AND NETACV__C BETWEEN 0 AND 50000, NETACV__C, 0)),0) AS LOST_ACV,
  COUNT(DISTINCT IFF(NOT "Is Won" AND NETACV__C BETWEEN 0 AND 50000, ID, NULL)) AS LOST_OPPS
FROM BI_PRESENTATION.REPORT.VW_PIPELINE
WHERE "Is Closed"
  AND "Close Date" >= '2026-10-01' AND "Close Date" < '2027-01-01'
"""

    # 4) Funnel — Q4 open stages only (ACV metrics)
    funnel = """
SELECT STAGE,
  CASE STAGE
    WHEN '2 - Analysis' THEN 2 WHEN '3 - Executive Alignment' THEN 3
    WHEN '4 - Solution Validation' THEN 4 WHEN '5 - Negotiate' THEN 5
    WHEN '6 - Finance Hold' THEN 6 WHEN '7 - Finance Review' THEN 7 ELSE 99 END AS ORD,
  COALESCE(SUM(METRIC_VALUE),0) AS ACV
FROM BI_STAGING.DATA.OPPORTUNITY_ACV_METRICS
WHERE METRIC_NAME='Forecasted Net ACV' AND STAGE_GROUP='2-7'
  AND CLOSE_DATE >= '2026-10-01' AND CLOSE_DATE < '2027-01-01'
GROUP BY 1,2
"""

    # 5) Created by month — short window
    created_month = """
SELECT DATE_TRUNC('month', STAGE_2_DATETIME) AS MONTH, COALESCE(SUM(METRIC_VALUE),0) AS ACV
FROM BI_STAGING.DATA.OPPORTUNITY_ACV_METRICS
WHERE METRIC_NAME='Forecasted Net ACV' AND STAGE_2_ATTAINED
  AND STAGE_2_DATETIME >= '2025-10-01'
GROUP BY 1
"""

    # 6) ONE VW open scan → charts (SEG/PROD/SRC) + KPI grain (early + sourcing)
    # Workbook derives 1-row KPI Open from this grain (no second open VW scan).
    charts = """
WITH open_all AS (
  SELECT
    LEFT("Stage Name",1) AS STAGE_N,
    CASE
      WHEN CONTAINS("Segment",'Core') THEN 'Core'
      WHEN CONTAINS("Segment",'Mid') OR "Segment"='MM' THEN 'Mid-Market'
      WHEN CONTAINS("Segment",'Enterprise') OR CONTAINS("Segment",'Up-Market') THEN 'Enterprise'
      ELSE 'Other'
    END AS SEG,
    CASE
      WHEN CONTAINS("Product Category",'Analytics') OR CONTAINS("Product Category",'Marketing')
        OR CONTAINS("Product Category",'Client') OR CONTAINS("Product Category",'Content')
        THEN 'Insurance Intelligence'
      WHEN CONTAINS("Product Category",'RQC') OR CONTAINS("Product Category",'AMS')
        OR CONTAINS("Product Category",'Service') THEN 'RQC & AMS'
      ELSE 'Platform Sales'
    END AS PGRP,
    CASE WHEN "Lead Source"='Marketing' THEN 'Marketing'
         WHEN "Lead Source"='Sales Generated' THEN 'Sales' ELSE 'Other' END AS SRC,
    CASE WHEN FCST_NETACV BETWEEN 0 AND 5000000 THEN FCST_NETACV ELSE 0 END AS ACV,
    ID
  FROM BI_PRESENTATION.REPORT.VW_PIPELINE
  WHERE NOT "Is Closed" AND LEFT("Stage Name",1) IN ('0','1','2','3','4','5','6','7')
),
open_27 AS (
  SELECT * FROM open_all WHERE STAGE_N IN ('2','3','4','5','6','7')
),
seg_act AS (
  SELECT SEG AS DIM, COALESCE(SUM(ACV),0) AS ACTUAL FROM open_27 WHERE SEG <> 'Other' GROUP BY 1
),
prod_act AS (
  SELECT PGRP AS DIM, COALESCE(SUM(ACV),0) AS ACTUAL FROM open_27 GROUP BY 1
),
src_act AS (
  SELECT SRC AS DIM, COUNT(DISTINCT ID) AS OPPS, COALESCE(SUM(ACV),0) AS ACTUAL FROM open_27 GROUP BY 1
),
kpi AS (
  SELECT
    COALESCE(SUM(IFF(STAGE_N IN ('2','3','4','5','6','7') AND SRC='Marketing', ACV, 0)),0) AS MKT_ACV,
    COALESCE(SUM(IFF(STAGE_N IN ('2','3','4','5','6','7') AND SRC='Sales', ACV, 0)),0) AS SALES_ACV,
    COUNT(DISTINCT IFF(STAGE_N='0', ID, NULL)) AS S0_OPPS,
    COALESCE(SUM(IFF(STAGE_N='0', ACV, 0)),0) AS S0_ACV,
    COUNT(DISTINCT IFF(STAGE_N='1', ID, NULL)) AS S1_OPPS,
    COALESCE(SUM(IFF(STAGE_N='1', ACV, 0)),0) AS S1_ACV,
    COUNT(DISTINCT IFF(STAGE_N='2', ID, NULL)) AS S2_OPPS,
    COALESCE(SUM(IFF(STAGE_N='2', ACV, 0)),0) AS S2_ACV
  FROM open_all
)
SELECT 'SEG' AS GRAIN, t.DIM, 'Target' AS SERIES, t.TARGET AS VAL, NULL::FLOAT AS OPPS
FROM (
  SELECT 'Core' AS DIM, 18000000::FLOAT AS TARGET
  UNION ALL SELECT 'Mid-Market', 16000000
  UNION ALL SELECT 'Enterprise', 20000000
) t
UNION ALL
SELECT 'SEG', a.DIM, 'Actual', a.ACTUAL, NULL FROM seg_act a
UNION ALL
SELECT 'PROD', t.DIM, 'Target', t.TARGET, NULL FROM (
  SELECT 'Insurance Intelligence' AS DIM, 31000000::FLOAT AS TARGET
  UNION ALL SELECT 'RQC & AMS', 22000000
  UNION ALL SELECT 'Platform Sales', 1000000
) t
UNION ALL
SELECT 'PROD', a.DIM, 'Actual', a.ACTUAL, NULL FROM prod_act a
UNION ALL
SELECT 'SRC', a.DIM, 'Actual', a.ACTUAL, a.OPPS::FLOAT FROM src_act a
UNION ALL
SELECT 'KPI', 'MKT', 'Actual', k.MKT_ACV, NULL FROM kpi k
UNION ALL
SELECT 'KPI', 'SALES', 'Actual', k.SALES_ACV, NULL FROM kpi k
UNION ALL
SELECT 'KPI', 'S0', 'Actual', k.S0_ACV, k.S0_OPPS::FLOAT FROM kpi k
UNION ALL
SELECT 'KPI', 'S1', 'Actual', k.S1_ACV, k.S1_OPPS::FLOAT FROM kpi k
UNION ALL
SELECT 'KPI', 'S2', 'Actual', k.S2_ACV, k.S2_OPPS::FLOAT FROM kpi k
"""

    pack_cols = [
        ("TOTAL_OPPS", None), ("TOTAL_ACV", m()), ("Q4_OPPS", None), ("Q4_ACV", m()),
        ("NQ_OPPS", None), ("NQ_ACV", m()), ("Q2OUT_OPPS", None), ("Q2OUT_ACV", m()),
        ("CLOSE_CY_ACV", m()), ("CLOSE_NY_ACV", m()), ("CLOSE_FY_ACV", m()), ("AVG_DEAL", m()),
        ("YTD_ACV", m()), ("Q4_CREATED_ACV", m()), ("Q4_CREATED_OPPS", None),
        ("MONTH_ACV", m()), ("MONTH_OPPS", None),
        ("WEEK_ACV", m()), ("WEEK_OPPS", None),
        ("CREATED_CLOSING_ACV", m()), ("CREATED_CLOSING_OPPS", None),
        ("YEAR_GOAL", m()), ("Q4_GOAL", m()),
        ("YEAR_ELAPSED", p()), ("Q4_ELAPSED", p()),
        ("YEAR_PCT_GOAL", p()), ("Q4_PCT_GOAL", p()),
        ("CLOSE_CY_PCT", p()), ("CLOSE_NY_PCT", p()), ("CLOSE_FY_PCT", p()),
    ]
    closed_cols = [
        ("WON_ACV", m()), ("WON_OPPS", None), ("LOST_ACV", m()), ("LOST_OPPS", None),
    ]
    # Daily open ACV trend — date-filtered snapshot (one job for Movement)
    snap = """
SELECT SNAPSHOTDATE AS DT, COALESCE(SUM(FCST_NETACV),0) AS ACV
FROM BI_STAGING.SNAPSHOT.VW_PIPELINE
WHERE SNAPSHOTDATE >= DATEADD(day, -60, CURRENT_DATE())
  AND LEFT(STAGE_NAME,1) IN ('2','3','4','5','6','7')
  AND FCST_NETACV BETWEEN 0 AND 5000000
GROUP BY 1
"""

    return [
        sql_table("kpi-pack", "KPI Pack", pack, pack_cols),
        sql_table("kpi-walkin", "KPI Walkin", walkin, [("WALKIN_OPPS", None), ("WALKIN_ACV", m())]),
        sql_table("kpi-closed", "KPI Closed Q4", closed, closed_cols),
        # ONE open VW scan — charts + KPI grain (early/sourcing). Workbook reads KPIs via plugin.
        sql_table("chart-tv", "Chart Target Actual Source", charts, [
            ("GRAIN", None), ("DIM", None), ("SERIES", None), ("VAL", m()), ("OPPS", None)]),
        sql_table("chart-funnel", "Chart Funnel", funnel, [
            ("STAGE", None), ("ORD", None), ("ACV", m())]),
        sql_table("chart-created", "Chart Created", created_month, [
            ("MONTH", {"kind": "datetime", "formatString": "%b %Y"}), ("ACV", m())]),
        sql_table("chart-snap", "Chart Snapshot Trend", snap, [
            ("DT", {"kind": "datetime", "formatString": "%b %d"}), ("ACV", m())]),
    ]


def main():
    els = build()
    body = {
        "name": "Pipeline Tracker FY2026 · Model",
        "folderId": FOLDER,
        "schemaVersion": 1,
        "pages": [{"id": "page-main", "name": "Sources", "elements": els}],
    }
    nchar = sum(len(e.get("source", {}).get("statement") or "") for e in els)
    print("elements", len(els), "sql_chars", nchar)
    print("PUT", api("PUT", f"/v2/dataModels/{DM}/spec", body))
    spec = api("GET", f"/v2/dataModels/{DM}/spec")
    by = {}
    for p in spec.get("pages", []):
        for e in p.get("elements", []):
            if isinstance(e, dict):
                by[e.get("name")] = e.get("id")
    out = {"dataModelId": DM, "byName": by}
    json.dump(out, open(OUT, "w"), indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
