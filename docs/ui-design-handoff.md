# UI Design Handoff — Pipeline Tracker FY2026 (Sigma)

**Paste this filepath into a new desktop Agent chat focused on visual fidelity:**

```
/Users/gabrielegjones/Library/Application Support/Cursor/AgentStores/cursor_agent_stores/bc-20d85b1c-d9b3-44e8-bbbc-854dc0e6cfa9/files/docs/ui-design-handoff.md
```

**Mission for the next chat:** Make the live Sigma workbook look **much closer to the Replit stills** (1:1 chrome, density, pace bars, funnel, movement cards). Data layer is already re-architected — **do not put custom SQL back into the workbook**.

---

## Live artifacts (do not recreate from scratch)

| Item | Value |
| --- | --- |
| Workbook | https://app.sigmacomputing.com/zywave/workbook/46Enwkdr17UMrr2Tm9qdWt |
| Workbook UUID | `86f3c78f-e9ce-4eee-b117-3c61a8c11e1d` |
| Data model | https://app.sigmacomputing.com/zywave/data-model/9a07948f-75c9-46d2-b8ca-70700e2ab669 |
| Data model UUID | `9a07948f-75c9-46d2-b8ca-70700e2ab669` |
| Data model name | `Pipeline Tracker FY2026 — Data` |
| Folder | https://app.sigmacomputing.com/zywave/f/5EFLG4WW7cjvngI0kCudpF (`5EFLG4WW7cjvngI0kCudpF`) |
| Connection | `BI_Snowflake_Service` · `e2b90d0c-34fd-4423-a4c3-0569c58f33df` |

### Rebuild scripts (workspace)

```
/Users/gabrielegjones/.cursor/zywave/scripts/create_pipeline_data_model.py   # SQL lives here → DM
/Users/gabrielegjones/.cursor/zywave/scripts/rebuild_pipeline_fast.py        # workbook UI (data-model sources only)
/Users/gabrielegjones/.cursor/zywave/scripts/rebuild_pipeline_v4.py          # prior still-matched chrome (reference only; had mega-SQL)
```

### Auth

```bash
set -a; source ~/.zywave/sigma-zywave.env; set +a
export SIGMA_BASE_URL="$ZYWAVE_BASE_URL"
export SIGMA_CLIENT_ID="$ZYWAVE_CLIENT_ID"
export SIGMA_CLIENT_SECRET="$ZYWAVE_CLIENT_SECRET"
eval "$(bash /Users/gabrielegjones/.claude/skills/sigma-api/scripts/get-token.sh)"
```

---

## What is DONE vs what YOU own

### Done (do not regress)

1. **Data model owns all SQL** — 6 lean SQL tables + 1 warehouse table. Workbook has **zero** `source.kind: sql` / `warehouse-table`.
2. **No mega `src-facts` CTE** — previous slowdown (one ~5KB CTE, ~39 dependents, multi-scan ACV). Replaced with:
   - `Open Pipeline ACV` — filtered row-level (`Forecasted Net ACV` + `STAGE_GROUP = '2-7'`)
   - `Pipeline Created ACV` — Stage 2 attained + boolean flags in SQL
   - `VW Pipeline` — warehouse pushdown for sourcing / won / lost
   - `Walk-in Q4` — tiny snapshot agg (MAX FCST per opp, capped)
   - `Pipeline Snapshots` — daily GROUP BY for movement trend
   - `Goals` / `Segment Targets` — 2–3 row hand-entry literals
3. KPIs aggregate in Sigma via `Sum` / `SumIf` / `CountDistinct` on those sources.
4. Spec shape that **works** for Zywave PUT: document workbook with layout `<Page>` + `<Container type="grid">` + `<Element>` — **never** `GridContainer` / `LayoutElement`.
5. Text elements: **never bare `<p>`** — Sigma rejects them. Always `class="p-small"` or inline `style`.
6. Chart `name` must be a **string**, not an object. Avoid invalid kinds (e.g. combo-chart). Prefer stripping `legend` / `dataLabel` if PUT rejects.

### Your job (UI / look-and-feel)

Pixel-match the Replit stills. Prior build passes were rejected as “generic” / “look like shit” even when numbers were live. **Stills are the source of truth**, not inventing a Sigma default dashboard.

---

## Design source of truth

### Stills (open these; match composition)

```
.../bc-20d85b1c-…/files/media/gong-stills/
```

