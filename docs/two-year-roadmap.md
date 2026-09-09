# Two years of PulseAnalytics

What a two-person data team built, in the order they built it, and why.

The team is two people who overlap heavily but lean in different directions:

- **the platform lead** — ingestion, warehouse, streaming, infrastructure, CI
- **the analytics lead** — modelling, metric definitions, dashboards, the
  stakeholder relationship

Neither works alone. The most useful thing in this document is not the list of
features; it is the sequence, and the things that were deliberately *not* built
at each point.

---

## Year 1 — make the numbers exist and make them trusted

### Q1 2024 · Get one number right

**Problem.** Every team quoted a different revenue figure. Finance exported from
the OLTP database, marketing pulled from the ad platforms, the board deck was
assembled by hand in a spreadsheet each month.

**Shipped**

- Nightly CSV extract from the OLTP database into a bronze landing zone
  (`etl/extract/csv_source.py`, `database/init/002_bronze_tables.sql`).
- Silver layer with the first real repairs: de-duplicating replayed orders,
  fixing negative quantities, canonicalising loyalty tier.
- `gold.fact_orders`, `gold.dim_date`, `gold.dim_customer`, and one mart:
  `mart_sales_daily`.
- **One definition of revenue**, written down in `docs/kpi-definitions.md`
  before any dashboard was built.

**The decision that mattered.** Bronze rejects nothing. The first instinct was
to filter bad rows at load; the second, better, instinct was that a filter
nobody remembers writing is how data disappears. Bronze lands everything and the
quality layer counts it.

**Not built.** No dashboard. For six weeks the output was a weekly CSV and a
conversation. Building a dashboard on a metric nobody had agreed to would have
locked in the disagreement.

---

### Q2 2024 · Make it trustworthy before making it pretty

**Problem.** The pipeline worked. Nobody believed it, because when a number
looked odd there was no way to tell whether the data or the pipeline was wrong.

**Shipped**

- `etl/quality/` — the check framework and the first ~20 checks.
- `ops.pipeline_runs` and `ops.data_quality_results`: what ran, how long, how
  many rows, what broke.
- The five **reconciliation** checks. Line revenue must equal header revenue;
  the daily mart must equal the fact it is built on.
- `tests/` — a real warehouse built from real generated data, not mocks.

**The decision that mattered.** Non-zero thresholds. The first version of the
suite failed every night on the 0.07% of customers with no email address. Within
two weeks people had stopped reading the alerts. Re-tuning those checks to
warnings with quantified thresholds — and being explicit that they encode an
*accepted* business reality — is what made the suite worth having.

**Not built.** No alerting. Results were recorded and reviewed on Monday. Paging
someone about a warehouse nobody had come to depend on yet would have been
theatre.

---

### Q3 2024 · The star schema, and the first dashboards

**Problem.** Every new question meant new bespoke SQL. Answering "revenue by
region by month for the electronics category" took a day.

**Shipped**

- Full Kimball star: seven dimensions, five facts, surrogate keys, Unknown
  members on `-1`.
- `fact_sales` at line grain **alongside** `fact_orders` at header grain.
- The Streamlit executive and sales dashboards.
- `dashboards/streamlit/theme.py` — one palette, one set of chart rules, applied
  everywhere.

**The decision that mattered.** Two order grains. It looked redundant until the
first AOV number came out 40% low because it had been averaged from the line
fact. Keeping both grains explicit makes that error structurally impossible
rather than merely discouraged.

**The other decision that mattered.** A design system for charts, on day one of
the first dashboard. Fixed categorical order, one hue per entity, no dual axes,
sequential ramps for magnitude only. Retrofitting consistency across thirty
charts is far more expensive than starting with it, and the *no dual axis* rule
alone has prevented several misleading charts.

---

### Q4 2024 · Customers, not just orders

**Problem.** The business could see what it sold. It could not see who kept
buying, who left, or what an acquired customer was worth.

**Shipped**

- `mart_customer_360`, `mart_rfm_segments`, `mart_cohort_retention`,
  `mart_churn_monthly`.
- The customer dashboard: RFM segments, the cohort heatmap, LTV curves.
- `gold.analysis_window` — the platform's definition of "today".

