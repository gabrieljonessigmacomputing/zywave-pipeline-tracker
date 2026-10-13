#!/usr/bin/env python3
"""Pipeline Tracker FY2026 — still-matched workbook on layered data model.

Sources ONLY data-model elements (1-row KPIs + small chart grains).
No custom SQL / warehouse tables in the workbook.
Plugins (pace-bullet, stage-funnel) hosted on GitHub Pages — register in Sigma admin.
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
DM_IDS = "/tmp/zywave-pt-dm.json"

TEAL, BLUE, ORANGE, RED, GREEN = "#0d9488", "#2563eb", "#f97316", "#dc2626", "#16a34a"
CANVAS, WHITE, MUTED, INK = "#f8fafc", "#ffffff", "#64748b", "#0f172a"
SECTION_BG = "#f1f5f9"
AMBER_BG, TEAL_BG, RED_BG, GREEN_BG = "#fffbeb", "#ecfdf5", "#fef2f2", "#f0fdf4"
BORDER = "#e2e8f0"
STAGE_COLORS = ["#38bdf8", "#3b82f6", "#6366f1", "#a855f7", "#db2777", "#f9a8d4"]

PLUGIN_PACE = "https://gabrieljonessigmacomputing.github.io/zywave-pipeline-tracker/plugins/pace-bullet/"
PLUGIN_FUNNEL = "https://gabrieljonessigmacomputing.github.io/zywave-pipeline-tracker/plugins/stage-funnel/"


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
        raise RuntimeError(f"{e.code}: {e.read().decode()[:8000]}") from e


def dm_id() -> str:
    if os.path.exists(DM_IDS):
        try:
            return json.load(open(DM_IDS)).get("dataModelId") or DM
        except Exception:
            pass
    return DM


def dm_src(element_id: str) -> dict:
    return {"kind": "data-model", "dataModelId": dm_id(), "elementId": element_id}


def T(id_, body):
    body = re.sub(r"<p>(?!</p>)", '<p class="p-small">', body)
    return {"id": id_, "kind": "text", "body": body}


def C(id_, bg=WHITE, border=BORDER):
    return {
        "id": id_,
        "kind": "container",
        "style": {
            "backgroundColor": bg,
            "borderColor": border,
            "borderWidth": 1,
            "borderRadius": "round",
        },
    }


def kpi(id_, title, source, formula, color=INK, bg=None, fmt="$,.2s"):
    return {
        "id": id_,
        "kind": "kpi-chart",
        "name": title,
        "source": {"kind": "table", "elementId": source},
        "columns": [
            {
                "id": f"{id_}-v",
                "formula": formula,
                "format": {"kind": "number", "formatString": fmt},
            }
        ],
        "value": {"columnId": f"{id_}-v", "fontSize": "auto", "color": color},
        "style": {"borderRadius": "round", "backgroundColor": bg or WHITE},
    }


def E(eid, c1, c2, r1, r2, indent=0):
    pad = "  " * (indent + 1)
    return f'{pad}<Element elementId="{eid}" gridColumn="{c1} / {c2}" gridRow="{r1} / {r2}"/>'


def Cont(cid, c1, c2, r1, r2, kids, indent=0):
    pad = "  " * (indent + 1)
    return (
        f'{pad}<Container elementId="{cid}" type="grid" '
        f'gridColumn="{c1} / {c2}" gridRow="{r1} / {r2}" '
        f'gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">\n'
        + "\n".join(kids)
        + f"\n{pad}</Container>"
    )


def page(pid, lines):
    return (
        f'<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="{pid}">\n'
        + "\n".join(lines)
        + "\n</Page>"
    )


def passthrough(wid: str, wname: str, element_id: str, dm_name: str, cols: list[tuple]):
    """Thin workbook table over DM — names differ so lineage is readable."""
    columns = []
    for cid, cname, fmt in cols:
        c = {"id": cid, "name": cname, "formula": f"[{dm_name}/{cname}]"}
        if fmt:
            c["format"] = fmt
        columns.append(c)
    return {
        "id": wid,
        "kind": "table",
        "name": wname,
        "source": dm_src(element_id),
        "columns": columns,
    }


def money():
    return {"kind": "number", "formatString": "$,.0f"}


def pct():
    return {"kind": "number", "formatString": ".1%"}


def build():
    els: list[dict] = []
    m, p = money, pct

    # ── Workbook bindings (clear names ≠ DM names) ───────────
    els += [
        passthrough(
            "wb-open",
            "WB Open Horizons",
            "kpi-open",
            "KPI Open Horizons",
            [
                ("a", "TOTAL_OPPS", None),
                ("b", "TOTAL_ACV", m()),
                ("c", "Q4_OPPS", None),
                ("d", "Q4_ACV", m()),
                ("e", "NQ_OPPS", None),
                ("f", "NQ_ACV", m()),
                ("g", "Q2OUT_OPPS", None),
                ("h", "Q2OUT_ACV", m()),
                ("i", "CLOSE_CY_ACV", m()),
                ("j", "CLOSE_NY_ACV", m()),
                ("k", "CLOSE_FY_ACV", m()),
            ],
        ),
        passthrough(
            "wb-created",
            "WB Pipeline Created",
            "kpi-created",
            "KPI Pipeline Created",
            [
                ("a", "YTD_ACV", m()),
                ("b", "Q4_ACV", m()),
                ("c", "WEEK_ACV", m()),
                ("d", "WEEK_OPPS", None),
                ("e", "CREATED_CLOSING_ACV", m()),
                ("f", "CREATED_CLOSING_OPPS", None),
                ("g", "YEAR_GOAL", m()),
                ("h", "Q4_GOAL", m()),
                ("i", "YEAR_ELAPSED", p()),
                ("j", "Q4_ELAPSED", p()),
            ],
        ),
        passthrough(
            "wb-walkin",
            "WB Walk-in",
            "kpi-walkin",
            "KPI Walk-in Q4",
            [("a", "OPPS", None), ("b", "ACV", m())],
        ),
        passthrough(
            "wb-closed",
            "WB Closed Q4",
            "kpi-closed",
            "KPI Closed Q4",
            [
                ("a", "WON_ACV", m()),
                ("b", "WON_OPPS", None),
                ("c", "LOST_ACV", m()),
                ("d", "LOST_OPPS", None),
            ],
        ),
        passthrough(
            "wb-sourcing",
            "WB Sourcing Mix",
            "kpi-sourcing",
            "KPI Sourcing Mix",
            [("a", "SOURCE_BUCKET", None), ("b", "OPPS", None), ("c", "ACV", m())],
        ),
        passthrough(
            "wb-funnel",
            "WB Q4 Funnel",
            "funnel-q4",
            "Chart Q4 Funnel by Stage",
            [("a", "STAGE", None), ("b", "ORD", None), ("c", "OPPS", None), ("d", "ACV", m())],
        ),
        passthrough(
            "wb-open-month",
            "WB Open Month Stage",
            "chart-open-month",
            "Chart Open by Close Month Stage",
            [
                ("a", "CLOSE_MONTH", {"kind": "datetime", "formatString": "%b %Y"}),
                ("b", "STAGE", None),
                ("c", "ACV", m()),
            ],
        ),
        passthrough(
            "wb-open-prod",
            "WB Open Product",
            "chart-open-prod",
            "Chart Open by Product",
            [("a", "PRODUCT_CATEGORY", None), ("b", "ACV", m())],
        ),
        passthrough(
            "wb-created-month",
            "WB Created Month",
            "chart-created-month",
            "Chart Created by Month",
            [
                ("a", "MONTH", {"kind": "datetime", "formatString": "%b %Y"}),
                ("b", "ACV", m()),
                ("c", "OPPS", None),
            ],
        ),
        passthrough(
            "wb-snap",
            "WB Snapshot Trend",
            "snap-daily",
            "Chart Snapshot Trend",
            [
                ("a", "SNAPSHOTDATE", {"kind": "datetime", "formatString": "%b %d"}),
                ("b", "OPPS", None),
                ("c", "FCST_NETACV", m()),
            ],
        ),
        passthrough(
            "wb-pace",
            "WB Pace Strip",
            "pace-long",
            "Chart Pace Strip",
            [
                ("a", "METRIC", None),
                ("b", "PART", None),
                ("c", "VAL", p()),
                ("d", "PACED", p()),
            ],
        ),
        passthrough(
            "wb-seg",
            "WB Segment Attainment",
            "chart-seg-att",
            "Chart Attainment by Segment",
            [("a", "NEW_SEGMENT", None), ("b", "OPPS", None), ("c", "ACV", m())],
        ),
        passthrough(
            "wb-goals",
            "WB Goals",
            "dim-goals",
            "Dim Goals",
            [("a", "METRIC", None), ("b", "GOAL", m())],
        ),
        passthrough(
            "wb-seg-tgt",
            "WB Segment Targets",
            "dim-seg-tgt",
            "Dim Segment Targets",
            [("a", "SEGMENT", None), ("b", "TARGET", m())],
        ),
    ]

    # Formula helpers (1-row Sum)
    ytd = "Sum([WB Pipeline Created/YTD_ACV])"
    cq4 = "Sum([WB Pipeline Created/Q4_ACV])"
    week = "Sum([WB Pipeline Created/WEEK_ACV])"
    week_o = "Sum([WB Pipeline Created/WEEK_OPPS])"
    ccq = "Sum([WB Pipeline Created/CREATED_CLOSING_ACV])"
    ccq_o = "Sum([WB Pipeline Created/CREATED_CLOSING_OPPS])"
    ygoal = "Sum([WB Pipeline Created/YEAR_GOAL])"
    qgoal = "Sum([WB Pipeline Created/Q4_GOAL])"
    yelap = "Sum([WB Pipeline Created/YEAR_ELAPSED])"
    qelap = "Sum([WB Pipeline Created/Q4_ELAPSED])"

    tot = "Sum([WB Open Horizons/TOTAL_ACV])"
    tot_o = "Sum([WB Open Horizons/TOTAL_OPPS])"
    q4a = "Sum([WB Open Horizons/Q4_ACV])"
    q4o = "Sum([WB Open Horizons/Q4_OPPS])"
    nqa = "Sum([WB Open Horizons/NQ_ACV])"
    nqo = "Sum([WB Open Horizons/NQ_OPPS])"
    q2a = "Sum([WB Open Horizons/Q2OUT_ACV])"
    q2o = "Sum([WB Open Horizons/Q2OUT_OPPS])"
    cy = "Sum([WB Open Horizons/CLOSE_CY_ACV])"
    ny = "Sum([WB Open Horizons/CLOSE_NY_ACV])"
    fy = "Sum([WB Open Horizons/CLOSE_FY_ACV])"

    walk = "Sum([WB Walk-in/ACV])"
    walk_o = "Sum([WB Walk-in/OPPS])"
    won = "Sum([WB Closed Q4/WON_ACV])"
    won_o = "Sum([WB Closed Q4/WON_OPPS])"
    lost = "Sum([WB Closed Q4/LOST_ACV])"
    lost_o = "Sum([WB Closed Q4/LOST_OPPS])"

    mkt = 'SumIf([WB Sourcing Mix/ACV], [WB Sourcing Mix/SOURCE_BUCKET] = "Marketing")'
    sales = 'SumIf([WB Sourcing Mix/ACV], [WB Sourcing Mix/SOURCE_BUCKET] = "Sales")'
    src_tot = "Sum([WB Sourcing Mix/ACV])"

    # Controls
    els += [
        {
            "kind": "control",
            "id": "ctrl-segment",
            "controlId": "Segment",
            "name": "Segment",
            "controlType": "list",
            "mode": "include",
            "selectionMode": "single",
            "source": {
                "kind": "manual",
                "valueType": "text",
                "values": ["All", "Core", "Mid-Market", "Enterprise"],
                "labels": ["All Segments", "Core", "Mid-Market", "Enterprise"],
            },
            "value": "All",
        },
        {
            "kind": "control",
            "id": "ctrl-dealtype",
            "controlId": "DealType",
            "name": "Deal Type",
            "controlType": "list",
            "mode": "include",
            "selectionMode": "single",
            "source": {
                "kind": "manual",
                "valueType": "text",
                "values": ["All", "New Business", "Renewal", "Product Addition"],
                "labels": ["All", "New Business", "Renewal", "Product Addition"],
            },
            "value": "All",
        },
        {
            "kind": "control",
            "id": "ctrl-stage1",
            "controlId": "IncludeStage1",
            "name": "Include Stage 1",
            "controlType": "checkbox",
            "mode": "True/False",
            "value": False,
        },
        {
            "kind": "control",
            "id": "ctrl-period",
            "controlId": "SourcingPeriod",
            "name": "Period",
            "controlType": "list",
            "mode": "include",
            "selectionMode": "single",
            "source": {
                "kind": "manual",
                "valueType": "text",
                "values": ["Q4", "YTD"],
                "labels": ["Current Quarter (Q4)", "Year-to-Date"],
            },
            "value": "Q4",
        },
    ]

    def pace_bar(eid: str, metric: str):
        return {
            "id": eid,
            "kind": "bar-chart",
            "name": "pace",
            "source": {"kind": "table", "elementId": "wb-pace"},
            "columns": [
                {"id": f"{eid}-m", "name": "Metric", "formula": "[WB Pace Strip/METRIC]"},
                {"id": f"{eid}-p", "name": "Part", "formula": "[WB Pace Strip/PART]"},
                {
                    "id": f"{eid}-v",
                    "name": "Val",
                    "formula": f'SumIf([WB Pace Strip/VAL], [WB Pace Strip/METRIC] = "{metric}")',
                    "format": {"kind": "number", "formatString": ".0%"},
                },
            ],
            "xAxis": {"columnId": f"{eid}-m"},
            "yAxis": {"columnIds": [f"{eid}-v"]},
            "color": {
                "by": "category",
                "column": f"{eid}-p",
                "palette": {"Actual": ORANGE, "Remain": "#e2e8f0"},
            },
            "orientation": "horizontal",
            "stacking": "normalized",
            "style": {"backgroundColor": WHITE},
        }

    # ═══════════════ ROTB ═══════════════
    els += [
        T(
            "rotb-title",
            f'# ROTB Summary\n<p class="p-small"><span style="color: {MUTED}">One-page view of creation, coverage, movement, and demand. Q4 · FY2026</span></p>',
        ),
        T(
            "rotb-badge",
            f'<p style="text-align: right"><span style="color: {MUTED}">Read-only snapshot · October · Snowflake SoT</span></p>',
        ),
        C("sec-01", SECTION_BG, SECTION_BG),
        C("sec-02", SECTION_BG, SECTION_BG),
        C("sec-03", SECTION_BG, SECTION_BG),
        C("sec-04", SECTION_BG, SECTION_BG),
        C("sec-05", SECTION_BG, SECTION_BG),
        C("card-year"),
        C("card-q4"),
        C("card-week"),
        C("card-ccq", AMBER_BG, "#fbbf24"),
        C("card-cwq", TEAL_BG, "#5eead4"),
        T(
            "rotb-s01",
            f'## <span style="color: {TEAL}">01 / PIPELINE CREATION</span>\n'
            f'**<span style="color: {INK}">Creation pace</span>**',
        ),
        T(
            "rk-year-body",
            f'<p class="p-small"><span style="color: {MUTED}">Year Pipeline Created</span></p>\n'
            f'<p class="p-small"><span style="font-size: 36px; color: {INK}">{{{{{ytd} | $,.2s}}}}</span></p>\n'
            f'<p class="p-small"><span style="color: {ORANGE}">{{{{{ytd} / {ygoal} | .1%}}}} of goal</span></p>',
        ),
        pace_bar("rk-year-bar", "Year"),
        T(
            "rk-year-foot",
            f'<p class="p-small"><span style="color: {MUTED}">Target: $94.6M</span> · '
            f'<span style="color: {ORANGE}">{{{{{yelap} | .1%}}}} paced</span></p>\n'
            f'<p class="p-small"><span style="color: {MUTED}">Year progress {{{{{yelap} | .0%}}}}</span></p>',
        ),
        T(
            "rk-q4-body",
            f'<p class="p-small"><span style="color: {MUTED}">Q4 Pipeline Created</span></p>\n'
            f'<p class="p-small"><span style="font-size: 36px; color: {INK}">{{{{{cq4} | $,.2s}}}}</span></p>\n'
            f'<p class="p-small"><span style="color: {ORANGE}">{{{{{cq4} / {qgoal} | .1%}}}} of goal</span></p>',
        ),
        pace_bar("rk-q4-bar", "Q4"),
        T(
            "rk-q4-foot",
            f'<p class="p-small"><span style="color: {MUTED}">Target: $26.7M</span> · '
            f'<span style="color: {ORANGE}">{{{{{qelap} | .1%}}}} paced</span></p>\n'
            f'<p class="p-small"><span style="color: {MUTED}">Quarter progress {{{{{qelap} | .0%}}}}</span></p>',
        ),
        kpi("rk-week", "Created This Week", "wb-created", week, INK),
        T(
            "rk-week-cap",
            f'<p class="p-small"><span style="color: {MUTED}">{{{{{week_o} | ,.0f}}}} opportunities</span></p>',
        ),
        kpi("rk-ccq", "Created & Closing This Quarter", "wb-created", ccq, ORANGE, AMBER_BG),
        T(
            "rk-ccq-cap",
            f'<p class="p-small"><span style="color: {MUTED}">{{{{{ccq_o} | ,.0f}}}} opportunities</span></p>',
        ),
        kpi("rk-cwq", "Created & Won This Quarter", "wb-closed", won, GREEN, TEAL_BG),
        T(
            "rk-cwq-cap",
            f'<p class="p-small"><span style="color: {MUTED}">{{{{{won_o} | ,.0f}}}} opportunities</span></p>',
        ),
        T(
            "pace-plugin-note",
            f'<p class="p-small"><span style="color: {ORANGE}">PLUGIN</span> '
            f'<span style="color: {MUTED}">paced tick — register </span>'
            f'<span style="color: {BLUE}">{PLUGIN_PACE}</span>'
            f'<span style="color: {MUTED}"> · native = 100% Actual/Remain strip</span></p>',
        ),
        T(
            "rotb-s02",
            f'## <span style="color: {TEAL}">02 / COVERAGE</span>\n'
            f'**<span style="color: {INK}">Open pipeline</span>**',
        ),
        C("cov-1"),
        C("cov-2"),
        C("cov-3"),
        C("cov-4"),
        kpi("rk-open", "Total Open Pipeline", "wb-open", tot, TEAL, TEAL_BG),
        kpi("rk-cq", "Closing This Quarter", "wb-open", q4a, BLUE),
        kpi("rk-nq", "Closing Next Quarter", "wb-open", nqa, BLUE),
        kpi("rk-2q", "Closing Two Quarters Out", "wb-open", q2a, BLUE),
        T(
            "rotb-s03",
            f'## <span style="color: {MUTED}">03 / PIPELINE MANAGEMENT</span>\n'
            f'**<span style="color: {INK}">Q4 movement</span>**',
        ),
        C("mgmt-w"),
        C("mgmt-l", RED_BG, "#fecaca"),
        C("mgmt-n", GREEN_BG, "#bbf7d0"),
        kpi("rk-walk", "Walk-in (Q4 start)", "wb-walkin", walk, BLUE),
        T(
            "rk-walk-cap",
            f'<p class="p-small"><span style="color: {MUTED}">Frozen 2026-10-01 · {{{{{walk_o} | ,.0f}}}} opps · FCST ≤ $2M</span></p>',
        ),
        kpi("rk-lost", "Closed Lost", "wb-closed", lost, RED, RED_BG),
        T(
            "rk-lost-cap",
            f'<p class="p-small"><span style="color: {MUTED}">{{{{{lost_o} | ,.0f}}}} opps · ≤ $50k/deal</span></p>',
        ),
        kpi("rk-won2", "Closed Won", "wb-closed", won, GREEN, GREEN_BG),
        T(
            "rk-won2-cap",
            f'<p class="p-small"><span style="color: {MUTED}">{{{{{won_o} | ,.0f}}}} opportunities</span></p>',
        ),
        T(
            "rotb-s04",
            f'## <span style="color: {BLUE}">04 / MARKETING PERFORMANCE</span>\n'
            f'**<span style="color: {INK}">Demand signals · October</span>**',
        ),
    ]
    for eid, title in [
        ("dm-mql", "MQLs this month"),
        ("dm-s0", "Stage 0 this month"),
        ("dm-s1", "Stage 1 this month"),
        ("dm-s2", "Stage 2 this month"),
    ]:
        els.append(C(eid))
        els.append(
            T(
                f"{eid}-b",
                f'<p class="p-small"><span style="color: {MUTED}">{title}</span></p>\n'
                f'<p class="p-small" style="text-align: center"><span style="font-size: 32px; color: #cbd5e1">—</span></p>\n'
                f'<p class="p-small"><span style="color: #94a3b8">Awaiting top-of-funnel feed</span></p>',
            )
        )
    els += [
        T(
            "rotb-s05",
            f'## <span style="color: {ORANGE}">05 / SALES PIPELINE GENERATION</span>\n'
            f'**<span style="color: {INK}">Open Stage 2+ by Lead Source</span>**',
        ),
        C("sg-m"),
        C("sg-s"),
        kpi("rk-mkt", "Marketing-sourced", "wb-sourcing", mkt, BLUE),
        kpi("rk-sales", "Sales-sourced", "wb-sourcing", sales, ORANGE),
    ]

    # ═══════════════ OPEN ═══════════════
    els += [
        T(
            "open-title",
            f'# Open Pipeline\n<p class="p-small"><span style="color: {MUTED}">FY2026 Stage 2+ Pipeline by Close Date</span></p>',
        ),
        T(
            "open-live",
            f'<p style="text-align: right"><span style="color: {GREEN}">Live from Snowflake</span></p>',
        ),
    ]
    for cid in ["okc-u", "okc-t", "okc-w", "okc-q", "okc-avg", "okc-chg"]:
        els.append(C(cid))
    els += [
        kpi("ok-u", "Unique Opportunities", "wb-open", tot_o, INK, fmt=",.0f"),
        kpi("ok-t", "Total Pipeline ACV", "wb-open", tot, INK),
        kpi("ok-w", "Walk-in Pipeline", "wb-walkin", walk, BLUE),
        T("ok-w-cap", f'<p class="p-small"><span style="color: {MUTED}">Q4 start (frozen)</span></p>'),
        kpi("ok-q", "Q4 Pipeline ACV", "wb-open", q4a, INK),
        T(
            "ok-q-cap",
            f'<p class="p-small"><span style="color: {MUTED}">{{{{{q4o} | ,.0f}}}} opps</span></p>',
        ),
        kpi(
            "ok-avg",
            "Avg Deal Size",
            "wb-open",
            f"({tot}) / ({tot_o})",
            INK,
            fmt="$,.0f",
        ),
        T(
            "open-chg",
            f'## Q4 Pipeline Changes\n<span style="color: {MUTED}">Current quarter pipeline movement</span>',
        ),
        kpi("ok-q4tot", "Current Open Pipeline", "wb-open", q4a, INK),
        T(
            "ok-q4link",
            f'<p class="p-small"><span style="color: {BLUE}">Close Date: Current Quarter</span></p>',
        ),
        {
            "id": "chart-funnel",
            "kind": "bar-chart",
            "name": "Stage composition",
            "source": {"kind": "table", "elementId": "wb-funnel"},
            "columns": [
                {"id": "cf-b", "name": "Bucket", "formula": "'Q4 Open'"},
                {"id": "cf-s", "name": "Stage", "formula": "[WB Q4 Funnel/STAGE]"},
                {
                    "id": "cf-v",
                    "name": "ACV",
                    "formula": "Sum([WB Q4 Funnel/ACV])",
                    "format": {"kind": "number", "formatString": "$,.2s"},
                },
                {"id": "cf-o", "name": "Order", "formula": "Min([WB Q4 Funnel/ORD])"},
            ],
            "xAxis": {"columnId": "cf-b"},
            "yAxis": {"columnIds": ["cf-v"]},
            "orientation": "horizontal",
            "stacking": "stacked",
            "color": {"by": "category", "column": "cf-s", "scheme": STAGE_COLORS},
            "style": {"backgroundColor": WHITE, "borderRadius": "round"},
        },
        T(
            "funnel-plugin",
            f'<p class="p-small"><span style="color: {ORANGE}">PLUGIN</span> '
            f'<span style="color: {MUTED}">tapered funnel — </span>'
            f'<span style="color: {BLUE}">{PLUGIN_FUNNEL}</span></p>',
        ),
        T("mv-left", f'<p class="p-small"><span style="color: {MUTED}">WHAT LEFT</span></p>'),
        C("mv-push-c", RED_BG, "#fecaca"),
        C("mv-lost-c", RED_BG, "#fecaca"),
        T(
            "mv-push",
            f'<p class="p-small"><span style="color: {RED}">Pushed Out</span></p>\n'
            f'<p class="p-small" style="text-align: center"><span style="font-size: 28px; color: {RED}">—</span></p>\n'
            f'<p class="p-small"><span style="color: {MUTED}">Needs snapshot diffs</span></p>',
        ),
        kpi("mv-lost", "Closed Lost", "wb-closed", lost, RED, RED_BG),
        T("mv-also", f'<p class="p-small"><span style="color: {MUTED}">ALSO LEFT PIPELINE</span></p>'),
        C("mv-pullb-c", RED_BG, "#fecaca"),
        C("mv-won-c", GREEN_BG, "#bbf7d0"),
        T(
            "mv-pullb",
            f'<p class="p-small"><span style="color: {RED}">Pulled Back</span></p>\n'
            f'<p class="p-small" style="text-align: center"><span style="font-size: 28px; color: {RED}">$0</span></p>',
        ),
        kpi("mv-won", "Closed Won", "wb-closed", won, GREEN, GREEN_BG),
        T("mv-add", f'<p class="p-small"><span style="color: {MUTED}">WHAT ADDED</span></p>'),
        C("mv-pulli-c", GREEN_BG, "#bbf7d0"),
        C("mv-size-c", GREEN_BG, "#bbf7d0"),
        T(
            "mv-pulli",
            f'<p class="p-small"><span style="color: {GREEN}">Pulled In</span></p>\n'
            f'<p class="p-small" style="text-align: center"><span style="font-size: 28px; color: {GREEN}">—</span></p>',
        ),
        T(
            "mv-size",
            f'<p class="p-small"><span style="color: {GREEN}">Size Increases</span></p>\n'
            f'<p class="p-small" style="text-align: center"><span style="font-size: 28px; color: {GREEN}">—</span></p>',
        ),
        {
            "id": "chart-seg-month",
            "kind": "bar-chart",
            "name": "Open Pipeline by Close Month × Stage",
            "source": {"kind": "table", "elementId": "wb-open-month"},
            "columns": [
                {
                    "id": "csm-q",
                    "name": "Close Month",
                    "formula": "[WB Open Month Stage/CLOSE_MONTH]",
                    "format": {"kind": "datetime", "formatString": "%b %Y"},
                },
                {"id": "csm-s", "name": "Stage", "formula": "[WB Open Month Stage/STAGE]"},
                {
                    "id": "csm-v",
                    "name": "ACV",
                    "formula": "Sum([WB Open Month Stage/ACV])",
                    "format": {"kind": "number", "formatString": "$,.2s"},
                },
            ],
            "xAxis": {"columnId": "csm-q"},
            "yAxis": {"columnIds": ["csm-v"]},
            "color": {"by": "category", "column": "csm-s", "scheme": STAGE_COLORS},
            "stacking": "stacked",
            "style": {"backgroundColor": WHITE, "borderRadius": "round", "borderColor": BORDER, "borderWidth": 1},
        },
        {
            "id": "chart-prod",
            "kind": "bar-chart",
            "name": "Open Pipeline by Product Category",
            "source": {"kind": "table", "elementId": "wb-open-prod"},
            "columns": [
                {"id": "cp-p", "name": "Product", "formula": "[WB Open Product/PRODUCT_CATEGORY]"},
                {
                    "id": "cp-v",
                    "name": "ACV",
                    "formula": "Sum([WB Open Product/ACV])",
                    "format": {"kind": "number", "formatString": "$,.2s"},
                },
            ],
            "xAxis": {"columnId": "cp-p"},
            "yAxis": {"columnIds": ["cp-v"]},
            "orientation": "horizontal",
            "color": {"by": "single", "value": TEAL},
            "style": {"backgroundColor": WHITE, "borderRadius": "round", "borderColor": BORDER, "borderWidth": 1},
        },
    ]

    # ═══════════════ TOTAL ═══════════════
    els += [
        T(
            "total-title",
            f'# Total Company\n<p class="p-small"><span style="color: {MUTED}">All pipeline sources</span></p>',
        ),
        C("tc-1"),
        C("tc-2"),
        C("tc-3"),
        kpi("tk-cq", "Pipeline to Close · Current Quarter", "wb-open", q4a, INK),
        T(
            "tk-cq-cap",
            f'<p class="p-small"><span style="color: {MUTED}">Q4 2026 · {{{{{q4o} | ,.0f}}}} open deals</span></p>',
        ),
        kpi("tk-nq", "Pipeline to Close · Next Quarter", "wb-open", nqa, INK),
        T(
            "tk-nq-cap",
            f'<p class="p-small"><span style="color: {MUTED}">Q1 2027 · {{{{{nqo} | ,.0f}}}} open deals</span></p>',
        ),
        kpi("tk-2q", "Pipeline to Close · Two Quarters Out", "wb-open", q2a, INK),
        T(
            "tk-2q-cap",
            f'<p class="p-small"><span style="color: {MUTED}">Q2 2027 · {{{{{q2o} | ,.0f}}}} open deals</span></p>',
        ),
        {
            "id": "chart-seg",
            "kind": "bar-chart",
            "name": "Open ACV by New Segment",
            "source": {"kind": "table", "elementId": "wb-seg"},
            "columns": [
                {"id": "cs-s", "name": "Segment", "formula": "[WB Segment Attainment/NEW_SEGMENT]"},
                {
                    "id": "cs-v",
                    "name": "ACV",
                    "formula": "Sum([WB Segment Attainment/ACV])",
                    "format": {"kind": "number", "formatString": "$,.2s"},
                },
            ],
            "xAxis": {"columnId": "cs-s"},
            "yAxis": {"columnIds": ["cs-v"]},
            "color": {"by": "single", "value": BLUE},
            "style": {"backgroundColor": WHITE, "borderRadius": "round", "borderColor": BORDER, "borderWidth": 1},
        },
        {
            "id": "tbl-attain",
            "kind": "table",
            "name": "Attainment by New Segment",
            "source": {"kind": "table", "elementId": "wb-seg"},
            "columns": [
                {"id": "ta-s", "name": "Segment", "formula": "[WB Segment Attainment/NEW_SEGMENT]"},
                {
                    "id": "ta-a",
                    "name": "ACV",
                    "formula": "Sum([WB Segment Attainment/ACV])",
                    "format": {"kind": "number", "formatString": "$,.0f"},
                },
                {
                    "id": "ta-o",
                    "name": "Opps",
                    "formula": "Sum([WB Segment Attainment/OPPS])",
                    "format": {"kind": "number", "formatString": ",.0f"},
                },
            ],
        },
        T(
            "total-defs",
            f'<p class="p-small"><span style="color: {MUTED}">Targets in Dim Segment Targets (data model). Actuals pre-aggregated open Stage 2+.</span></p>',
        ),
    ]

    # ═══════════════ SOURCING ═══════════════
    els += [
        T(
            "sourcing-title",
            f'# Pipeline Sourcing\n<p class="p-small"><span style="color: {MUTED}">FY2026 Stage 2+ by Lead Source · mix target M 39% / S 61%</span></p>',
        ),
        C("sc-row", SECTION_BG, SECTION_BG),
        kpi("sk-m", "Marketing-sourced", "wb-sourcing", mkt, BLUE),
        T("sk-m-cap", f'<p class="p-small"><span style="color: {MUTED}">target mix 39%</span></p>'),
        kpi("sk-s", "Sales-sourced", "wb-sourcing", sales, ORANGE),
        T("sk-s-cap", f'<p class="p-small"><span style="color: {MUTED}">target mix 61%</span></p>'),
        kpi("sk-t", "Total sourced (Stage 2+)", "wb-sourcing", src_tot, INK),
        T(
            "sk-mix",
            f'<p class="p-small"><span style="color: {MUTED}">Mix target</span></p>\n'
            f'<p class="p-small" style="text-align: center"><span style="font-size: 22px; color: {INK}">M 39% / S 61%</span></p>',
        ),
        {
            "id": "chart-src",
            "kind": "bar-chart",
            "name": "Open Stage 2+ by Lead Source",
            "source": {"kind": "table", "elementId": "wb-sourcing"},
            "columns": [
                {"id": "cr-s", "name": "Source", "formula": "[WB Sourcing Mix/SOURCE_BUCKET]"},
                {
                    "id": "cr-v",
                    "name": "ACV",
                    "formula": "Sum([WB Sourcing Mix/ACV])",
                    "format": {"kind": "number", "formatString": "$,.2s"},
                },
            ],
            "xAxis": {"columnId": "cr-s"},
            "yAxis": {"columnIds": ["cr-v"]},
            "color": {"by": "single", "value": BLUE},
            "style": {"backgroundColor": WHITE, "borderRadius": "round", "borderColor": BORDER, "borderWidth": 1},
        },
        {
            "id": "tbl-src-prod",
            "kind": "table",
            "name": "Sourcing mix detail",
            "source": {"kind": "table", "elementId": "wb-sourcing"},
            "columns": [
                {"id": "tsp-s", "name": "Source", "formula": "[WB Sourcing Mix/SOURCE_BUCKET]"},
                {
                    "id": "tsp-a",
                    "name": "ACV",
                    "formula": "Sum([WB Sourcing Mix/ACV])",
                    "format": {"kind": "number", "formatString": "$,.0f"},
                },
                {
                    "id": "tsp-o",
                    "name": "Opps",
                    "formula": "Sum([WB Sourcing Mix/OPPS])",
                    "format": {"kind": "number", "formatString": ",.0f"},
                },
            ],
        },
    ]

    # ═══════════════ MOVEMENT ═══════════════
    els += [
        T(
            "movement-title",
            f'# Pipeline Movement\n<p class="p-small"><span style="color: {MUTED}">Daily snapshots</span></p>',
        ),
        C("mc-1"),
        C("mc-2"),
        C("mc-3"),
        C("mc-4"),
        C("mc-5"),
        C("mc-6"),
        kpi("mk-open", "Total Open Pipeline", "wb-open", tot, INK, fmt="$,.0f"),
        T(
            "mk-delta",
            f'<p class="p-small"><span style="color: {MUTED}">30-Day Delta</span></p>\n'
            f'<p class="p-small" style="text-align: center"><span style="font-size: 28px; color: {BLUE}">—</span></p>',
        ),
        T(
            "mk-yoy",
            f'<p class="p-small"><span style="color: {MUTED}">YoY (Oct vs Oct)</span></p>\n'
            f'<p class="p-small" style="text-align: center"><span style="font-size: 28px; color: {BLUE}">—</span></p>',
        ),
        kpi("mk-opps", "Open Opportunities", "wb-open", tot_o, INK, fmt=",.0f"),
        kpi("mk-avg", "Avg Deal Size", "wb-open", f"({tot}) / ({tot_o})", INK, fmt="$,.0f"),
        T(
            "mk-split",
            f'<p class="p-small"><span style="color: {MUTED}">Deal size split</span></p>',
        ),
        {
            "id": "chart-move",
            "kind": "line-chart",
            "name": "Pipeline Movement",
            "source": {"kind": "table", "elementId": "wb-snap"},
            "columns": [
                {
                    "id": "cm-d",
                    "name": "Date",
                    "formula": "[WB Snapshot Trend/SNAPSHOTDATE]",
                    "format": {"kind": "datetime", "formatString": "%b %d"},
                },
                {
                    "id": "cm-v",
                    "name": "FCST",
                    "formula": "Sum([WB Snapshot Trend/FCST_NETACV])",
                    "format": {"kind": "number", "formatString": "$,.0f"},
                },
            ],
            "xAxis": {"columnId": "cm-d"},
            "yAxis": {"columnIds": ["cm-v"]},
            "color": {"by": "single", "value": TEAL},
            "style": {"backgroundColor": WHITE, "borderRadius": "round", "borderColor": BORDER, "borderWidth": 1},
        },
        T(
            "move-note",
            f'<p class="p-small"><span style="color: {MUTED}">Snapshot FCST capped $0–$2M/opp. Deltas need paired snapshot dates in the data model.</span></p>',
        ),
    ]

    # ═══════════════ CREATED ═══════════════
    els += [
        T(
            "created-title",
            f'# Pipeline Created\n<p class="p-small"><span style="color: {MUTED}">Equation strip · Stage 2 attained</span></p>',
        ),
        T(
            "created-eq",
            f'<p class="p-small"><span style="color: {MUTED}">Open (Qtr Start) + Created − Won − Lost − Pulled Back − Other = Total Open</span></p>',
        ),
        C("cc-start"),
        C("cc-cr"),
        C("cc-wn"),
        C("cc-ls"),
        C("cc-pb"),
        C("cc-ot"),
        C("cc-tot"),
        C("cc-cy"),
        C("cc-ny"),
        C("cc-fy"),
        kpi("ck-start", "Open (Qtr Start)", "wb-walkin", walk, BLUE, fmt="$,.0f"),
        T("ck-plus", f'<p class="p-small" style="text-align: center"><span style="font-size: 28px; color: {MUTED}">+</span></p>'),
        kpi("ck-cr", "Created This Quarter", "wb-created", cq4, GREEN, fmt="$,.0f"),
        T("ck-m1", f'<p class="p-small" style="text-align: center"><span style="font-size: 28px; color: {MUTED}">−</span></p>'),
        kpi("ck-wn", "Won", "wb-closed", won, GREEN, fmt="$,.0f"),
        T("ck-m2", f'<p class="p-small" style="text-align: center"><span style="font-size: 28px; color: {MUTED}">−</span></p>'),
        kpi("ck-ls", "Lost", "wb-closed", lost, RED, fmt="$,.0f"),
        T("ck-m3", f'<p class="p-small" style="text-align: center"><span style="font-size: 28px; color: {MUTED}">−</span></p>'),
        T(
            "ck-pb",
            f'<p class="p-small"><span style="color: {MUTED}">Pulled Back</span></p>\n'
            f'<p class="p-small" style="text-align: center"><span style="font-size: 22px; color: {INK}">$0</span></p>',
        ),
        T("ck-m4", f'<p class="p-small" style="text-align: center"><span style="font-size: 28px; color: {MUTED}">−</span></p>'),
        T(
            "ck-ot",
            f'<p class="p-small"><span style="color: {MUTED}">Other</span></p>\n'
            f'<p class="p-small" style="text-align: center"><span style="font-size: 22px; color: {INK}">—</span></p>',
        ),
        T("ck-eq", f'<p class="p-small" style="text-align: center"><span style="font-size: 28px; color: {MUTED}">=</span></p>'),
        kpi("ck-tot", "Total Open Pipeline", "wb-open", tot, BLUE, fmt="$,.0f"),
        kpi("ck-cy", "Closing Current Year", "wb-open", cy, TEAL, fmt="$,.0f"),
        kpi("ck-ny", "Closing Next Year", "wb-open", ny, BLUE, fmt="$,.0f"),
        kpi("ck-fy", "Future Years (2028+)", "wb-open", fy, BLUE, fmt="$,.0f"),
        {
            "id": "chart-created",
            "kind": "bar-chart",
            "name": "Pipeline Created by Month",
            "source": {"kind": "table", "elementId": "wb-created-month"},
            "columns": [
                {
                    "id": "ccm-m",
                    "name": "Month",
                    "formula": "[WB Created Month/MONTH]",
                    "format": {"kind": "datetime", "formatString": "%b %Y"},
                },
                {
                    "id": "ccm-v",
                    "name": "Created ACV",
                    "formula": "Sum([WB Created Month/ACV])",
                    "format": {"kind": "number", "formatString": "$,.2s"},
                },
            ],
            "xAxis": {"columnId": "ccm-m"},
            "yAxis": {"columnIds": ["ccm-v"]},
            "stacking": "none",
            "color": {"by": "single", "value": TEAL},
            "style": {"backgroundColor": WHITE, "borderRadius": "round", "borderColor": BORDER, "borderWidth": 1},
        },
    ]

    # ═══════════════ DATA (lineage + plugins) ═══════════════
    els.append(
        T(
            "data-note",
            f"""# Architecture · lineage · plugins

