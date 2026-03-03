# PulseAnalytics

A real-time business analytics platform: two years of retail history, a
medallion warehouse, a Kimball star schema, a live event stream, eight
analytical models, five dashboards and a data-quality suite that can be shown to
fail.

**It runs on a laptop with no Docker, no broker and no cloud account.** Four
commands, about a minute, and everything below is live.

---

## Quick start

```bash
git clone <this-repo> && cd pulseanalytics
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python scripts/run_demo.py          # generate -> build -> analyse -> stream -> export
python -m streamlit run dashboards/streamlit/app.py
```

Or step by step:

```bash
python data-generator/generate_data.py --preset small   # 2 years of history
python -m etl.pipeline --full-refresh                   # bronze -> silver -> gold
python -m analytics.run_analytics                       # every model, one report
python -m streamlit run dashboards/streamlit/app.py     # http://localhost:8501
```

To watch the real-time page move:

```bash
# terminal 1
python -m streaming.producer.event_producer --rate 8 --duration 0
# terminal 2
python -m streaming.consumer.stream_consumer --duration 0
```

Check the state of everything at any point:

```bash
python scripts/healthcheck.py
```

---

## What it does

```
        BATCH                    REAL-TIME                  EXTERNAL API
   nightly OLTP extract     orders / payments / stock       FX rates (public,
   data/raw/*.csv           / clickstream events            degrades to fallback)
        │                          │                             │
        ▼                          ▼                             │
   csv_source.py            streaming/bus.py                     │
                     (NDJSON files → Kafka → Event Hubs,         │
                            one client, one env var)             │
        │                          │                             │
        └──────────────┬───────────┴─────────────────────────────┘
                       ▼
   ┌────────────────────────────────────────────────────────────────┐
   │ BRONZE  raw landing. Nothing rejected. Lineage on every row.    │
   │ SILVER  cleaned, de-duplicated, conformed. Repairs asserted.    │
   │ GOLD    star schema (7 dims + an SCD2 history, 5 facts)         │
   │         + 23 marts                                             │
   │ OPS     run log, 64 quality checks, streaming landing zone      │
   └────────────────────────────────────────────────────────────────┘
                       │
        ┌──────────────┼───────────────┬─────────────────┐
        ▼              ▼               ▼                 ▼
   Streamlit       FastAPI        Power BI          reports/*.md
   5 dashboards    /api/*         model as text     + CSV extracts
```

| | |
| --- | --- |
| **Data** | 2 years, deterministic from a seed. Growth, weekly and yearly seasonality, Black Friday, power-law repeat purchasing, customers who churn, payment failures with retries, stock simulated against real demand, and a controlled amount of dirty data. |
| **Warehouse** | Medallion layers, Kimball star, 23 marts. Runs unchanged on DuckDB and PostgreSQL — CI proves it on both. |
| **Analytics** | RFM, k-means segmentation, churn propensity, CLV (three ways), cohort retention, price/volume/mix, market basket, marketing attribution (five models), inventory optimisation, forecasting. All on numpy/pandas — no scikit-learn, so the maths is auditable. |
| **Real-time** | Four correlated topics, at-least-once delivery, event-time windows, rolling KPIs, a live dashboard and a query API. |
| **Quality** | 64 checks over 6 dimensions, with a test that proves the suite can fail. |
| **Ops** | Docker Compose, 223 tests, CI on every push, and OIDC deployment pipelines to Azure with approval gates and one-click rollback. |

---

## Six things worth looking at

### 1. One definition per metric — [`docs/kpi-definitions.md`](docs/kpi-definitions.md)

Every metric is defined once, in prose, then implemented once in SQL. The
dashboards, the API, the Python models and the DAX library all read that. Five
**reconciliation checks** assert the implementations agree:

```
SUM(fact_sales.net_amount)  ==  SUM(fact_orders.net_amount)
SUM(mart_sales_daily.revenue) == SUM(fact_orders.net_amount)
SUM(mart_customer_360.lifetime_revenue) == SUM(fact_orders.net_amount)
```

These catch the failure mode that matters: a **silently wrong number**, which is
invisible in a dashboard until someone acts on it.

### 2. The data-quality suite can be shown to fail

64 checks across completeness, validity, uniqueness, consistency, accuracy and
timeliness. Thresholds are non-zero where the source is *known* to be imperfect,
because a suite that cries wolf gets switched off.

And it is falsifiable — `test_the_suite_would_catch_a_real_defect` introduces a
genuine defect, asserts the suite goes red, then repairs it. Without that, a
passing suite proves nothing.

### 3. Reproducibility is structural

Every recency metric anchors to `gold.analysis_window.as_of_date` — the latest
date in the data — not the wall clock. The same dataset produces the same
segments today and in six months, so a screenshot, a test and a report always
agree. Switching to a live feed means pointing that one column at
`CURRENT_DATE`.