**The decision that mattered.** Anchoring recency to the data, not the clock.
The first cohort chart moved every time it was opened, which destroyed trust in
it instantly. Anchoring to `MAX(order_date)` made every screenshot, test and
report agree. It is one small table and it is the reason the whole platform is
reproducible.

**The other decision that mattered.** A cohort is the month of the first
*purchase*, not the signup month. The signup-based version was built first, and
showed a retention cliff that turned out to be an activation problem wearing a
retention costume.

---

## Year 2 — make it real-time, make it predictive, make it deployable

### Q1 2025 · Real-time

**Problem.** Payment failures were discovered the next morning. A gateway
degradation on a Friday evening cost a full night of orders before anyone knew.

**Shipped**

- `streaming/` — four correlated topics: orders, payments, inventory,
  clickstream.
- `streaming/bus.py`: one interface, two implementations (NDJSON files, Kafka).
- The consumer, micro-batched, committing offsets only after a successful write.
- `ops.stream_events`, `ops.realtime_kpis`, and the real-time dashboard.
- `streaming/processors/realtime_api.py` for non-dashboard consumers.

**The decision that mattered.** Event time, not wall-clock time. A replayed
stream now reproduces exactly the KPIs it produced live, which is what makes the
real-time layer testable at all.

**The other decision that mattered.** The consumer owns no metric definitions.
It lands events and recomputes a window; every metric stays in SQL alongside the
batch ones. "Revenue" cannot mean two things depending on which pipeline
produced it.

**The mistake.** The first version dropped `ops.stream_events` on every batch
rebuild, because it was created alongside the bronze tables with
`DROP`+`CREATE`. A routine warehouse refresh silently wiped the real-time
landing zone. Fixed by making `ops.*` `CREATE TABLE IF NOT EXISTS`, and covered
by a test — a batch job that can destroy the streaming layer is exactly the kind
of coupling that causes a 3am page.

---

### Q2 2025 · Marketing, honestly

**Problem.** Marketing reported a blended ROAS of 4.2. Nobody could say what it
was attributed on, and the number was being used to set budget.

**Shipped**

- `mart_campaign_performance`, `mart_channel_performance`,
  `mart_acquisition_channel`.
- `analytics/marketing/attribution.py` — the same revenue under five attribution
  models, side by side.
- LTV : CAC by acquisition channel; a concrete budget reallocation.

**The decision that mattered.** Publishing five attribution models rather than
picking one. No model is correct, and the *spread between them* turned out to be
the finding: an influencer channel with a large positive `upper_funnel_bias` was
being starved by a last-touch budget. A single ROAS number would have hidden it
completely.

**The discipline that came with it.** Every approximate number is labelled where
it appears. The incrementality proxy says on the dashboard that it cannot
separate a campaign from a seasonal upswing. Stating a limitation costs a line
of text; discovering it in a board meeting costs the platform's credibility.

---

### Q3 2025 · Prediction

**Problem.** Everything was retrospective. Purchasing over-ordered on gut feel;
retention found out about churn after it had happened.

**Shipped**

- `analytics/forecasting/forecast.py` — Holt-Winters, linear trend and seasonal
  naive, selected by backtest against a held-out tail.
- `analytics/customer/churn.py` — logistic propensity scoring with a rewound
  feature snapshot.
- `analytics/inventory/optimisation.py` — safety stock, reorder points, EOQ,
  ABC×XYZ.
- `analytics/sales/basket.py` — product affinity with lift, not just confidence.

**The decision that mattered.** Reporting seasonal naive as a first-class
result. The first forecast was Holt-Winters with a respectable MAPE, presented
alone. Backtesting it against "next week looks like last week" showed the naive
baseline winning on the daily series. Publishing both is what stopped the team
deploying a model that added nothing.

**The other decision that mattered.** Rewinding the churn feature snapshot 90
days. The first model scored 0.94 AUC and was useless — it had been trained on
features computed at the same moment as the label, so `recency_days` *was* the
label. The honest version scores lower and actually predicts.

**The decision to use a linear model.** A gradient-boosted model scored slightly
better. The retention team needed to know *why* a customer was at risk in order
to write a campaign, and could not act on a black box. The coefficients are part
of the deliverable.

---

### Q4 2025 · Deployable

**Problem.** Everything ran on two laptops. There was no path to a shared,
always-on environment, and no answer to "what happens when one of you is away".

**Shipped**

