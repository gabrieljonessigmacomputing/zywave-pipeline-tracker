#!/usr/bin/env python3
"""Lean DM: few SQL grains, each meant to run ONCE in the workbook.

Warehouse jobs explode when Sigma re-inlines custom SQL into every Sum()/table.
Keep ≤8 SQL elements; workbook must not fan one grain into many Sum() viz.
Open-VW (kpi-src) stays Sourcing-only; closemo/product are ACV + Open-only.
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
WITH open_opps AS (
  SELECT OPPORTUNITY_ID,
    COALESCE(SUM(METRIC_VALUE),0) AS ACV,
    MIN(CLOSE_DATE) AS CLOSE_DATE,
    COUNT(*) AS LINES
  FROM BI_STAGING.DATA.OPPORTUNITY_ACV_METRICS
  WHERE METRIC_NAME = 'Forecasted Net ACV' AND STAGE_GROUP = '2-7'
    AND METRIC_VALUE BETWEEN 0 AND 5000000
  GROUP BY 1
),
open_acv AS (
  SELECT
    COUNT(*) AS TOTAL_OPPS,
    COALESCE(SUM(ACV),0) AS TOTAL_ACV,
    COALESCE(SUM(LINES),0) AS DEAL_PRODUCT_LINES,
    COUNT(IFF(CLOSE_DATE >= '2026-10-01' AND CLOSE_DATE < '2027-01-01', 1, NULL)) AS Q4_OPPS,
    COALESCE(SUM(IFF(CLOSE_DATE >= '2026-10-01' AND CLOSE_DATE < '2027-01-01', ACV, 0)),0) AS Q4_ACV,
    COUNT(IFF(CLOSE_DATE >= '2027-01-01' AND CLOSE_DATE < '2027-04-01', 1, NULL)) AS NQ_OPPS,
    COALESCE(SUM(IFF(CLOSE_DATE >= '2027-01-01' AND CLOSE_DATE < '2027-04-01', ACV, 0)),0) AS NQ_ACV,
    COUNT(IFF(CLOSE_DATE >= '2027-04-01' AND CLOSE_DATE < '2027-07-01', 1, NULL)) AS Q2OUT_OPPS,
    COALESCE(SUM(IFF(CLOSE_DATE >= '2027-04-01' AND CLOSE_DATE < '2027-07-01', ACV, 0)),0) AS Q2OUT_ACV,
    COALESCE(SUM(IFF(YEAR(CLOSE_DATE)=2026, ACV, 0)),0) AS CLOSE_CY_ACV,
    COALESCE(SUM(IFF(YEAR(CLOSE_DATE)=2027, ACV, 0)),0) AS CLOSE_NY_ACV,
    COALESCE(SUM(IFF(YEAR(CLOSE_DATE)>=2028, ACV, 0)),0) AS CLOSE_FY_ACV,
    IFF(COUNT(*)>0, COALESCE(SUM(ACV),0)/COUNT(*), 0) AS AVG_DEAL,
    COUNT(IFF(ACV >= 50000, 1, NULL)) AS LARGE_OPPS,
    COUNT(IFF(ACV < 50000, 1, NULL)) AS SMALL_OPPS,
    COALESCE(SUM(IFF(ACV >= 50000, ACV, 0)),0) AS LARGE_ACV,
    COALESCE(SUM(IFF(ACV < 50000, ACV, 0)),0) AS SMALL_ACV
  FROM open_opps
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
),
closed AS (
  SELECT
    COALESCE(SUM(IFF(STAGE_GROUP = 'Won' AND METRIC_VALUE BETWEEN 0 AND 5000000, METRIC_VALUE, 0)), 0) AS WON_ACV,
    COUNT(DISTINCT IFF(STAGE_GROUP = 'Won' AND METRIC_VALUE BETWEEN 0 AND 5000000, OPPORTUNITY_ID, NULL)) AS WON_OPPS,
    COALESCE(SUM(IFF(STAGE_GROUP = 'Lost' AND METRIC_VALUE BETWEEN 0 AND 50000, METRIC_VALUE, 0)), 0) AS LOST_ACV,
    COUNT(DISTINCT IFF(STAGE_GROUP = 'Lost' AND METRIC_VALUE BETWEEN 0 AND 50000, OPPORTUNITY_ID, NULL)) AS LOST_OPPS,
    COALESCE(SUM(IFF(
      STAGE_GROUP = 'Won' AND METRIC_VALUE BETWEEN 0 AND 5000000
      AND STAGE_2_DATETIME >= '2026-10-01' AND STAGE_2_DATETIME < '2027-01-01',
      METRIC_VALUE, 0)), 0) AS CREATED_WON_ACV,
    COUNT(DISTINCT IFF(
      STAGE_GROUP = 'Won' AND METRIC_VALUE BETWEEN 0 AND 5000000
      AND STAGE_2_DATETIME >= '2026-10-01' AND STAGE_2_DATETIME < '2027-01-01',
      OPPORTUNITY_ID, NULL)) AS CREATED_WON_OPPS
  FROM BI_STAGING.DATA.OPPORTUNITY_ACV_METRICS
  WHERE METRIC_NAME = 'Forecasted Net ACV'
    AND STAGE_GROUP IN ('Won', 'Lost')
    AND CLOSE_DATE >= '2026-10-01' AND CLOSE_DATE < '2027-01-01'
),
early AS (
  SELECT
    COUNT(DISTINCT IFF(LEFT(STAGE,1)='0' AND METRIC_VALUE BETWEEN 0 AND 5000000, OPPORTUNITY_ID, NULL)) AS S0_OPPS,
    COALESCE(SUM(IFF(LEFT(STAGE,1)='0' AND METRIC_VALUE BETWEEN 0 AND 5000000, METRIC_VALUE, 0)),0) AS S0_ACV,
    COUNT(DISTINCT IFF(LEFT(STAGE,1)='1' AND METRIC_VALUE BETWEEN 0 AND 5000000, OPPORTUNITY_ID, NULL)) AS S1_OPPS,
    COALESCE(SUM(IFF(LEFT(STAGE,1)='1' AND METRIC_VALUE BETWEEN 0 AND 5000000, METRIC_VALUE, 0)),0) AS S1_ACV,
    COUNT(DISTINCT IFF(LEFT(STAGE,1)='2' AND METRIC_VALUE BETWEEN 0 AND 5000000, OPPORTUNITY_ID, NULL)) AS S2_OPPS,
    COALESCE(SUM(IFF(LEFT(STAGE,1)='2' AND METRIC_VALUE BETWEEN 0 AND 5000000, METRIC_VALUE, 0)),0) AS S2_ACV
  FROM BI_STAGING.DATA.OPPORTUNITY_ACV_METRICS
  WHERE METRIC_NAME = 'Forecasted Net ACV'
    AND LEFT(STAGE,1) IN ('0','1','2')
),
-- Tiny snapshot join — same freeze as kpi-walkin (keeps bridge residual on pack).
walkin AS (
  SELECT COUNT(*) AS WALKIN_OPPS, COALESCE(SUM(v),0) AS WALKIN_ACV FROM (
    SELECT OPPORTUNITYID, MAX(FCST_NETACV) AS v
    FROM BI_STAGING.SNAPSHOT.VW_PIPELINE
    WHERE SNAPSHOTDATE = '2026-10-01'
      AND LEFT(STAGE_NAME,1) IN ('2','3','4','5','6','7')
      AND CLOSE_DATE >= '2026-10-01' AND CLOSE_DATE < '2027-01-01'
    GROUP BY 1 HAVING MAX(FCST_NETACV) BETWEEN 0 AND 2000000
  )
)
SELECT o.*, c.*, z.*, e.*,
  {YEAR_GOAL}::FLOAT AS YEAR_GOAL, {Q4_GOAL}::FLOAT AS Q4_GOAL,
  LEAST(1, DATEDIFF(day,'2026-01-01',CURRENT_DATE())/365.0) AS YEAR_ELAPSED,
  LEAST(1, GREATEST(0, DATEDIFF(day,'2026-10-01',CURRENT_DATE())/92.0)) AS Q4_ELAPSED,
  c.YTD_ACV/{YEAR_GOAL} AS YEAR_PCT_GOAL,
  c.Q4_CREATED_ACV/{Q4_GOAL} AS Q4_PCT_GOAL,
  IFF(o.TOTAL_ACV>0, o.CLOSE_CY_ACV/o.TOTAL_ACV, 0) AS CLOSE_CY_PCT,
  IFF(o.TOTAL_ACV>0, o.CLOSE_NY_ACV/o.TOTAL_ACV, 0) AS CLOSE_NY_PCT,
  IFF(o.TOTAL_ACV>0, o.CLOSE_FY_ACV/o.TOTAL_ACV, 0) AS CLOSE_FY_PCT,
  w.WALKIN_OPPS AS PACK_WALKIN_OPPS, w.WALKIN_ACV AS PACK_WALKIN_ACV,
  -- Coverage: open ACV / creation goals (stills Coverage page)
  IFF({Q4_GOAL}>0, o.Q4_ACV/{Q4_GOAL}, 0) AS Q4_COVERAGE,
  IFF({YEAR_GOAL}>0, o.TOTAL_ACV/{YEAR_GOAL}, 0) AS YEAR_COVERAGE,
  -- Bridge residual (stills "Other Adjustments"): open − (walk-in + created − won − lost)
  o.TOTAL_ACV - (w.WALKIN_ACV + c.Q4_CREATED_ACV - z.WON_ACV - z.LOST_ACV) AS OTHER_ADJ_ACV,
  o.Q4_ACV - (w.WALKIN_ACV + c.Q4_CREATED_ACV - z.WON_ACV - z.LOST_ACV) AS Q4_OTHER_ADJ_ACV
FROM open_acv o
CROSS JOIN created c
CROSS JOIN closed z
CROSS JOIN early e
CROSS JOIN walkin w
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

    # 3) Open sourcing + SEG — Sourcing page only (never bind on ROTB/Open/Total/Created).
    # Column-prune then agg. Segment labels often include prefixes (e.g. "1 - Core").
    src_kpi = """
