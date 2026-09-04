# Power BI

This folder holds everything needed to build the Power BI report against the
PulseAnalytics warehouse. There is deliberately **no `.pbix` in the repository**:
a binary that cannot be diffed, reviewed or merged does not belong in version
control, and one that is three commits stale is worse than none. What is here
instead is the whole model as text.

| File | What it is |
| --- | --- |
| `model.md` | relationships, storage mode, aggregation defaults, page layout |
| `measures.dax` | the full measure library, matching `docs/kpi-definitions.md` |
| `theme.json` | the report theme - same palette as the Streamlit app |
| `export_for_powerbi.py` | writes the gold layer to parquet/csv for a file-based import |

## Build it in five steps

1. **Have a warehouse.**

   ```bash
   python data-generator/generate_data.py --preset medium
   python -m etl.pipeline --full-refresh
   ```

2. **Point Power BI at the data.** Either connect to Postgres (`docker compose
   up -d postgres`, then Get Data → PostgreSQL → `localhost:5432` → `pulse` →
   schema `gold`), or export files:

   ```bash
   python dashboards/powerbi/export_for_powerbi.py
   # Power BI Desktop -> Get Data -> Folder -> data/exports/powerbi
   ```

3. **Set up the model** exactly as `model.md` describes - the relationships, and
   in particular **marking `dim_date` as the date table**. Time intelligence
   returns silently wrong numbers without it.

4. **Paste in the measures.** New table → name it `Measures` → add each measure
   from `measures.dax`.

5. **Apply the theme.** View → Themes → Browse → `theme.json`.

## Why the measures aggregate facts, not marts

`gold.mart_sales_daily` already contains daily revenue, and a card bound to it
would be simpler. It would also be wrong the moment someone adds a region
slicer, because the mart has no region column - the visual would silently ignore
the slicer and show the company total.

So the measures aggregate `fact_orders` and `fact_sales`, which carry every
dimension key, and the marts are used for the things that genuinely cannot be
recomputed in a filter context: cohort grids, RFM segments, ABC classes.

## Keeping DAX and SQL honest

Every measure here has a SQL counterpart in `database/analytics/`, and both
implement a definition written down once in `docs/kpi-definitions.md`. When a
definition changes, all three change together. The reconciliation checks in
`etl/quality/suite.py` verify the SQL side (`line revenue reconciles to order
revenue`, `daily mart reconciles to fact_orders`); the DAX side is verified by
comparing a card against the same figure on the Streamlit executive page, which
is the manual step this repository does not automate.
