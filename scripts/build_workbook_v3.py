#!/usr/bin/env python3
"""Still-dense workbook on KPI ROTB Pack (1 Snowflake round-trip for KPIs).

Visual rules from Gong stills:
- White canvas, slate section shells, numbered teal headers
- Year/Q4 = text heroes (36px) + thin pace strip — not fat KPI widgets
- Amber / teal tint cards for Closing / Won
- No PLUGIN banners on visible pages
- Total Company = Target(blue) vs Actual(green) grouped bars
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

FOLDER = "5EFLG4WW7cjvngI0kCudpF"
WB = "86f3c78f-e9ce-4eee-b117-3c61a8c11e1d"
DM = "e9511cff-4ab8-48c4-96e0-fbf2b3b96f10"

TEAL, BLUE, ORANGE, RED, GREEN = "#0d9488", "#2563eb", "#f97316", "#dc2626", "#16a34a"
CANVAS, WHITE, MUTED, INK = "#ffffff", "#ffffff", "#64748b", "#0f172a"
SECTION = "#f1f5f9"
AMBER_BG, TEAL_BG, RED_BG, GREEN_BG = "#fffbeb", "#ecfdf5", "#fef2f2", "#f0fdf4"
BORDER = "#e2e8f0"
STAGE_COLORS = ["#38bdf8", "#3b82f6", "#6366f1", "#a855f7", "#db2777", "#f9a8d4"]


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
            return json.loads(raw) if raw else {"ok": True}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{e.code}: {e.read().decode()[:8000]}") from e


def dm(eid):
    return {"kind": "data-model", "dataModelId": DM, "elementId": eid}


def T(i, b):
    b = re.sub(r"<p>(?!</p>)", '<p class="p-small">', b)
    b = re.sub(r"font-weight:\s*[^;]+;?", "", b)
    return {"id": i, "kind": "text", "body": b}


def C(i, bg=WHITE, border=BORDER):
    return {
        "id": i, "kind": "container",
        "style": {"backgroundColor": bg, "borderColor": border, "borderWidth": 1, "borderRadius": "round"},
    }


def kpi(i, title, src, formula, color=INK, bg=None, fmt="$,.2s"):
    return {
        "id": i, "kind": "kpi-chart", "name": title,
        "source": {"kind": "table", "elementId": src},
        "columns": [{"id": f"{i}-v", "formula": formula, "format": {"kind": "number", "formatString": fmt}}],
        "value": {"columnId": f"{i}-v", "fontSize": "auto", "color": color},
        "style": {"borderRadius": "round", "backgroundColor": bg or WHITE},
    }


def E(eid, c1, c2, r1, r2, indent=0):
    return f'{"  "*(indent+1)}<Element elementId="{eid}" gridColumn="{c1} / {c2}" gridRow="{r1} / {r2}"/>'


def Cont(cid, c1, c2, r1, r2, kids, indent=0):
    pad = "  " * (indent + 1)
    return (
        f'{pad}<Container elementId="{cid}" type="grid" gridColumn="{c1} / {c2}" gridRow="{r1} / {r2}" '
        f'gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">\n'
        + "\n".join(kids) + f"\n{pad}</Container>"
    )


def page(pid, lines):
    return (
        f'<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="{pid}">\n'
        + "\n".join(lines) + "\n</Page>"
    )


def pass_tbl(wid, wname, eid, dname, cols):
    out = []
    for cid, cname, fmt in cols:
        c = {"id": cid, "name": cname, "formula": f"[{dname}/{cname}]"}
        if fmt:
            c["format"] = fmt
        out.append(c)
    return {"id": wid, "kind": "table", "name": wname, "source": dm(eid), "columns": out}


def money():
    return {"kind": "number", "formatString": "$,.0f"}


def pct():
    return {"kind": "number", "formatString": ".1%"}


def build():
    els = []
    m, p = money, pct

    # ONE pack for almost all KPIs
    rotb_names = [
        "TOTAL_OPPS", "TOTAL_ACV", "Q4_OPPS", "Q4_ACV", "NQ_OPPS", "NQ_ACV",
        "Q2OUT_OPPS", "Q2OUT_ACV", "CLOSE_CY_ACV", "CLOSE_NY_ACV", "CLOSE_FY_ACV",
        "YTD_ACV", "Q4_CREATED_ACV", "WEEK_ACV", "WEEK_OPPS",
        "CREATED_CLOSING_ACV", "CREATED_CLOSING_OPPS",
        "WALKIN_OPPS", "WALKIN_ACV", "WON_ACV", "WON_OPPS", "LOST_ACV", "LOST_OPPS",
        "MKT_ACV", "SALES_ACV", "YEAR_GOAL", "Q4_GOAL",
        "YEAR_ELAPSED", "Q4_ELAPSED", "YEAR_PCT_GOAL", "Q4_PCT_GOAL",
    ]
    els.append(pass_tbl(
        "wb-rotb", "WB ROTB Pack", "kpi-rotb", "KPI ROTB Pack",
        [(f"c{i}", n, p() if "ELAPSED" in n or "PCT" in n else (m() if "OPP" not in n else None))
         for i, n in enumerate(rotb_names)],
    ))
    els += [
        pass_tbl("wb-pace", "WB Pace", "pace-long", "Chart Pace Strip",
                 [("a", "METRIC", None), ("b", "PART", None), ("c", "VAL", p()), ("d", "PACED", p())]),
        pass_tbl("wb-funnel", "WB Funnel", "funnel-q4", "Chart Q4 Funnel",
                 [("a", "STAGE", None), ("b", "ORD", None), ("c", "OPPS", None), ("d", "ACV", m())]),
        pass_tbl("wb-om", "WB Open Month", "chart-open-month", "Chart Open Month Stage",
                 [("a", "CLOSE_MONTH", {"kind": "datetime", "formatString": "%b %Y"}),
                  ("b", "STAGE", None), ("c", "ACV", m())]),
        pass_tbl("wb-op", "WB Open Product", "chart-open-prod", "Chart Open Product",
                 [("a", "PRODUCT_CATEGORY", None), ("b", "ACV", m())]),
        pass_tbl("wb-cm", "WB Created Month", "chart-created-month", "Chart Created Month",
                 [("a", "MONTH", {"kind": "datetime", "formatString": "%b %Y"}), ("b", "ACV", m())]),
        pass_tbl("wb-snap", "WB Snap", "snap-daily", "Chart Snapshot Trend",
                 [("a", "SNAPSHOTDATE", {"kind": "datetime", "formatString": "%b %d"}), ("b", "FCST_NETACV", m())]),
        pass_tbl("wb-seg-tv", "WB Seg TV", "chart-seg-tv", "Chart Segment Target vs Actual",
                 [("a", "SEG", None), ("b", "SERIES", None), ("c", "VAL", m())]),
        pass_tbl("wb-prod-tv", "WB Prod TV", "chart-prod-tv", "Chart Product Target vs Actual",
                 [("a", "PGRP", None), ("b", "SERIES", None), ("c", "VAL", m())]),
        pass_tbl("wb-src", "WB Sourcing", "kpi-sourcing", "KPI Sourcing Mix",
                 [("a", "SOURCE_BUCKET", None), ("b", "OPPS", None), ("c", "ACV", m())]),
    ]

    R = "WB ROTB Pack"
    def S(col):
        return f"Sum([{R}/{col}])"

    ytd, cq4, week, week_o = S("YTD_ACV"), S("Q4_CREATED_ACV"), S("WEEK_ACV"), S("WEEK_OPPS")
    ccq, ccq_o = S("CREATED_CLOSING_ACV"), S("CREATED_CLOSING_OPPS")
    ypct, qpct = S("YEAR_PCT_GOAL"), S("Q4_PCT_GOAL")
    yelap, qelap = S("YEAR_ELAPSED"), S("Q4_ELAPSED")
    tot, tot_o = S("TOTAL_ACV"), S("TOTAL_OPPS")
    q4a, q4o = S("Q4_ACV"), S("Q4_OPPS")
    nqa, nqo = S("NQ_ACV"), S("NQ_OPPS")
    q2a, q2o = S("Q2OUT_ACV"), S("Q2OUT_OPPS")
    walk, walk_o = S("WALKIN_ACV"), S("WALKIN_OPPS")
    won, won_o = S("WON_ACV"), S("WON_OPPS")
    lost, lost_o = S("LOST_ACV"), S("LOST_OPPS")
    mkt, sales = S("MKT_ACV"), S("SALES_ACV")
    cy, ny, fy = S("CLOSE_CY_ACV"), S("CLOSE_NY_ACV"), S("CLOSE_FY_ACV")

    els += [
        {"kind": "control", "id": "ctrl-segment", "controlId": "Segment", "name": "All Segments",
         "controlType": "list", "mode": "include", "selectionMode": "single",
         "source": {"kind": "manual", "valueType": "text",
                    "values": ["All", "Core", "Mid-Market", "Enterprise"],
                    "labels": ["All Segments", "Core", "Mid-Market", "Enterprise"]}, "value": "All"},
        {"kind": "control", "id": "ctrl-dealtype", "controlId": "DealType", "name": "All Deal Types",
         "controlType": "list", "mode": "include", "selectionMode": "single",
         "source": {"kind": "manual", "valueType": "text",
                    "values": ["All", "New Business", "Renewal", "Product Addition"],
                    "labels": ["All Deal Types", "New Business", "Renewal", "Product Addition"]}, "value": "All"},
        {"kind": "control", "id": "ctrl-stage1", "controlId": "IncludeStage1",
         "name": "Include Stage 1 (Unique Meeting Run)", "controlType": "checkbox", "mode": "True/False", "value": False},
        {"kind": "control", "id": "ctrl-period", "controlId": "SourcingPeriod", "name": "Period",
         "controlType": "list", "mode": "include", "selectionMode": "single",
         "source": {"kind": "manual", "valueType": "text", "values": ["Q4", "YTD"],
                    "labels": ["Current Quarter (Q4)", "Year-to-Date"]}, "value": "Q4"},
    ]

    def pace(eid, metric):
        return {
            "id": eid, "kind": "bar-chart", "name": " ",
            "source": {"kind": "table", "elementId": "wb-pace"},
            "columns": [
                {"id": f"{eid}-m", "name": "M", "formula": f'SumIf([WB Pace/VAL], [WB Pace/METRIC]="{metric}" And [WB Pace/PART]="Actual")',
                 "format": {"kind": "number", "formatString": ".0%"}},
                {"id": f"{eid}-x", "name": "X", "formula": "'·'"},
            ],
            "xAxis": {"columnId": f"{eid}-x"},
            "yAxis": {"columnIds": [f"{eid}-m"]},
            "orientation": "horizontal", "stacking": "none",
            "color": {"by": "single", "value": ORANGE},
            "style": {"backgroundColor": WHITE},
        }

    # ═══ ROTB ═══
    els += [
        T("rotb-title", f'# ROTB Summary\n<p class="p-small"><span style="color:{MUTED}">One-page view of creation, coverage, movement, and demand. Q4 · FY2026</span></p>'),
        T("rotb-badge", f'<p style="text-align:right"><span style="color:{MUTED}">Read-only snapshot · October</span></p>'),
        C("sec-01", SECTION, SECTION), C("sec-02", SECTION, SECTION), C("sec-03", SECTION, SECTION),
        C("sec-04", SECTION, SECTION), C("sec-05", SECTION, SECTION),
        C("card-year"), C("card-q4"), C("card-week"), C("card-ccq", AMBER_BG, "#fbbf24"), C("card-cwq", TEAL_BG, "#5eead4"),
        T("rotb-s01", f'## <span style="color:{TEAL}">01 / PIPELINE CREATION</span>\nCreation pace'),
        T("rk-year-body",
          f'<p class="p-small"><span style="color:{MUTED}">Year Pipeline Created</span></p>\n'
          f'<p class="p-small"><span style="font-size:36px;font-weight:700;color:{INK}">{{{{{ytd} | $,.2s}}}}</span></p>\n'
          f'<p class="p-small"><span style="color:{ORANGE}">{{{{{ypct} | .1%}}}} of goal</span></p>'),
        pace("rk-year-bar", "Year"),
        T("rk-year-foot",
          f'<p class="p-small"><span style="color:{MUTED}">Target: $94.6M</span> · '
          f'<span style="color:{ORANGE}">{{{{{yelap} | .1%}}}} paced</span></p>\n'
          f'<p class="p-small"><span style="color:{MUTED}">Year progress {{{{{yelap} | .0%}}}}</span></p>'),
        T("rk-q4-body",
          f'<p class="p-small"><span style="color:{MUTED}">Q4 Pipeline Created</span></p>\n'
          f'<p class="p-small"><span style="font-size:36px;font-weight:700;color:{INK}">{{{{{cq4} | $,.2s}}}}</span></p>\n'
          f'<p class="p-small"><span style="color:{ORANGE}">{{{{{qpct} | .1%}}}} of goal</span> · '
          f'<span style="color:{MUTED}">{{{{{qelap} | .0%}}}} through quarter</span></p>'),
        pace("rk-q4-bar", "Q4"),
        T("rk-q4-foot",
          f'<p class="p-small"><span style="color:{MUTED}">Target: $26.7M</span> · '
          f'<span style="color:{ORANGE}">{{{{{qelap} | .1%}}}} paced</span></p>\n'
          f'<p class="p-small"><span style="color:{MUTED}">Quarter progress {{{{{qelap} | .0%}}}}</span></p>'),
        kpi("rk-week", "Created This Week", "wb-rotb", week),
        T("rk-week-cap", f'<p class="p-small"><span style="color:{MUTED}">{{{{{week_o} | ,.0f}}}} opportunities</span></p>'),
        kpi("rk-ccq", "Created & Closing This Quarter", "wb-rotb", ccq, ORANGE, AMBER_BG),
        T("rk-ccq-cap", f'<p class="p-small"><span style="color:{MUTED}">{{{{{ccq_o} | ,.0f}}}} opportunities</span></p>'),
        kpi("rk-cwq", "Created & Won This Quarter", "wb-rotb", won, GREEN, TEAL_BG),
        T("rk-cwq-cap", f'<p class="p-small"><span style="color:{MUTED}">{{{{{won_o} | ,.0f}}}} opportunities</span></p>'),
        T("rotb-s02", f'## <span style="color:{TEAL}">02 / COVERAGE</span>\nOpen pipeline'),
        C("cov-1"), C("cov-2"), C("cov-3"), C("cov-4"),
        kpi("rk-open", "Total Open Pipeline", "wb-rotb", tot, TEAL, TEAL_BG),
        kpi("rk-cq", "Closing This Quarter", "wb-rotb", q4a, BLUE),
        kpi("rk-nq", "Closing Next Quarter", "wb-rotb", nqa, BLUE),
        kpi("rk-2q", "Closing Two Quarters Out", "wb-rotb", q2a, BLUE),
        T("rotb-s03", f'## <span style="color:{MUTED}">03 / PIPELINE MANAGEMENT</span>\nQ4 movement'),
        C("mgmt-w"), C("mgmt-l", RED_BG, "#fecaca"), C("mgmt-n", GREEN_BG, "#bbf7d0"),
        kpi("rk-walk", "Walk-in (Q4 start)", "wb-rotb", walk, BLUE),
        T("rk-walk-cap", f'<p class="p-small"><span style="color:{MUTED}">Frozen 2026-10-01 · {{{{{walk_o} | ,.0f}}}} opps</span></p>'),
        kpi("rk-lost", "Closed Lost", "wb-rotb", lost, RED, RED_BG),
        T("rk-lost-cap", f'<p class="p-small"><span style="color:{MUTED}">{{{{{lost_o} | ,.0f}}}} opps · ≤ $50k</span></p>'),
        kpi("rk-won2", "Closed Won", "wb-rotb", won, GREEN, GREEN_BG),
        T("rk-won2-cap", f'<p class="p-small"><span style="color:{MUTED}">{{{{{won_o} | ,.0f}}}} opportunities</span></p>'),
        T("rotb-s04", f'## <span style="color:{BLUE}">04 / MARKETING PERFORMANCE</span>\nDemand signals · October'),
    ]
    for eid, title in [("dm-mql", "MQLs this month"), ("dm-s0", "Stage 0 this month"),
                       ("dm-s1", "Stage 1 this month"), ("dm-s2", "Stage 2 this month")]:
        els += [C(eid), T(f"{eid}-b",
            f'<p class="p-small"><span style="color:{MUTED}">{title}</span></p>\n'
            f'<p class="p-small" style="text-align:center"><span style="font-size:28px;color:#cbd5e1">—</span></p>')]
    els += [
        T("rotb-s05", f'## <span style="color:{ORANGE}">05 / SALES PIPELINE GENERATION</span>\nOpen Stage 2+ by Lead Source'),
        C("sg-m"), C("sg-s"),
        kpi("rk-mkt", "Marketing-sourced", "wb-rotb", mkt, BLUE),
        kpi("rk-sales", "Sales-sourced", "wb-rotb", sales, ORANGE),
    ]

    # ═══ OPEN ═══
    for cid in ["okc-u", "okc-t", "okc-w", "okc-q", "okc-avg", "okc-chg"]:
        els.append(C(cid))
    els += [
        T("open-title", f'# Open Pipeline\n<p class="p-small"><span style="color:{MUTED}">FY2026 Stage 2+ Pipeline by Close Date</span></p>'),
        T("open-live", f'<p style="text-align:right"><span style="color:{GREEN}">Live from Snowflake</span></p>'),
        kpi("ok-u", "Unique Opportunities", "wb-rotb", tot_o, fmt=",.0f"),
        kpi("ok-t", "Total Pipeline ACV", "wb-rotb", tot),
        kpi("ok-w", "Walk-in Pipeline", "wb-rotb", walk, BLUE),
        T("ok-w-cap", f'<p class="p-small"><span style="color:{MUTED}">Q4 start (frozen)</span></p>'),
        kpi("ok-q", "Q4 Pipeline ACV", "wb-rotb", q4a),
        T("ok-q-cap", f'<p class="p-small"><span style="color:{MUTED}">{{{{{q4o} | ,.0f}}}} opps</span></p>'),
        kpi("ok-avg", "Avg Deal Size", "wb-rotb", f"({tot})/({tot_o})", fmt="$,.0f"),
        T("open-chg", f'## Q4 Pipeline Changes\n<span style="color:{MUTED}">Current quarter pipeline movement</span>'),
        T("ok-q4tot",
          f'<p class="p-small"><span style="color:{MUTED}">Current Open Pipeline</span></p>\n'
          f'<p class="p-small"><span style="font-size:32px;font-weight:700;color:{INK}">{{{{{q4a} | $,.2s}}}}</span></p>\n'
          f'<p class="p-small"><span style="color:{BLUE}">Close Date: Current Quarter</span></p>'),
        {
            "id": "chart-funnel", "kind": "bar-chart", "name": " ",
            "source": {"kind": "table", "elementId": "wb-funnel"},
            "columns": [
                {"id": "cf-b", "name": "B", "formula": "'Q4'"},
                {"id": "cf-s", "name": "Stage", "formula": "[WB Funnel/STAGE]"},
                {"id": "cf-v", "name": "ACV", "formula": "Sum([WB Funnel/ACV])",
                 "format": {"kind": "number", "formatString": "$,.2s"}},
            ],
            "xAxis": {"columnId": "cf-b"}, "yAxis": {"columnIds": ["cf-v"]},
            "orientation": "horizontal", "stacking": "stacked",
            "color": {"by": "category", "column": "cf-s", "scheme": STAGE_COLORS},
            "style": {"backgroundColor": WHITE, "borderRadius": "round"},
        },
        T("mv-left", f'<p class="p-small"><span style="color:{MUTED}">WHAT LEFT</span></p>'),
        C("mv-push-c", RED_BG, "#fecaca"), C("mv-lost-c", RED_BG, "#fecaca"),
        T("mv-push", f'<p class="p-small"><span style="color:{RED}">Pushed Out</span></p>\n'
          f'<p class="p-small" style="text-align:center"><span style="font-size:26px;color:{RED}">—</span></p>'),
        kpi("mv-lost", "Closed Lost", "wb-rotb", lost, RED, RED_BG),
        T("mv-also", f'<p class="p-small"><span style="color:{MUTED}">ALSO LEFT PIPELINE</span></p>'),
        C("mv-pullb-c", RED_BG, "#fecaca"), C("mv-won-c", GREEN_BG, "#bbf7d0"),
        T("mv-pullb", f'<p class="p-small"><span style="color:{RED}">Pulled Back</span></p>\n'
          f'<p class="p-small" style="text-align:center"><span style="font-size:26px;color:{RED}">$0</span></p>'),
        kpi("mv-won", "Closed Won", "wb-rotb", won, GREEN, GREEN_BG),
        T("mv-add", f'<p class="p-small"><span style="color:{MUTED}">WHAT ADDED</span></p>'),
        C("mv-pulli-c", GREEN_BG, "#bbf7d0"), C("mv-size-c", GREEN_BG, "#bbf7d0"),
        T("mv-pulli", f'<p class="p-small"><span style="color:{GREEN}">Pulled In</span></p>\n'
          f'<p class="p-small" style="text-align:center"><span style="font-size:26px;color:{GREEN}">—</span></p>'),
        T("mv-size", f'<p class="p-small"><span style="color:{GREEN}">Size Increases</span></p>\n'
          f'<p class="p-small" style="text-align:center"><span style="font-size:26px;color:{GREEN}">—</span></p>'),
        {
            "id": "chart-seg-month", "kind": "bar-chart", "name": "Close Month × Stage",
            "source": {"kind": "table", "elementId": "wb-om"},
            "columns": [
                {"id": "csm-q", "name": "Month", "formula": "[WB Open Month/CLOSE_MONTH]",
                 "format": {"kind": "datetime", "formatString": "%b %Y"}},
                {"id": "csm-s", "name": "Stage", "formula": "[WB Open Month/STAGE]"},
                {"id": "csm-v", "name": "ACV", "formula": "Sum([WB Open Month/ACV])",
                 "format": {"kind": "number", "formatString": "$,.2s"}},
            ],
            "xAxis": {"columnId": "csm-q"}, "yAxis": {"columnIds": ["csm-v"]},
            "color": {"by": "category", "column": "csm-s", "scheme": STAGE_COLORS}, "stacking": "stacked",
            "style": {"backgroundColor": WHITE, "borderRadius": "round", "borderColor": BORDER, "borderWidth": 1},
        },
        {
            "id": "chart-prod", "kind": "bar-chart", "name": "By Product Category",
            "source": {"kind": "table", "elementId": "wb-op"},
            "columns": [
                {"id": "cp-p", "name": "Product", "formula": "[WB Open Product/PRODUCT_CATEGORY]"},
                {"id": "cp-v", "name": "ACV", "formula": "Sum([WB Open Product/ACV])",
                 "format": {"kind": "number", "formatString": "$,.2s"}},
            ],
            "xAxis": {"columnId": "cp-p"}, "yAxis": {"columnIds": ["cp-v"]}, "orientation": "horizontal",
            "color": {"by": "single", "value": TEAL},
            "style": {"backgroundColor": WHITE, "borderRadius": "round", "borderColor": BORDER, "borderWidth": 1},
        },
    ]

    # ═══ TOTAL ═══
    els += [
        T("total-title", f'# Total Company\n<p class="p-small"><span style="color:{MUTED}">All pipeline sources</span></p>'),
        C("tc-1"), C("tc-2"), C("tc-3"),
        kpi("tk-cq", "Pipeline to Close in Current Quarter", "wb-rotb", q4a),
        T("tk-cq-cap", f'<p class="p-small"><span style="color:{MUTED}">Q4 2026 · {{{{{q4o} | ,.0f}}}} open deals</span></p>'),
        kpi("tk-nq", "Pipeline to Close in Next Quarter", "wb-rotb", nqa),
        T("tk-nq-cap", f'<p class="p-small"><span style="color:{MUTED}">Q1 2027 · {{{{{nqo} | ,.0f}}}} open deals</span></p>'),
        kpi("tk-2q", "Pipeline to Close 2 Quarters Out", "wb-rotb", q2a),
        T("tk-2q-cap", f'<p class="p-small"><span style="color:{MUTED}">Q2 2027 · {{{{{q2o} | ,.0f}}}} open deals</span></p>'),
        {
            "id": "chart-seg", "kind": "bar-chart", "name": "Pipeline by Segment",
            "source": {"kind": "table", "elementId": "wb-seg-tv"},
            "columns": [
                {"id": "cs-s", "name": "Segment", "formula": "[WB Seg TV/SEG]"},
                {"id": "cs-r", "name": "Series", "formula": "[WB Seg TV/SERIES]"},
                {"id": "cs-v", "name": "Val", "formula": "Sum([WB Seg TV/VAL])",
                 "format": {"kind": "number", "formatString": "$,.2s"}},
            ],
            "xAxis": {"columnId": "cs-s"}, "yAxis": {"columnIds": ["cs-v"]},
            "color": {"by": "category", "column": "cs-r", "palette": {"Target": BLUE, "Actual": GREEN}},
            "stacking": "none",
            "style": {"backgroundColor": WHITE, "borderRadius": "round", "borderColor": BORDER, "borderWidth": 1},
        },
        {
            "id": "chart-pgrp", "kind": "bar-chart", "name": "Pipeline by Product Group",
            "source": {"kind": "table", "elementId": "wb-prod-tv"},
            "columns": [
                {"id": "pg-s", "name": "Group", "formula": "[WB Prod TV/PGRP]"},
                {"id": "pg-r", "name": "Series", "formula": "[WB Prod TV/SERIES]"},
                {"id": "pg-v", "name": "Val", "formula": "Sum([WB Prod TV/VAL])",
                 "format": {"kind": "number", "formatString": "$,.2s"}},
            ],
            "xAxis": {"columnId": "pg-s"}, "yAxis": {"columnIds": ["pg-v"]},
            "color": {"by": "category", "column": "pg-r", "palette": {"Target": BLUE, "Actual": GREEN}},
            "stacking": "none",
            "style": {"backgroundColor": WHITE, "borderRadius": "round", "borderColor": BORDER, "borderWidth": 1},
        },
        T("total-defs",
          f'<p class="p-small"><span style="color:{MUTED}">Attainment by New Segment · Up-Market = Mid-Market + Enterprise · '
          f'Insurance Intelligence = Analytics + Client + Content · RQC &amp; AMS = RQC + Service</span></p>'),
        {
            "id": "tbl-attain", "kind": "table", "name": "Attainment by New Segment",
            "source": {"kind": "table", "elementId": "wb-seg-tv"},
            "columns": [
                {"id": "ta-s", "name": "Segment", "formula": "[WB Seg TV/SEG]"},
                {"id": "ta-r", "name": "Series", "formula": "[WB Seg TV/SERIES]"},
                {"id": "ta-v", "name": "Value", "formula": "Sum([WB Seg TV/VAL])",
                 "format": {"kind": "number", "formatString": "$,.0f"}},
            ],
        },
    ]

    # ═══ SOURCING ═══
    els += [
        T("sourcing-title", f'# Pipeline Sourcing\n<p class="p-small"><span style="color:{MUTED}">Stage 2+ by Lead Source · mix target M 39% / S 61%</span></p>'),
        C("sc-row", SECTION, SECTION),
        kpi("sk-m", "Marketing-sourced", "wb-rotb", mkt, BLUE),
        T("sk-m-cap", f'<p class="p-small"><span style="color:{MUTED}">target mix 39%</span></p>'),
        kpi("sk-s", "Sales-sourced", "wb-rotb", sales, ORANGE),
        T("sk-s-cap", f'<p class="p-small"><span style="color:{MUTED}">target mix 61%</span></p>'),
        kpi("sk-t", "Total Stage 2+", "wb-rotb", f"({mkt})+({sales})", INK),
        T("sk-mix", f'<p class="p-small" style="text-align:center"><span style="font-size:22px;color:{INK}">M 39% / S 61%</span></p>'),
        {
            "id": "chart-src", "kind": "bar-chart", "name": "By Lead Source",
            "source": {"kind": "table", "elementId": "wb-src"},
            "columns": [
                {"id": "cr-s", "name": "Source", "formula": "[WB Sourcing/SOURCE_BUCKET]"},
                {"id": "cr-v", "name": "ACV", "formula": "Sum([WB Sourcing/ACV])",
                 "format": {"kind": "number", "formatString": "$,.2s"}},
            ],
            "xAxis": {"columnId": "cr-s"}, "yAxis": {"columnIds": ["cr-v"]},
            "color": {"by": "single", "value": BLUE},
            "style": {"backgroundColor": WHITE, "borderRadius": "round", "borderColor": BORDER, "borderWidth": 1},
        },
        {
            "id": "tbl-src", "kind": "table", "name": "Sourcing detail",
            "source": {"kind": "table", "elementId": "wb-src"},
            "columns": [
                {"id": "ts-s", "name": "Source", "formula": "[WB Sourcing/SOURCE_BUCKET]"},
                {"id": "ts-a", "name": "ACV", "formula": "Sum([WB Sourcing/ACV])",
                 "format": {"kind": "number", "formatString": "$,.0f"}},
                {"id": "ts-o", "name": "Opps", "formula": "Sum([WB Sourcing/OPPS])",
                 "format": {"kind": "number", "formatString": ",.0f"}},
            ],
        },
    ]

    # ═══ MOVEMENT / CREATED ═══
    els += [
        T("movement-title", f'# Pipeline Movement\n<p class="p-small"><span style="color:{MUTED}">Daily snapshots</span></p>'),
        C("mc-1"), C("mc-2"), C("mc-3"),
        kpi("mk-open", "Total Open Pipeline", "wb-rotb", tot, fmt="$,.0f"),
        T("mk-delta", f'<p class="p-small"><span style="color:{MUTED}">30-Day Delta</span></p>\n'
          f'<p class="p-small" style="text-align:center"><span style="font-size:26px;color:{BLUE}">—</span></p>'),
        T("mk-yoy", f'<p class="p-small"><span style="color:{MUTED}">YoY</span></p>\n'
          f'<p class="p-small" style="text-align:center"><span style="font-size:26px;color:{BLUE}">—</span></p>'),
        {
            "id": "chart-move", "kind": "line-chart", "name": "Snapshot FCST",
            "source": {"kind": "table", "elementId": "wb-snap"},
            "columns": [
                {"id": "cm-d", "name": "Date", "formula": "[WB Snap/SNAPSHOTDATE]",
                 "format": {"kind": "datetime", "formatString": "%b %d"}},
                {"id": "cm-v", "name": "FCST", "formula": "Sum([WB Snap/FCST_NETACV])",
                 "format": {"kind": "number", "formatString": "$,.0f"}},
            ],
            "xAxis": {"columnId": "cm-d"}, "yAxis": {"columnIds": ["cm-v"]},
            "color": {"by": "single", "value": TEAL},
            "style": {"backgroundColor": WHITE, "borderRadius": "round", "borderColor": BORDER, "borderWidth": 1},
        },
        T("created-title", f'# Pipeline Created\n<p class="p-small"><span style="color:{MUTED}">Open (Qtr Start) + Created − Won − Lost − Pulled Back − Other = Total Open</span></p>'),
        C("cc-start"), C("cc-cr"), C("cc-wn"), C("cc-ls"), C("cc-tot"),
        kpi("ck-start", "Open (Qtr Start)", "wb-rotb", walk, BLUE, fmt="$,.0f"),
        T("ck-plus", f'<p class="p-small" style="text-align:center"><span style="font-size:28px;color:{MUTED}">+</span></p>'),
        kpi("ck-cr", "Created This Quarter", "wb-rotb", cq4, GREEN, fmt="$,.0f"),
        T("ck-m1", f'<p class="p-small" style="text-align:center"><span style="font-size:28px;color:{MUTED}">−</span></p>'),
        kpi("ck-wn", "Won", "wb-rotb", won, GREEN, fmt="$,.0f"),
        T("ck-m2", f'<p class="p-small" style="text-align:center"><span style="font-size:28px;color:{MUTED}">−</span></p>'),
        kpi("ck-ls", "Lost", "wb-rotb", lost, RED, fmt="$,.0f"),
        T("ck-eq", f'<p class="p-small" style="text-align:center"><span style="font-size:28px;color:{MUTED}">=</span></p>'),
        kpi("ck-tot", "Total Open", "wb-rotb", tot, BLUE, fmt="$,.0f"),
        kpi("ck-cy", "Closing CY", "wb-rotb", cy, TEAL, fmt="$,.0f"),
        kpi("ck-ny", "Closing NY", "wb-rotb", ny, BLUE, fmt="$,.0f"),
        kpi("ck-fy", "Future Years", "wb-rotb", fy, BLUE, fmt="$,.0f"),
        C("cc-cy"), C("cc-ny"), C("cc-fy"),
        {
            "id": "chart-created", "kind": "bar-chart", "name": "Created by Month",
            "source": {"kind": "table", "elementId": "wb-cm"},
            "columns": [
                {"id": "ccm-m", "name": "Month", "formula": "[WB Created Month/MONTH]",
                 "format": {"kind": "datetime", "formatString": "%b %Y"}},
                {"id": "ccm-v", "name": "ACV", "formula": "Sum([WB Created Month/ACV])",
                 "format": {"kind": "number", "formatString": "$,.2s"}},
            ],
            "xAxis": {"columnId": "ccm-m"}, "yAxis": {"columnIds": ["ccm-v"]},
            "color": {"by": "single", "value": TEAL},
            "style": {"backgroundColor": WHITE, "borderRadius": "round", "borderColor": BORDER, "borderWidth": 1},
        },
        T("data-note", f"""# Fast lineage

