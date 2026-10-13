#!/usr/bin/env python3
"""Workbook that does NOT Sum() custom-SQL packs into every KPI.

Sigma inlines custom SQL into each Sum() viz → 30× 2-minute queries.
Fix: one hidden table per SQL grain; TEXT heroes use {{[Table/Col]}} (no Sum).
kpi-chart only where source is already tiny AND used once.
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
PLUGIN_IDS = os.path.join(os.path.dirname(__file__), "..", "plugins", "plugin-ids.json")


def load_plugin_ids():
    path = os.path.abspath(PLUGIN_IDS)
    if not os.path.exists(path):
        raise SystemExit(f"Missing {path} — run scripts/register_plugins.py first")
    return json.load(open(path))

TEAL, BLUE, ORANGE, RED, GREEN = "#0d9488", "#2563eb", "#f97316", "#dc2626", "#16a34a"
MUTED, INK, WHITE = "#64748b", "#0f172a", "#ffffff"
SECTION, BORDER = "#f1f5f9", "#e2e8f0"
AMBER_BG, TEAL_BG, RED_BG, GREEN_BG = "#fffbeb", "#ecfdf5", "#fef2f2", "#f0fdf4"
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
            return json.loads(raw) if raw else {}
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
    for i, (cname, fmt) in enumerate(cols):
        c = {"id": f"{wid}-{i}", "name": cname, "formula": f"[{dname}/{cname}]"}
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
    els += [
        pass_tbl("wb-pack", "WB Pack", "kpi-pack", "KPI Pack", pack_cols),
        pass_tbl("wb-walkin", "WB Walkin", "kpi-walkin", "KPI Walkin",
                 [("WALKIN_OPPS", None), ("WALKIN_ACV", m())]),
        # Closed Q4 only (date-selective) — safe for ROTB.
        pass_tbl("wb-closed", "WB Closed", "kpi-closed", "KPI Closed Q4", [
            ("WON_ACV", m()), ("WON_OPPS", None), ("LOST_ACV", m()), ("LOST_OPPS", None),
        ]),
        # Early stages (ACV) — never waits on VW.
        pass_tbl("wb-open", "WB Open", "kpi-open", "KPI Open", [
            ("S0_OPPS", None), ("S0_ACV", m()), ("S1_OPPS", None), ("S1_ACV", m()),
            ("S2_OPPS", None), ("S2_ACV", m()),
        ]),
        # Open-VW sourcing — Sourcing + Total pages only (NOT on ROTB).
        pass_tbl("wb-src", "WB Sourcing", "kpi-src", "KPI Sourcing", [
            ("MKT_ACV", m()), ("SALES_ACV", m()), ("SRC_TOTAL_ACV", m()),
            ("MKT_MIX", p()), ("SALES_MIX", p()),
            ("SEG_CORE", m()), ("SEG_MID", m()), ("SEG_ENT", m()),
            ("SEG_UNMAPPED", m()), ("OPEN_ALL_ACV", m()),
        ]),
        pass_tbl("wb-funnel", "WB Funnel", "chart-funnel", "Chart Funnel",
                 [("STAGE", None), ("ORD", None), ("ACV", m())]),
        # ACV-only TV grain (fast). SEG Actual from wb-src in the plugin.
        pass_tbl("wb-tv", "WB TV", "chart-tv", "Chart Target Actual Source",
                 [("GRAIN", None), ("DIM", None), ("SERIES", None), ("VAL", m()), ("OPPS", None)]),
    ]

    # Column ids on wb-pack (must match pack_cols order above)
    PACK_YTD, PACK_Q4C = "wb-pack-12", "wb-pack-13"
    PACK_YG, PACK_Q4G = "wb-pack-21", "wb-pack-22"
    PACK_YEL, PACK_Q4EL = "wb-pack-23", "wb-pack-24"

    plug = load_plugin_ids()
    PACE_ID, FUNNEL_ID, TV_ID = plug["pace"], plug["funnel"], plug["tv"]
    P, W = "WB Pack", "WB Walkin"
    Z, O, S = "WB Closed", "WB Open", "WB Sourcing"

    def ref(table, col, fmt):
        return "{{" + f"[{table}/{col}] | {fmt}" + "}}"

    def pace_plugin(eid, title, actual_col, goal_col, paced_col):
        # Bind directly to wb-pack so pack SQL runs once (no child table re-inline).
        return {
            "id": eid, "kind": "plugin", "pluginId": PACE_ID, "displayName": title,
            "config": {
                "source": {"kind": "element", "elementId": "wb-pack"},
                "actual": {"kind": "column", "columnId": actual_col, "source": "source"},
                "goal": {"kind": "column", "columnId": goal_col, "source": "source"},
                "pacedPct": {"kind": "column", "columnId": paced_col, "source": "source"},
                "title": title,
                "valueFormat": "$,.2s",
                "fillColor": ORANGE,
                "tickColor": "#334155",
            },
            "style": {"backgroundColor": WHITE},
        }

    def funnel_plugin(eid, src_eid="wb-funnel"):
        return {
            "id": eid, "kind": "plugin", "pluginId": FUNNEL_ID, "displayName": "Stage funnel",
            "config": {
                "source": {"kind": "element", "elementId": src_eid},
                "stage": {"kind": "column", "columnId": f"{src_eid}-0", "source": "source"},
                "acv": {"kind": "column", "columnId": f"{src_eid}-2", "source": "source"},
                "order": {"kind": "column", "columnId": f"{src_eid}-1", "source": "source"},
            },
            "style": {"backgroundColor": WHITE},
        }

    def tv_plugin(eid, src_eid="wb-tv"):
        # ACV-only grain — no open-VW bind on Total (SEG Actual omitted for speed).
        return {
            "id": eid, "kind": "plugin", "pluginId": TV_ID, "displayName": "Target vs Actual",
            "config": {
                "source": {"kind": "element", "elementId": src_eid},
                "grain": {"kind": "column", "columnId": f"{src_eid}-0", "source": "source"},
                "dim": {"kind": "column", "columnId": f"{src_eid}-1", "source": "source"},
                "series": {"kind": "column", "columnId": f"{src_eid}-2", "source": "source"},
                "val": {"kind": "column", "columnId": f"{src_eid}-3", "source": "source"},
                "opps": {"kind": "column", "columnId": f"{src_eid}-4", "source": "source"},
            },
            "style": {"backgroundColor": WHITE},
        }

    def label(txt, color=MUTED):
        return f'<p class="p-small"><span style="color:{color}">{txt}</span></p>'

    def hero(val_html, color=INK, size=36):
        return f'<p class="p-small"><span style="font-size:{size}px;color:{color}">{val_html}</span></p>'

    # Controls
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
         "name": "Include Stage 1 (Unique Meeting Run)", "controlType": "checkbox",
         "mode": "True/False", "value": False},
        {"kind": "control", "id": "ctrl-period", "controlId": "SourcingPeriod", "name": "Period",
         "controlType": "list", "mode": "include", "selectionMode": "single",
         "source": {"kind": "manual", "valueType": "text", "values": ["Q4", "YTD"],
                    "labels": ["Current Quarter (Q4)", "Year-to-Date"]}, "value": "Q4"},
    ]

    # ═══════════════ ROTB (still chrome: section shells + pace strips) ═══════════════
    els += [
        T("rotb-title", f'# ROTB Summary\n<p class="p-small"><span style="color:{MUTED}">One-page view of creation, coverage, movement, and demand. Q4 · FY2026</span></p>'),
        T("rotb-badge", f'<p style="text-align:right"><span style="color:{MUTED}">Read-only snapshot · October · Snowflake SoT</span></p>'),
        C("sec-01", SECTION, SECTION), C("sec-02", SECTION, SECTION), C("sec-03", SECTION, SECTION),
        C("sec-04", SECTION, SECTION),
        C("card-year"), C("card-q4"), C("card-week"), C("card-ccq", AMBER_BG, "#fbbf24"), C("card-cwq", TEAL_BG, "#5eead4"),
        T("rotb-s01", f'## <span style="color:{TEAL}">01 / PIPELINE CREATION</span>\nCreation pace'),
        pace_plugin("plugin-pace-year", "Year Pipeline Created", PACK_YTD, PACK_YG, PACK_YEL),
        pace_plugin("plugin-pace-q4", "Q4 Pipeline Created", PACK_Q4C, PACK_Q4G, PACK_Q4EL),
        T("rk-week",
          label("CREATED THIS WEEK") + "\n" +
          hero(ref(P, "WEEK_ACV", "$,.2s"), INK, 32) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"WEEK_OPPS",",.0f")} opportunities</span></p>'),
        T("rk-ccq",
          label("CREATED & CLOSING THIS QUARTER") + "\n" +
          hero(ref(P, "CREATED_CLOSING_ACV", "$,.2s"), ORANGE, 32) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"CREATED_CLOSING_OPPS",",.0f")} opportunities</span></p>'),
        T("rk-cwq",
          label("AVG DEAL SIZE") + "\n" +
          hero(ref(P, "AVG_DEAL", "$,.2s"), GREEN, 32) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Open Stage 2+ · pack grain</span></p>'),
        T("rotb-s02", f'## <span style="color:{TEAL}">02 / COVERAGE</span>\nOpen pipeline'),
        C("cov-1", TEAL_BG, "#99f6e4"), C("cov-2"), C("cov-3"), C("cov-4"),
        T("rk-open", label("TOTAL OPEN PIPELINE") + "\n" + hero(ref(P, "TOTAL_ACV", "$,.2s"), TEAL, 32)),
        T("rk-cq", label("CLOSING THIS QUARTER") + "\n" + hero(ref(P, "Q4_ACV", "$,.2s"), BLUE, 32)),
        T("rk-nq", label("CLOSING NEXT QUARTER") + "\n" + hero(ref(P, "NQ_ACV", "$,.2s"), BLUE, 32)),
        T("rk-2q", label("CLOSING TWO QUARTERS OUT") + "\n" + hero(ref(P, "Q2OUT_ACV", "$,.2s"), BLUE, 32)),
        T("rotb-s03", f'## <span style="color:{MUTED}">03 / PIPELINE MANAGEMENT</span>\nQ4 walk-in (closed won/lost on Movement)'),
        C("mgmt-w"),
        T("rk-walk",
          label("WALK-IN (Q4 START)") + "\n" +
          hero(ref(W, "WALKIN_ACV", "$,.2s"), BLUE, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Frozen · {ref(W,"WALKIN_OPPS",",.0f")} opps · closed detail on Movement</span></p>'),
        T("rotb-s04", f'## <span style="color:{BLUE}">04 / EARLY STAGE PIPELINE</span>\nOpen Stage 0–2 · Snowflake SoT'),
        C("dm-s0"), C("dm-s1"), C("dm-s2", TEAL_BG, "#5eead4"), C("dm-mo"),
        T("dm-s0-b",
          label("STAGE 0 OPEN") + "\n" +
          hero(ref(O, "S0_ACV", "$,.2s"), BLUE, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(O,"S0_OPPS",",.0f")} opportunities</span></p>'),
        T("dm-s1-b",
          label("STAGE 1 OPEN") + "\n" +
          hero(ref(O, "S1_ACV", "$,.2s"), BLUE, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(O,"S1_OPPS",",.0f")} opportunities</span></p>'),
        T("dm-s2-b",
          label("STAGE 2 OPEN") + "\n" +
          hero(ref(O, "S2_ACV", "$,.2s"), TEAL, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(O,"S2_OPPS",",.0f")} opportunities</span></p>'),
        T("dm-mo-b",
          label("STAGE 2 CREATED THIS MONTH") + "\n" +
          hero(ref(P, "MONTH_ACV", "$,.2s"), ORANGE, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"MONTH_OPPS",",.0f")} opportunities</span></p>'),
        # Sourcing intentionally omitted from ROTB (open-VW is slow) — see Pipeline Sourcing tab.
        T("rotb-progress",
          f'<p class="p-small"><span style="color:{MUTED}">Year progress {ref(P,"YEAR_ELAPSED",".0%")} · '
          f'Quarter progress {ref(P,"Q4_ELAPSED",".0%")}</span></p>'),
    ]

    # ═══════════════ OPEN (best sheet — keep density) ═══════════════
    for cid in ["okc-u", "okc-t", "okc-q", "okc-avg", "okc-chg"]:
        els.append(C(cid))
    els.append(C("okc-w", "#eff6ff", "#93c5fd"))  # walk-in blue chrome (still)
    els += [
        T("open-title", f'# Open Pipeline\n<p class="p-small"><span style="color:{MUTED}">FY2026 Stage 2+ Pipeline by Close Date</span></p>'),
        T("open-live", f'<p class="p-small" style="text-align:right"><span style="color:{GREEN}">Live from Snowflake</span></p>'),
        T("ok-u", label("UNIQUE OPPORTUNITIES") + "\n" + hero(ref(P, "TOTAL_OPPS", ",.0f"), INK, 28)),
        T("ok-t", label("TOTAL PIPELINE ACV") + "\n" + hero(ref(P, "TOTAL_ACV", "$,.2s"), INK, 28)),
        T("ok-w",
          label("WALK-IN PIPELINE") + "\n" +
          hero(ref(W, "WALKIN_ACV", "$,.2s"), BLUE, 28) + "\n" +
          f'<p class="p-small"><span style="color:{BLUE}">Q4 start (frozen)</span></p>'),
        T("ok-q",
          label("Q4 PIPELINE ACV") + "\n" +
          hero(ref(P, "Q4_ACV", "$,.2s"), INK, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"Q4_OPPS",",.0f")} opps</span></p>'),
        T("ok-avg", label("AVG DEAL SIZE") + "\n" + hero(ref(P, "AVG_DEAL", "$,.2s"), INK, 28)),
        T("open-chg", f'## Q4 Pipeline Changes\n<span style="color:{MUTED}">Current quarter pipeline movement</span>'),
        T("ok-q4tot",
          label("CURRENT OPEN PIPELINE") + "\n" +
          hero(ref(P, "Q4_ACV", "$,.2s"), INK, 32) + "\n" +
          f'<p class="p-small"><span style="color:{BLUE}">Close Date: Current Quarter</span></p>'),
        funnel_plugin("plugin-funnel"),
        # Closed won/lost intentionally omitted here (VW) — see Movement tab.
        T("mv-left", f'<p class="p-small"><span style="color:{MUTED}">BASELINE · EARLY · ADDED (closed won/lost on Movement)</span></p>'),
        C("mv-walk-c", "#eff6ff", "#93c5fd"), C("mv-early-c", RED_BG, "#fecaca"),
        T("mv-walk",
          f'<p class="p-small"><span style="color:{BLUE}">Walk-in (Q4 start)</span></p>\n'
          + hero(ref(W, "WALKIN_ACV", "$,.2s"), BLUE, 26) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Frozen · {ref(W,"WALKIN_OPPS",",.0f")} opps</span></p>'),
        T("mv-early",
          f'<p class="p-small"><span style="color:{RED}">Early stage open (S0)</span></p>\n'
          + hero(ref(O, "S0_ACV", "$,.2s"), RED, 22) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">S0 {ref(O,"S0_OPPS",",.0f")} · S1 {ref(O,"S1_OPPS",",.0f")} opps</span></p>'),
        T("mv-add", f'<p class="p-small"><span style="color:{MUTED}">WHAT ADDED</span></p>'),
        C("mv-cr-c", GREEN_BG, "#bbf7d0"), C("mv-ccq-c", AMBER_BG, "#fbbf24"),
        T("mv-cr",
          f'<p class="p-small"><span style="color:{GREEN}">Created This Quarter</span></p>\n'
          + hero(ref(P, "Q4_CREATED_ACV", "$,.2s"), GREEN, 26) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"Q4_CREATED_OPPS",",.0f")} opps</span></p>'),
        T("mv-ccq",
          f'<p class="p-small"><span style="color:{ORANGE}">Created &amp; Closing This Q</span></p>\n'
          + hero(ref(P, "CREATED_CLOSING_ACV", "$,.2s"), ORANGE, 26) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"CREATED_CLOSING_OPPS",",.0f")} opps</span></p>'),
    ]

    # ═══════════════ TOTAL ═══════════════
    els += [
        T("total-title", f'# Total Company\n<p class="p-small"><span style="color:{MUTED}">ACV-fast · product actuals + segment 2H targets (segment actuals on Sourcing)</span></p>'),
        C("tc-1"), C("tc-2"), C("tc-3"),
        T("tk-cq",
          label("PIPELINE TO CLOSE IN CURRENT QUARTER") + "\n" +
          hero(ref(P, "Q4_ACV", "$,.2s")) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Q4 2026 · {ref(P,"Q4_OPPS",",.0f")} open deals</span></p>'),
        T("tk-nq",
          label("PIPELINE TO CLOSE IN NEXT QUARTER") + "\n" +
          hero(ref(P, "NQ_ACV", "$,.2s")) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Q1 2027 · {ref(P,"NQ_OPPS",",.0f")} open deals</span></p>'),
        T("tk-2q",
          label("PIPELINE TO CLOSE 2 QUARTERS OUT") + "\n" +
          hero(ref(P, "Q2OUT_ACV", "$,.2s")) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Q2 2027 · {ref(P,"Q2OUT_OPPS",",.0f")} open deals</span></p>'),
        tv_plugin("plugin-tv"),
        T("total-defs",
          f'<p class="p-small"><span style="color:{MUTED}">Product actuals = ACV metrics (fast) · '
          f'Segment bars = 2H targets (open-VW segment actuals on Pipeline Sourcing) · '
          f'Up-Market = Mid-Market + Enterprise · II = Analytics + Client + Content · RQC &amp; AMS = RQC + Service</span></p>'),
    ]

    # ═══════════════ SOURCING ═══════════════
    els += [
        T("sourcing-title", f'# Pipeline Sourcing\n<p class="p-small"><span style="color:{MUTED}">Marketing vs Sales · Stage 2+</span></p>'),
        C("sc-row", SECTION, SECTION),
        C("sc-m-card"), C("sc-s-card"), C("sc-t-card"), C("sc-mix-card", AMBER_BG, "#fbbf24"),
        T("sk-m",
          label("MARKETING-SOURCED") + "\n" +
          hero(ref(S, "MKT_ACV", "$,.2s"), BLUE, 32) + "\n" +
          f'<p class="p-small"><span style="color:{BLUE}">Actual mix {ref(S,"MKT_MIX",".0%")}</span></p>\n'
          f'<p class="p-small"><span style="color:{MUTED}">target mix 39%</span></p>'),
        T("sk-s",
          label("SALES-SOURCED") + "\n" +
          hero(ref(S, "SALES_ACV", "$,.2s"), ORANGE, 32) + "\n" +
          f'<p class="p-small"><span style="color:{ORANGE}">Actual mix {ref(S,"SALES_MIX",".0%")}</span></p>\n'
          f'<p class="p-small"><span style="color:{MUTED}">target mix 61%</span></p>'),
        T("sk-t",
          label("TOTAL STAGE 2+") + "\n" +
          hero(ref(S, "SRC_TOTAL_ACV", "$,.2s"), INK, 32) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Marketing + Sales open ACV</span></p>'),
        T("sk-mix",
          label("MIX · ACTUAL vs TARGET") + "\n" +
          f'<p class="p-small" style="text-align:center"><span style="font-size:22px;color:{INK}">'
          f'M {ref(S,"MKT_MIX",".0%")} / S {ref(S,"SALES_MIX",".0%")}</span></p>\n'
          f'<p class="p-small" style="text-align:center"><span style="color:{MUTED}">target M 39% / S 61%</span></p>'),
        C("sc-seg-row", SECTION, SECTION),
        C("sc-core"), C("sc-mid"), C("sc-ent"), C("sc-unmap", "#f8fafc", BORDER),
        T("sk-core",
          label("CORE · TAGGED") + "\n" +
          hero(ref(S, "SEG_CORE", "$,.2s"), BLUE, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">2H target $18M · pipe-token in SplitSegment</span></p>'),
        T("sk-mid",
          label("MID-MARKET · TAGGED") + "\n" +
          hero(ref(S, "SEG_MID", "$,.2s"), TEAL, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">2H target $16M</span></p>'),
        T("sk-ent",
          label("ENTERPRISE / UP-MARKET · TAGGED") + "\n" +
          hero(ref(S, "SEG_ENT", "$,.2s"), ORANGE, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">2H target $20M</span></p>'),
        T("sk-unmap",
          label("UNTAGGED OPEN ACV") + "\n" +
          hero(ref(S, "SEG_UNMAPPED", "$,.2s"), MUTED, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">No Core/Mid/Enterprise token in Segment</span></p>'),
        T("sk-note",
          f'<p class="p-small"><span style="color:{MUTED}">Open-VW 1-row · Lead Source + SplitSegment tokens · '
          f'close Q4–Q2-out · VW {ref(S,"OPEN_ALL_ACV","$,.2s")} (pack {ref(P,"TOTAL_ACV","$,.2s")}) · '
          f'only slow page · Q4 FY2026</span></p>'),
    ]

    # ═══════════════ MOVEMENT ═══════════════
    els += [
        T("movement-title", f'# Pipeline Movement\n<p class="p-small"><span style="color:{MUTED}">Q4 closed from ACV metrics · 14-day snapshot trend</span></p>'),
        C("mc-1"), C("mc-2"), C("mc-3"), C("mc-4", GREEN_BG, "#bbf7d0"), C("mc-5", RED_BG, "#fecaca"), C("mc-6", AMBER_BG, "#fbbf24"),
        T("mk-open", label("TOTAL OPEN PIPELINE") + "\n" + hero(ref(P, "TOTAL_ACV", "$,.0f"), INK, 32)),
        T("mk-q4",
          label("Q4 OPEN ACV") + "\n" +
          hero(ref(P, "Q4_ACV", "$,.0f"), BLUE, 32) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"Q4_OPPS",",.0f")} opps</span></p>'),
        T("mk-walk", label("WALK-IN (Q4 START)") + "\n" + hero(ref(W, "WALKIN_ACV", "$,.0f"), TEAL, 32)),
        T("mk-won",
          label("CLOSED WON (Q4)") + "\n" +
          hero(ref(Z, "WON_ACV", "$,.0f"), GREEN, 32) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(Z,"WON_OPPS",",.0f")} opps</span></p>'),
        T("mk-lost",
          label("CLOSED LOST (Q4)") + "\n" +
          hero(ref(Z, "LOST_ACV", "$,.0f"), RED, 32) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(Z,"LOST_OPPS",",.0f")} opps · ≤ $50k</span></p>'),
        T("mk-created", label("CREATED Q4") + "\n" + hero(ref(P, "Q4_CREATED_ACV", "$,.0f"), ORANGE, 32)),
        T("mv-trend-h", f'## Daily open pipeline\n<span style="color:{MUTED}">Last 14 days · Stage 2+ forecasted net ACV</span>'),
        {
            "id": "chart-snap", "kind": "line-chart", "name": "Open Pipeline Snapshot Trend",
            "source": dm("chart-snap"),
            "columns": [
                {"id": "sn-d", "name": "Date", "formula": "[Chart Snapshot Trend/DT]",
                 "format": {"kind": "datetime", "formatString": "%b %d"}},
                {"id": "sn-v", "name": "ACV", "formula": "[Chart Snapshot Trend/ACV]",
                 "format": {"kind": "number", "formatString": "$,.2s"}},
            ],
            "xAxis": {"columnId": "sn-d"}, "yAxis": {"columnIds": ["sn-v"]},
            "color": {"by": "single", "value": BLUE},
            "style": {"backgroundColor": WHITE, "borderRadius": "round", "borderColor": BORDER, "borderWidth": 1},
        },
    ]

    # ═══════════════ CREATED ═══════════════
    els += [
        T("created-title", f'# Pipeline Created\n<p class="p-small"><span style="color:{MUTED}">YoY pipeline creation trends · Stage 2+</span></p>'),
        C("ckp-1"), C("ckp-2"), C("ckp-3", TEAL_BG, "#5eead4"), C("ckp-4", GREEN_BG, "#bbf7d0"), C("ckp-5", AMBER_BG, "#fbbf24"),
        T("ckp-week",
          label("CREATED THIS WEEK") + "\n" +
          hero(ref(P, "WEEK_ACV", "$,.2s"), BLUE, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"WEEK_OPPS",",.0f")} opps</span></p>'),
        T("ckp-qtr",
          label("CREATED THIS QUARTER") + "\n" +
          hero(ref(P, "Q4_CREATED_ACV", "$,.2s"), BLUE, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"Q4_CREATED_OPPS",",.0f")} opps</span></p>'),
        T("ckp-month",
          label("CREATED THIS MONTH") + "\n" +
          hero(ref(P, "MONTH_ACV", "$,.2s"), TEAL, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"MONTH_OPPS",",.0f")} opps</span></p>'),
        T("ckp-ccq",
          label("CREATED & CLOSING THIS Q") + "\n" +
          hero(ref(P, "CREATED_CLOSING_ACV", "$,.2s"), ORANGE, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"CREATED_CLOSING_OPPS",",.0f")} opps</span></p>'),
        T("ckp-won",
          label("CLOSING THIS YEAR") + "\n" +
          hero(ref(P, "CLOSE_CY_ACV", "$,.2s"), GREEN, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"CLOSE_CY_PCT",".0%")} of open · pack grain</span></p>'),
        T("bridge-h", f'## Pipeline Bridge — Q4 FY2026\n<span style="color:{MUTED}">Walk-in + created ≈ open (won/lost detail on Movement · no VW here)</span>'),
        C("cc-start"), C("cc-cr", GREEN_BG, "#bbf7d0"), C("cc-tot", "#eff6ff", "#93c5fd"),
        T("ck-start", label("OPEN (QTR START)") + "\n" + hero(ref(W, "WALKIN_ACV", "$,.0f"), BLUE, 24)),
        T("ck-plus", f'<p class="p-small" style="text-align:center"><span style="font-size:28px;color:{MUTED}">+</span></p>'),
        T("ck-cr", label("CREATED THIS QUARTER") + "\n" + hero(ref(P, "Q4_CREATED_ACV", "$,.0f"), GREEN, 24)),
        T("ck-eq", f'<p class="p-small" style="text-align:center"><span style="font-size:28px;color:{MUTED}">≈</span></p>'),
        T("ck-tot", label("TOTAL OPEN") + "\n" + hero(ref(P, "TOTAL_ACV", "$,.0f"), BLUE, 24)),
        T("close-h", f'## Total open pipeline by close year\n<span style="color:{MUTED}">Share of open ACV</span>'),
        C("cc-cy"), C("cc-ny"), C("cc-fy"),
        T("ck-cy",
          label("CURRENT YEAR (2026)") + "\n" +
          hero(ref(P, "CLOSE_CY_ACV", "$,.0f"), TEAL, 26) + "\n" +
          f'<p class="p-small"><span style="color:{TEAL}">{ref(P,"CLOSE_CY_PCT",".0%")} of open</span></p>'),
        T("ck-ny",
          label("NEXT YEAR (2027)") + "\n" +
          hero(ref(P, "CLOSE_NY_ACV", "$,.0f"), BLUE, 26) + "\n" +
          f'<p class="p-small"><span style="color:{BLUE}">{ref(P,"CLOSE_NY_PCT",".0%")} of open</span></p>'),
        T("ck-fy",
          label("FUTURE YEARS (2028+)") + "\n" +
          hero(ref(P, "CLOSE_FY_ACV", "$,.0f"), MUTED, 26) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"CLOSE_FY_PCT",".0%")} of open</span></p>'),
        # Chart sources DM directly — no pass-through table (avoids CREATED_MO ×2).
        {
            "id": "chart-created", "kind": "bar-chart", "name": "Pipeline Created by Month (Stage 2+)",
            "source": dm("chart-created"),
            "columns": [
                {"id": "ccm-m", "name": "Month", "formula": "[Chart Created/MONTH]",
                 "format": {"kind": "datetime", "formatString": "%b %Y"}},
                {"id": "ccm-v", "name": "ACV", "formula": "[Chart Created/ACV]",
                 "format": {"kind": "number", "formatString": "$,.2s"}},
            ],
            "xAxis": {"columnId": "ccm-m"}, "yAxis": {"columnIds": ["ccm-v"]},
            "color": {"by": "single", "value": TEAL},
            "style": {"backgroundColor": WHITE, "borderRadius": "round", "borderColor": BORDER, "borderWidth": 1},
        },
        T("data-note", """# Fast path

