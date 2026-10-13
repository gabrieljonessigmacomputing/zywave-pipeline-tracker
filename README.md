# Zywave Pipeline Tracker FY2026

Sigma rebuild of Zywave’s Replit **Pipeline Tracker** (ROTB + top 6 pages): layered data model, still-matched workbook, and custom plugins.

## Live

| Artifact | URL |
| --- | --- |
| Workbook | https://app.sigmacomputing.com/zywave/workbook/46Enwkdr17UMrr2Tm9qdWt |
| Data model | https://app.sigmacomputing.com/zywave/data-model/e9511cff-4ab8-48c4-96e0-fbf2b3b96f10 |
| Folder | https://app.sigmacomputing.com/zywave/f/5EFLG4WW7cjvngI0kCudpF |

## Why this architecture

Previous attempts put a mega custom-SQL “facts” CTE (or a full `VW_PIPELINE` bind) under every KPI. That made lineage unreadable and load times molasses.

**Now:**

1. **Data model** owns all SQL — tiny 1-row KPI tables + small chart grains (no full-history warehouse bind).
2. **Workbook** has **zero** SQL / warehouse sources — only `data-model` bindings named `WB *` → `KPI/Chart/Dim *`.
3. **Plugins** for Replit pace tick + tapered funnel (GitHub Pages).

```
Snowflake
  ├─ OPPORTUNITY_ACV_METRICS → KPI Open / Created / Funnel / charts
  ├─ VW_PIPELINE (filtered)  → KPI Closed Q4 / Sourcing / Segment
  └─ SNAPSHOT.VW_PIPELINE    → Walk-in / Snapshot trend
         ↓
  Data model (14 elements, layered pages)
         ↓
  Workbook WB* passthroughs → KPIs / charts
```

## Plugins (register in Sigma)

Admin → Account → Plugins → add URL:

| Plugin | URL |
| --- | --- |
| Pace bullet | https://gabrieljonessigmacomputing.github.io/zywave-pipeline-tracker/plugins/pace-bullet/ |
| Stage funnel | https://gabrieljonessigmacomputing.github.io/zywave-pipeline-tracker/plugins/stage-funnel/ |

See [`plugins/README.md`](./plugins/README.md) for column binds.

## Scripts

```bash
set -a; source ~/.zywave/sigma-zywave.env; set +a
export SIGMA_BASE_URL="$ZYWAVE_BASE_URL"
export SIGMA_CLIENT_ID="$ZYWAVE_CLIENT_ID"
export SIGMA_CLIENT_SECRET="$ZYWAVE_CLIENT_SECRET"
eval "$(bash ~/.claude/skills/sigma-api/scripts/get-token.sh)"

python3 scripts/build_data_model.py   # create/update layered DM
python3 scripts/build_workbook.py     # PUT workbook (DM sources only)
```

## Skills used

- `~/.claude/skills/sigma-api`
- `~/.claude/skills/sigma-workbooks` (+ `from-image` workflow)
- `~/.claude/skills/sigma-plugin-development` / `sigma-plugin-patterns`

Auth: Zywave-only vars in `~/.zywave/sigma-zywave.env` (never other Sigma orgs).

## Performance (v3 — current)

ROTB KPIs load from **one** Snowflake query: `KPI ROTB Pack` (open + created + walk-in + closed + sourcing in a single statement).

Workbook: `sql=0`, `data-model=10`. Charts are separate small GROUP BYs (only hit when those pages need them).

Rebuild:
```bash
python3 scripts/build_data_model_fast.py
python3 scripts/build_workbook_v3.py
```
