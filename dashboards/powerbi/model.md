# Power BI semantic model

The warehouse is a star schema, so the Power BI model is a direct import of it
rather than a reshaping. Everything below is what a modeller has to set by hand
after loading the tables, because it is not carried by the files.

## Loading

Two supported paths, both reading the *same* gold layer:

| Path | When | How |
| --- | --- | --- |
| **Direct to Postgres** | the docker stack is up; a live report | Get Data → PostgreSQL → `localhost:5432`, database `pulse`, schema `gold` |
| **Folder of files** | reviewing without a database; the Azure/ADLS shape | `python dashboards/powerbi/export_for_powerbi.py` then Get Data → Folder |

Use **Import** storage mode, not DirectQuery. The gold layer is already
aggregated and fits comfortably in memory; DirectQuery would push a query to the
warehouse on every slicer click and lose the time-intelligence functions that
depend on a marked date table.

## Relationships

All one-to-many, single direction, from the dimension to the fact. Single
direction on purpose: bi-directional filtering on a star with five facts creates
ambiguous filter paths, and the resulting numbers are wrong in ways that are very
hard to find.

| From (1) | To (many) | Key | Active |
| --- | --- | --- | --- |
| `dim_date[date_key]` | `fact_orders[order_date_key]` | date | yes |
| `dim_date[date_key]` | `fact_sales[order_date_key]` | date | yes |
| `dim_date[date_key]` | `fact_payments[payment_date_key]` | date | yes |
| `dim_date[date_key]` | `fact_inventory[snapshot_date_key]` | date | yes |
| `dim_date[date_key]` | `fact_customer_events[event_date_key]` | date | yes |
| `dim_customer[customer_key]` | `fact_orders[customer_key]` | surrogate | yes |
| `dim_customer[customer_key]` | `fact_sales[customer_key]` | surrogate | yes |
| `dim_customer[customer_key]` | `fact_customer_events[customer_key]` | surrogate | yes |
| `dim_customer[customer_key]` | `mart_customer_360[customer_key]` | surrogate | yes |
| `dim_product[product_key]` | `fact_sales[product_key]` | surrogate | yes |
| `dim_product[product_key]` | `fact_inventory[product_key]` | surrogate | yes |
| `dim_store[store_key]` | `fact_orders[store_key]` | surrogate | yes |
| `dim_region[region_key]` | `fact_orders[region_key]` | surrogate | yes |
| `dim_campaign[campaign_key]` | `fact_orders[campaign_key]` | surrogate | yes |
| `dim_payment_method[payment_method_key]` | `fact_payments[payment_method_key]` | surrogate | yes |

**Mark `dim_date` as a date table** on `date_value`. Without that, `TOTALYTD`,
`SAMEPERIODLASTYEAR` and `DATESINPERIOD` silently return wrong results rather
than erroring — the most expensive five-second omission in Power BI.

Every dimension carries an **Unknown member** with key `-1`. That is why every
relationship can stay an inner-style single-direction join and no fact row is
ever dropped from a visual. A fact row legitimately pointing at `-1` (for example
an order with no campaign) is data, not a failure; a *sales* row pointing at
`-1` is a broken join, and the data-quality suite fails the run for it.

## Tables to hide from the report view

Hide the raw key columns so a report author cannot accidentally drag a surrogate
key onto a visual:

- every `*_key` column on every fact,
- `dim_date[date_key]`,
- the `_loaded_at` / `_source_file` lineage columns if they were imported.

## Aggregation defaults

Set **"Do not summarize"** on: all `*_key` columns, `dim_date[year_number]`,
`dim_date[month_number]`, `dim_customer[customer_id]`, `dim_product[product_id]`,
and every `*_pct` column. Power BI defaults numeric columns to Sum, and a summed
percentage is the classic dashboard embarrassment.

Sort `dim_date[month_short]` by `dim_date[month_number]`, and
`dim_date[day_short]` by `dim_date[day_of_week]`, or the axes come out
alphabetically.

## Report pages

Mirroring the Streamlit app one-for-one, so the two never drift:

| Page | Visuals |
| --- | --- |
| **Executive** | six KPI cards; revenue line with 7-day average; monthly column; region bar; category bar |
| **Sales** | trend with granularity slicer; YoY indexed line; revenue waterfall (volume/price/mix); weekday and month index columns; product table |
| **Customers** | RFM segment bars (share of customers vs share of revenue); cohort retention matrix with a single-hue conditional format; LTV curves; churn risk table |
| **Marketing** | profit ROAS bar with a break-even line; spend vs revenue clustered column; campaign scatter with a break-even diagonal; attribution comparison |
| **Operations** | payment failure rate line; failure reason table; stock status bar; funnel; pipeline and data-quality tables |

## Theme

Apply `theme.json` (View → Themes → Browse for themes). It carries the same
eight-slot categorical order, the same single-hue sequential ramp and the same
reserved status colours as the Streamlit app, so a chart looks identical in both
tools.

Two rules the theme cannot enforce, so enforce them by hand:

1. **Never use the secondary y-axis.** Power BI makes it one checkbox away, and
   it is the fastest way to publish a chart that implies a correlation the data
   does not contain. Two units → two visuals, or index both to 100.
2. **Never let a colour ramp encode the same thing the bar length already
   encodes.** One series is one colour. A value ramp on nominal categories burns
   the only free channel on information already on screen.

## Refresh

| Source | Schedule | Notes |
| --- | --- | --- |
| Postgres (direct) | after the nightly batch run | the pipeline writes `ops.pipeline_runs`; gate the refresh on the last run being `success` |
| Folder export | after `export_for_powerbi.py` | run it as the final step of the batch job |

The real-time page is deliberately **not** in Power BI. Sub-minute latency wants
a push dataset or the Streamlit page reading `ops.stream_events` directly; a
scheduled import refresh cannot deliver it, and pretending otherwise produces a
"live" dashboard that is fifteen minutes stale.
