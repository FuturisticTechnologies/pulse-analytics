# Architecture

## The shape of it

```
        BATCH                    REAL-TIME                  EXTERNAL API
   OLTP nightly extract     order / payment / stock       FX rates (public)
   data/raw/*.csv           / clickstream events          etl/extract/api_source.py
        │                          │                             │
        ▼                          ▼                             │
  etl/extract/csv_source     streaming/producer                  │
        │                          │                             │
        │                    streaming/bus.py                    │
        │                  (files locally, Kafka in docker,      │
        │                   Event Hubs on Azure - one client)    │
        │                          │                             │
        │                    streaming/consumer                  │
        │                          │                             │
        ▼                          ▼                             ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │  BRONZE   raw landing. Nothing rejected, nothing dropped.        │
  │           Lineage stamped on every row (_loaded_at, _source).    │
  └──────────────────────────────────────────────────────────────────┘
        │                                              ops.stream_events
        ▼                                                      │
  ┌──────────────────────────────────────────────────────────────────┐
  │  SILVER   cleaned, typed, de-duplicated, conformed.              │
  │           Every repair is asserted by the quality suite.         │
  └──────────────────────────────────────────────────────────────────┘
        │
        ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │  GOLD     Kimball star: 7 conformed dims (+ an SCD2 customer     │
  │           history) and 5 facts at 3 grains                       │
  │           + 23 pre-aggregated marts                              │
  └──────────────────────────────────────────────────────────────────┘
        │                          │                        │
        ▼                          ▼                        ▼
   Streamlit               FastAPI (/api/*)            Power BI
   5 dashboards            real-time + curated         same model, same palette
                                                       (dashboards/powerbi/)

  Running alongside everything:
    ops.pipeline_runs         what ran, how long, how many rows, what broke
    ops.data_quality_results  64 checks across 6 dimensions, every run
```

## The decisions, and why

### Medallion, not a single transformation step

Three layers cost more SQL than one. What they buy:

- **Bronze never rejects a row.** If the source system sends garbage, it lands
  and gets *counted*, rather than vanishing into a filter nobody remembers
  writing. Every quality question about the source is answerable.
- **Silver is where repairs happen, and they are asserted.** The source ships
  duplicate orders, negative quantities and orphan foreign keys. Silver fixes
  each one, and `etl/quality/suite.py` asserts the fix worked — so "we clean the
  data" is a tested claim, not a comment.
- **Gold is what anyone queries.** By the time a dashboard reads a number, every
  cleaning decision is upstream and visible.

The alternative — one big transformation — makes "why is this number wrong"
a question with no isolated answer.

### Transformations in SQL, models in Python

The split is not stylistic:

| | Owns | Because |
| --- | --- | --- |
| **SQL** (`database/`) | aggregation, joins, every business *definition* | it is what the warehouse actually executes, it runs unchanged on DuckDB / Postgres / Synapse / Databricks SQL, and an analyst who does not write Python can still read and fix it |
| **Python** (`analytics/`) | k-means, churn scoring, forecasting, basket affinity, inventory optimisation | these need iteration, linear algebra or optimisation that SQL expresses badly or not at all |

If two people could disagree about what a number *means*, it is defined once, in
SQL, and everything reads that. The Python models consume gold marts through
`analytics/common/datasets.py` — so an analysis is provably reading the same
revenue figure as the dashboard.

### One codebase across four backends

`pulse/db.py` is a thin facade over DuckDB and PostgreSQL; `streaming/bus.py` is
a thin facade over newline-delimited files and Kafka. The SQL in `database/` is
written in the portable subset both engines understand.

The result: the local demo needs no Docker and no broker, and it is still a
faithful rehearsal of the production path. `docker compose up` swaps in real
Postgres and a real Kafka API; Terraform swaps in Azure Database for
PostgreSQL and Event Hubs. The
application code is identical in all three.

The cost is a handful of dialect translations in `Database._adapt` and a
discipline about which SQL features to use. That is a much smaller price than
maintaining two implementations, which is what "we'll build the real one later"
always becomes.