### 4. The local demo is an honest rehearsal of production

`pulse/db.py` is one facade over DuckDB and PostgreSQL. `streaming/bus.py` is
one facade over NDJSON files and Kafka. The SQL is written in the portable
subset both engines understand.

So the zero-install laptop demo, `docker compose up` (Postgres + Redpanda) and
the Azure deployment (Azure Database for PostgreSQL + Event Hubs) all run
**the same code** — only
environment variables change. CI builds the whole warehouse on PostgreSQL on
every push to prove the claim rather than assert it.

### 5. Limitations are stated where the number appears

Attribution is labelled **last-touch** on the dashboard, because that is the
limit of the source data — and the Marketing page shows the same revenue under
four other models, because the spread between them is the actual finding. The
incrementality figure says on screen that it cannot separate a campaign from a
seasonal upswing. Two payment success rates are published with distinct names,
because "success rate" is ambiguous and the ambiguity costs money.

### 6. The charts follow one design system

[`dashboards/streamlit/theme.py`](dashboards/streamlit/theme.py): a fixed
eight-slot CVD-safe categorical order that never cycles, single-hue sequential
ramps, reserved status colours, thin marks and hairline grids — and **no
dual-axis charts anywhere**, enforced by a test. Two y-scales whose alignment is
arbitrary is the fastest way to publish a chart that implies a correlation the
data does not contain.

The Power BI theme uses the same palette; a test fails if the two drift apart.

---

## Repository layout

```
pulseanalytics/
├── data-generator/     two years of realistic, deterministic history
├── pulse/              config, DB facade, KPI helpers - imported by everything
├── database/
│   ├── init/           schemas, bronze landing tables, ops metadata
│   ├── staging/        silver: cleaning, de-duplication, conforming
│   ├── warehouse/      star schema: 7 dimensions, 5 facts, indexes
│   └── analytics/      23 gold marts + reporting views
├── etl/
│   ├── extract/        CSV source + external FX API (degrades, never fails)
│   ├── load/           bronze loaders, idempotent
│   ├── transform/      runs the SQL, in order, with row accounting
│   ├── quality/        the check framework and the 64-check suite
│   ├── run_context.py  ops.pipeline_runs - what ran, how long, what broke
│   └── pipeline.py     the single entry point
├── streaming/
│   ├── bus.py          one interface: NDJSON files | Kafka | Event Hubs
│   ├── events.py       the shared envelope every topic uses
│   ├── producer/       four correlated simulated source systems
│   ├── consumer/       micro-batched, commits only after a successful write
│   └── processors/     rolling KPI windows + the FastAPI query surface
├── analytics/
│   ├── common/         cached gold readers + the model implementations
│   ├── customer/       segmentation, churn, CLV
│   ├── sales/          seasonality, price/volume/mix, market basket
│   ├── marketing/      five attribution models, campaign economics
│   ├── inventory/      safety stock, EOQ, ABC×XYZ
│   ├── forecasting/    Holt-Winters, backtested against a naive baseline
│   └── run_analytics.py  one command -> reports/insight_report.md
├── dashboards/
│   ├── streamlit/      5 pages + one design system
│   └── powerbi/        model, measures and theme as text (no .pbix in git)
├── tests/              222 tests against a real warehouse, not mocks
├── infrastructure/     Terraform: ADLS, Event Hubs, managed Postgres, ACR
├── scripts/            run_demo.py, healthcheck.py
└── docs/               architecture, data model, KPIs, quality, roadmap
```

---

## Running it other ways

### Against Postgres and a real Kafka API

```bash
docker compose up -d postgres redpanda console
export PULSE_DB_ENGINE=postgres PULSE_STREAM_BACKEND=kafka
pip install -r requirements-optional.txt
python -m etl.pipeline --full-refresh
```

Redpanda console at <http://localhost:8090>. The application code does not
change.

### The whole stack in containers

```bash
docker compose --profile app up -d
```

Dashboard <http://localhost:8501> · API <http://localhost:8000/docs> ·
Kafka console <http://localhost:8090>

### On Azure

Deployment is automated end to end — GitHub Actions to Azure over OIDC, with no
stored credentials:

```
push to main   →  build image  →  deploy dev  →  (approval)  →  promote to prod
```

One image is built and that **exact** image is promoted; prod never gets a
rebuild. Prod applies a *saved plan file* that a human approved, so what was
reviewed is what is applied. Rollback is the same pipeline with an older tag.

```bash
./scripts/bootstrap_azure.sh dev your-org/pulseanalytics   # one-time OIDC setup
# then: Actions → Deploy infrastructure → environment: dev, apply: ticked
```