| Page | Primary stills |
| --- | --- |
| ROTB Summary | `walk_3500`, `walk_3540`, `walk_3620`, `t1850`, `t2030`, `extra_3510`–`extra_3550` |
| Total Company | `walk_3640`, `walk_3700`, `walk_3740` |
| Pipeline Sourcing | (see plan §3.3 — stills around walk_3800+) |
| Open Pipeline | `t1010`, walk ~39–41m frames |
| Pipeline Movement | ~41:30 frames |
| Pipeline Created | ~42:00 frames |

Full layout maps + tokens: [`replit-dashboard-replication-plan.md`](./replit-dashboard-replication-plan.md)  
Original build brief: [`sigma-build-brief.md`](./sigma-build-brief.md)

### Design tokens (from Replit)

| Token | Value / rule |
| --- | --- |
| Canvas | `#f8fafc` (slate-50) — page `backgroundColor` |
| Cards | `#ffffff`, border `#e2e8f0`, `borderRadius: round`, light section shells `#f1f5f9` |
| Ink / muted | `#0f172a` / `#64748b` |
| Teal (sections / open) | `#0d9488` |
| Blue (marketing / pipeline) | `#2563eb` |
| Orange (pace / sales / closing highlight) | `#f97316` |
| Red / green | `#dc2626` / `#16a34a` |
| Highlight cards | Amber bg `#fffbeb` + border `#fbbf24`; teal bg `#ecfdf5` + `#5eead4`; red/green soft fills for lost/won |
| Stage palette | `["#38bdf8","#3b82f6","#6366f1","#a855f7","#db2777","#f9a8d4"]` |
| KPI money format | `$,.2s` on heroes; `$,.0f` in tables |
| Section headers | `01 / PIPELINE CREATION` style — teal/blue/orange numbered labels + short subtitle |

---

## Page-by-page composition targets (what “perfect” means)

### ROTB Summary

Five numbered section shells (full-width containers on slate), **not** a flat KPI grid.

1. **01 Creation pace** — 5 cards in one row:
   - Year / Q4: muted label → **36px hero $** → orange “% of goal” → **horizontal pace strip** (orange fill + gray remain) → footer “Target: $X · Y% paced” + year/quarter progress %
   - Week: simple KPI + “N opportunities”
   - Created & Closing: **amber** card
   - Created & Won: **teal/green** card
2. **02 Coverage** — 4 equal cards (Total Open teal-tinted; CQ / NQ / 2Q out)
3. **03 Pipeline management** — Walk-in / Closed Lost (red shell) / Closed Won (green shell) + captions
4. **04 Marketing performance** — MQL / S0 / S1 / S2 placeholders OK if no feed (“—” + “Awaiting top-of-funnel feed”) — keep card chrome
5. **05 Sales pipeline generation** — Marketing-sourced vs Sales-sourced KPIs

**Critical visual gap today:** pace bars are a weak single horizontal bar, not the Replit **100% stacked Actual+Remain strip with paced tick**. Org has **no** pace plugin (only OnLoad plugins). Options:
- Native: 100% stacked bar from long-format Actual/Remain + optional `refMarks` for paced %
- Better: small `@sigmacomputing/plugin` dual-marker bullet (flag as PLUGIN until built)

### Open Pipeline

- Top KPI strip (unique opps, total ACV, walk-in, Q4 ACV, deal-product lines, avg deal)
- **Q4 Pipeline Changes** block with movement groups: WHAT LEFT / ALSO LEFT / WHAT ADDED (Pushed Out, Closed Lost, Pulled Back, Closed Won, Pulled In, Size Increases) — red/green card chrome
- **Stacked horizontal stage strip** (native MVP) vs true tapered funnel → PLUGIN placeholder labeled clearly
- Close month × stage stacked bar; product category bar

### Total Company / Sourcing / Movement / Created

Match still density: horizon KPI row, segment attainment table with conditional colors, marketing/sales mix cards (39% / 61% targets), snapshot line chart, Created **equation strip** (`Open + Created − Won − Lost − … = Total Open`).

---

## Hard-won Sigma / Zywave lessons (read before editing)

### Spec / API

1. Workbook PUT: `PUT /v2/workbooks/{id}/spec` with `{ "name", "folderId", "description", "document": { schemaVersion, pages, elements, layout, theme } }`.
2. Layout XML uses **`<Element elementId=…>`** and **`<Container elementId=… type="grid" …>`** only.
3. Theme: Light + medium space; canvas `#f8fafc` on pages.
4. Controls exist: Segment, Deal Type, Include Stage 1, SourcingPeriod — wire filters properly (many are currently decorative).
5. After UI edits, prefer iterating `rebuild_pipeline_fast.py` (or a new `rebuild_pipeline_ui.py`) and PUT — don’t hand-edit 176 elements in the UI without a script if you need repeatability.