- `docker-compose.yml` — Postgres and Redpanda, exercising the production code
  paths locally.
- `infrastructure/terraform/` — ADLS Gen2, Event Hubs, Azure Database for
  PostgreSQL, Container Registry, Key Vault, Container Apps, Databricks.
- `.github/workflows/ci.yml` — the full pipeline plus the quality suite on every
  push.
- `dashboards/powerbi/` — the model as text, for the stakeholders who live in
  Power BI.
- `scripts/run_demo.py` and `scripts/healthcheck.py`.

**The decision that mattered.** Terraform with the cheapest working defaults and
a printed cost estimate. The first draft defaulted to provisioned SQL and
premium Databricks — about £600/month for a dev environment nobody would use at
night. Serverless SQL that auto-pauses and Container Apps that scale to zero
bring dev to roughly £30.

**The other decision that mattered.** Managed PostgreSQL, not Synapse. Synapse is right
past a terabyte; below that it is a large bill for a warehouse a single
well-indexed SQL database serves faster. The gold layer is already a star
schema, so the migration is a DDL change and a bulk copy — a real path, kept
open, not taken prematurely.

**The thing that was kept out of git.** No `.pbix`. A binary that cannot be
diffed, reviewed or merged does not belong in version control, and one three
commits stale is worse than none.

---

## What we would do next

In the order we would do it, and honestly about why each has waited.

**1. A real orchestrator (Dagster or Databricks Jobs).**
`etl/pipeline.py` is a linear DAG of six stages. It has been enough because
there are six stages and one schedule. The moment there are two schedules and a
dependency between them, hand-rolled orchestration stops being enough. The stage
boundaries and `ops.pipeline_runs` are already shaped so this is a wrapper, not
a rewrite.

**2. Incremental loads.**
Every run is a full rebuild, which takes eleven seconds on the demo dataset and
about four minutes on the largest preset. Incremental buys nothing yet.
`ops.load_watermarks` exists for when it does. Doing it early would have added
"which rows changed" bugs to a pipeline that had enough to prove already.

**3. SCD Type 2 on the dimensions that need it.**
`dim_customer_history` has the Type 2 shape and one version per customer,
because the source ships no change history. Wiring real change capture would let
us answer "revenue by the tier the customer held *at the time of purchase*",
which is currently unanswerable.

**4. Alerting with an owner.**
Terraform creates the action group. Nothing routes to it, because routing to a
rota that does not exist is worse than not alerting. This is an organisational
change first and a technical one second.

**5. Drift and profiling.**
The quality suite catches broken data. It does not catch data that is
structurally valid and quietly different — a category disappearing, a
distribution shifting, cardinality doubling. `ops.data_quality_results` is the
right history to build that on.

**6. Experimentation.**
The incrementality proxy is the weakest number in the platform and it is used to
argue about budget. A geo holdout or matched-market design would replace it with
something defensible. This needs marketing to agree to withhold spend, which is
a conversation, not a sprint.

**7. A semantic layer.**
Metric definitions live in one document and three implementations (SQL, Python,
DAX). The reconciliation checks keep the SQL implementations honest; the DAX
side is verified by hand. A semantic layer would collapse the three into one.
Worth doing when a fourth consumer appears — not before.

---

## What two years actually taught

**Definitions before dashboards.** The six weeks in Q1 2024 with no dashboard
were the highest-leverage weeks of the project. Every metric argument since has
been resolvable by pointing at a document.

**Quality thresholds are business decisions.** A zero-tolerance suite that fires
nightly gets muted, and a muted suite catches nothing. Every non-zero threshold
here encodes a known, accepted reality — and is written down as such.

**Reproducibility is a feature, not hygiene.** Anchoring to the data instead of
the clock is one small table. It is why a screenshot from March still matches
the warehouse in September, and it is the single change that did most for trust.

**Say what a number cannot tell you.** Labelling last-touch attribution as
last-touch, marking the incrementality proxy as a proxy, publishing two payment
success rates instead of one ambiguous one — every one of those cost a line of
text and bought credibility that would have been very expensive to recover after
losing it in a board meeting.

**Simple models that people can act on beat better models they cannot.** The
linear churn model, the explainable CLV formula, the seasonal-naive baseline —
all chosen over more sophisticated alternatives because the output had to
survive contact with someone who then had to *do* something.