The runbook, permissions model and cost table are in
[`docs/deployment.md`](docs/deployment.md); the infrastructure design is in
[`infrastructure/terraform/README.md`](infrastructure/terraform/README.md).
Roughly **£40/month** for dev (burstable Postgres, Container Apps that scale to
zero) — a deployment guide that does not say what it costs is incomplete.

### Bigger data

```bash
python data-generator/generate_data.py --preset medium   # 60k orders, ~1 min
python data-generator/generate_data.py --preset large    # 250k orders
```

---

## Tests

```bash
python -m pytest              # ~45 seconds
```

222 tests, run against a **real warehouse built from a real generated dataset**
in a temporary DuckDB file — not against mocks. That costs a minute and buys
tests that actually exercise the SQL, which is where the logic lives. A mocked
test of a data pipeline verifies the mock.

What they cover, beyond the obvious:

- the generator is byte-for-byte deterministic for a seed
- the injected defects really exist, so the quality layer is not theatre
- the star schema neither drops nor duplicates orders
- the funnel is monotonically decreasing
- the churn model's features predate its labels (no future leakage)
- every attribution model credits the same total revenue
- the consumer commits offsets only after a successful write
- KPI windows use event time, so a replayed stream reproduces its own results
- no dashboard page creates a secondary y-axis
- the Power BI theme has not drifted from the Streamlit palette

---

## Configuration

Everything has a working default; `.env` is optional. See
[`.env.example`](.env.example).

| Variable | Default | Effect |
| --- | --- | --- |
| `PULSE_DB_ENGINE` | `duckdb` | `duckdb` (zero install) or `postgres` |
| `PULSE_STREAM_BACKEND` | `local` | `local` (NDJSON files) or `kafka` |
| `PULSE_SEED` | `20240101` | changes the dataset; same seed, same bytes |
| `PULSE_END_DATE` | `2025-12-31` | the last day of history (two years back from here) |
| `PULSE_CHURN_WINDOW_DAYS` | `90` | days without an order before a customer is churned |

---

## Documentation

| | |
| --- | --- |
| [architecture.md](docs/architecture.md) | the decisions, the trade-offs, and what is deliberately absent |
| [data-model.md](docs/data-model.md) | layers, the star, why two order grains, what silver repairs |
| [kpi-definitions.md](docs/kpi-definitions.md) | **the contract** — every metric, with its judgement calls stated |
| [data-quality.md](docs/data-quality.md) | the framework, the six dimensions, why thresholds are not zero |
| [two-year-roadmap.md](docs/two-year-roadmap.md) | what a two-person team built quarter by quarter, and the mistakes |
| [deployment.md](docs/deployment.md) | the deployment pipelines: bootstrap, promotion, rollback, permissions, cost |

### Formal documents (PDF)

| | |
| --- | --- |
| **[PulseAnalytics-Architecture.pdf](docs/PulseAnalytics-Architecture.pdf)** | Software Architecture Document — 38 pages, 15 UML diagrams. Project description, quality-attribute scenarios, container/component/logical/data/process/deployment views, 18 architecture decisions with their costs, and a verification matrix. |
| **[PulseAnalytics-BRD.pdf](docs/PulseAnalytics-BRD.pdf)** | Business Requirements Document — 38 pages, 7 diagrams. Objectives, stakeholders, scope, UML use cases, 12 business and 38 functional requirements, 17 NFRs, acceptance criteria and a full traceability matrix. |

Both are rebuilt from text sources with `cd docs/build && npm install && npm run build`.
Diagrams are UML — class, sequence, state, activity, ER and use case — with the
component, deployment and use case diagrams hand-authored in SVG because Mermaid
has no notation for provided/required interfaces, 3D nodes or actors.

---

## What this is not

Stated plainly, because a portfolio project that pretends to be complete is less
credible than one that knows its edges:

- **Not orchestrated.** `etl/pipeline.py` is a linear DAG of six stages. Dagster
  or Databricks Jobs would earn their place in production; the stage boundaries
  and `ops.pipeline_runs` are already shaped so adding one is a wrapper.
- **Not incremental.** Every run is a full rebuild — eleven seconds on the demo
  dataset. `ops.load_watermarks` exists for when that stops being true.
- **No real SCD Type 2.** `dim_customer_history` has the Type 2 shape and one
  version per customer, because the source ships no change history.
- **No alerting.** Terraform creates the action group; nothing routes to it,
  because routing to a rota that does not exist is worse than not alerting.
- **No `.pbix` in git.** A binary that cannot be diffed or merged does not belong
  in version control. The model is here as text instead.
- **The incrementality number is a proxy.** It cannot separate a campaign from a
  seasonal upswing. A real answer needs a geo holdout, which the source data does
  not support — and the dashboard says so.