## Data model (source of truth)
`Pipeline Tracker FY2026 · Model`  
https://app.sigmacomputing.com/zywave/data-model/{dm_id()}

| Layer | Elements | Grain |
| --- | --- | --- |
| 01 KPIs | Open / Created / Walk-in / Closed / Sourcing | **1 row** (or few) — fast |
| 02 Charts | Funnel, month×stage, product, created, snap, pace, segment | small GROUP BY |
| 03 Dims | Goals, Segment Targets | literals |

Workbook tables are named `WB *` and bind to `KPI/Chart/Dim *` — **no duplicate names, no SQL in workbook**.

## Plugins (register in Sigma Admin → Account → Plugins)
1. Pace bullet: {PLUGIN_PACE}
2. Stage funnel: {PLUGIN_FUNNEL}

Repo: https://github.com/gabrieljonessigmacomputing/zywave-pipeline-tracker
""",
        )
    )

    def L(eid, c1, c2, r1, r2):
        return E(eid, c1, c2, r1, r2, indent=1)

    rotb_l = [
        E("rotb-title", 1, 18, 1, 3),
        E("rotb-badge", 18, 25, 1, 3),
        Cont(
            "sec-01",
            1,
            25,
            3,
            14,
            [
                L("rotb-s01", 1, 25, 1, 2),
                Cont(
                    "card-year",
                    1,
                    6,
                    2,
                    10,
                    [
                        L("rk-year-body", 1, 25, 1, 4),
                        L("rk-year-bar", 1, 25, 4, 6),
                        L("rk-year-foot", 1, 25, 6, 9),
                    ],
                    indent=2,
                ),
                Cont(
                    "card-q4",
                    6,
                    11,
                    2,
                    10,
                    [
                        L("rk-q4-body", 1, 25, 1, 4),
                        L("rk-q4-bar", 1, 25, 4, 6),
                        L("rk-q4-foot", 1, 25, 6, 9),
                    ],
                    indent=2,
                ),
                Cont(
                    "card-week",
                    11,
                    15,
                    2,
                    10,
                    [L("rk-week", 1, 25, 1, 6), L("rk-week-cap", 1, 25, 6, 9)],
                    indent=2,
                ),
                Cont(
                    "card-ccq",
                    15,
                    20,
                    2,
                    10,
                    [L("rk-ccq", 1, 25, 1, 6), L("rk-ccq-cap", 1, 25, 6, 9)],
                    indent=2,
                ),
                Cont(
                    "card-cwq",
                    20,
                    25,
                    2,
                    10,
                    [L("rk-cwq", 1, 25, 1, 6), L("rk-cwq-cap", 1, 25, 6, 9)],
                    indent=2,
                ),
                L("pace-plugin-note", 1, 25, 10, 11),
            ],
        ),
        Cont(
            "sec-02",
            1,
            25,
            14,
            19,
            [
                L("rotb-s02", 1, 25, 1, 2),
                Cont("cov-1", 1, 7, 2, 6, [L("rk-open", 1, 25, 1, 8)], indent=2),
                Cont("cov-2", 7, 13, 2, 6, [L("rk-cq", 1, 25, 1, 8)], indent=2),
                Cont("cov-3", 13, 19, 2, 6, [L("rk-nq", 1, 25, 1, 8)], indent=2),
                Cont("cov-4", 19, 25, 2, 6, [L("rk-2q", 1, 25, 1, 8)], indent=2),
            ],
        ),
        Cont(
            "sec-03",
            1,
            25,
            19,
            24,
            [
                L("rotb-s03", 1, 25, 1, 2),
                Cont(
                    "mgmt-w",
                    1,
                    9,
                    2,
                    6,
                    [L("rk-walk", 1, 25, 1, 5), L("rk-walk-cap", 1, 25, 5, 7)],
                    indent=2,
                ),
                Cont(
                    "mgmt-l",
                    9,
                    17,
                    2,
                    6,
                    [L("rk-lost", 1, 25, 1, 5), L("rk-lost-cap", 1, 25, 5, 7)],
                    indent=2,
                ),
                Cont(
                    "mgmt-n",
                    17,
                    25,
                    2,
                    6,
                    [L("rk-won2", 1, 25, 1, 5), L("rk-won2-cap", 1, 25, 5, 7)],
                    indent=2,
                ),
            ],
        ),
        Cont(
            "sec-04",
            1,
            25,
            24,
            29,
            [
                L("rotb-s04", 1, 25, 1, 2),
                Cont("dm-mql", 1, 7, 2, 6, [L("dm-mql-b", 1, 25, 1, 8)], indent=2),
                Cont("dm-s0", 7, 13, 2, 6, [L("dm-s0-b", 1, 25, 1, 8)], indent=2),
                Cont("dm-s1", 13, 19, 2, 6, [L("dm-s1-b", 1, 25, 1, 8)], indent=2),
                Cont("dm-s2", 19, 25, 2, 6, [L("dm-s2-b", 1, 25, 1, 8)], indent=2),
            ],
        ),
        Cont(
            "sec-05",
            1,
            25,
            29,
            34,
            [
                L("rotb-s05", 1, 25, 1, 2),
                Cont("sg-m", 1, 13, 2, 6, [L("rk-mkt", 1, 25, 1, 8)], indent=2),
                Cont("sg-s", 13, 25, 2, 6, [L("rk-sales", 1, 25, 1, 8)], indent=2),
            ],
        ),
    ]

    open_l = [
        E("open-title", 1, 18, 1, 3),
        E("open-live", 18, 25, 1, 3),
        E("ctrl-segment", 1, 7, 3, 4),
        E("ctrl-dealtype", 7, 14, 3, 4),
        E("ctrl-stage1", 14, 20, 3, 4),
        Cont("okc-u", 1, 6, 4, 8, [L("ok-u", 1, 25, 1, 8)]),
        Cont("okc-t", 6, 11, 4, 8, [L("ok-t", 1, 25, 1, 8)]),
        Cont("okc-w", 11, 16, 4, 8, [L("ok-w", 1, 25, 1, 6), L("ok-w-cap", 1, 25, 6, 8)]),
        Cont("okc-q", 16, 21, 4, 8, [L("ok-q", 1, 25, 1, 6), L("ok-q-cap", 1, 25, 6, 8)]),
        Cont("okc-avg", 21, 25, 4, 8, [L("ok-avg", 1, 25, 1, 8)]),
        Cont(
            "okc-chg",
            1,
            25,
            8,
            22,
            [
                L("open-chg", 1, 25, 1, 2),
                L("ok-q4tot", 1, 8, 2, 5),
                L("ok-q4link", 1, 8, 5, 6),
                L("chart-funnel", 1, 15, 6, 12),
                L("funnel-plugin", 1, 15, 12, 13),
                L("mv-left", 15, 25, 2, 3),
                Cont("mv-push-c", 15, 20, 3, 6, [L("mv-push", 1, 25, 1, 8)], indent=2),
                Cont("mv-lost-c", 20, 25, 3, 6, [L("mv-lost", 1, 25, 1, 8)], indent=2),
                L("mv-also", 15, 25, 6, 7),
                Cont("mv-pullb-c", 15, 20, 7, 10, [L("mv-pullb", 1, 25, 1, 8)], indent=2),
                Cont("mv-won-c", 20, 25, 7, 10, [L("mv-won", 1, 25, 1, 8)], indent=2),
                L("mv-add", 15, 25, 10, 11),
                Cont("mv-pulli-c", 15, 20, 11, 14, [L("mv-pulli", 1, 25, 1, 8)], indent=2),
                Cont("mv-size-c", 20, 25, 11, 14, [L("mv-size", 1, 25, 1, 8)], indent=2),
            ],
        ),
        E("chart-seg-month", 1, 13, 22, 32),
        E("chart-prod", 13, 25, 22, 32),
    ]

    total_l = [
        E("total-title", 1, 25, 1, 3),
        Cont("tc-1", 1, 9, 3, 7, [L("tk-cq", 1, 25, 1, 5), L("tk-cq-cap", 1, 25, 5, 7)]),
        Cont("tc-2", 9, 17, 3, 7, [L("tk-nq", 1, 25, 1, 5), L("tk-nq-cap", 1, 25, 5, 7)]),
        Cont("tc-3", 17, 25, 3, 7, [L("tk-2q", 1, 25, 1, 5), L("tk-2q-cap", 1, 25, 5, 7)]),
        E("chart-seg", 1, 25, 7, 16),
        E("total-defs", 1, 25, 16, 17),
        E("tbl-attain", 1, 25, 17, 26),
    ]

    sourcing_l = [
        E("sourcing-title", 1, 18, 1, 3),
        E("ctrl-period", 18, 25, 1, 3),
        Cont(
            "sc-row",
            1,
            25,
            3,
            9,
            [
                L("sk-m", 1, 7, 1, 5),
                L("sk-m-cap", 1, 7, 5, 7),
                L("sk-s", 7, 13, 1, 5),
                L("sk-s-cap", 7, 13, 5, 7),
                L("sk-t", 13, 19, 1, 5),
                L("sk-mix", 19, 25, 1, 7),
            ],
        ),
        E("chart-src", 1, 12, 9, 20),
        E("tbl-src-prod", 12, 25, 9, 20),
    ]

    movement_l = [
        E("movement-title", 1, 25, 1, 3),
        Cont("mc-1", 1, 9, 3, 7, [L("mk-open", 1, 25, 1, 8)]),
        Cont("mc-2", 9, 17, 3, 7, [L("mk-delta", 1, 25, 1, 8)]),
        Cont("mc-3", 17, 25, 3, 7, [L("mk-yoy", 1, 25, 1, 8)]),
        Cont("mc-4", 1, 9, 7, 11, [L("mk-opps", 1, 25, 1, 8)]),
        Cont("mc-5", 9, 17, 7, 11, [L("mk-avg", 1, 25, 1, 8)]),
        Cont("mc-6", 17, 25, 7, 11, [L("mk-split", 1, 25, 1, 8)]),
        E("chart-move", 1, 25, 11, 22),
        E("move-note", 1, 25, 22, 23),
    ]

    created_l = [
        E("created-title", 1, 25, 1, 3),
        E("created-eq", 1, 25, 3, 4),
        Cont("cc-start", 1, 4, 4, 8, [L("ck-start", 1, 25, 1, 8)]),
        E("ck-plus", 4, 5, 4, 8),
        Cont("cc-cr", 5, 8, 4, 8, [L("ck-cr", 1, 25, 1, 8)]),
        E("ck-m1", 8, 9, 4, 8),
        Cont("cc-wn", 9, 12, 4, 8, [L("ck-wn", 1, 25, 1, 8)]),
        E("ck-m2", 12, 13, 4, 8),
        Cont("cc-ls", 13, 16, 4, 8, [L("ck-ls", 1, 25, 1, 8)]),
        E("ck-m3", 16, 17, 4, 8),
        Cont("cc-pb", 17, 19, 4, 8, [L("ck-pb", 1, 25, 1, 8)]),
        E("ck-m4", 19, 20, 4, 8),
        Cont("cc-ot", 20, 22, 4, 8, [L("ck-ot", 1, 25, 1, 8)]),
        E("ck-eq", 22, 23, 4, 8),
        Cont("cc-tot", 23, 25, 4, 8, [L("ck-tot", 1, 25, 1, 8)]),
        Cont("cc-cy", 1, 9, 8, 12, [L("ck-cy", 1, 25, 1, 8)]),
        Cont("cc-ny", 9, 17, 8, 12, [L("ck-ny", 1, 25, 1, 8)]),
        Cont("cc-fy", 17, 25, 8, 12, [L("ck-fy", 1, 25, 1, 8)]),
        E("chart-created", 1, 25, 12, 22),
    ]

    # Place source tables on hidden Data page for lineage visibility
    data_l = [E("data-note", 1, 25, 1, 10)]
    row = 10
    for wid in [
        "wb-open",
        "wb-created",
        "wb-walkin",
        "wb-closed",
        "wb-sourcing",
        "wb-funnel",
        "wb-open-month",
        "wb-open-prod",
        "wb-created-month",
        "wb-snap",
        "wb-pace",
        "wb-seg",
        "wb-goals",
        "wb-seg-tgt",
    ]:
        data_l.append(E(wid, 1, 25, row, row + 4))
        row += 4

    layout = "\n".join(
        [
            '<?xml version="1.0" encoding="utf-8"?>',
            page("page-rotb", rotb_l),
            page("page-total", total_l),
            page("page-sourcing", sourcing_l),
            page("page-open", open_l),
            page("page-movement", movement_l),
            page("page-created", created_l),
            page("page-data", data_l),
        ]
    )

    seen = {e["id"]: e for e in els}
    elements = list(seen.values())
    placed = set(re.findall(r'elementId="([^"]+)"', layout))
    ids = {e["id"] for e in elements}
    missing = placed - ids
    unplaced = ids - placed
    if missing:
        raise SystemExit(f"missing elements: {sorted(missing)}")
    if unplaced:
        raise SystemExit(f"unplaced: {sorted(unplaced)}")

    return {
        "name": "Pipeline Tracker FY2026",
        "folderId": FOLDER,
        "description": "Layered DM KPIs + still chrome. Plugins on GitHub Pages.",
        "document": {
            "schemaVersion": 1,
            "kind": "workbook",
            "settings": {
                "theme": {
                    "name": "Light",
                    "overrides": {
                        "hasCards": "shown",
                        "borderRadius": "round",
                        "space": {"unit": "medium"},
                        "colors": {
                            "highlight": TEAL,
                            "success": GREEN,
                            "warning": ORANGE,
                            "danger": RED,
                            "surface": CANVAS,
                        },
                    },
                },
                "navigation": {"primary": "sidebar", "pageSidebar": "enabled"},
            },
            "pages": [
                {"id": "page-rotb", "name": "ROTB Summary", "backgroundColor": CANVAS},
                {"id": "page-total", "name": "Total Company", "backgroundColor": CANVAS},
                {"id": "page-sourcing", "name": "Pipeline Sourcing", "backgroundColor": CANVAS},
                {"id": "page-open", "name": "Open Pipeline", "backgroundColor": CANVAS},
                {"id": "page-movement", "name": "Pipeline Movement", "backgroundColor": CANVAS},
                {"id": "page-created", "name": "Pipeline Created", "backgroundColor": CANVAS},
                {"id": "page-data", "name": "Data", "visibility": "hidden"},
            ],
            "elements": elements,
            "layout": layout,
        },
    }


def main():
    spec = build()
    out = "/tmp/zywave-pt-wb.json"
    with open(out, "w") as f:
        json.dump(spec, f)
    tables = [e for e in spec["document"]["elements"] if e.get("kind") == "table"]
    sql = [e for e in tables if e.get("source", {}).get("kind") == "sql"]
    dm = [e for e in tables if e.get("source", {}).get("kind") == "data-model"]
    print(
        f"wrote {out} elements={len(spec['document']['elements'])} "
        f"dm_tables={len(dm)} sql={len(sql)}"
    )
    if sql:
        raise SystemExit("workbook must not contain SQL sources")
    try:
        print("PUT", api("PUT", f"/v2/workbooks/{WB}/spec", spec))
        return
    except RuntimeError as e:
        print("ERR1", str(e)[:4000])
    for el in spec["document"]["elements"]:
        if el.get("kind") == "text":
            el["body"] = re.sub(r"<p>(?!</p>)", '<p class="p-small">', el["body"])
        if el.get("kind") in ("bar-chart", "line-chart"):
            el.pop("legend", None)
            el.pop("dataLabel", None)
            if isinstance(el.get("name"), dict):
                el["name"] = el["name"].get("text") or el["id"]
            # stacking normalized may fail — fall back
            if el.get("stacking") == "normalized":
                el["stacking"] = "stacked"
    for attempt in range(12):
        try:
            print("PUT", api("PUT", f"/v2/workbooks/{WB}/spec", spec))
            with open(out, "w") as f:
                json.dump(spec, f)
            return
        except RuntimeError as err:
            msg = str(err)
            print(f"ERR{attempt+2}", msg[:2500])
            idxs = [int(x) for x in re.findall(r"elements\[(\d+)\]", msg)]
            for idx in idxs:
                el = spec["document"]["elements"][idx]
                print("fix", el.get("id"), el.get("kind"))
                if el.get("kind") == "text":
                    el["body"] = re.sub(
                        r"<p(?![^>]*class)(?![^>]*style)>",
                        '<p class="p-small">',
                        el["body"],
                    )
                for k in ("legend", "dataLabel", "refMarks", "palette"):
                    if k == "palette" and isinstance(el.get("color"), dict):
                        el["color"].pop("palette", None)
                    else:
                        el.pop(k, None)
                if "stacking" in msg.lower() or "normalized" in msg.lower():
                    if el.get("stacking") == "normalized":
                        el["stacking"] = "stacked"
                if "Invalid kind" in msg or "color" in msg.lower():
                    if el.get("kind") == "bar-chart":
                        el["color"] = {"by": "single", "value": ORANGE}
            with open(out, "w") as f:
                json.dump(spec, f)
    raise SystemExit("PUT failed")


if __name__ == "__main__":
    main()