### Data model rules (do not violate)

1. **All custom SQL stays in** `Pipeline Tracker FY2026 — Data`.
2. Workbook tables use `"source": { "kind": "data-model", "dataModelId": "…", "elementId": "src-open" }` etc.
3. To change SQL: edit `create_pipeline_data_model.py` → PUT data model spec (GET first to preserve IDs) → leave workbook formulas alone when possible.
4. Never reintroduce a single-row mega CTE that scans ACV metrics many times and fans out to every KPI.
5. Caps that matter for sane numbers:
   - Walk-in: `MAX(FCST)` per opp, `0–2e6`
   - Lost: `NETACV__C` `0–50k` (warehouse outliers)
   - Open FCST sanity: `0–5e6` for sourcing mixes

### Metric definitions (SoT)

| Concept | Definition |
| --- | --- |
| Open | `OPPORTUNITY_ACV_METRICS` · `METRIC_NAME = 'Forecasted Net ACV'` · `STAGE_GROUP = '2-7'` |
| Created | Same metric · `STAGE_2_ATTAINED = TRUE` · date filters on `STAGE_2_DATETIME` |
| Won / Lost / Lead Source | `BI_PRESENTATION.REPORT.VW_PIPELINE` |
| Walk-in | Snapshot `BI_STAGING.SNAPSHOT.VW_PIPELINE` on `2026-10-01` |
| Goals | Year `$94.6M`, Q4 `$26.7M` (hand-entry) |

### Plugins (true gaps only)

Org plugins are effectively **OnLoad-only** — no shipping pace/funnel plugins yet.

| Gap | Native MVP | Ideal |
| --- | --- | --- |
| Paced tick inside goal bar | 100% stacked Actual/Remain + text “X% paced” | Dual-marker bullet plugin |
| Tapered funnel | Horizontal stacked stage strip + legend | Funnel plugin |
| Snapshot diffs (pushed/pulled/size) | “—” placeholders until snapshot-diff SQL in **data model** | New DM table, then cards |

Label PLUGIN gaps in orange muted text; don’t fake them as done.

---

## Suggested work order for the design chat

1. Open stills side-by-side with workbook URL; screenshot Sigma pages for diff.
2. Restore **v4 chrome density** from `rebuild_pipeline_v4.py` layout helpers (`pace_strip`, section Cont nesting, movement card groups) **while keeping** `dm_source()` bindings from `rebuild_pipeline_fast.py`.
3. Fix pace strips: long-format Actual/Remain in **data model** (tiny SQL) or Sigma reshape — not a mega facts table.
4. Match ROTB section 01 card heights / 36px heroes / amber+teal highlight cards first (highest emotional gap).
5. Open Pipeline funnel + movement card chrome second.
6. Total / Sourcing / Movement / Created polish third.
7. Wire controls to real filters last.
8. Validate: workbook `sql` source count stays **0**; DM still has the lean SQL.

---

## Anti-patterns (user already rejected these)

- Stub / fake KPI numbers
- Generic Sigma KPI row with no section shells
- One giant custom SQL feeding everything
- SQL left inside the workbook after the data-model move
- Bare `<p>` text bodies
- Claiming “perfect” without still side-by-side
- Purple default / AI-slop dashboard aesthetics
- Building nav-only pages (ABM / Coverage / BI Top 100) before top 6 look right

---

## Quick verify commands

```bash
# Workbook has no SQL
python3 - <<'PY'
import json,os,urllib.request
set=os.environ
# after auth…
# GET workbook spec and count source kinds
PY

# Recreate DM if needed
python3 /Users/gabrielegjones/.cursor/zywave/scripts/create_pipeline_data_model.py

# Rebuild workbook UI (data-model sources)
python3 /Users/gabrielegjones/.cursor/zywave/scripts/rebuild_pipeline_fast.py
```

Expected inventory after a good PUT:

- Workbook: `data-model=7`, `sql=0`, `warehouse=0`
- Data model: 6 SQL + 1 warehouse (`src-pipe`)

---

## Companion docs

| Doc | Why |
| --- | --- |
| [`sigma-build-brief.md`](./sigma-build-brief.md) | Original build-now brief, auth, folder |
| [`replit-dashboard-replication-plan.md`](./replit-dashboard-replication-plan.md) | Per-page still maps + tokens |
| [`sigma-build-status.md`](./sigma-build-status.md) | Status log (update after your pass) |
| Skills | `~/.claude/skills/sigma-{api,workbooks,plugin-development}/` |

---

*Handoff written after perf rebuild + data-model migration. UI still needs a dedicated still-matching pass.*