WITH base AS (
  SELECT
    "Lead Source" AS LEAD_SRC,
    -- Market tier is often a pipe token inside Segment/SplitSegment (e.g. "... | Core").
    COALESCE(NULLIF(TRIM("SplitSegment"), ''), NULLIF(TRIM("Segment"), '')) AS SEG,
    -- Stills: New Logo / Cross-Sell — presentation VW column is "Opp Type".
    "Opp Type" AS DEAL_TYPE,
    FCST_NETACV AS ACV
  FROM BI_PRESENTATION.REPORT.VW_PIPELINE
  WHERE NOT "Is Closed"
    AND LEFT("Stage Name", 1) IN ('2', '3', '4', '5', '6', '7')
    AND FCST_NETACV BETWEEN 0 AND 5000000
    -- Bound close window (matches pack horizons) so VW scan stays smaller.
    AND "Close Date" >= '2026-10-01' AND "Close Date" < '2027-07-01'
),
tagged AS (
  SELECT
    LEAD_SRC, ACV, SEG, DEAL_TYPE,
    CASE
      WHEN SEG IS NULL THEN NULL
      WHEN CONTAINS(UPPER(SEG), 'MID-MARKET') OR CONTAINS(UPPER(SEG), 'MID MARKET')
        OR SEG = 'MM' OR CONTAINS(UPPER(SEG), '| MID') THEN 'Mid-Market'
      WHEN CONTAINS(UPPER(SEG), 'ENTERPRISE') OR CONTAINS(UPPER(SEG), 'UP-MARKET')
        OR CONTAINS(UPPER(SEG), 'UP MARKET') OR CONTAINS(UPPER(SEG), 'UPMARKET') THEN 'Enterprise'
      WHEN CONTAINS(UPPER(SEG), 'CORE') THEN 'Core'
      ELSE NULL
    END AS MKT_SEG,
    CASE
      WHEN DEAL_TYPE IS NULL THEN 'Uncategorized'
      WHEN CONTAINS(UPPER(DEAL_TYPE), 'NEW LOGO') OR CONTAINS(UPPER(DEAL_TYPE), 'NEW BUSINESS')
        OR CONTAINS(UPPER(DEAL_TYPE), 'NEWLOGO') THEN 'New Logo'
      WHEN CONTAINS(UPPER(DEAL_TYPE), 'CROSS') OR CONTAINS(UPPER(DEAL_TYPE), 'EXPAN')
        OR CONTAINS(UPPER(DEAL_TYPE), 'UPSELL') OR CONTAINS(UPPER(DEAL_TYPE), 'UP-SELL')
        OR CONTAINS(UPPER(DEAL_TYPE), 'EXISTING') OR CONTAINS(UPPER(DEAL_TYPE), 'ADD-ON')
        OR CONTAINS(UPPER(DEAL_TYPE), 'ADDON') OR CONTAINS(UPPER(DEAL_TYPE), 'PRODUCT ADD')
        THEN 'Cross-Sell'
      ELSE 'Uncategorized'
    END AS DEAL_BUCKET
  FROM base
)
SELECT
  COALESCE(SUM(IFF(LEAD_SRC = 'Marketing', ACV, 0)), 0) AS MKT_ACV,
  COALESCE(SUM(IFF(LEAD_SRC = 'Sales Generated', ACV, 0)), 0) AS SALES_ACV,
  COALESCE(SUM(IFF(LEAD_SRC IN ('Marketing', 'Sales Generated'), ACV, 0)), 0) AS SRC_TOTAL_ACV,
  IFF(
    COALESCE(SUM(IFF(LEAD_SRC IN ('Marketing', 'Sales Generated'), ACV, 0)), 0) > 0,
    COALESCE(SUM(IFF(LEAD_SRC = 'Marketing', ACV, 0)), 0)
      / COALESCE(SUM(IFF(LEAD_SRC IN ('Marketing', 'Sales Generated'), ACV, 0)), 0),
    0) AS MKT_MIX,
  IFF(
    COALESCE(SUM(IFF(LEAD_SRC IN ('Marketing', 'Sales Generated'), ACV, 0)), 0) > 0,
    COALESCE(SUM(IFF(LEAD_SRC = 'Sales Generated', ACV, 0)), 0)
      / COALESCE(SUM(IFF(LEAD_SRC IN ('Marketing', 'Sales Generated'), ACV, 0)), 0),
    0) AS SALES_MIX,
  COALESCE(SUM(IFF(MKT_SEG = 'Core', ACV, 0)), 0) AS SEG_CORE,
  COALESCE(SUM(IFF(MKT_SEG = 'Mid-Market', ACV, 0)), 0) AS SEG_MID,
  COALESCE(SUM(IFF(MKT_SEG = 'Enterprise', ACV, 0)), 0) AS SEG_ENT,
  COALESCE(SUM(IFF(MKT_SEG IS NULL, ACV, 0)), 0) AS SEG_UNMAPPED,
  COALESCE(SUM(IFF(MKT_SEG = 'Core' AND LEAD_SRC = 'Marketing', ACV, 0)), 0) AS CORE_MKT,
  COALESCE(SUM(IFF(MKT_SEG = 'Core' AND LEAD_SRC = 'Sales Generated', ACV, 0)), 0) AS CORE_SALES,
  COALESCE(SUM(IFF(MKT_SEG = 'Mid-Market' AND LEAD_SRC = 'Marketing', ACV, 0)), 0) AS MID_MKT,
  COALESCE(SUM(IFF(MKT_SEG = 'Mid-Market' AND LEAD_SRC = 'Sales Generated', ACV, 0)), 0) AS MID_SALES,
  COALESCE(SUM(IFF(MKT_SEG = 'Enterprise' AND LEAD_SRC = 'Marketing', ACV, 0)), 0) AS ENT_MKT,
  COALESCE(SUM(IFF(MKT_SEG = 'Enterprise' AND LEAD_SRC = 'Sales Generated', ACV, 0)), 0) AS ENT_SALES,
  COALESCE(SUM(IFF(DEAL_BUCKET = 'New Logo', ACV, 0)), 0) AS NL_ACV,
  COALESCE(SUM(IFF(DEAL_BUCKET = 'New Logo' AND LEAD_SRC = 'Marketing', ACV, 0)), 0) AS NL_MKT,
  COALESCE(SUM(IFF(DEAL_BUCKET = 'New Logo' AND LEAD_SRC = 'Sales Generated', ACV, 0)), 0) AS NL_SALES,
  COALESCE(SUM(IFF(DEAL_BUCKET = 'Cross-Sell', ACV, 0)), 0) AS XS_ACV,
  COALESCE(SUM(IFF(DEAL_BUCKET = 'Cross-Sell' AND LEAD_SRC = 'Marketing', ACV, 0)), 0) AS XS_MKT,
  COALESCE(SUM(IFF(DEAL_BUCKET = 'Cross-Sell' AND LEAD_SRC = 'Sales Generated', ACV, 0)), 0) AS XS_SALES,
  COALESCE(SUM(IFF(DEAL_BUCKET = 'Uncategorized', ACV, 0)), 0) AS UNC_ACV,
  COALESCE(SUM(ACV), 0) AS OPEN_ALL_ACV,
  -- Stills Q4 deal-type targets (sourced pipeline)
  10363027::FLOAT AS NL_TARGET,
  16342279::FLOAT AS XS_TARGET,
  IFF(10363027 > 0,
    COALESCE(SUM(IFF(DEAL_BUCKET = 'New Logo', ACV, 0)), 0) / 10363027, 0) AS NL_PCT_GOAL,
  IFF(16342279 > 0,
    COALESCE(SUM(IFF(DEAL_BUCKET = 'Cross-Sell', ACV, 0)), 0) / 16342279, 0) AS XS_PCT_GOAL,
  IFF(18000000 > 0,
    COALESCE(SUM(IFF(MKT_SEG = 'Core', ACV, 0)), 0) / 18000000, 0) AS CORE_PCT_GOAL,
  IFF(16000000 > 0,
    COALESCE(SUM(IFF(MKT_SEG = 'Mid-Market', ACV, 0)), 0) / 16000000, 0) AS MID_PCT_GOAL,
  IFF(20000000 > 0,
    COALESCE(SUM(IFF(MKT_SEG = 'Enterprise', ACV, 0)), 0) / 20000000, 0) AS ENT_PCT_GOAL
