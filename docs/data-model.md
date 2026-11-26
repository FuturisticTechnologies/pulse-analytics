# Data model

## Layers

| Schema | Grain | Rules |
| --- | --- | --- |
| `bronze` | as the source sent it | no NOT NULL, no keys, wide types. Nothing is ever rejected. |
| `silver` | one row per business entity | trimmed, typed, de-duplicated, conformed. Repairs are flagged, not hidden. |
| `gold` | star schema + marts | what everything queries. One definition per metric. |
| `ops` | platform metadata | run log, quality results, streaming landing zone. Append-only. |

## The star

```
                          gold.dim_date
                                │
        ┌────────────┬──────────┼──────────┬─────────────┐
        │            │          │          │             │
 dim_customer   dim_product  dim_store  dim_region  dim_campaign
        │            │          │          │             │
        └────────────┴────┬─────┴──────────┴─────────────┘
                          │
        ┌─────────────┬───┴────────┬───────────────┬──────────────────┐
        ▼             ▼            ▼               ▼                  ▼
   fact_sales    fact_orders  fact_payments  fact_inventory  fact_customer_events
   (order line)  (order)      (attempt)      (product-week)  (event)
                                   │
                          dim_payment_method
```

### Dimensions

| Table | Rows | Natural key | Notes |
| --- | --- | --- | --- |
| `dim_date` | 2 192 | `date_value` | 2022-01-01 → 2027-12-31. Generated in SQL so the warehouse rebuilds from the database alone. Carries `is_peak_season`, `is_black_friday_window`. |
| `dim_customer` | customers + 1 | `customer_id` | Type 1. Demographics, acquisition channel, loyalty tier. |
| `dim_customer_history` | one per version | `customer_id` + `valid_from` | **Type 2**, for "revenue by the tier held at purchase time". |
| `dim_product` | products + 1 | `product_id` | Category hierarchy, unit economics, price band. |
| `dim_store` | stores + 1 | `store_id` | Physical and online; `is_digital` gates floor-space metrics. |
| `dim_region` | regions + 1 | `region_id` | Rolls up to `super_region` (Americas / EMEA / APAC). |
| `dim_campaign` | campaigns + 1 | `campaign_id` | The `-1` member is `'No Campaign'`, which is a real business state. |
| `dim_payment_method` | methods | `payment_method` | Rolls up to `method_family` (Card / Wallet / Bank). |

The `+ 1` is the Unknown member on key `-1`. It exists so facts can join
inner-style without ever dropping a row, and so a broken join shows up as a
countable number instead of a silent shortfall.

### Facts

| Table | Grain | Additivity | Key measures |
| --- | --- | --- | --- |
| `fact_sales` | order **line** | fully additive | `quantity`, `net_amount`, `cost_amount`, `gross_profit` |
| `fact_orders` | order **header** | fully additive | `net_amount`, `shipping_amount`, `tax_amount`, `item_count`, `customer_order_seq`, `days_since_prev_order` |
| `fact_payments` | payment **attempt** | fully additive | `amount`, `attempt_number`, `seconds_after_order` |
| `fact_inventory` | product × **week** | **semi-additive** | `on_hand_units`, `days_of_cover`, `estimated_lost_revenue` |
| `fact_customer_events` | one **event** | fully additive | `duration_seconds`, `funnel_step` |

## Three modelling decisions worth defending

### Why two grains for orders

`fact_sales` is the atomic fact and everything aggregates from it. But
order-level measures — average order value, basket size, shipping, tax — cannot
be summed from the line fact without double-counting, and *averaging* the line
fact answers a different question entirely (average line value, which is
materially smaller than AOV).

A separate header fact is the standard Kimball answer. It keeps both grains
honest and makes the error impossible rather than merely discouraged.

The quality suite asserts they agree on the one measure they share:

```sql
SUM(fact_sales.net_amount)  ==  SUM(fact_orders.net_amount)   -- where is_revenue
```

### Why inventory is semi-additive, and why that is structural

`on_hand_units` sums across products but **not** across dates. Summing a
periodic-snapshot fact over time reports stock the business never held — the
single most common inventory-reporting bug.

Prevention, at three levels:

1. `gold.mart_inventory_health` reads only the latest snapshot per product, so
   the mart cannot express the wrong number;
2. a test asserts the mart has exactly one row per product;
3. the DAX measure uses `LASTDATE(dim_date[date_value])`, and `model.md` says
   why.

### Why flags instead of filters

Cancelled and returned orders stay in the facts, flagged `is_revenue`,
`is_cancelled`, `is_returned`. Revenue excludes them by flag, never by deletion.

Deleting them would make the revenue query simpler and make operations blind:
cancellation rate, return rate and the reasons behind them all need those rows.
Orphan clickstream customers are treated the same way — the event is kept, the
broken key is nulled, and `is_orphan_customer` is set. Deleting the event would
quietly understate traffic.

## What silver repairs

Every one of these is a real defect the generator injects on purpose, and every
repair is asserted by a check in `etl/quality/suite.py`:

| Defect in bronze | Repair in silver | Assertion |
| --- | --- | --- |
| The source replays some orders verbatim | de-duplicate on `order_id`, keep one | `silver.orders.order_id` is unique |
| Returns integration emits negative quantities | absolute value, recompute money columns from first principles | no `quantity <= 0` survives |
| Loyalty tier arrives as `'GOLD  '`, `'gold'`, `'Gold'` | map to one canonical label | tier is in the accepted set |
| Clickstream contains customer ids that never existed | null the key, set `is_orphan_customer` | zero dangling `customer_id` |
| Some customers have no email | keep the customer, set `is_missing_email` | warning at a 2% threshold |

Note what is *not* repaired: the missing emails. A null email is a marketing
problem, not a reason to lose the revenue attached to that customer. It is
flagged, counted, and reported — which is the honest treatment.

## Marts

26 tables in `database/analytics/`, grouped by the audience that reads them:

| Domain | Marts |
| --- | --- |
| Sales | `mart_sales_daily`, `mart_sales_monthly`, `mart_product_performance`, `mart_category_performance` |
| Customer | `mart_customer_360`, `mart_rfm_segments`, `mart_rfm_summary`, `mart_cohort_retention`, `mart_retention_summary`, `mart_churn_monthly` |
| Marketing | `mart_campaign_performance`, `mart_channel_performance`, `mart_acquisition_channel` |
| Regional | `mart_regional_performance`, `mart_store_performance`, `mart_revenue_local` |
| Inventory | `mart_inventory_health`, `mart_inventory_weekly` |
| Behaviour | `mart_conversion_funnel`, `mart_funnel_by_device` |
| Payments | `mart_payment_health`, `mart_payment_failures`, `mart_payment_gateway_success` |
| Fulfilment | `mart_order_exceptions`, `mart_order_exceptions_monthly` |
| Executive | `mart_executive_kpis` (exactly one row) |

Plus `gold.analysis_window` — one row defining the platform's "today".

## Build order

Enforced by filename prefix within each layer, and by layer order in
`pulse/sql.py`:

```
init       001_schemas  →  002_bronze_tables  →  003_ops_tables
staging    010_reference → 011_customers → 012_orders → 013_payments
           → 014_inventory → 015_events → 016_fx
warehouse  020_dim_date → 021_dimensions → 022_fact_sales → 023_fact_payments
           → 024_fact_inventory → 025_fact_events → 026_indexes
analytics  030_analysis_window → 031..043 marts and views
```

`012_silver_orders.sql` builds `order_items` before `orders`, because the order
header's money columns are recomputed from its lines rather than trusted from
the source.

## Portability

The SQL uses only what DuckDB and PostgreSQL both understand:

- `DROP TABLE IF EXISTS` + `CREATE TABLE AS SELECT` (Postgres has no
  `CREATE OR REPLACE TABLE`)
- `FILTER (WHERE ...)`, `DATE_TRUNC`, `EXTRACT`, window functions, `NTILE`
- date arithmetic as `date - date` (integer days in both engines)
- `generate_series(DATE, DATE, INTERVAL)` returning timestamps, cast to `DATE`

`Database._adapt` handles the few remaining differences (`DOUBLE PRECISION`,
`TIMESTAMP WITHOUT TIME ZONE`, `epoch_ms`). Everything else is one dialect.
