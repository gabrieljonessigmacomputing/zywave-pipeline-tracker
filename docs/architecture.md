# Data architecture

## Lineage (readable)

```
KPI chart / viz
  → WB <Name>          (workbook table, passthrough)
    → <KPI|Chart|Dim>  (data model element)
      → Custom SQL or filtered extract
        → Snowflake table
```

Workbook never contains `source.kind: sql` or `warehouse-table`.

## Perf rules

1. Prefer **1-row KPI SQL** over row-level facts + SumIf in Sigma.
2. Never bind full `VW_PIPELINE` into the workbook.
3. Chart grains are pre-aggregated GROUP BYs (funnel ~6 rows, months ~20, etc.).
4. Caps: walk-in FCST ≤ $2M/opp; lost NETACV ≤ $50k; sourcing FCST ≤ $5M.

## Rebuild

See repo README. Auth via `~/.zywave/sigma-zywave.env` only.