**ROTB / Open / Created / Movement KPIs** → `WB ROTB Pack` → `KPI ROTB Pack` (**one** Snowflake query).

Charts are separate small GROUP BYs (funnel, month, snap, target-vs-actual).

Plugins (register in Admin):  
https://gabrieljonessigmacomputing.github.io/zywave-pipeline-tracker/plugins/pace-bullet/  
https://gabrieljonessigmacomputing.github.io/zywave-pipeline-tracker/plugins/stage-funnel/
"""),
    ]

    def L(e, a, b, c, d):
        return E(e, a, b, c, d, 1)

    rotb = [
        E("rotb-title", 1, 18, 1, 3), E("rotb-badge", 18, 25, 1, 3),
        Cont("sec-01", 1, 25, 3, 13, [
            L("rotb-s01", 1, 25, 1, 2),
            Cont("card-year", 1, 6, 2, 10, [L("rk-year-body", 1, 25, 1, 4), L("rk-year-bar", 1, 25, 4, 6), L("rk-year-foot", 1, 25, 6, 9)], 2),
            Cont("card-q4", 6, 11, 2, 10, [L("rk-q4-body", 1, 25, 1, 4), L("rk-q4-bar", 1, 25, 4, 6), L("rk-q4-foot", 1, 25, 6, 9)], 2),
            Cont("card-week", 11, 15, 2, 10, [L("rk-week", 1, 25, 1, 6), L("rk-week-cap", 1, 25, 6, 9)], 2),
            Cont("card-ccq", 15, 20, 2, 10, [L("rk-ccq", 1, 25, 1, 6), L("rk-ccq-cap", 1, 25, 6, 9)], 2),
            Cont("card-cwq", 20, 25, 2, 10, [L("rk-cwq", 1, 25, 1, 6), L("rk-cwq-cap", 1, 25, 6, 9)], 2),
        ]),
        Cont("sec-02", 1, 25, 13, 18, [
            L("rotb-s02", 1, 25, 1, 2),
            Cont("cov-1", 1, 7, 2, 6, [L("rk-open", 1, 25, 1, 8)], 2),
            Cont("cov-2", 7, 13, 2, 6, [L("rk-cq", 1, 25, 1, 8)], 2),
            Cont("cov-3", 13, 19, 2, 6, [L("rk-nq", 1, 25, 1, 8)], 2),
            Cont("cov-4", 19, 25, 2, 6, [L("rk-2q", 1, 25, 1, 8)], 2),
        ]),
        Cont("sec-03", 1, 25, 18, 23, [
            L("rotb-s03", 1, 25, 1, 2),
            Cont("mgmt-w", 1, 9, 2, 6, [L("rk-walk", 1, 25, 1, 5), L("rk-walk-cap", 1, 25, 5, 7)], 2),
            Cont("mgmt-l", 9, 17, 2, 6, [L("rk-lost", 1, 25, 1, 5), L("rk-lost-cap", 1, 25, 5, 7)], 2),
            Cont("mgmt-n", 17, 25, 2, 6, [L("rk-won2", 1, 25, 1, 5), L("rk-won2-cap", 1, 25, 5, 7)], 2),
        ]),
        Cont("sec-04", 1, 25, 23, 28, [
            L("rotb-s04", 1, 25, 1, 2),
            Cont("dm-mql", 1, 7, 2, 6, [L("dm-mql-b", 1, 25, 1, 8)], 2),
            Cont("dm-s0", 7, 13, 2, 6, [L("dm-s0-b", 1, 25, 1, 8)], 2),
            Cont("dm-s1", 13, 19, 2, 6, [L("dm-s1-b", 1, 25, 1, 8)], 2),
            Cont("dm-s2", 19, 25, 2, 6, [L("dm-s2-b", 1, 25, 1, 8)], 2),
        ]),
        Cont("sec-05", 1, 25, 28, 33, [
            L("rotb-s05", 1, 25, 1, 2),
            Cont("sg-m", 1, 13, 2, 6, [L("rk-mkt", 1, 25, 1, 8)], 2),
            Cont("sg-s", 13, 25, 2, 6, [L("rk-sales", 1, 25, 1, 8)], 2),
        ]),
    ]
    open_l = [
        E("open-title", 1, 18, 1, 3), E("open-live", 18, 25, 1, 3),
        E("ctrl-stage1", 1, 10, 3, 4), E("ctrl-segment", 10, 17, 3, 4), E("ctrl-dealtype", 17, 25, 3, 4),
        Cont("okc-u", 1, 6, 4, 8, [L("ok-u", 1, 25, 1, 8)]),
        Cont("okc-t", 6, 11, 4, 8, [L("ok-t", 1, 25, 1, 8)]),
        Cont("okc-w", 11, 16, 4, 8, [L("ok-w", 1, 25, 1, 6), L("ok-w-cap", 1, 25, 6, 8)]),
        Cont("okc-q", 16, 21, 4, 8, [L("ok-q", 1, 25, 1, 6), L("ok-q-cap", 1, 25, 6, 8)]),
        Cont("okc-avg", 21, 25, 4, 8, [L("ok-avg", 1, 25, 1, 8)]),
        Cont("okc-chg", 1, 25, 8, 20, [
            L("open-chg", 1, 25, 1, 2), L("ok-q4tot", 1, 9, 2, 6), L("chart-funnel", 1, 15, 6, 13),
            L("mv-left", 15, 25, 2, 3),
            Cont("mv-push-c", 15, 20, 3, 6, [L("mv-push", 1, 25, 1, 8)], 2),
            Cont("mv-lost-c", 20, 25, 3, 6, [L("mv-lost", 1, 25, 1, 8)], 2),
            L("mv-also", 15, 25, 6, 7),
            Cont("mv-pullb-c", 15, 20, 7, 10, [L("mv-pullb", 1, 25, 1, 8)], 2),
            Cont("mv-won-c", 20, 25, 7, 10, [L("mv-won", 1, 25, 1, 8)], 2),
            L("mv-add", 15, 25, 10, 11),
            Cont("mv-pulli-c", 15, 20, 11, 14, [L("mv-pulli", 1, 25, 1, 8)], 2),
            Cont("mv-size-c", 20, 25, 11, 14, [L("mv-size", 1, 25, 1, 8)], 2),
        ]),
        E("chart-seg-month", 1, 13, 20, 30), E("chart-prod", 13, 25, 20, 30),
    ]
    total_l = [
        E("total-title", 1, 25, 1, 3),
        Cont("tc-1", 1, 9, 3, 7, [L("tk-cq", 1, 25, 1, 5), L("tk-cq-cap", 1, 25, 5, 7)]),
        Cont("tc-2", 9, 17, 3, 7, [L("tk-nq", 1, 25, 1, 5), L("tk-nq-cap", 1, 25, 5, 7)]),
        Cont("tc-3", 17, 25, 3, 7, [L("tk-2q", 1, 25, 1, 5), L("tk-2q-cap", 1, 25, 5, 7)]),
        E("chart-seg", 1, 13, 7, 17), E("chart-pgrp", 13, 25, 7, 17),
        E("total-defs", 1, 25, 17, 18), E("tbl-attain", 1, 25, 18, 28),
    ]
    sourcing_l = [
        E("sourcing-title", 1, 18, 1, 3), E("ctrl-period", 18, 25, 1, 3),
        Cont("sc-row", 1, 25, 3, 9, [
            L("sk-m", 1, 7, 1, 5), L("sk-m-cap", 1, 7, 5, 7),
            L("sk-s", 7, 13, 1, 5), L("sk-s-cap", 7, 13, 5, 7),
            L("sk-t", 13, 19, 1, 5), L("sk-mix", 19, 25, 1, 7),
        ]),
        E("chart-src", 1, 12, 9, 20), E("tbl-src", 12, 25, 9, 20),
    ]
    movement_l = [
        E("movement-title", 1, 25, 1, 3),
        Cont("mc-1", 1, 9, 3, 7, [L("mk-open", 1, 25, 1, 8)]),
        Cont("mc-2", 9, 17, 3, 7, [L("mk-delta", 1, 25, 1, 8)]),
        Cont("mc-3", 17, 25, 3, 7, [L("mk-yoy", 1, 25, 1, 8)]),
        E("chart-move", 1, 25, 7, 20),
    ]
    created_l = [
        E("created-title", 1, 25, 1, 3),
        Cont("cc-start", 1, 5, 3, 7, [L("ck-start", 1, 25, 1, 8)]),
        E("ck-plus", 5, 6, 3, 7),
        Cont("cc-cr", 6, 10, 3, 7, [L("ck-cr", 1, 25, 1, 8)]),
        E("ck-m1", 10, 11, 3, 7),
        Cont("cc-wn", 11, 15, 3, 7, [L("ck-wn", 1, 25, 1, 8)]),
        E("ck-m2", 15, 16, 3, 7),
        Cont("cc-ls", 16, 20, 3, 7, [L("ck-ls", 1, 25, 1, 8)]),
        E("ck-eq", 20, 21, 3, 7),
        Cont("cc-tot", 21, 25, 3, 7, [L("ck-tot", 1, 25, 1, 8)]),
        Cont("cc-cy", 1, 9, 7, 11, [L("ck-cy", 1, 25, 1, 8)]),
        Cont("cc-ny", 9, 17, 7, 11, [L("ck-ny", 1, 25, 1, 8)]),
        Cont("cc-fy", 17, 25, 7, 11, [L("ck-fy", 1, 25, 1, 8)]),
        E("chart-created", 1, 25, 11, 22),
    ]
    data_l = [E("data-note", 1, 25, 1, 8)]
    row = 8
    for wid in ["wb-rotb", "wb-pace", "wb-funnel", "wb-om", "wb-op", "wb-cm", "wb-snap", "wb-seg-tv", "wb-prod-tv", "wb-src"]:
        data_l.append(E(wid, 1, 25, row, row + 3))
        row += 3

    layout = "\n".join([
        '<?xml version="1.0" encoding="utf-8"?>',
        page("page-rotb", rotb), page("page-total", total_l), page("page-sourcing", sourcing_l),
        page("page-open", open_l), page("page-movement", movement_l), page("page-created", created_l),
        page("page-data", data_l),
    ])
    seen = {e["id"]: e for e in els}
    elements = list(seen.values())
    placed = set(re.findall(r'elementId="([^"]+)"', layout))
    ids = {e["id"] for e in elements}
    if placed - ids:
        raise SystemExit(f"missing {sorted(placed - ids)}")
    if ids - placed:
        raise SystemExit(f"unplaced {sorted(ids - placed)}")

    return {
        "name": "Pipeline Tracker FY2026",
        "folderId": FOLDER,
        "description": "v3 still-dense · 1× ROTB pack query · Target vs Actual",
        "document": {
            "schemaVersion": 1, "kind": "workbook",
            "settings": {
                "theme": {
                    "name": "Light",
                    "overrides": {
                        "hasCards": "shown", "borderRadius": "round",
                        "space": {"unit": "medium"},
                        "colors": {"highlight": TEAL, "success": GREEN, "warning": ORANGE, "danger": RED, "surface": "#f8fafc"},
                    },
                },
                "navigation": {"primary": "sidebar", "pageSidebar": "enabled"},
            },
            "pages": [
                {"id": "page-rotb", "name": "ROTB Summary", "backgroundColor": "#f8fafc"},
                {"id": "page-total", "name": "Total Company", "backgroundColor": "#f8fafc"},
                {"id": "page-sourcing", "name": "Pipeline Sourcing", "backgroundColor": "#f8fafc"},
                {"id": "page-open", "name": "Open Pipeline", "backgroundColor": "#f8fafc"},
                {"id": "page-movement", "name": "Pipeline Movement", "backgroundColor": "#f8fafc"},
                {"id": "page-created", "name": "Pipeline Created", "backgroundColor": "#f8fafc"},
                {"id": "page-data", "name": "Data", "visibility": "hidden"},
            ],
            "elements": elements, "layout": layout,
        },
    }


def main():
    spec = build()
    out = "/tmp/zywave-pt-wb-v3.json"
    with open(out, "w") as f:
        json.dump(spec, f)
    dm_n = sum(1 for e in spec["document"]["elements"] if e.get("kind") == "table" and e.get("source", {}).get("kind") == "data-model")
    sql_n = sum(1 for e in spec["document"]["elements"] if e.get("kind") == "table" and e.get("source", {}).get("kind") == "sql")
    print(f"elements={len(spec['document']['elements'])} dm={dm_n} sql={sql_n}")
    try:
        print("PUT", api("PUT", f"/v2/workbooks/{WB}/spec", spec))
        return
    except RuntimeError as e:
        print("ERR1", str(e)[:3500])
    for el in spec["document"]["elements"]:
        if el.get("kind") == "text":
            el["body"] = re.sub(r"<p>(?!</p>)", '<p class="p-small">', el["body"])
        if el.get("kind") in ("bar-chart", "line-chart"):
            el.pop("legend", None)
            el.pop("dataLabel", None)
            if isinstance(el.get("color"), dict):
                el["color"].pop("palette", None)
                if el["color"].get("by") == "category" and "scheme" not in el["color"]:
                    el["color"] = {"by": "single", "value": ORANGE}
    for attempt in range(15):
        try:
            print("PUT", api("PUT", f"/v2/workbooks/{WB}/spec", spec))
            return
        except RuntimeError as err:
            msg = str(err)
            print(f"ERR{attempt+2}", msg[:2000])
            for idx in [int(x) for x in re.findall(r"elements\[(\d+)\]", msg)]:
                el = spec["document"]["elements"][idx]
                print("fix", el.get("id"), el.get("kind"))
                if el.get("kind") == "bar-chart":
                    el["color"] = {"by": "single", "value": BLUE if "seg" in el["id"] or "src" in el["id"] else ORANGE}
                    el.pop("legend", None)
                if el.get("kind") == "text":
                    el["body"] = re.sub(r"<p(?![^>]*class)>", '<p class="p-small">', el["body"])
            with open(out, "w") as f:
                json.dump(spec, f)
    raise SystemExit("failed")


if __name__ == "__main__":
    main()