ROTB / Open / Total / Created / Movement KPIs = ACV metrics (+ walk-in snapshot).
Sourcing only = open presentation VW (Lead Source + SplitSegment tokens).
Movement trend = 14-day snapshot VW. TV = ACV product; segment targets on Total.
"""),
    ]

    def L(e, a, b, c, d):
        return E(e, a, b, c, d, 1)

    # Equal 5-wide cards (24/5 ≈ 4.8 → 5+5+5+5+4). Progress sits BELOW sec-01
    # so it never steals auto-row tracks from the plugin cards.
    rotb = [
        E("rotb-title", 1, 18, 1, 3), E("rotb-badge", 18, 25, 1, 3),
        Cont("sec-01", 1, 25, 3, 12, [
            L("rotb-s01", 1, 25, 1, 2),
            Cont("card-year", 1, 6, 2, 8, [L("plugin-pace-year", 1, 25, 1, 8)], 2),
            Cont("card-q4", 6, 11, 2, 8, [L("plugin-pace-q4", 1, 25, 1, 8)], 2),
            Cont("card-week", 11, 16, 2, 8, [L("rk-week", 1, 25, 1, 8)], 2),
            Cont("card-ccq", 16, 21, 2, 8, [L("rk-ccq", 1, 25, 1, 8)], 2),
            Cont("card-cwq", 21, 25, 2, 8, [L("rk-cwq", 1, 25, 1, 8)], 2),
        ]),
        E("rotb-progress", 1, 25, 12, 13),
        Cont("sec-02", 1, 25, 13, 18, [
            L("rotb-s02", 1, 25, 1, 2),
            Cont("cov-1", 1, 7, 2, 6, [L("rk-open", 1, 25, 1, 8)], 2),
            Cont("cov-2", 7, 13, 2, 6, [L("rk-cq", 1, 25, 1, 8)], 2),
            Cont("cov-3", 13, 19, 2, 6, [L("rk-nq", 1, 25, 1, 8)], 2),
            Cont("cov-4", 19, 25, 2, 6, [L("rk-2q", 1, 25, 1, 8)], 2),
        ]),
        Cont("sec-03", 1, 25, 18, 23, [
            L("rotb-s03", 1, 25, 1, 2),
            Cont("mgmt-w", 1, 25, 2, 6, [L("rk-walk", 1, 25, 1, 8)], 2),
        ]),
        Cont("sec-04", 1, 25, 23, 28, [
            L("rotb-s04", 1, 25, 1, 2),
            Cont("dm-s0", 1, 7, 2, 6, [L("dm-s0-b", 1, 25, 1, 8)], 2),
            Cont("dm-s1", 7, 13, 2, 6, [L("dm-s1-b", 1, 25, 1, 8)], 2),
            Cont("dm-s2", 13, 19, 2, 6, [L("dm-s2-b", 1, 25, 1, 8)], 2),
            Cont("dm-mo", 19, 25, 2, 6, [L("dm-mo-b", 1, 25, 1, 8)], 2),
        ]),
    ]
    open_l = [
        E("open-title", 1, 18, 1, 3), E("open-live", 18, 25, 1, 3),
        E("ctrl-stage1", 1, 10, 3, 4), E("ctrl-segment", 10, 17, 3, 4), E("ctrl-dealtype", 17, 25, 3, 4),
        Cont("okc-u", 1, 6, 4, 8, [L("ok-u", 1, 25, 1, 8)]),
        Cont("okc-t", 6, 11, 4, 8, [L("ok-t", 1, 25, 1, 8)]),
        Cont("okc-w", 11, 16, 4, 8, [L("ok-w", 1, 25, 1, 8)]),
        Cont("okc-q", 16, 21, 4, 8, [L("ok-q", 1, 25, 1, 8)]),
        Cont("okc-avg", 21, 25, 4, 8, [L("ok-avg", 1, 25, 1, 8)]),
        Cont("okc-chg", 1, 25, 8, 24, [
            L("open-chg", 1, 25, 1, 2), L("ok-q4tot", 1, 9, 2, 5), L("plugin-funnel", 1, 15, 5, 17),
            L("mv-left", 15, 25, 2, 3),
            Cont("mv-walk-c", 15, 20, 3, 7, [L("mv-walk", 1, 25, 1, 8)], 2),
            Cont("mv-early-c", 20, 25, 3, 7, [L("mv-early", 1, 25, 1, 8)], 2),
            L("mv-add", 15, 25, 7, 8),
            Cont("mv-cr-c", 15, 20, 8, 12, [L("mv-cr", 1, 25, 1, 8)], 2),
            Cont("mv-ccq-c", 20, 25, 8, 12, [L("mv-ccq", 1, 25, 1, 8)], 2),
        ]),
    ]
    total_l = [
        E("total-title", 1, 25, 1, 3),
        Cont("tc-1", 1, 9, 3, 8, [L("tk-cq", 1, 25, 1, 8)]),
        Cont("tc-2", 9, 17, 3, 8, [L("tk-nq", 1, 25, 1, 8)]),
        Cont("tc-3", 17, 25, 3, 8, [L("tk-2q", 1, 25, 1, 8)]),
        E("plugin-tv", 1, 25, 8, 26),
        E("total-defs", 1, 25, 26, 28),
    ]
    sourcing_l = [
        E("sourcing-title", 1, 18, 1, 3), E("ctrl-period", 18, 25, 1, 3),
        Cont("sc-row", 1, 25, 3, 12, [
            Cont("sc-m-card", 1, 7, 1, 10, [L("sk-m", 1, 25, 1, 9)], 2),
            Cont("sc-s-card", 7, 13, 1, 10, [L("sk-s", 1, 25, 1, 9)], 2),
            Cont("sc-t-card", 13, 19, 1, 10, [L("sk-t", 1, 25, 1, 9)], 2),
            Cont("sc-mix-card", 19, 25, 1, 10, [L("sk-mix", 1, 25, 1, 9)], 2),
        ]),
        Cont("sc-seg-row", 1, 25, 12, 20, [
            Cont("sc-core", 1, 7, 1, 10, [L("sk-core", 1, 25, 1, 9)], 2),
            Cont("sc-mid", 7, 13, 1, 10, [L("sk-mid", 1, 25, 1, 9)], 2),
            Cont("sc-ent", 13, 19, 1, 10, [L("sk-ent", 1, 25, 1, 9)], 2),
            Cont("sc-unmap", 19, 25, 1, 10, [L("sk-unmap", 1, 25, 1, 9)], 2),
        ]),
        E("sk-note", 1, 25, 20, 22),
    ]
    movement_l = [
        E("movement-title", 1, 25, 1, 3),
        Cont("mc-1", 1, 9, 3, 8, [L("mk-open", 1, 25, 1, 8)]),
        Cont("mc-2", 9, 17, 3, 8, [L("mk-q4", 1, 25, 1, 8)]),
        Cont("mc-3", 17, 25, 3, 8, [L("mk-walk", 1, 25, 1, 8)]),
        Cont("mc-4", 1, 9, 8, 13, [L("mk-won", 1, 25, 1, 8)]),
        Cont("mc-5", 9, 17, 8, 13, [L("mk-lost", 1, 25, 1, 8)]),
        Cont("mc-6", 17, 25, 8, 13, [L("mk-created", 1, 25, 1, 8)]),
        E("mv-trend-h", 1, 25, 13, 15),
        E("chart-snap", 1, 25, 15, 26),
    ]
    created_l = [
        E("created-title", 1, 25, 1, 3),
        Cont("ckp-1", 1, 6, 3, 8, [L("ckp-week", 1, 25, 1, 8)]),
        Cont("ckp-2", 6, 11, 3, 8, [L("ckp-qtr", 1, 25, 1, 8)]),
        Cont("ckp-3", 11, 16, 3, 8, [L("ckp-month", 1, 25, 1, 8)]),
        Cont("ckp-4", 16, 21, 3, 8, [L("ckp-ccq", 1, 25, 1, 8)]),
        Cont("ckp-5", 21, 25, 3, 8, [L("ckp-won", 1, 25, 1, 8)]),
        E("bridge-h", 1, 25, 8, 10),
        Cont("cc-start", 1, 8, 10, 14, [L("ck-start", 1, 25, 1, 8)]),
        E("ck-plus", 8, 9, 10, 14),
        Cont("cc-cr", 9, 16, 10, 14, [L("ck-cr", 1, 25, 1, 8)]),
        E("ck-eq", 16, 17, 10, 14),
        Cont("cc-tot", 17, 25, 10, 14, [L("ck-tot", 1, 25, 1, 8)]),
        E("close-h", 1, 25, 14, 16),
        Cont("cc-cy", 1, 9, 16, 20, [L("ck-cy", 1, 25, 1, 8)]),
        Cont("cc-ny", 9, 17, 16, 20, [L("ck-ny", 1, 25, 1, 8)]),
        Cont("cc-fy", 17, 25, 16, 20, [L("ck-fy", 1, 25, 1, 8)]),
        E("chart-created", 1, 25, 20, 30),
    ]
    data_l = [E("data-note", 1, 25, 1, 6)]
    row = 6
    for wid in ["wb-pack", "wb-walkin", "wb-closed", "wb-open", "wb-src", "wb-funnel", "wb-tv"]:
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
        "description": "Still chrome · registered pace + funnel plugins · text KPIs (pack once).",
        "document": {
            "schemaVersion": 1, "kind": "workbook",
            "settings": {
                "theme": {
                    "name": "Light",
                    "overrides": {
                        "hasCards": "shown", "borderRadius": "round", "space": {"unit": "medium"},
                        "colors": {"highlight": TEAL, "success": GREEN, "warning": ORANGE, "danger": RED},
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
    # strip accidental dead code from hero()
    out = "/tmp/zywave-pt-once.json"
    json.dump(spec, open(out, "w"))
    n_kpi = sum(1 for e in spec["document"]["elements"] if e.get("kind") == "kpi-chart")
    n_sql_src = sum(1 for e in spec["document"]["elements"]
                    if e.get("kind") == "table" and e.get("source", {}).get("kind") == "sql")
    print(f"els={len(spec['document']['elements'])} kpi-charts={n_kpi} workbook-sql={n_sql_src}")
    assert n_kpi == 0, "kpi-charts would re-inline custom SQL"
    assert n_sql_src == 0
    print("PUT", api("PUT", f"/v2/workbooks/{WB}/spec", spec))


if __name__ == "__main__":
    main()
