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
        ("MONTH_GOAL", m()), ("MONTH_ELAPSED", p()), ("MONTH_PCT_GOAL", p()),
    ]
    els += [
        pass_tbl("wb-pack", "WB Pack", "kpi-pack", "KPI Pack", pack_cols),
        pass_tbl("wb-walkin", "WB Walkin", "kpi-walkin", "KPI Walkin",
                 [("WALKIN_OPPS", None), ("WALKIN_ACV", m())]),
        # Open-VW sourcing — Sourcing only (NOT on ROTB/Open/Total/Created/Movement).
        pass_tbl("wb-src", "WB Sourcing", "kpi-src", "KPI Sourcing", [
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
        ]),
        pass_tbl("wb-funnel", "WB Funnel", "chart-funnel", "Chart Funnel",
                 [("STAGE", None), ("ORD", None), ("ACV", m())]),
        # ACV-only TV grain (fast).
        pass_tbl("wb-tv", "WB TV", "chart-tv", "Chart Target Actual Source",
                 [("GRAIN", None), ("DIM", None), ("SERIES", None), ("VAL", m()), ("OPPS", None)]),
    ]

    # Column ids on wb-pack (must match pack_cols order above)
    PACK_YTD, PACK_Q4C = "wb-pack-17", "wb-pack-18"
    PACK_YG, PACK_Q4G = "wb-pack-38", "wb-pack-39"
    PACK_YEL, PACK_Q4EL = "wb-pack-40", "wb-pack-41"
    # MONTH_ACV=20, MONTH_GOAL / MONTH_ELAPSED appended after OTHER_ADJ cols
    PACK_MO = "wb-pack-20"
    PACK_MOG, PACK_MOEL = "wb-pack-53", "wb-pack-54"

    plug = load_plugin_ids()
    PACE_ID, FUNNEL_ID, TV_ID = plug["pace"], plug["funnel"], plug["tv"]
    P, W = "WB Pack", "WB Walkin"
    S = "WB Sourcing"

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
        # Chrome-only controls (still match). Not wired into SQL grains — keep decorative.
        {"kind": "control", "id": "ctrl-segment", "controlId": "Segment", "name": "All Segments",
         "controlType": "list", "mode": "include", "selectionMode": "single",
         "source": {"kind": "manual", "valueType": "text",
                    "values": ["All", "Core", "Mid-Market", "Enterprise"],
                    "labels": ["All Segments", "Core", "Mid-Market", "Enterprise"]}, "value": "All"},
        {"kind": "control", "id": "ctrl-dealtype", "controlId": "DealType", "name": "All Deal Types",
         "controlType": "list", "mode": "include", "selectionMode": "single",
         "source": {"kind": "manual", "valueType": "text",
                    "values": ["All", "New Logo", "Cross-Sell / Expansion", "Uncategorized"],
                    "labels": ["All Deal Types", "New Logo", "Cross-Sell / Expansion", "Uncategorized"]}, "value": "All"},
        {"kind": "control", "id": "ctrl-stage1", "controlId": "IncludeStage1",
         "name": "Include Stage 1 (Unique Meeting Run)", "controlType": "checkbox",
         "mode": "True/False", "value": False},
        {"kind": "control", "id": "ctrl-period", "controlId": "SourcingPeriod", "name": "Close window",
         "controlType": "list", "mode": "include", "selectionMode": "single",
         "source": {"kind": "manual", "valueType": "text", "values": ["Q4Q2"],
                    "labels": ["Q4–Q2-out (fixed · open-VW)"]}, "value": "Q4Q2"},
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
          label("CREATED & WON THIS QUARTER") + "\n" +
          hero(ref(P, "CREATED_WON_ACV", "$,.2s"), GREEN, 32) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"CREATED_WON_OPPS",",.0f")} opportunities</span></p>'),
        T("rotb-s02", f'## <span style="color:{TEAL}">02 / COVERAGE</span>\nOpen pipeline'),
        C("cov-1", TEAL_BG, "#99f6e4"), C("cov-2"), C("cov-3"), C("cov-4"),
        T("rk-open",
          label("TOTAL OPEN PIPELINE") + "\n" +
          hero(ref(P, "TOTAL_ACV", "$,.2s"), TEAL, 32) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"TOTAL_OPPS",",.0f")} opportunities</span></p>'),
        T("rk-cq",
          label("CLOSING THIS QUARTER") + "\n" +
          hero(ref(P, "Q4_ACV", "$,.2s"), BLUE, 32) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Q4 2026 · {ref(P,"Q4_OPPS",",.0f")} opportunities</span></p>'),
        T("rk-nq",
          label("CLOSING NEXT QUARTER") + "\n" +
          hero(ref(P, "NQ_ACV", "$,.2s"), BLUE, 32) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Q1 2027 · {ref(P,"NQ_OPPS",",.0f")} opportunities</span></p>'),
        T("rk-2q",
          label("CLOSING TWO QUARTERS OUT") + "\n" +
          hero(ref(P, "Q2OUT_ACV", "$,.2s"), BLUE, 32) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Q2 2027 · {ref(P,"Q2OUT_OPPS",",.0f")} opportunities</span></p>'),
        T("rotb-s03", f'## <span style="color:{MUTED}">03 / PIPELINE MANAGEMENT</span>\nQ4 walk-in + closed (ACV pack · same grain as Movement)'),
        C("mgmt-w"), C("mgmt-won", GREEN_BG, "#bbf7d0"), C("mgmt-lost", RED_BG, "#fecaca"),
        T("rk-walk",
          label("WALK-IN (Q4 START)") + "\n" +
          hero(ref(W, "WALKIN_ACV", "$,.2s"), BLUE, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Frozen · {ref(W,"WALKIN_OPPS",",.0f")} opps</span></p>'),
        T("rk-won",
          label("CLOSED WON (Q4)") + "\n" +
          hero(ref(P, "WON_ACV", "$,.2s"), GREEN, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"WON_OPPS",",.0f")} opps · pack</span></p>'),
        T("rk-lost",
          label("CLOSED LOST (Q4)") + "\n" +
          hero(ref(P, "LOST_ACV", "$,.2s"), RED, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"LOST_OPPS",",.0f")} opps · ≤ $50k</span></p>'),
        T("rotb-s04", f'## <span style="color:{BLUE}">04 / EARLY STAGE PIPELINE</span>\nOpen Stage 0–2 · Snowflake SoT'),
        C("dm-s0"), C("dm-s1"), C("dm-s2", TEAL_BG, "#5eead4"), C("dm-mo"),
        T("dm-s0-b",
          label("STAGE 0 OPEN") + "\n" +
          hero(ref(P, "S0_ACV", "$,.2s"), BLUE, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"S0_OPPS",",.0f")} opportunities</span></p>'),
        T("dm-s1-b",
          label("STAGE 1 OPEN") + "\n" +
          hero(ref(P, "S1_ACV", "$,.2s"), BLUE, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"S1_OPPS",",.0f")} opportunities</span></p>'),
        T("dm-s2-b",
          label("STAGE 2 OPEN") + "\n" +
          hero(ref(P, "S2_ACV", "$,.2s"), TEAL, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"S2_OPPS",",.0f")} opportunities</span></p>'),
        T("dm-mo-b",
          label("STAGE 2 CREATED THIS MONTH") + "\n" +
          hero(ref(P, "MONTH_ACV", "$,.2s"), ORANGE, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"MONTH_OPPS",",.0f")} opportunities</span></p>'),
        # 05 Marketing — ACV month pace + early open proxies (no MQL feed / no open-VW)
        C("sec-05", SECTION, SECTION),
        T("rotb-s05", f'## <span style="color:{BLUE}">05 / MARKETING PERFORMANCE</span>\nDemand signals · month creation pace (ACV) · MQL feed pending'),
        C("mkt-pace"), C("mkt-s0"), C("mkt-s1"), C("mkt-s2"),
        pace_plugin("plugin-pace-month", "Stage 2 $ created this month", PACK_MO, PACK_MOG, PACK_MOEL),
        T("rk-mkt-s0",
          label("STAGE 0 (OPEN)") + "\n" +
          hero(ref(P, "S0_ACV", "$,.2s"), BLUE, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"S0_OPPS",",.0f")} · early open proxy</span></p>'),
        T("rk-mkt-s1",
          label("STAGE 1 (OPEN)") + "\n" +
          hero(ref(P, "S1_ACV", "$,.2s"), BLUE, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"S1_OPPS",",.0f")} · early open proxy</span></p>'),
        T("rk-mkt-s2",
          label("STAGE 2 (OPEN)") + "\n" +
          hero(ref(P, "S2_ACV", "$,.2s"), TEAL, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"S2_OPPS",",.0f")} · early open proxy</span></p>'),
        # 06 Sales gen — pointer only; Lead Source lives on Sourcing (open-VW)
        C("sec-06", SECTION, SECTION),
        T("rotb-s06", f'## <span style="color:{ORANGE}">06 / SALES PIPELINE GENERATION</span>\nMarketing vs Sales · live on Pipeline Sourcing'),
        C("sg-note", AMBER_BG, "#fbbf24"),
        T("rk-sg",
          label("MARKETING VS SALES") + "\n" +
          hero("→ Sourcing", ORANGE, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Lead Source needs open-VW · kept off this page for speed · '
          f'Month created {ref(P,"MONTH_ACV","$,.2s")} ({ref(P,"MONTH_OPPS",",.0f")} opps)</span></p>'),
        T("rotb-progress",
          f'<p class="p-small"><span style="color:{MUTED}">Year progress {ref(P,"YEAR_ELAPSED",".0%")} · '
          f'Quarter progress {ref(P,"Q4_ELAPSED",".0%")}</span></p>'),
    ]

    # ═══════════════ OPEN (best sheet — keep density) ═══════════════
    for cid in ["okc-u", "okc-t", "okc-q", "okc-avg", "okc-lines", "okc-chg", "okc-funnel", "okc-mv"]:
        els.append(C(cid))
    els.append(C("okc-w", "#eff6ff", "#93c5fd"))  # walk-in blue chrome (still)
    els += [
        T("open-title", f'# Open Pipeline\n<p class="p-small"><span style="color:{MUTED}">FY2026 Stage 2+ by close date · ACV-fast (filters are chrome-only)</span></p>'),
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
        C("okc-lines"),
        T("ok-lines",
          label("DEAL-PRODUCT LINES") + "\n" +
          hero(ref(P, "DEAL_PRODUCT_LINES", ",.0f"), INK, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">ACV metric rows · Stage 2+</span></p>'),
        C("okc-lg", "#f5f3ff", "#c4b5fd"), C("okc-sm", GREEN_BG, "#bbf7d0"),
        T("ok-lg",
          label("LARGE DEALS (≥ $50k)") + "\n" +
          hero(ref(P, "LARGE_OPPS", ",.0f"), "#7c3aed", 26) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"LARGE_ACV","$,.2s")} ACV</span></p>'),
        T("ok-sm",
          label("SMALL DEALS (< $50k)") + "\n" +
          hero(ref(P, "SMALL_OPPS", ",.0f"), GREEN, 26) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"SMALL_ACV","$,.2s")} ACV</span></p>'),
        T("open-chg", f'## Q4 Pipeline Changes\n<span style="color:{MUTED}">Current quarter pipeline movement</span>'),
        T("ok-q4tot",
          label("CURRENT OPEN PIPELINE") + "\n" +
          hero(ref(P, "Q4_ACV", "$,.2s"), INK, 32) + "\n" +
          f'<p class="p-small"><span style="color:{BLUE}">Close Date: Current Quarter</span></p>'),
        funnel_plugin("plugin-funnel"),
        # Stills: WHAT LEFT / ALSO LEFT / WHAT ADDED — pack only (no open-VW)
        T("mv-left", f'<p class="p-small"><span style="color:{RED}">WHAT LEFT</span></p>'),
        C("mv-push-c", RED_BG, "#fecaca"), C("mv-lost-c", RED_BG, "#fecaca"),
        T("mv-push",
          f'<p class="p-small"><span style="color:{RED}">Pushed Out</span></p>\n'
          + hero("—", MUTED, 26) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Close-date push feed not in pack</span></p>'),
        T("mv-lost",
          f'<p class="p-small"><span style="color:{RED}">Closed Lost</span></p>\n'
          + hero(ref(P, "LOST_ACV", "$,.2s"), RED, 26) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"LOST_OPPS",",.0f")} opps · Q4 · ≤ $50k</span></p>'),
        T("mv-also", f'<p class="p-small"><span style="color:{MUTED}">ALSO LEFT PIPELINE</span></p>'),
        C("mv-pull-c", RED_BG, "#fecaca"), C("mv-won-c", GREEN_BG, "#bbf7d0"),
        T("mv-pull",
          f'<p class="p-small"><span style="color:{RED}">Pulled Back (to S0/S1)</span></p>\n'
          + hero("—", MUTED, 26) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Stage-drop feed not in pack</span></p>'),
        T("mv-won",
          f'<p class="p-small"><span style="color:{GREEN}">Closed Won</span></p>\n'
          + hero(ref(P, "WON_ACV", "$,.2s"), GREEN, 26) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"WON_OPPS",",.0f")} opps · Q4</span></p>'),
        T("mv-add", f'<p class="p-small"><span style="color:{GREEN}">WHAT ADDED</span></p>'),
        C("mv-cr-c", GREEN_BG, "#bbf7d0"), C("mv-ccq-c", AMBER_BG, "#fbbf24"),
        T("mv-cr",
          f'<p class="p-small"><span style="color:{GREEN}">Created This Quarter</span></p>\n'
          + hero(ref(P, "Q4_CREATED_ACV", "$,.2s"), GREEN, 26) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"Q4_CREATED_OPPS",",.0f")} opps</span></p>'),
        T("mv-ccq",
          f'<p class="p-small"><span style="color:{ORANGE}">Created &amp; Closing This Q</span></p>\n'
          + hero(ref(P, "CREATED_CLOSING_ACV", "$,.2s"), ORANGE, 26) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"CREATED_CLOSING_OPPS",",.0f")} opps</span></p>'),
        C("mv-walk-c", "#eff6ff", "#93c5fd"),
        T("mv-walk",
          f'<p class="p-small"><span style="color:{BLUE}">Walk-in baseline (Q4 start)</span></p>\n'
          + hero(ref(W, "WALKIN_ACV", "$,.2s"), BLUE, 22) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Frozen · {ref(W,"WALKIN_OPPS",",.0f")} opps</span></p>'),
        T("open-mo-h", f'## Open Pipeline by Close Month — Stage\n<span style="color:{MUTED}">FY2026 · Stages 2–7 · ACV metrics (fast)</span>'),
        {
            "id": "chart-closemo", "kind": "bar-chart",
            "name": "Open Pipeline by Close Month — Stage",
            "source": dm("chart-closemo"),
            "columns": [
                {"id": "cmo-m", "name": "Month", "formula": "[Chart Close Month Stage/MONTH]",
                 "format": {"kind": "datetime", "formatString": "%b"}},
                {"id": "cmo-s", "name": "Stage", "formula": "[Chart Close Month Stage/STAGE]"},
                {"id": "cmo-v", "name": "ACV", "formula": "[Chart Close Month Stage/ACV]",
                 "format": {"kind": "number", "formatString": "$,.2s"}},
            ],
            "xAxis": {"columnId": "cmo-m"},
            "yAxis": {"columnIds": ["cmo-v"]},
            "stacking": "stacked",
            "color": {
                "by": "category", "column": "cmo-s",
                "scheme": ["#38bdf8", "#3b82f6", "#6366f1", "#a855f7", "#db2777", "#f9a8d4"],
            },
            "style": {"backgroundColor": WHITE, "borderRadius": "round", "borderColor": BORDER, "borderWidth": 1},
        },
        T("open-prod-h", f'## Open Pipeline by Product\n<span style="color:{MUTED}">FY2026 Stage 2+ · ACV metrics (fast)</span>'),
        {
            "id": "chart-product", "kind": "bar-chart",
            "name": "Open Pipeline by Product Category",
            "source": dm("chart-product"),
            "columns": [
                {"id": "cp-p", "name": "Product", "formula": "[Chart Product Category/PRODUCT]"},
                {"id": "cp-v", "name": "ACV", "formula": "[Chart Product Category/ACV]",
                 "format": {"kind": "number", "formatString": "$,.2s"}},
            ],
            "xAxis": {"columnId": "cp-p"},
            "yAxis": {"columnIds": ["cp-v"]},
            "color": {"by": "single", "value": BLUE},
            "style": {"backgroundColor": WHITE, "borderRadius": "round", "borderColor": BORDER, "borderWidth": 1},
        },
        T("open-sum-h", f'## Summary tables\n<span style="color:{MUTED}">Q4 stage funnel + product group · same ACV grains (no extra SQL)</span>'),
        # Pass-through only — no Sum() (would re-inline custom SQL).
        {
            "id": "tbl-stage-sum", "kind": "table", "name": "Summary by Stage (Q4)",
            "source": dm("chart-funnel"),
            "columns": [
                {"id": "tss-s", "name": "Stage", "formula": "[Chart Funnel/STAGE]"},
                {"id": "tss-o", "name": "Ord", "formula": "[Chart Funnel/ORD]"},
                {"id": "tss-a", "name": "ACV", "formula": "[Chart Funnel/ACV]", "format": m()},
            ],
            "style": {"backgroundColor": WHITE, "borderRadius": "round", "borderColor": BORDER, "borderWidth": 1},
        },
        {
            "id": "tbl-prod-sum", "kind": "table", "name": "Summary by Product",
            "source": dm("chart-product"),
            "columns": [
                {"id": "tps-p", "name": "Product", "formula": "[Chart Product Category/PRODUCT]"},
                {"id": "tps-d", "name": "Deals", "formula": "[Chart Product Category/OPPS]"},
                {"id": "tps-a", "name": "ACV", "formula": "[Chart Product Category/ACV]", "format": m()},
            ],
            "style": {"backgroundColor": WHITE, "borderRadius": "round", "borderColor": BORDER, "borderWidth": 1},
        },
    ]

    # ═══════════════ TOTAL ═══════════════
    els += [
        T("total-title", f'# Total Company\n<p class="p-small"><span style="color:{MUTED}">ACV-fast · product actuals + segment 2H targets (segment actuals on Sourcing)</span></p>'),
        C("tc-att-y", TEAL_BG, "#99f6e4"), C("tc-att-q", AMBER_BG, "#fbbf24"), C("tc-att-cov", "#eff6ff", "#93c5fd"), C("tc-att-ytd"),
        T("tk-att-y",
          label("YEAR CREATION ATTAINMENT") + "\n" +
          hero(ref(P, "YEAR_PCT_GOAL", ".1%"), TEAL, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"YTD_ACV","$,.2s")} / {ref(P,"YEAR_GOAL","$,.2s")} · '
          f'{ref(P,"YEAR_ELAPSED",".0%")} elapsed</span></p>'),
        T("tk-att-q",
          label("Q4 CREATION ATTAINMENT") + "\n" +
          hero(ref(P, "Q4_PCT_GOAL", ".1%"), ORANGE, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"Q4_CREATED_ACV","$,.2s")} / {ref(P,"Q4_GOAL","$,.2s")} · '
          f'{ref(P,"Q4_ELAPSED",".0%")} elapsed</span></p>'),
        T("tk-att-cov",
          label("Q4 OPEN COVERAGE") + "\n" +
          hero(ref(P, "Q4_COVERAGE", ".1%"), BLUE, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Q4 open / Q4 creation goal</span></p>'),
        T("tk-att-ytd",
          label("YTD PIPELINE CREATED") + "\n" +
          hero(ref(P, "YTD_ACV", "$,.2s"), INK, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Stage 2+ attained · FY2026</span></p>'),
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
        T("total-early-h", f'## Early Stage Pipeline\n<span style="color:{MUTED}">Open S0–S2 · ACV pack (segment breakdown on Sourcing)</span>'),
        C("te-s0"), C("te-s1"), C("te-s2", TEAL_BG, "#5eead4"), C("te-mo", AMBER_BG, "#fbbf24"),
        T("te-s0-b",
          label("STAGE 0 OPEN") + "\n" +
          hero(ref(P, "S0_ACV", "$,.2s"), BLUE, 26) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"S0_OPPS",",.0f")} opps</span></p>'),
        T("te-s1-b",
          label("STAGE 1 OPEN") + "\n" +
          hero(ref(P, "S1_ACV", "$,.2s"), BLUE, 26) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"S1_OPPS",",.0f")} opps</span></p>'),
        T("te-s2-b",
          label("STAGE 2 OPEN") + "\n" +
          hero(ref(P, "S2_ACV", "$,.2s"), TEAL, 26) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"S2_OPPS",",.0f")} opps</span></p>'),
        T("te-mo-b",
          label("CREATED THIS MONTH") + "\n" +
          hero(ref(P, "MONTH_ACV", "$,.2s"), ORANGE, 26) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"MONTH_OPPS",",.0f")} opps</span></p>'),
        T("total-seg-h", f'## Segment 2H targets\n<span style="color:{MUTED}">Plan chrome · tagged actuals live on Pipeline Sourcing (open-VW)</span>'),
        C("ts-core"), C("ts-mid"), C("ts-ent"), C("ts-tot", TEAL_BG, "#99f6e4"),
        T("ts-core-b",
          label("CORE · 2H TARGET") + "\n" +
          hero("$18M", BLUE, 26) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Actuals → Sourcing</span></p>'),
        T("ts-mid-b",
          label("MID-MARKET · 2H TARGET") + "\n" +
          hero("$16M", TEAL, 26) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Actuals → Sourcing</span></p>'),
        T("ts-ent-b",
          label("ENTERPRISE · 2H TARGET") + "\n" +
          hero("$20M", ORANGE, 26) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Actuals → Sourcing</span></p>'),
        T("ts-tot-b",
          label("TOTAL OPEN (PACK)") + "\n" +
          hero(ref(P, "TOTAL_ACV", "$,.2s"), TEAL, 26) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"TOTAL_OPPS",",.0f")} opps · ACV-fast</span></p>'),
        T("total-defs",
          f'<p class="p-small"><span style="color:{MUTED}">Product actuals = ACV metrics (fast) · '
          f'Segment bars = 2H targets (open-VW segment actuals on Pipeline Sourcing) · '
          f'Up-Market = Mid-Market + Enterprise · II = Analytics + Client + Content · RQC &amp; AMS = RQC + Service</span></p>'),
    ]

    # ═══════════════ SOURCING ═══════════════
    els += [
        T("sourcing-title", f'# Pipeline Sourcing\n<p class="p-small"><span style="color:{MUTED}">Marketing vs Sales · Stage 2+ · open-VW (slow) below · pack strip is ACV-fast</span></p>'),
        C("sc-fast", TEAL_BG, "#99f6e4"),
        T("sk-fast",
          label("FAST STRIP · PACK (ACV)") + "\n" +
          f'<p class="p-small"><span style="font-size:22px;color:{INK}">Q4 open {ref(P,"Q4_ACV","$,.2s")} · '
          f'Total open {ref(P,"TOTAL_ACV","$,.2s")} · Created Q4 {ref(P,"Q4_CREATED_ACV","$,.2s")}</span></p>\n'
          f'<p class="p-small"><span style="color:{MUTED}">Shows immediately · Lead Source / segment wait on VW below</span></p>'),
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
        C("sc-deal-row", SECTION, SECTION),
        C("sc-nl"), C("sc-xs"), C("sc-unc", "#f8fafc", BORDER),
        T("sk-nl",
          label("NEW LOGO") + "\n" +
          hero(ref(S, "NL_ACV", "$,.2s"), BLUE, 28) + "\n" +
          f'<p class="p-small"><span style="color:{GREEN}">{ref(S,"NL_PCT_GOAL",".1%")} of goal</span> · '
          f'<span style="color:{MUTED}">target {ref(S,"NL_TARGET","$,.2s")}</span></p>\n'
          f'<p class="p-small"><span style="color:{BLUE}">M {ref(S,"NL_MKT","$,.2s")}</span> · '
          f'<span style="color:{ORANGE}">S {ref(S,"NL_SALES","$,.2s")}</span></p>'),
        T("sk-xs",
          label("CROSS-SELL / EXPANSION") + "\n" +
          hero(ref(S, "XS_ACV", "$,.2s"), ORANGE, 28) + "\n" +
          f'<p class="p-small"><span style="color:{GREEN}">{ref(S,"XS_PCT_GOAL",".1%")} of goal</span> · '
          f'<span style="color:{MUTED}">target {ref(S,"XS_TARGET","$,.2s")}</span></p>\n'
          f'<p class="p-small"><span style="color:{BLUE}">M {ref(S,"XS_MKT","$,.2s")}</span> · '
          f'<span style="color:{ORANGE}">S {ref(S,"XS_SALES","$,.2s")}</span></p>'),
        T("sk-unc",
          label("UNCATEGORIZED DEAL TYPE") + "\n" +
          hero(ref(S, "UNC_ACV", "$,.2s"), MUTED, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Outside New Logo / Cross-Sell</span></p>'),
        C("sc-seg-row", SECTION, SECTION),
        C("sc-core"), C("sc-mid"), C("sc-ent"), C("sc-unmap", "#f8fafc", BORDER),
        T("sk-core",
          label("CORE · TAGGED") + "\n" +
          hero(ref(S, "SEG_CORE", "$,.2s"), BLUE, 28) + "\n" +
          f'<p class="p-small"><span style="color:{GREEN}">{ref(S,"CORE_PCT_GOAL",".1%")} of 2H goal</span></p>\n'
          f'<p class="p-small"><span style="color:{BLUE}">M {ref(S,"CORE_MKT","$,.2s")}</span> · '
          f'<span style="color:{ORANGE}">S {ref(S,"CORE_SALES","$,.2s")}</span></p>'),
        T("sk-mid",
          label("MID-MARKET · TAGGED") + "\n" +
          hero(ref(S, "SEG_MID", "$,.2s"), TEAL, 28) + "\n" +
          f'<p class="p-small"><span style="color:{GREEN}">{ref(S,"MID_PCT_GOAL",".1%")} of 2H goal</span></p>\n'
          f'<p class="p-small"><span style="color:{BLUE}">M {ref(S,"MID_MKT","$,.2s")}</span> · '
          f'<span style="color:{ORANGE}">S {ref(S,"MID_SALES","$,.2s")}</span></p>'),
        T("sk-ent",
          label("ENTERPRISE / UP-MARKET · TAGGED") + "\n" +
          hero(ref(S, "SEG_ENT", "$,.2s"), ORANGE, 28) + "\n" +
          f'<p class="p-small"><span style="color:{GREEN}">{ref(S,"ENT_PCT_GOAL",".1%")} of 2H goal</span></p>\n'
          f'<p class="p-small"><span style="color:{BLUE}">M {ref(S,"ENT_MKT","$,.2s")}</span> · '
          f'<span style="color:{ORANGE}">S {ref(S,"ENT_SALES","$,.2s")}</span></p>'),
        T("sk-unmap",
          label("UNTAGGED OPEN ACV") + "\n" +
          hero(ref(S, "SEG_UNMAPPED", "$,.2s"), MUTED, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">No Core/Mid/Enterprise token in Segment</span></p>'),
        T("sk-note",
          f'<p class="p-small"><span style="color:{MUTED}">Open-VW 1-row · Lead Source × Opp Type × SplitSegment · '
          f'close Q4–Q2-out · VW {ref(S,"OPEN_ALL_ACV","$,.2s")} (pack {ref(P,"TOTAL_ACV","$,.2s")}) · '
          f'only slow page</span></p>'),
    ]

    # ═══════════════ MOVEMENT ═══════════════
    els += [
        T("movement-title",
          f'# Pipeline Movement\n<p class="p-small"><span style="color:{MUTED}">'
          f'ACV-fast · daily snapshot chart deferred (keeps this page hot) · pack + walk-in</span></p>'),
        C("mc-1"), C("mc-2"), C("mc-3"),
        C("mc-4", GREEN_BG, "#bbf7d0"), C("mc-5", RED_BG, "#fecaca"), C("mc-6", AMBER_BG, "#fbbf24"),
        C("mc-7"), C("mc-8"), C("mc-9", "#f5f3ff", "#c4b5fd"), C("mc-10", GREEN_BG, "#bbf7d0"),
        T("mk-open",
          label("TOTAL OPEN PIPELINE") + "\n" +
          hero(ref(P, "TOTAL_ACV", "$,.0f"), INK, 32) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Q4 close {ref(P,"Q4_ACV","$,.0f")} · matches Open</span></p>'),
        T("mk-q4",
          label("Q4 OPEN ACV") + "\n" +
          hero(ref(P, "Q4_ACV", "$,.0f"), BLUE, 32) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"Q4_OPPS",",.0f")} opps</span></p>'),
        T("mk-walk",
          label("WALK-IN (Q4 START)") + "\n" +
          hero(ref(W, "WALKIN_ACV", "$,.0f"), TEAL, 32) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Frozen · {ref(W,"WALKIN_OPPS",",.0f")} opps</span></p>'),
        T("mk-won",
          label("CLOSED WON (Q4)") + "\n" +
          hero(ref(P, "WON_ACV", "$,.0f"), GREEN, 32) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"WON_OPPS",",.0f")} opps</span></p>'),
        T("mk-lost",
          label("CLOSED LOST (Q4)") + "\n" +
          hero(ref(P, "LOST_ACV", "$,.0f"), RED, 32) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"LOST_OPPS",",.0f")} opps · ≤ $50k</span></p>'),
        T("mk-created",
          label("CREATED Q4") + "\n" +
          hero(ref(P, "Q4_CREATED_ACV", "$,.0f"), ORANGE, 32) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"Q4_CREATED_OPPS",",.0f")} opps</span></p>'),
        T("mk-opps",
          label("OPEN OPPORTUNITIES") + "\n" +
          hero(ref(P, "TOTAL_OPPS", ",.0f"), INK, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Stage 2+ · unique</span></p>'),
        T("mk-avg",
          label("AVG DEAL SIZE") + "\n" +
          hero(ref(P, "AVG_DEAL", "$,.0f"), BLUE, 28)),
        T("mk-large",
          label("LARGE DEALS (≥ $50k)") + "\n" +
          hero(ref(P, "LARGE_OPPS", ",.0f"), "#7c3aed", 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"LARGE_ACV","$,.2s")} ACV</span></p>'),
        T("mk-small",
          label("SMALL DEALS (< $50k)") + "\n" +
          hero(ref(P, "SMALL_OPPS", ",.0f"), GREEN, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"SMALL_ACV","$,.2s")} ACV</span></p>'),
        C("mc-cov-y", TEAL_BG, "#99f6e4"), C("mc-cov-q", "#eff6ff", "#93c5fd"),
        T("mk-cov-y",
          label("YEAR OPEN COVERAGE") + "\n" +
          hero(ref(P, "YEAR_COVERAGE", ".1%"), TEAL, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Total open / year creation goal</span></p>'),
        T("mk-cov-q",
          label("Q4 OPEN COVERAGE") + "\n" +
          hero(ref(P, "Q4_COVERAGE", ".1%"), BLUE, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Q4 open / Q4 creation goal</span></p>'),
        T("mv-bridge-h", f'## Q4 bridge\n<span style="color:{MUTED}">Walk-in + created − won − lost · pack grain · no daily snapshot VW</span>'),
        C("mb-w"), C("mb-c", GREEN_BG, "#bbf7d0"), C("mb-won", GREEN_BG, "#bbf7d0"), C("mb-lost", RED_BG, "#fecaca"), C("mb-q", "#eff6ff", "#93c5fd"),
        T("mb-walk", label("WALK-IN") + "\n" + hero(ref(W, "WALKIN_ACV", "$,.2s"), TEAL, 26)),
        T("mb-cr", label("+ CREATED") + "\n" + hero(ref(P, "Q4_CREATED_ACV", "$,.2s"), GREEN, 26)),
        T("mb-wn", label("− WON") + "\n" + hero(ref(P, "WON_ACV", "$,.2s"), GREEN, 26)),
        T("mb-ls", label("− LOST ≤$50k") + "\n" + hero(ref(P, "LOST_ACV", "$,.2s"), RED, 26)),
        T("mb-q4", label("= Q4 OPEN") + "\n" + hero(ref(P, "Q4_ACV", "$,.2s"), BLUE, 26)),
        T("mv-snap-note",
          f'<p class="p-small"><span style="color:{MUTED}">Daily snapshot / 30-day delta / YoY lines need BI_STAGING.SNAPSHOT — '
          f'intentionally omitted so Movement stays ACV-fast. Use Open close-month×stage for composition.</span></p>'),
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
          label("CREATED & WON THIS Q") + "\n" +
          hero(ref(P, "CREATED_WON_ACV", "$,.2s"), GREEN, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"CREATED_WON_OPPS",",.0f")} opps · pack</span></p>'),
        T("bridge-h", f'## Pipeline Bridge — Q4 FY2026\n<span style="color:{MUTED}">Walk-in + Created − Won − Lost + Other Adj ≈ Open · pack grain</span>'),
        C("cc-start"), C("cc-cr", GREEN_BG, "#bbf7d0"), C("cc-won", GREEN_BG, "#bbf7d0"),
        C("cc-lost", RED_BG, "#fecaca"), C("cc-tot", "#eff6ff", "#93c5fd"),
        T("ck-start", label("WALK-IN (QTR START)") + "\n" + hero(ref(W, "WALKIN_ACV", "$,.2s"), BLUE, 22)),
        T("ck-plus", f'<p class="p-small" style="text-align:center"><span style="font-size:28px;color:{MUTED}">+</span></p>'),
        T("ck-cr", label("CREATED") + "\n" + hero(ref(P, "Q4_CREATED_ACV", "$,.2s"), GREEN, 22)),
        T("ck-minus1", f'<p class="p-small" style="text-align:center"><span style="font-size:28px;color:{MUTED}">−</span></p>'),
        T("ck-won", label("WON") + "\n" + hero(ref(P, "WON_ACV", "$,.2s"), GREEN, 22)),
        T("ck-minus2", f'<p class="p-small" style="text-align:center"><span style="font-size:28px;color:{MUTED}">−</span></p>'),
        T("ck-lost", label("LOST") + "\n" + hero(ref(P, "LOST_ACV", "$,.2s"), RED, 22)),
        T("ck-plus2", f'<p class="p-small" style="text-align:center"><span style="font-size:28px;color:{MUTED}">+</span></p>'),
        C("cc-adj", AMBER_BG, "#fbbf24"),
        T("ck-adj",
          label("OTHER ADJ") + "\n" +
          hero(ref(P, "OTHER_ADJ_ACV", "$,.2s"), ORANGE, 22) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Residual vs walk-in bridge</span></p>'),
        T("ck-eq", f'<p class="p-small" style="text-align:center"><span style="font-size:28px;color:{MUTED}">≈</span></p>'),
        T("ck-tot", label("TOTAL OPEN") + "\n" + hero(ref(P, "TOTAL_ACV", "$,.2s"), BLUE, 22)),
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
        T("yoy-h", f'## Pipeline Created by Quarter — YoY\n<span style="color:{MUTED}">FY2025 vs FY2026 · Stage 2+ attained · ACV metrics</span>'),
        {
            "id": "chart-created", "kind": "bar-chart", "name": "Pipeline Created YoY by Quarter",
            "source": dm("chart-created"),
            "columns": [
                {"id": "ccm-q", "name": "Quarter", "formula": "[Chart Created/QUARTER]"},
                {"id": "ccm-ord", "name": "Ord", "formula": "[Chart Created/ORD]"},
                {"id": "ccm-fy", "name": "FY", "formula": "[Chart Created/FY]"},
                {"id": "ccm-v", "name": "ACV", "formula": "[Chart Created/ACV]",
                 "format": {"kind": "number", "formatString": "$,.2s"}},
            ],
            "xAxis": {"columnId": "ccm-q"}, "yAxis": {"columnIds": ["ccm-v"]},
            "color": {
                "by": "category", "column": "ccm-fy",
                "scheme": ["#94a3b8", "#38bdf8"],
            },
            "style": {"backgroundColor": WHITE, "borderRadius": "round", "borderColor": BORDER, "borderWidth": 1},
        },
        T("data-note", """# Fast path

Hot pages = ACV pack (open/created/won/lost/early/size/bridge residual/coverage) + walk-in + funnel/TV
+ Open close-month×stage + product bars + Created YoY quarters.
Sourcing only = open presentation VW (Lead Source × Opp Type × SplitSegment).
Coverage / ABM = pack chrome (no open-VW). No daily snapshot grain.
"""),
    ]

    # ═══════════════ COVERAGE (stills) — pack only, no open-VW ═══════════════
    els += [
        T("cov-title", f'# Pipeline Coverage\n<p class="p-small"><span style="color:{MUTED}">Plan vs open coverage · ACV pack · segment tagged actuals on Sourcing</span></p>'),
        C("covp-1", TEAL_BG, "#99f6e4"), C("covp-2", "#eff6ff", "#93c5fd"), C("covp-3"), C("covp-4", AMBER_BG, "#fbbf24"),
        T("cov-k1",
          label("TOTAL OPEN / YEAR GOAL") + "\n" +
          hero(ref(P, "YEAR_COVERAGE", ".1%"), TEAL, 32) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"TOTAL_ACV","$,.2s")} open · goal {ref(P,"YEAR_GOAL","$,.2s")}</span></p>'),
        T("cov-k2",
          label("Q4 OPEN / Q4 GOAL") + "\n" +
          hero(ref(P, "Q4_COVERAGE", ".1%"), BLUE, 32) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"Q4_ACV","$,.2s")} open · goal {ref(P,"Q4_GOAL","$,.2s")}</span></p>'),
        T("cov-k3",
          label("Q4 OPEN PIPELINE") + "\n" +
          hero(ref(P, "Q4_ACV", "$,.2s"), INK, 32) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"Q4_OPPS",",.0f")} opps · Stage 2+</span></p>'),
        T("cov-k4",
          label("NEXT QUARTER OPEN") + "\n" +
          hero(ref(P, "NQ_ACV", "$,.2s"), ORANGE, 32) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">{ref(P,"NQ_OPPS",",.0f")} opps · Q1 2027</span></p>'),
        T("cov-seg-h", f'## Segment 2H plan coverage\n<span style="color:{MUTED}">Targets chrome · tagged open actuals live on Pipeline Sourcing</span>'),
        C("cov-sc"), C("cov-sm"), C("cov-se"), C("cov-st", TEAL_BG, "#99f6e4"),
        T("cov-sc-b",
          label("CORE · 2H TARGET") + "\n" +
          hero("$18M", BLUE, 26) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Actuals → Sourcing</span></p>'),
        T("cov-sm-b",
          label("MID-MARKET · 2H TARGET") + "\n" +
          hero("$16M", TEAL, 26) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Actuals → Sourcing</span></p>'),
        T("cov-se-b",
          label("ENTERPRISE · 2H TARGET") + "\n" +
          hero("$20M", ORANGE, 26) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Actuals → Sourcing</span></p>'),
        T("cov-st-b",
          label("TOTAL OPEN (PACK)") + "\n" +
          hero(ref(P, "TOTAL_ACV", "$,.2s"), TEAL, 26) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Year coverage {ref(P,"YEAR_COVERAGE",".1%")}</span></p>'),
        T("cov-note",
          f'<p class="p-small"><span style="color:{MUTED}">Coverage ratios use creation goals as the plan denominator (stills). '
          f'Segment % of 2H goal requires open-VW tags — kept on Pipeline Sourcing so this page stays hot.</span></p>'),
    ]

    # ═══════════════ ABM (stills) — frozen baseline chrome ═══════════════
    els += [
        T("abm-title", f'# Q4 Big Bet ABM Plays\n<p class="p-small"><span style="color:{MUTED}">Frozen ABM opportunity baseline · October snapshot</span></p>'),
        C("abm-1", AMBER_BG, "#fbbf24"), C("abm-2"), C("abm-3", TEAL_BG, "#99f6e4"),
        T("abm-k1",
          label("BASELINE STATUS") + "\n" +
          hero("Frozen", ORANGE, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">ABM playbook feed not in ACV pack</span></p>'),
        T("abm-k2",
          label("Q4 OPEN CONTEXT") + "\n" +
          hero(ref(P, "Q4_ACV", "$,.2s"), INK, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Company Q4 open · {ref(P,"Q4_OPPS",",.0f")} opps</span></p>'),
        T("abm-k3",
          label("WALK-IN (Q4 START)") + "\n" +
          hero(ref(W, "WALKIN_ACV", "$,.2s"), TEAL, 28) + "\n" +
          f'<p class="p-small"><span style="color:{MUTED}">Frozen snapshot · {ref(W,"WALKIN_OPPS",",.0f")} opps</span></p>'),
        T("abm-note",
          f'<p class="p-small"><span style="color:{MUTED}">Stills ABM list is a frozen Salesforce baseline. '
          f'When the ABM opportunity table lands in Snowflake, bind it here — never fan open-VW into hot pages.</span></p>'),
    ]

    def L(e, a, b, c, d):
        return E(e, a, b, c, d, 1)

    # Equal 5-wide cards (24/5 ≈ 4.8 → 5+5+5+5+4). Progress sits BELOW sec-01
    # so it never steals auto-row tracks from the plugin cards.
    rotb = [
        E("rotb-title", 1, 18, 1, 3), E("rotb-badge", 18, 25, 1, 3),
        Cont("sec-01", 1, 25, 3, 12, [
            L("rotb-s01", 1, 25, 1, 2),
            # Plugins need tall inner grid tracks; text cards use short 1/2.
            Cont("card-year", 1, 6, 2, 9, [L("plugin-pace-year", 1, 25, 1, 8)], 2),
            Cont("card-q4", 6, 11, 2, 9, [L("plugin-pace-q4", 1, 25, 1, 8)], 2),
            Cont("card-week", 11, 16, 2, 9, [L("rk-week", 1, 25, 1, 2)], 2),
            Cont("card-ccq", 16, 21, 2, 9, [L("rk-ccq", 1, 25, 1, 2)], 2),
            Cont("card-cwq", 21, 25, 2, 9, [L("rk-cwq", 1, 25, 1, 2)], 2),
        ]),
        E("rotb-progress", 1, 25, 12, 13),
        Cont("sec-02", 1, 25, 13, 18, [
            L("rotb-s02", 1, 25, 1, 2),
            Cont("cov-1", 1, 7, 2, 6, [L("rk-open", 1, 25, 1, 2)], 2),
            Cont("cov-2", 7, 13, 2, 6, [L("rk-cq", 1, 25, 1, 2)], 2),
            Cont("cov-3", 13, 19, 2, 6, [L("rk-nq", 1, 25, 1, 2)], 2),
            Cont("cov-4", 19, 25, 2, 6, [L("rk-2q", 1, 25, 1, 2)], 2),
        ]),
        Cont("sec-03", 1, 25, 18, 25, [
            L("rotb-s03", 1, 25, 1, 2),
            Cont("mgmt-w", 1, 9, 2, 8, [L("rk-walk", 1, 25, 1, 2)], 2),
            Cont("mgmt-won", 9, 17, 2, 8, [L("rk-won", 1, 25, 1, 2)], 2),
            Cont("mgmt-lost", 17, 25, 2, 8, [L("rk-lost", 1, 25, 1, 2)], 2),
        ]),
        Cont("sec-04", 1, 25, 25, 32, [
            L("rotb-s04", 1, 25, 1, 2),
            Cont("dm-s0", 1, 7, 2, 6, [L("dm-s0-b", 1, 25, 1, 2)], 2),
            Cont("dm-s1", 7, 13, 2, 6, [L("dm-s1-b", 1, 25, 1, 2)], 2),
            Cont("dm-s2", 13, 19, 2, 6, [L("dm-s2-b", 1, 25, 1, 2)], 2),
            Cont("dm-mo", 19, 25, 2, 6, [L("dm-mo-b", 1, 25, 1, 2)], 2),
        ]),
        Cont("sec-05", 1, 25, 32, 41, [
            L("rotb-s05", 1, 25, 1, 2),
            Cont("mkt-pace", 1, 10, 2, 10, [L("plugin-pace-month", 1, 25, 1, 8)], 2),
            Cont("mkt-s0", 10, 15, 2, 10, [L("rk-mkt-s0", 1, 25, 1, 2)], 2),
            Cont("mkt-s1", 15, 20, 2, 10, [L("rk-mkt-s1", 1, 25, 1, 2)], 2),
            Cont("mkt-s2", 20, 25, 2, 10, [L("rk-mkt-s2", 1, 25, 1, 2)], 2),
        ]),
        Cont("sec-06", 1, 25, 41, 47, [
            L("rotb-s06", 1, 25, 1, 2),
            Cont("sg-note", 1, 25, 2, 5, [L("rk-sg", 1, 25, 1, 2)], 2),
        ]),
    ]
    open_l = [
        E("open-title", 1, 18, 1, 3), E("open-live", 18, 25, 1, 3),
        E("ctrl-stage1", 1, 10, 3, 4), E("ctrl-segment", 10, 17, 3, 4), E("ctrl-dealtype", 17, 25, 3, 4),
        Cont("okc-u", 1, 5, 4, 8, [L("ok-u", 1, 25, 1, 2)]),
        Cont("okc-t", 5, 9, 4, 8, [L("ok-t", 1, 25, 1, 2)]),
        Cont("okc-w", 9, 13, 4, 8, [L("ok-w", 1, 25, 1, 2)]),
        Cont("okc-q", 13, 17, 4, 8, [L("ok-q", 1, 25, 1, 2)]),
        Cont("okc-lines", 17, 21, 4, 8, [L("ok-lines", 1, 25, 1, 2)]),
        Cont("okc-avg", 21, 25, 4, 8, [L("ok-avg", 1, 25, 1, 2)]),
        Cont("okc-lg", 1, 13, 8, 12, [L("ok-lg", 1, 25, 1, 2)]),
        Cont("okc-sm", 13, 25, 8, 12, [L("ok-sm", 1, 25, 1, 2)]),
        # Header + funnel LEFT / movement RIGHT as page siblings (plugin overflow
        # was covering nested cards when both lived in one container).
        Cont("okc-chg", 1, 25, 12, 14, [L("open-chg", 1, 25, 1, 8)]),
        Cont("okc-funnel", 1, 13, 14, 30, [
            L("ok-q4tot", 1, 25, 1, 3),
            L("plugin-funnel", 1, 25, 3, 16),
        ]),
        Cont("okc-mv", 13, 25, 14, 30, [
            L("mv-left", 1, 25, 1, 2),
            Cont("mv-push-c", 1, 13, 2, 6, [L("mv-push", 1, 25, 1, 2)], 2),
            Cont("mv-lost-c", 13, 25, 2, 6, [L("mv-lost", 1, 25, 1, 2)], 2),
            L("mv-also", 1, 25, 6, 7),
            Cont("mv-pull-c", 1, 13, 7, 11, [L("mv-pull", 1, 25, 1, 2)], 2),
            Cont("mv-won-c", 13, 25, 7, 11, [L("mv-won", 1, 25, 1, 2)], 2),
            L("mv-add", 1, 25, 11, 12),
            Cont("mv-cr-c", 1, 13, 12, 16, [L("mv-cr", 1, 25, 1, 2)], 2),
            Cont("mv-ccq-c", 13, 25, 12, 16, [L("mv-ccq", 1, 25, 1, 2)], 2),
            Cont("mv-walk-c", 1, 25, 16, 19, [L("mv-walk", 1, 25, 1, 2)], 2),
        ]),
        E("open-mo-h", 1, 25, 30, 32),
        E("chart-closemo", 1, 25, 32, 44),
        E("open-prod-h", 1, 25, 44, 46),
        E("chart-product", 1, 25, 46, 56),
        E("open-sum-h", 1, 25, 56, 58),
        E("tbl-stage-sum", 1, 13, 58, 68),
        E("tbl-prod-sum", 13, 25, 58, 68),
    ]
    total_l = [
        E("total-title", 1, 25, 1, 3),
        Cont("tc-att-y", 1, 7, 3, 8, [L("tk-att-y", 1, 25, 1, 2)]),
        Cont("tc-att-q", 7, 13, 3, 8, [L("tk-att-q", 1, 25, 1, 2)]),
        Cont("tc-att-cov", 13, 19, 3, 8, [L("tk-att-cov", 1, 25, 1, 2)]),
        Cont("tc-att-ytd", 19, 25, 3, 8, [L("tk-att-ytd", 1, 25, 1, 2)]),
        Cont("tc-1", 1, 9, 8, 13, [L("tk-cq", 1, 25, 1, 2)]),
        Cont("tc-2", 9, 17, 8, 13, [L("tk-nq", 1, 25, 1, 2)]),
        Cont("tc-3", 17, 25, 8, 13, [L("tk-2q", 1, 25, 1, 2)]),
        E("plugin-tv", 1, 25, 13, 27),
        E("total-early-h", 1, 25, 27, 29),
        Cont("te-s0", 1, 7, 29, 34, [L("te-s0-b", 1, 25, 1, 2)]),
        Cont("te-s1", 7, 13, 29, 34, [L("te-s1-b", 1, 25, 1, 2)]),
        Cont("te-s2", 13, 19, 29, 34, [L("te-s2-b", 1, 25, 1, 2)]),
        Cont("te-mo", 19, 25, 29, 34, [L("te-mo-b", 1, 25, 1, 2)]),
        E("total-seg-h", 1, 25, 34, 36),
        Cont("ts-core", 1, 7, 36, 41, [L("ts-core-b", 1, 25, 1, 2)]),
        Cont("ts-mid", 7, 13, 36, 41, [L("ts-mid-b", 1, 25, 1, 2)]),
        Cont("ts-ent", 13, 19, 36, 41, [L("ts-ent-b", 1, 25, 1, 2)]),
        Cont("ts-tot", 19, 25, 36, 41, [L("ts-tot-b", 1, 25, 1, 2)]),
        E("total-defs", 1, 25, 41, 43),
    ]
    sourcing_l = [
        E("sourcing-title", 1, 18, 1, 3), E("ctrl-period", 18, 25, 1, 3),
        Cont("sc-fast", 1, 25, 3, 7, [L("sk-fast", 1, 25, 1, 7)]),
        Cont("sc-row", 1, 25, 7, 15, [
            Cont("sc-m-card", 1, 7, 1, 10, [L("sk-m", 1, 25, 1, 2)], 2),
            Cont("sc-s-card", 7, 13, 1, 10, [L("sk-s", 1, 25, 1, 2)], 2),
            Cont("sc-t-card", 13, 19, 1, 10, [L("sk-t", 1, 25, 1, 2)], 2),
            Cont("sc-mix-card", 19, 25, 1, 10, [L("sk-mix", 1, 25, 1, 2)], 2),
        ]),
        Cont("sc-deal-row", 1, 25, 15, 23, [
            Cont("sc-nl", 1, 9, 1, 10, [L("sk-nl", 1, 25, 1, 2)], 2),
            Cont("sc-xs", 9, 17, 1, 10, [L("sk-xs", 1, 25, 1, 2)], 2),
            Cont("sc-unc", 17, 25, 1, 10, [L("sk-unc", 1, 25, 1, 2)], 2),
        ]),
        Cont("sc-seg-row", 1, 25, 23, 31, [
            Cont("sc-core", 1, 7, 1, 10, [L("sk-core", 1, 25, 1, 2)], 2),
            Cont("sc-mid", 7, 13, 1, 10, [L("sk-mid", 1, 25, 1, 2)], 2),
            Cont("sc-ent", 13, 19, 1, 10, [L("sk-ent", 1, 25, 1, 2)], 2),
            Cont("sc-unmap", 19, 25, 1, 10, [L("sk-unmap", 1, 25, 1, 2)], 2),
        ]),
        E("sk-note", 1, 25, 31, 33),
        # Keep open-VW table on Sourcing only (not Data) so other pages never bind it.
        E("wb-src", 1, 25, 33, 35),
    ]
    movement_l = [
        E("movement-title", 1, 25, 1, 3),
        Cont("mc-1", 1, 9, 3, 8, [L("mk-open", 1, 25, 1, 2)]),
        Cont("mc-2", 9, 17, 3, 8, [L("mk-q4", 1, 25, 1, 2)]),
        Cont("mc-3", 17, 25, 3, 8, [L("mk-walk", 1, 25, 1, 2)]),
        Cont("mc-4", 1, 9, 8, 13, [L("mk-won", 1, 25, 1, 2)]),
        Cont("mc-5", 9, 17, 8, 13, [L("mk-lost", 1, 25, 1, 2)]),
        Cont("mc-6", 17, 25, 8, 13, [L("mk-created", 1, 25, 1, 2)]),
        Cont("mc-7", 1, 7, 13, 18, [L("mk-opps", 1, 25, 1, 2)]),
        Cont("mc-8", 7, 13, 13, 18, [L("mk-avg", 1, 25, 1, 2)]),
        Cont("mc-9", 13, 19, 13, 18, [L("mk-large", 1, 25, 1, 2)]),
        Cont("mc-10", 19, 25, 13, 18, [L("mk-small", 1, 25, 1, 2)]),
        Cont("mc-cov-y", 1, 13, 18, 23, [L("mk-cov-y", 1, 25, 1, 2)]),
        Cont("mc-cov-q", 13, 25, 18, 23, [L("mk-cov-q", 1, 25, 1, 2)]),
        E("mv-bridge-h", 1, 25, 23, 25),
        Cont("mb-w", 1, 6, 25, 31, [L("mb-walk", 1, 25, 1, 2)]),
        Cont("mb-c", 6, 11, 25, 31, [L("mb-cr", 1, 25, 1, 2)]),
        Cont("mb-won", 11, 16, 25, 31, [L("mb-wn", 1, 25, 1, 2)]),
        Cont("mb-lost", 16, 21, 25, 31, [L("mb-ls", 1, 25, 1, 2)]),
        Cont("mb-q", 21, 25, 25, 31, [L("mb-q4", 1, 25, 1, 2)]),
        E("mv-snap-note", 1, 25, 31, 33),
    ]
    created_l = [
        E("created-title", 1, 25, 1, 3),
        Cont("ckp-1", 1, 6, 3, 8, [L("ckp-week", 1, 25, 1, 2)]),
        Cont("ckp-2", 6, 11, 3, 8, [L("ckp-qtr", 1, 25, 1, 2)]),
        Cont("ckp-3", 11, 16, 3, 8, [L("ckp-month", 1, 25, 1, 2)]),
        Cont("ckp-4", 16, 21, 3, 8, [L("ckp-ccq", 1, 25, 1, 2)]),
        Cont("ckp-5", 21, 25, 3, 8, [L("ckp-won", 1, 25, 1, 2)]),
        E("bridge-h", 1, 25, 8, 10),
        Cont("cc-start", 1, 4, 10, 15, [L("ck-start", 1, 25, 1, 2)]),
        E("ck-plus", 4, 5, 10, 15),
        Cont("cc-cr", 5, 8, 10, 15, [L("ck-cr", 1, 25, 1, 2)]),
        E("ck-minus1", 8, 9, 10, 15),
        Cont("cc-won", 9, 12, 10, 15, [L("ck-won", 1, 25, 1, 2)]),
        E("ck-minus2", 12, 13, 10, 15),
        Cont("cc-lost", 13, 16, 10, 15, [L("ck-lost", 1, 25, 1, 2)]),
        E("ck-plus2", 16, 17, 10, 15),
        Cont("cc-adj", 17, 21, 10, 15, [L("ck-adj", 1, 25, 1, 2)]),
        E("ck-eq", 21, 22, 10, 15),
        Cont("cc-tot", 22, 25, 10, 15, [L("ck-tot", 1, 25, 1, 2)]),
        E("close-h", 1, 25, 15, 17),
        Cont("cc-cy", 1, 9, 17, 21, [L("ck-cy", 1, 25, 1, 2)]),
        Cont("cc-ny", 9, 17, 17, 21, [L("ck-ny", 1, 25, 1, 2)]),
        Cont("cc-fy", 17, 25, 17, 21, [L("ck-fy", 1, 25, 1, 2)]),
        E("yoy-h", 1, 25, 21, 23),
        E("chart-created", 1, 25, 23, 35),
    ]
    coverage_l = [
        E("cov-title", 1, 25, 1, 3),
        Cont("covp-1", 1, 7, 3, 9, [L("cov-k1", 1, 25, 1, 2)]),
        Cont("covp-2", 7, 13, 3, 9, [L("cov-k2", 1, 25, 1, 2)]),
        Cont("covp-3", 13, 19, 3, 9, [L("cov-k3", 1, 25, 1, 2)]),
        Cont("covp-4", 19, 25, 3, 9, [L("cov-k4", 1, 25, 1, 2)]),
        E("cov-seg-h", 1, 25, 9, 11),
        Cont("cov-sc", 1, 7, 11, 16, [L("cov-sc-b", 1, 25, 1, 2)]),
        Cont("cov-sm", 7, 13, 11, 16, [L("cov-sm-b", 1, 25, 1, 2)]),
        Cont("cov-se", 13, 19, 11, 16, [L("cov-se-b", 1, 25, 1, 2)]),
        Cont("cov-st", 19, 25, 11, 16, [L("cov-st-b", 1, 25, 1, 2)]),
        E("cov-note", 1, 25, 16, 18),
    ]
    abm_l = [
        E("abm-title", 1, 25, 1, 3),
        Cont("abm-1", 1, 9, 3, 9, [L("abm-k1", 1, 25, 1, 2)]),
        Cont("abm-2", 9, 17, 3, 9, [L("abm-k2", 1, 25, 1, 2)]),
        Cont("abm-3", 17, 25, 3, 9, [L("abm-k3", 1, 25, 1, 2)]),
        E("abm-note", 1, 25, 9, 12),
    ]
    data_l = [E("data-note", 1, 25, 1, 6)]
    row = 6
    for wid in ["wb-pack", "wb-walkin", "wb-funnel", "wb-tv"]:
        data_l.append(E(wid, 1, 25, row, row + 3))
        row += 3

    layout = "\n".join([
        '<?xml version="1.0" encoding="utf-8"?>',
        page("page-rotb", rotb), page("page-total", total_l), page("page-sourcing", sourcing_l),
        page("page-open", open_l), page("page-movement", movement_l), page("page-created", created_l),
        page("page-abm", abm_l), page("page-coverage", coverage_l),
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
                {"id": "page-abm", "name": "Q4 Big Bet ABM Plays", "backgroundColor": "#f8fafc"},
                {"id": "page-coverage", "name": "Pipeline Coverage", "backgroundColor": "#f8fafc"},
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