### Kimball star schema, with surrogate keys

Five facts at three grains:

| Fact | Grain | Type |
| --- | --- | --- |
| `fact_sales` | one order **line** | transaction |
| `fact_orders` | one order **header** | transaction |
| `fact_payments` | one payment **attempt** | transaction |
| `fact_inventory` | one product, one **week** | periodic snapshot |
| `fact_customer_events` | one clickstream **event** | transaction |

Two grains for orders looks redundant until you compute average order value:
averaging the line fact answers a different question and gives a materially
smaller number. Keeping both grains explicit is the standard Kimball answer and
prevents that class of error structurally.

Every dimension carries an **Unknown member** (`key = -1`), so facts join
inner-style and no row is ever silently dropped from a visual. A fact row
legitimately pointing at `-1` (an order with no campaign) is data. A *sales* row
pointing at `-1` is a broken join, and the quality suite fails the run for it.

### The analysis anchor

Every recency-based metric — RFM, churn, active customers, trailing windows —
anchors to `gold.analysis_window.as_of_date`, which is the latest date present
in the data, **not** the wall clock.

That single decision is what makes the platform reproducible: the same dataset
produces the same segments today and in six months, so a screenshot, a test and
a report all agree. Switching to a live feed means pointing `as_of_date` at
`CURRENT_DATE` and changing nothing else.

### Streaming lands in a table

The consumer writes `ops.stream_events` and recomputes a rolling window into
`ops.realtime_kpis`. It owns no metric definitions of its own.

Three reasons the state is in a table rather than in the consumer's memory:

1. the dashboard, the API and the consumer are three separate processes;
2. restarting the consumer must not blank the dashboard;
3. keeping the window's history lets the live page draw a trend, which is the
   difference between a number and a signal.

Windows are measured in **event time**, not wall-clock time, so a replayed
stream reproduces exactly the KPIs it produced live.

### Ops tables survive a full refresh

`ops.*` uses `CREATE TABLE IF NOT EXISTS` while bronze uses `DROP`+`CREATE`.
A run log that does not outlive the run is not a run log — and dropping
`ops.stream_events` on every batch build would mean a batch job silently
destroying the real-time layer. That coupling is the kind of thing that causes a
3am page, so it is prevented in the DDL rather than by convention.

## Failure behaviour

| Failure | What happens |
| --- | --- |
| FX API unreachable | deterministic fallback rates, every row stamped `source='fallback'`, pipeline stays green |
| A quality check's SQL is broken | recorded as a failed check; the other 63 still run |
| A quality **error** check fails | `--fail-on-error` exits **2** (data is bad), distinct from **1** (code broke) |
| A pipeline stage throws | recorded in `ops.pipeline_runs` with the message; later stages skipped |
| Consumer crashes mid-batch | offset not committed → events re-delivered (at-least-once); `event_id` supports downstream de-duplication |
| Warehouse not built | dashboards render the two commands that fix it, not a stack trace |
| Source grows a column | ignored with a warning |
| Source **loses** a column | load fails loudly |

## What this deliberately is not

- **Not orchestrated by Airflow.** `etl/pipeline.py` is a linear DAG of six
  stages. Airflow, Dagster or a Databricks Job would each add real value in
  production, and would add a service to run and explain here. The stage
  boundaries and `ops.pipeline_runs` are already shaped so that dropping any of
  them in is a wrapper, not a rewrite.
- **Not incremental.** Every run is a full rebuild. At this data volume a full
  rebuild takes eleven seconds, and incremental loading buys complexity nothing
  currently needs. `ops.load_watermarks` exists for when it does.
- **Not a `.pbix` in git.** A binary that cannot be diffed or merged does not
  belong in version control. `dashboards/powerbi/` holds the model as text:
  relationships, measures, theme.

Deeper detail: [data-model.md](data-model.md) ·
[kpi-definitions.md](kpi-definitions.md) · [data-quality.md](data-quality.md) ·
[two-year-roadmap.md](two-year-roadmap.md)