FROM tagged
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

    # 5) Created YoY by quarter (stills) — long format for grouped bars; still ACV-only
    created_month = """
WITH q AS (
  SELECT
    QUARTER(STAGE_2_DATETIME) AS QN,
    YEAR(STAGE_2_DATETIME) AS YR,
    COALESCE(SUM(METRIC_VALUE),0) AS ACV
  FROM BI_STAGING.DATA.OPPORTUNITY_ACV_METRICS
  WHERE METRIC_NAME='Forecasted Net ACV' AND STAGE_2_ATTAINED = TRUE
    AND STAGE_2_DATETIME >= '2025-01-01' AND STAGE_2_DATETIME < '2027-01-01'
    AND METRIC_VALUE BETWEEN 0 AND 5000000
  GROUP BY 1, 2
)
SELECT
  'Q' || QN AS QUARTER,
  QN AS ORD,
  'FY' || YR AS FY,
  ACV
FROM q
WHERE YR IN (2025, 2026)
"""

    # 6) Close month × stage — ACV open FY2026 (Open page only; no VW)
    close_mo = """
SELECT DATE_TRUNC('month', CLOSE_DATE) AS MONTH,
  STAGE,
  CASE STAGE
    WHEN '2 - Analysis' THEN 2 WHEN '3 - Executive Alignment' THEN 3
    WHEN '4 - Solution Validation' THEN 4 WHEN '5 - Negotiate' THEN 5
    WHEN '6 - Finance Hold' THEN 6 WHEN '7 - Finance Review' THEN 7 ELSE 99 END AS ORD,
  COALESCE(SUM(METRIC_VALUE),0) AS ACV,
  COUNT(DISTINCT OPPORTUNITY_ID) AS OPPS
FROM BI_STAGING.DATA.OPPORTUNITY_ACV_METRICS
WHERE METRIC_NAME='Forecasted Net ACV' AND STAGE_GROUP='2-7'
  AND CLOSE_DATE >= '2026-01-01' AND CLOSE_DATE < '2027-01-01'
  AND METRIC_VALUE BETWEEN 0 AND 5000000
GROUP BY 1,2,3
"""

    # 7) TV charts — ACV product ONLY (no VW).
    charts = """
WITH prod_act AS (
  SELECT
    CASE
      WHEN CONTAINS(PRODUCT_CATEGORY,'Analytics') OR CONTAINS(PRODUCT_CATEGORY,'Marketing')
        OR CONTAINS(PRODUCT_CATEGORY,'Client') OR CONTAINS(PRODUCT_CATEGORY,'Content')
        THEN 'Insurance Intelligence'
      WHEN CONTAINS(PRODUCT_CATEGORY,'RQC') OR CONTAINS(PRODUCT_CATEGORY,'AMS')
        OR CONTAINS(PRODUCT_CATEGORY,'Service') THEN 'RQC & AMS'
      ELSE 'Platform Sales'
    END AS DIM,
    COALESCE(SUM(IFF(METRIC_VALUE BETWEEN 0 AND 5000000, METRIC_VALUE, 0)),0) AS ACTUAL
  FROM BI_STAGING.DATA.OPPORTUNITY_ACV_METRICS
  WHERE METRIC_NAME = 'Forecasted Net ACV' AND STAGE_GROUP = '2-7'
  GROUP BY 1
)
SELECT 'SEG' AS GRAIN, t.DIM, 'Target' AS SERIES, t.TARGET AS VAL, NULL::FLOAT AS OPPS
FROM (
  SELECT 'Core' AS DIM, 18000000::FLOAT AS TARGET
  UNION ALL SELECT 'Mid-Market', 16000000
  UNION ALL SELECT 'Enterprise', 20000000
) t
UNION ALL
SELECT 'PROD', t.DIM, 'Target', t.TARGET, NULL FROM (
  SELECT 'Insurance Intelligence' AS DIM, 31000000::FLOAT AS TARGET
  UNION ALL SELECT 'RQC & AMS', 22000000
  UNION ALL SELECT 'Platform Sales', 1000000
) t
UNION ALL
SELECT 'PROD', a.DIM, 'Actual', a.ACTUAL, NULL FROM prod_act a
"""

    pack_cols = [
        ("TOTAL_OPPS", None), ("TOTAL_ACV", m()), ("DEAL_PRODUCT_LINES", None),
        ("Q4_OPPS", None), ("Q4_ACV", m()),
        ("NQ_OPPS", None), ("NQ_ACV", m()), ("Q2OUT_OPPS", None), ("Q2OUT_ACV", m()),
        ("CLOSE_CY_ACV", m()), ("CLOSE_NY_ACV", m()), ("CLOSE_FY_ACV", m()), ("AVG_DEAL", m()),
        ("LARGE_OPPS", None), ("SMALL_OPPS", None), ("LARGE_ACV", m()), ("SMALL_ACV", m()),
        ("YTD_ACV", m()), ("Q4_CREATED_ACV", m()), ("Q4_CREATED_OPPS", None),
        ("MONTH_ACV", m()), ("MONTH_OPPS", None),
        ("WEEK_ACV", m()), ("WEEK_OPPS", None),
        ("CREATED_CLOSING_ACV", m()), ("CREATED_CLOSING_OPPS", None),
        ("WON_ACV", m()), ("WON_OPPS", None), ("LOST_ACV", m()), ("LOST_OPPS", None),
        ("CREATED_WON_ACV", m()), ("CREATED_WON_OPPS", None),
        ("S0_OPPS", None), ("S0_ACV", m()), ("S1_OPPS", None), ("S1_ACV", m()),
        ("S2_OPPS", None), ("S2_ACV", m()),
        ("YEAR_GOAL", m()), ("Q4_GOAL", m()),
        ("YEAR_ELAPSED", p()), ("Q4_ELAPSED", p()),
        ("YEAR_PCT_GOAL", p()), ("Q4_PCT_GOAL", p()),
        ("CLOSE_CY_PCT", p()), ("CLOSE_NY_PCT", p()), ("CLOSE_FY_PCT", p()),
        ("PACK_WALKIN_OPPS", None), ("PACK_WALKIN_ACV", m()),
        ("Q4_COVERAGE", p()), ("YEAR_COVERAGE", p()),
        ("OTHER_ADJ_ACV", m()), ("Q4_OTHER_ADJ_ACV", m()),
    ]
    src_kpi_cols = [
        ("MKT_ACV", m()), ("SALES_ACV", m()), ("SRC_TOTAL_ACV", m()),
        ("MKT_MIX", p()), ("SALES_MIX", p()),
        ("SEG_CORE", m()), ("SEG_MID", m()), ("SEG_ENT", m()),
        ("SEG_UNMAPPED", m()),
        ("CORE_MKT", m()), ("CORE_SALES", m()),
        ("MID_MKT", m()), ("MID_SALES", m()),
        ("ENT_MKT", m()), ("ENT_SALES", m()),
        ("NL_ACV", m()), ("NL_MKT", m()), ("NL_SALES", m()),
        ("XS_ACV", m()), ("XS_MKT", m()), ("XS_SALES", m()),
        ("UNC_ACV", m()),
        ("OPEN_ALL_ACV", m()),
        ("NL_TARGET", m()), ("XS_TARGET", m()),
        ("NL_PCT_GOAL", p()), ("XS_PCT_GOAL", p()),
        ("CORE_PCT_GOAL", p()), ("MID_PCT_GOAL", p()), ("ENT_PCT_GOAL", p()),
    ]
    return [
        sql_table("kpi-pack", "KPI Pack", pack, pack_cols),
        sql_table("kpi-walkin", "KPI Walkin", walkin, [("WALKIN_OPPS", None), ("WALKIN_ACV", m())]),
        # Open-VW only for Sourcing (not ROTB/Open/Total/Created/Movement)
        sql_table("kpi-src", "KPI Sourcing", src_kpi, src_kpi_cols),
        sql_table("chart-tv", "Chart Target Actual Source", charts, [
            ("GRAIN", None), ("DIM", None), ("SERIES", None), ("VAL", m()), ("OPPS", None)]),
        sql_table("chart-funnel", "Chart Funnel", funnel, [
            ("STAGE", None), ("ORD", None), ("ACV", m())]),
        sql_table("chart-created", "Chart Created", created_month, [
            ("QUARTER", None), ("ORD", None), ("FY", None), ("ACV", m())]),
        sql_table("chart-closemo", "Chart Close Month Stage", close_mo, [
            ("MONTH", {"kind": "datetime", "formatString": "%b %Y"}),
            ("STAGE", None), ("ORD", None), ("ACV", m()), ("OPPS", None)]),
        sql_table("chart-product", "Chart Product Category", """
SELECT
  CASE
    WHEN CONTAINS(PRODUCT_CATEGORY,'Analytics') OR CONTAINS(PRODUCT_CATEGORY,'Marketing')
      OR CONTAINS(PRODUCT_CATEGORY,'Client') OR CONTAINS(PRODUCT_CATEGORY,'Content')
      THEN 'Insurance Intelligence'
    WHEN CONTAINS(PRODUCT_CATEGORY,'RQC') OR CONTAINS(PRODUCT_CATEGORY,'AMS')
      OR CONTAINS(PRODUCT_CATEGORY,'Service') THEN 'RQC & AMS'
    ELSE 'Platform Sales'
  END AS PRODUCT,
  COALESCE(SUM(IFF(METRIC_VALUE BETWEEN 0 AND 5000000, METRIC_VALUE, 0)),0) AS ACV,
  COUNT(DISTINCT OPPORTUNITY_ID) AS OPPS
FROM BI_STAGING.DATA.OPPORTUNITY_ACV_METRICS
WHERE METRIC_NAME='Forecasted Net ACV' AND STAGE_GROUP='2-7'
GROUP BY 1
""", [
            ("PRODUCT", None), ("ACV", m()), ("OPPS", None)]),
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
