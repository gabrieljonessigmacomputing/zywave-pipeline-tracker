# Sigma plugins

Two single-file, vanilla-JS Sigma plugins (no build step). Each loads `@sigmacomputing/plugin` from unpkg.

## Hosting (GitHub Pages)

Register these URLs in Sigma (Administration → Account → Custom plugins):

- pace-bullet: https://gabrieljonessigmacomputing.github.io/zywave-pipeline-tracker/plugins/pace-bullet/
- stage-funnel: https://gabrieljonessigmacomputing.github.io/zywave-pipeline-tracker/plugins/stage-funnel/

Both show demo data until a source element is bound.

## pace-bullet

Goal pace bar: gray track, orange fill (actual / goal, clamped 0-100%), dark tick at the paced %.
The first row of the bound element is used (bind a single-row KPI/table).

| Setting | Type | Notes |
| --- | --- | --- |
| `source` | element | Table/pivot/KPI source |
| `actual` | number column | Big value and fill numerator |
| `goal` | number column | Fill denominator, "Target: $X" |
| `pacedPct` | number column | Tick position. 0-1 or 0-100 (auto-detected: values <= 1 are fractions) |
| `elapsedPct` | number column, optional | Used for the tick if `pacedPct` is unbound |
| `title` | text, optional | Small label above the value |
| `valueFormat` | text, optional | Hint like `$,.2s` (default) or `$,.0f` |
| `fillColor` / `tickColor` | text, optional | CSS colors, defaults `#f97316` / `#334155` |

## stage-funnel

Tapered funnel, one segment per row, colored `#38bdf8, #3b82f6, #6366f1, #a855f7, #db2777, #f9a8d4` (designed for stages 2-7).
Labels show stage name and money (`$,.2s`).

| Setting | Type | Notes |
| --- | --- | --- |
| `source` | element | Grouped table/pivot with one row per stage |
| `stage` | text column | Stage name |
| `acv` | number column | Segment size (ACV) |
| `order` | column, optional | Sort key; if unbound, sorts by stage name |

Tip: filter the source to stages 2-7 so the six palette colors map one-to-one.
