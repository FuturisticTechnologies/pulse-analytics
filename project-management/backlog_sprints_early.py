# -*- coding: utf-8 -*-
"""Sprints 1-7, 02 Mar 2026 - 05 Jun 2026. PULSE-12 .. PULSE-56.

Team for this stretch is three people: Geetha (Sr. Data Analyst, tech lead),
Divya (Data Analyst) and Devendranath (DevOps). QA joins in Sprint 8, the BA
in Sprint 13.
"""

from backlog_common import I, G, D, V, S1, S2, S3, S4, S5, S6, S7

EARLY = [

# ---------------------------------------------------------------- Sprint 1
I("PULSE-12", "Story", "Repository scaffold and local development environment", "Done",
  """
As an engineer on the team
I want a repository that clones and runs the same way on every machine
So that day one is not spent reconciling three different local setups.

Acceptance criteria
* src layout agreed and created: etl/, database/, analytics/, dashboards/,
  streaming/, tests/, docs/, scripts/, data-generator/
* .gitignore excludes data/, .venv/, *.duckdb and any .pbix
* .env.example documents every variable the code reads, with no real secrets
* README quickstart takes a clean clone to a built warehouse
  """,
  parent="PULSE-10", assignee=V, sprint=S1, points="3", components="Platform",
  labels="setup", created="2026-03-02 13:40:00", resolved="2026-03-05 11:05:00",
  comments=[
    ("2026-03-03 10:15:00", V, "Layout pushed. One thing I want to fix now rather than later: data/ is gitignored in full. Generated warehouses are large, they change on every run, and a committed .duckdb is a merge conflict nobody can resolve."),
    ("2026-03-03 15:22:00", D, "Cloned clean on my machine and the quickstart worked apart from the DuckDB extension download, which needs network on first run. Added a line to the README rather than vendoring it."),
    ("2026-03-05 11:04:00", G, "Approved. .env.example carrying every variable with placeholder values is the bit that will save us later - a missing env var should fail at startup with a name, not at 2am with a KeyError."),
  ]),

I("PULSE-13", "Task", "Pin the Python baseline and dependency set", "Done",
  """
Pin Python 3.12 and produce a requirements.txt with exact versions.

Acceptance criteria
* requirements.txt pinned to exact versions, not ranges
* documented reason for each non-obvious dependency
* fresh venv install verified on Windows and Linux
  """,
  parent="PULSE-10", assignee=V, sprint=S1, points="2", components="Platform",
  labels="setup", created="2026-03-02 13:45:00", resolved="2026-03-04 16:30:00",
  comments=[
    ("2026-03-04 09:10:00", V, "Pinned exact versions. Ranges are how a green build on Monday becomes a red build on Tuesday with no commits in between."),
    ("2026-03-04 16:28:00", D, "Verified on Windows. Worth noting for anyone hitting it: DuckDB is the local engine, Postgres is the deployment target, and the SQL is written to run on both. We should keep that constraint written down somewhere more permanent than this comment."),
  ]),

I("PULSE-14", "Story", "Synthetic data generator so we can build without prod access", "Done",
  """
As the data team
I want a generator that produces a realistic, correlated retail dataset
So that we can build and test the whole pipeline before prod access is granted.

Prod access is with the security review and nobody will commit to a date.
Waiting for it costs the entire first quarter.

Acceptance criteria
* customers, products, orders, order lines, payments, inventory, campaigns,
  clickstream and FX rates, mutually consistent
* seeded and reproducible - the same seed produces the same dataset
* size presets from a small demo set to a multi-million row set
* referential integrity holds across every generated file
  """,
  parent="PULSE-1", assignee=D, sprint=S1, points="8", components="ETL",
  labels="generator;foundation", created="2026-03-02 14:05:00",
  resolved="2026-03-12 15:40:00",
  comments=[
    ("2026-03-02 14:30:00", G, "Correlation is the part that matters. Uncorrelated random data will make every check pass and every model useless - seasonality, weekday effects, a loyalty tier that actually predicts order value, campaigns that actually move volume."),
    ("2026-03-06 11:50:00", D, "First pass generating. Added a weekly cycle, a Q4 lift and a payday spike, plus a small share of returns and cancellations so the status flags are not all completed."),
    ("2026-03-10 09:35:00", V, "Ran the largest preset overnight. 4.2m order lines in about nine minutes, and it is deterministic across two machines with the same seed. Good enough for load testing."),
    ("2026-03-12 15:38:00", G, "Accepted. Reproducibility from a seed is doing more work here than it looks - it means a failing test is a failing test everywhere, not just on the machine that generated the data."),
  ]),

I("PULSE-15", "Task", "Seed known defects into the generator", "Done",
  """
The generator must produce dirty data on purpose, so the quality layer has
something real to catch and we can assert it catches it.

Defects to inject, at configurable rates
* replayed orders - the same order_id landed twice with different ingest times
* negative quantities on a small share of lines
* loyalty tier case and whitespace drift: "Gold", "gold ", "GOLD"
* about 0.07% of customers with no email address
* a handful of orders referencing a customer_id that does not exist
* FX gaps on weekend dates
  """,
  parent="PULSE-1", assignee=D, sprint=S1, points="3", components="ETL",
  labels="generator;quality", created="2026-03-02 14:10:00",
  resolved="2026-03-13 12:10:00",
  comments=[
    ("2026-03-11 10:20:00", D, "Injecting the defects with a documented rate per defect, so a test can assert both that we caught them and how many there should be."),
    ("2026-03-13 12:08:00", G, "This is the ticket that makes the quality epic testable rather than aspirational. The missing-email rate in particular should stay at 0.07% - it is modelled on what the source system actually looks like."),
  ]),

I("PULSE-16", "Story", "Bronze schemas and landing tables", "Done",
  """
As the platform
I want a bronze schema whose tables mirror the source files exactly
So that a landed row can always be compared with what the source sent.

Acceptance criteria
* database/init/001_schemas.sql creates bronze, silver, gold and ops
* database/init/002_bronze_tables.sql mirrors each source file
* all bronze columns land as text, plus ingest metadata: source file,
  ingested_at, run_id, source row number
* no constraints, no keys, no not-null on bronze
  """,
  parent="PULSE-1", assignee=V, sprint=S1, points="5", components="ETL;Warehouse",
  labels="bronze", created="2026-03-03 09:20:00", resolved="2026-03-12 17:15:00",
  comments=[
    ("2026-03-03 11:40:00", V, "Landing everything as text is deliberate. A type cast at the bronze boundary is a silent filter - a value that will not cast becomes a null or an exception, and either way the original is gone."),
    ("2026-03-09 14:05:00", D, "Source row number added. When a check fails, being able to point at 'row 41,209 of orders_2026-03-08.csv' rather than 'some row somewhere' is the difference between a five minute fix and an afternoon."),
    ("2026-03-12 17:14:00", G, "Approved. Four schemas, clear ownership per layer, and the metadata columns on every bronze table."),
  ]),

I("PULSE-17", "Story", "Nightly CSV extract from the OLTP database", "Done",
  """
As the platform
I want a nightly extract of the OLTP tables into the bronze landing zone
So that there is one authoritative copy of source data each day.

Acceptance criteria
* etl/extract/csv_source.py reads a configured set of source files
* files land under data/raw partitioned by extract date
* an extract that finds no file fails loudly instead of loading nothing quietly
* checksum and row count recorded per file in the run context
  """,
  parent="PULSE-1", assignee=V, sprint=S1, points="5", components="ETL",
  labels="bronze;extract", created="2026-03-03 09:25:00",
  resolved="2026-03-13 16:50:00",
  comments=[
    ("2026-03-10 15:30:00", V, "The empty-source case is the one worth being careful about. A silent zero-row extract looks identical to a quiet business day until someone asks why last Tuesday is missing."),
    ("2026-03-13 16:48:00", G, "Agreed and accepted. Missing file is an error, zero rows in a present file is a warning with the count recorded."),
  ]),

I("PULSE-18", "Task", "ADR-001: Bronze rejects nothing", "Done",
  """
Record the decision and the reasoning, because this one will be questioned
again by whoever joins next.

Decision: the bronze layer lands every row it is given. Invalid, duplicated
and malformed rows are landed and counted, never filtered.

Rationale: a filter nobody remembers writing is how data disappears. If bad
rows are dropped at load, the only evidence they existed is in a log that
rotates. Landing them and counting them in the quality layer means the
question "how much of this is broken?" has a number.

Cost accepted: bronze is larger than it needs to be, and every downstream
layer has to be explicit about what it excludes.
  """,
  parent="PULSE-1", assignee=G, sprint=S1, points="1", components="Docs",
  labels="adr;decision", created="2026-03-04 10:00:00",
  resolved="2026-03-06 14:20:00",
  comments=[
    ("2026-03-04 10:45:00", V, "My first instinct was to filter at load, and I want that recorded in the ADR rather than quietly overwritten. It looks like tidiness right up to the first time someone asks where a row went."),
    ("2026-03-06 14:18:00", G, "Written up with your instinct included as the rejected alternative. An ADR that only records the winning argument is half an ADR."),
  ]),

I("PULSE-19", "Story", "Metric definition workshop and the KPI contract skeleton", "Done",
  """
As the business
I want one written definition per metric, agreed before implementation
So that two teams cannot quote two different revenue figures.

Acceptance criteria
* docs/kpi-definitions.md created with the contract statement at the top:
  if two people could disagree about what a number means, it is defined here
  and nothing computes its own version
* workshop held with finance, sales and marketing; disagreements recorded
  rather than smoothed over
* every definition carries: the rule, what it excludes, where it is
  implemented, and the judgement call it contains
  """,
  parent="PULSE-2", assignee=G, sprint=S1, points="5", components="Docs",
  labels="definitions;stakeholder", created="2026-03-03 10:30:00",
  resolved="2026-03-13 15:00:00",
  comments=[
    ("2026-03-05 16:20:00", G, "Workshop done and it was worse than expected, which is good. Finance excludes shipping from revenue, marketing includes it, and the board deck has been built from the marketing figure for the last two quarters."),
    ("2026-03-06 09:15:00", D, "That single difference is about 6% on the monthly number. Nobody had noticed because the two figures were never on the same page."),
    ("2026-03-11 11:40:00", V, "Asking the awkward question early: are we going to be the team that tells the board the last two decks were 6% high?"),
    ("2026-03-11 12:05:00", G, "Yes, but framed as 'here is the definition we are standardising on and here is the restated series', not as an accusation. The restatement is a one-off cost. Two live definitions is a permanent one."),
    ("2026-03-13 14:58:00", G, "Skeleton committed with revenue, gross profit, margin and AOV stubs. Detail lands in PULSE-24 and PULSE-25."),
  ]),

# ---------------------------------------------------------------- Sprint 2
I("PULSE-20", "Story", "Bronze loader - land everything, count everything", "Done",
  """
As the platform
I want a loader that writes every extracted row into bronze
So that ingestion never makes a judgement about data quality.

Acceptance criteria
* etl/load/load_bronze.py loads all configured sources in one run
* row counts in and out recorded per source, and they must match
* loads are idempotent per run_id - a re-run replaces its own rows only
* explicit dtype handling: everything lands as text
  """,
  parent="PULSE-1", assignee=V, sprint=S2, points="5", components="ETL",
  labels="bronze;load", created="2026-03-16 09:30:00",
  resolved="2026-03-25 16:20:00",
  comments=[
    ("2026-03-18 11:10:00", V, "Rows in must equal rows out is now an assertion in the loader, not a check downstream. If the loader loses a row, I want it to fail there rather than have the quality suite discover it two stages later."),
    ("2026-03-25 16:18:00", D, "Verified against the largest preset. Counts match on all eight sources, and re-running the same run_id is clean."),
  ]),

I("PULSE-21", "Story", "API extract for FX rates and campaign spend", "Done",
  """
As the platform
I want FX rates and campaign spend pulled from their APIs into bronze
So that multi-currency revenue and marketing cost are available to the model.

Acceptance criteria
* etl/extract/api_source.py with retry, exponential backoff and a request cap
* responses landed raw as JSON alongside the parsed rows
* a rate-limited or failed call fails the run with the endpoint named
* no credentials in code - everything from the environment
  """,
  parent="PULSE-1", assignee=V, sprint=S2, points="5", components="ETL",
  labels="extract;api", created="2026-03-16 09:35:00",
  resolved="2026-03-27 15:10:00",
  comments=[
    ("2026-03-20 14:25:00", V, "Landing the raw JSON as well as the parsed rows. When the provider changes a field name - and they will - the raw payload is the only way to prove what we were sent."),
    ("2026-03-24 10:05:00", D, "FX has no weekend rates. Not a bug in the extract, but it will matter in silver, so I have raised it there rather than papering over it here."),
    ("2026-03-27 15:08:00", G, "Accepted. Weekend FX handling is PULSE-34's problem and is written into that ticket."),
  ]),

I("PULSE-22", "Story", "Run context and ops.pipeline_runs", "Done",
  """
As an engineer
I want every pipeline run recorded with its stages, timings and row counts
So that "what happened last night" is a query, not an archaeology exercise.

Acceptance criteria
* database/init/003_ops_tables.sql creates ops.pipeline_runs
* etl/run_context.py issues a run_id and records stage start, end, status,
  rows in, rows out and the error if there is one
* a failed stage still writes its row
* the run_id is stamped onto every bronze row loaded in that run
  """,
  parent="PULSE-3", assignee=V, sprint=S2, points="5", components="ETL;Platform",
  labels="observability", created="2026-03-16 09:40:00",
  resolved="2026-03-26 17:30:00",
  comments=[
    ("2026-03-19 09:50:00", V, "A failed stage writing its row is the requirement people forget. A run table that only records successes tells you nothing on the morning you actually need it."),
    ("2026-03-26 17:28:00", G, "Approved. Also worth noting for the future: these stage boundaries are the seam a real orchestrator will wrap later. Keeping them clean now means Dagster is a wrapper rather than a rewrite."),
  ]),

I("PULSE-23", "Bug", "Bronze load strips leading zeros from order_id", "Done",
  """
Observed: order ids in the source such as 0004821 land in bronze as 4821.

Impact: joins between orders and order lines silently drop the affected rows.
About 1.2% of orders in the demo dataset, all of them older records from before
the source system widened its id format.

Cause: the CSV reader was inferring dtypes, so a numeric-looking id column
became an integer.

Fix: explicit dtype mapping in the extract - every bronze column is read and
landed as text, per ADR-001.

Found by: reconciliation between the source row count and joined line count.
  """,
  parent="PULSE-1", assignee=V, reporter=D, priority="High", sprint=S2, points="3",
  components="ETL", labels="bronze;data-loss", created="2026-03-19 11:05:00",
  resolved="2026-03-23 14:40:00",
  comments=[
    ("2026-03-19 11:20:00", D, "Found this because the order line count did not match the header count and the gap was suspiciously stable at about 1.2%. All the missing ids turn out to start with a zero."),
    ("2026-03-19 11:48:00", V, "Confirmed. The reader was inferring dtypes. This is exactly the failure ADR-001 predicted - nothing errored, nothing was logged, the rows just quietly stopped matching."),
    ("2026-03-20 09:30:00", G, "Raising the priority. Silent data loss beats loud failure on the list of things I do not want in this platform. Please add a check that asserts header-to-line join completeness so this class of thing cannot come back unnoticed."),
    ("2026-03-23 14:38:00", V, "Fixed with an explicit dtype map, and the join completeness check is in as one of the reconciliation checks in PULSE-40."),
  ]),

I("PULSE-24", "Story", "Define revenue, gross profit and gross margin", "Done",
  """
As the business
I want one written, implemented-once definition of revenue and margin
So that finance, marketing and the board deck agree.

Agreed definitions
* Revenue: net amount of completed orders - gross minus discounts, excluding
  shipping and tax. Cancelled, returned and pending orders stay in the fact
  table, flagged, because operations needs to see them.
* Gross profit: net_amount - cost_amount. Product cost only; no fulfilment,
  marketing or overhead allocation, because the source does not carry them and
  an invented allocation is a fabricated number presented as a measured one.
* Gross margin %: gross_profit / revenue, on net revenue rather than gross,
  because a gross denominator flatters the margin by the size of the discount.
  """,
  parent="PULSE-2", assignee=G, sprint=S2, points="5", components="Docs;Warehouse",
  labels="definitions;kpi", created="2026-03-16 10:15:00",
  resolved="2026-03-27 16:00:00",
  comments=[
    ("2026-03-17 15:30:00", G, "Finance has signed off on excluding shipping and tax. Their argument, which I am recording because it is the right one: they are pass-throughs, not earnings, and including them makes revenue move when the courier changes their pricing."),
    ("2026-03-23 10:20:00", D, "Implemented as a single is_revenue flag in silver rather than a status filter repeated in every mart. Twelve copies of a status list is twelve chances to get it wrong."),
    ("2026-03-27 15:55:00", G, "Signed off. Restatement of the last two quarters goes to the board as a note with the definition attached, not as a correction buried in a footnote."),
  ]),

I("PULSE-25", "Task", "Define AOV and record the order-grain trap", "Done",
  """
Define average order value, and write down the trap that comes with it.

Definition: AOV = revenue / distinct completed orders. It is a header-grain
metric and must never be computed by averaging line-grain rows.

Written into the KPI document with the reason, because the mistake is
invisible in the output - a wrong AOV looks like a plausible AOV.
  """,
  parent="PULSE-2", assignee=G, sprint=S2, points="2", components="Docs",
  labels="definitions;kpi", created="2026-03-16 10:20:00",
  resolved="2026-03-24 11:30:00",
  comments=[
    ("2026-03-18 09:40:00", G, "Writing this down now, before the facts exist, because there is no error message for averaging the wrong grain. You just get a number that is confidently wrong and nobody can tell by looking."),
    ("2026-03-24 11:28:00", D, "Documented. I suspect we will still hit it once anyway."),
  ]),

I("PULSE-26", "Task", "docker-compose with Postgres for local parity", "Done",
  """
Stand up Postgres in docker-compose so the deployment target can be exercised
locally, alongside the DuckDB path used for fast local iteration.

Acceptance criteria
* docker-compose up gives a working Postgres with the schemas created
* the same DDL runs on both engines, or the difference is documented
* a documented one-command teardown that does not leave volumes behind
  """,
  parent="PULSE-10", assignee=V, sprint=S2, points="3", components="Platform",
  labels="docker;local-parity", created="2026-03-17 14:20:00",
  resolved="2026-03-27 12:15:00",
  comments=[
    ("2026-03-24 16:10:00", V, "Running against both engines locally from here on. The gap we do not want is SQL that works in DuckDB, ships, and then meets Postgres for the first time in the cloud."),
    ("2026-03-27 12:12:00", D, "Found two divergences already - a date_trunc argument order difference and one window frame default. Both documented in the DDL rather than branched on."),
  ]),

# ---------------------------------------------------------------- Sprint 3
I("PULSE-27", "Story", "Silver reference data and customer staging", "Done",
  """
As the model
I want customers and reference data cleaned once, in silver
So that no downstream query repeats a cleanup rule.

Acceptance criteria
* database/staging/010_silver_reference.sql and 011_silver_customers.sql
* loyalty tier canonicalised - trimmed, title-cased, mapped to a known set,
  anything unmapped landing as Unknown rather than being dropped
* email normalised to lower case and trimmed; missing email stays missing and
  is not defaulted to an empty string
* typed columns with the cast rules documented in the file header
  """,
  parent="PULSE-2", assignee=D, sprint=S3, points="5", components="ETL",
  labels="silver", created="2026-03-30 09:20:00", resolved="2026-04-08 16:40:00",
  comments=[
    ("2026-03-31 14:15:00", D, "Nine distinct spellings of four loyalty tiers in the generated data, which is modelled on what the source actually contains. Canonicalising to the known set and landing anything else as Unknown."),
    ("2026-04-02 10:30:00", G, "Unknown rather than null, and definitely rather than dropped. A tier we do not recognise is a fact about the source system that somebody should eventually look at."),
    ("2026-04-08 16:38:00", G, "Accepted. Missing email staying genuinely missing matters for PULSE-41 - if we default it to an empty string, the completeness check becomes untrue rather than merely noisy."),
  ]),

I("PULSE-28", "Story", "Silver orders - de-duplicate replayed orders", "Done",
  """
As the model
I want replayed orders collapsed to one row each
So that revenue is not double counted.

The source replays orders on retry, landing the same order_id more than once
with different ingest timestamps and sometimes a changed status.

Acceptance criteria
* database/staging/012_silver_orders.sql de-duplicates on order_id
* the surviving row is the latest by source updated_at, not the first seen
* negative quantities corrected per the documented rule, with the original
  value retained in a separate column
* de-duplication counts written to the run context
  """,
  parent="PULSE-2", assignee=D, sprint=S3, points="8", components="ETL",
  labels="silver;dedupe", created="2026-03-30 09:25:00",
  resolved="2026-04-09 17:00:00",
  comments=[
    ("2026-04-01 11:20:00", D, "Roughly 0.9% of orders arrive more than once. Collapsing on order_id with a window function over ingest time."),
    ("2026-04-06 15:45:00", G, "Careful with the survivor rule - see PULSE-29. Ingest order and business order are not the same thing and the difference is a status field."),
    ("2026-04-09 16:58:00", D, "Reworked to latest source updated_at with ingest time as a tiebreak, and the original negative quantity is kept in quantity_raw so the correction is auditable rather than invisible."),
  ]),

I("PULSE-29", "Bug", "De-duplication keeps the earliest row and loses status changes", "Done",
  """
Observed: an order replayed as pending and then completed collapses to the
pending row, so its revenue is excluded.

Impact: about 0.3% of completed orders missing from revenue. Small in
percentage terms, systematically biased downwards, and invisible without
comparing against the source.

Cause: the de-duplication window was ordered by first ingest time, on the
assumption that the first landing is authoritative. It is not - the source
replays because something changed.

Fix: order by source updated_at descending, with ingest time as a tiebreak.
Add a reconciliation check comparing completed order counts against bronze.
  """,
  parent="PULSE-2", assignee=D, reporter=G, priority="High", sprint=S3, points="3",
  components="ETL", labels="silver;dedupe;revenue", created="2026-04-06 15:50:00",
  resolved="2026-04-09 12:20:00",
  comments=[
    ("2026-04-06 15:55:00", G, "Caught this reading the SQL rather than from a failing test, which is the uncomfortable part. Reviewing the merge is not a substitute for a check that would have caught it."),
    ("2026-04-07 09:40:00", D, "Confirmed and reproduced. 0.3% of completed orders were being dropped to pending. Fixing the window and adding the count comparison as a check so a review is not the only thing standing between us and this."),
    ("2026-04-09 12:18:00", G, "Verified against bronze. Counts reconcile. This one goes in the retro - two of our first three data bugs have been silent, and both were caught by comparing counts across layers."),
  ]),

I("PULSE-30", "Story", "Silver payments", "Done",
  """
As the model
I want payment attempts staged with a clear success definition
So that payment success rate is unambiguous.

Acceptance criteria
* database/staging/013_silver_payments.sql
* attempts and outcomes kept distinct - a retried payment is two attempts and
  one success, not one of each
* two success rates defined and both published: per attempt and per order
* gateway and method canonicalised
  """,
  parent="PULSE-2", assignee=D, sprint=S3, points="5", components="ETL",
  labels="silver;payments", created="2026-03-30 09:30:00",
  resolved="2026-04-10 15:30:00",
  comments=[
    ("2026-04-03 10:10:00", D, "Publishing two success rates rather than one. Per attempt is what the gateway conversation needs; per order is what the business cares about. One ambiguous number would get quoted in both conversations and be wrong in one of them."),
    ("2026-04-10 15:28:00", G, "Agreed, and both go into the KPI document with their denominators spelled out."),
  ]),

I("PULSE-31", "Task", "Pipeline orchestration skeleton", "Done",
  """
Wire the stages into one runnable pipeline: extract, load bronze, build
silver, build gold, build marts, run quality.

Acceptance criteria
* etl/pipeline.py runs the full sequence with one command
* each stage opens and closes its own run-context record
* a stage failure stops the run and leaves the warehouse in its last good
  state rather than half rebuilt
* stage boundaries are clean enough to be wrapped by a real orchestrator later
  """,
  parent="PULSE-1", assignee=V, sprint=S3, points="5", components="ETL;Platform",
  labels="pipeline", created="2026-03-31 09:15:00", resolved="2026-04-09 16:10:00",
  comments=[
    ("2026-03-31 09:40:00", V, "Explicitly not adding an orchestrator. Six stages and one schedule do not need Dagster, and adding it now buys complexity we cannot yet justify. The stage boundaries are shaped so it becomes a wrapper when we do need it."),
    ("2026-04-09 16:08:00", G, "Accepted, and I have raised PULSE-117 in the backlog so 'we should have an orchestrator' is a ticket with a trigger condition rather than a recurring conversation."),
  ]),

I("PULSE-32", "Story", "GitHub Actions CI on every push", "Done",
  """
As the team
I want the full pipeline to run on every push
So that a change that breaks the build is caught by the machine, not by the
next person to pull.

Acceptance criteria
* .github/workflows/ci.yml runs lint, tests and a full pipeline build on a
  generated dataset
* runs against both DuckDB and the containerised Postgres
* under ten minutes on the demo preset
* red build blocks merge
  """,
  parent="PULSE-10", assignee=V, sprint=S3, points="8", components="CI;Platform",
  labels="ci", created="2026-03-31 09:20:00", resolved="2026-04-10 17:20:00",
  comments=[
    ("2026-04-07 14:30:00", V, "Building a real warehouse from generated data in CI rather than mocking it. It costs about four minutes a run and it is the only way the SQL is actually exercised."),
    ("2026-04-10 17:15:00", D, "Green on both engines. Caught a Postgres-only cast error on the first run, which is precisely the class of thing this is for."),
    ("2026-04-10 17:18:00", G, "Approved. The quality suite joins this pipeline in PULSE-44 once it exists."),
  ]),

# ---------------------------------------------------------------- Sprint 4
I("PULSE-33", "Story", "Silver inventory and clickstream events", "Done",
  """
As the model
I want inventory snapshots and clickstream events staged
So that stock health and funnel analysis have a clean source.

Acceptance criteria
* database/staging/014_silver_inventory.sql and 015_silver_events.sql
* inventory snapshots deduplicated to one row per product, location, date
* event types canonicalised against a known list; unknown types kept and
  counted, not dropped
* session stitching rules documented in the file header
  """,
  parent="PULSE-2", assignee=D, sprint=S4, points="5", components="ETL",
  labels="silver", created="2026-04-13 09:20:00", resolved="2026-04-22 16:00:00",
  comments=[
    ("2026-04-16 11:25:00", D, "Session stitching is a judgement call - 30 minute inactivity timeout, and a session does not cross a day boundary. Written into the file header so the next person does not have to reverse engineer it from the SQL."),
    ("2026-04-22 15:58:00", G, "Good. Any rule with a number in it that someone chose should be findable by reading, not by tracing."),
  ]),

I("PULSE-34", "Story", "Silver FX and multi-currency normalisation", "Done",
  """
As the business
I want revenue in both local and reporting currency
So that regional performance is comparable without hiding the local reality.

Acceptance criteria
* database/staging/016_silver_fx.sql
* weekend and holiday gaps filled by carrying the last known rate forward,
  with the fill flagged rather than silent
* orders converted at the rate on the order date, not today's rate
* local currency amounts retained alongside the converted values
  """,
  parent="PULSE-2", assignee=G, sprint=S4, points="5", components="ETL",
  labels="silver;fx", created="2026-04-13 09:25:00", resolved="2026-04-23 15:40:00",
  comments=[
    ("2026-04-15 10:50:00", G, "Converting at the order-date rate rather than the current rate. Restating history every time the currency moves makes last month's report disagree with itself, and no explanation of why is ever satisfying."),
    ("2026-04-20 14:05:00", D, "Carry-forward fills are flagged in a rate_is_carried column so a check can count them. About 28% of dates are carried, which is just what weekends are."),
    ("2026-04-23 15:38:00", G, "Accepted, and the local currency columns stay. A regional manager should be able to see their own number in their own currency."),
  ]),

I("PULSE-35", "Story", "gold.analysis_window - anchor \"today\" to the data", "Done",
  """
As the platform
I want one table that defines what "today" means for every recency metric
So that the same dataset produces the same segments in six months.

Acceptance criteria
* database/analytics/030_analysis_window.sql exposes as_of_date, set to
  MAX(order_date) present in the data
* every recency-based metric reads it; no query calls CURRENT_DATE directly
* a test asserts no analytics SQL references CURRENT_DATE
* switching to a live feed is one change: point as_of_date at CURRENT_DATE

This is small and it is load-bearing. RFM, churn, cohorts and every "last 30
days" tile all depend on it.
  """,
  parent="PULSE-2", assignee=G, priority="High", sprint=S4, points="5",
  components="Warehouse", labels="reproducibility;kpi",
  created="2026-04-13 09:30:00", resolved="2026-04-24 14:30:00",
  comments=[
    ("2026-04-14 09:35:00", G, "This is one table and about eleven lines of SQL, and I think it will end up being the single highest-leverage thing in the warehouse. A screenshot from April should still match the warehouse in September."),
    ("2026-04-17 11:20:00", V, "The test that greps the analytics SQL for CURRENT_DATE is the part that makes it stick. A convention without an assertion is a suggestion, and someone will write CURRENT_DATE at 6pm on a Friday."),
    ("2026-04-24 14:28:00", D, "Merged with the test. It already caught one usage in a draft mart I had open."),
  ]),

I("PULSE-36", "Task", "ADR-002: Reproducibility anchor", "Done",
  """
Decision: all recency-based metrics anchor to gold.analysis_window.as_of_date,
derived from the data, never from the wall clock.

Rationale: a report, a test and a screenshot must agree. Wall-clock anchoring
means a cohort chart moves every time it is opened, which destroys trust in it
faster than being wrong would.

Cost accepted: "today" in the platform is the latest date in the data, which
is not today. Every dashboard states the as-of date on the page.
  """,
  parent="PULSE-2", assignee=G, sprint=S4, points="1", components="Docs",
  labels="adr;decision;reproducibility", created="2026-04-14 10:00:00",
  resolved="2026-04-17 12:00:00",
  comments=[
    ("2026-04-17 11:58:00", G, "Written up. The visible as-of date on every dashboard is part of the decision, not decoration - if the platform's today is not the calendar's today, the page has to say so."),
  ]),

I("PULSE-37", "Story", "Data quality check framework", "Done",
  """
As the team
I want a check framework where a new check is a small declaration
So that adding a check is cheap enough that we actually add them.

Acceptance criteria
* etl/quality/checks.py provides completeness, uniqueness, range, referential
  integrity, freshness and reconciliation check types
* every check declares: name, layer, severity, threshold and a description of
  what a failure means in business terms
* etl/quality/suite.py runs the suite and returns a structured result
* a check failing does not stop the suite
  """,
  parent="PULSE-3", assignee=D, sprint=S4, points="8", components="Quality",
  labels="quality;framework", created="2026-04-14 09:15:00",
  resolved="2026-04-24 16:20:00",
  comments=[
    ("2026-04-16 10:40:00", D, "Every check carries a plain-language description of what a failure means. A check called chk_cust_email_not_null tells the person reading the alert nothing about whether to care."),
    ("2026-04-21 15:15:00", G, "Severity as a first-class field rather than a convention. The difference between 'stop the pipeline' and 'note it for Monday' is a business decision and it should be visible in the declaration."),
    ("2026-04-24 16:18:00", G, "Accepted. Continuing past a failure matters - one broken check should not hide the other twenty-three results."),
  ]),

I("PULSE-38", "Story", "ops.data_quality_results history table", "Done",
  """
As the team
I want every check result stored with its run
So that we can see a trend rather than tonight's snapshot.

Acceptance criteria
* ops.data_quality_results records run_id, check name, layer, severity,
  observed value, threshold, pass/fail/warn and timestamp
* results are appended, never overwritten
* the table survives a full warehouse rebuild
  """,
  parent="PULSE-3", assignee=V, sprint=S4, points="3", components="Quality;Platform",
  labels="quality;observability", created="2026-04-14 09:20:00",
  resolved="2026-04-23 11:40:00",
  comments=[
    ("2026-04-20 09:25:00", V, "History rather than latest-state. A check that has been drifting for three weeks is a different problem from one that broke last night, and you cannot tell them apart from a snapshot."),
    ("2026-04-23 11:35:00", G, "Accepted. This history is also the foundation the drift work will eventually sit on - PULSE-121."),
  ]),

# ---------------------------------------------------------------- Sprint 5
I("PULSE-39", "Story", "First suite of completeness and validity checks", "Done",
  """
As the team
I want roughly twenty checks covering the bronze and silver layers
So that a broken load is visible without reading SQL.

Coverage
* bronze row counts against extract counts, per source
* not-null on business keys
* uniqueness on order_id, customer_id, product_id in silver
* referential integrity from orders to customers and products
* ranges on quantity, unit price, discount
* freshness of the latest order date against the extract date
* accepted-value checks on status, tier, channel, payment method
  """,
  parent="PULSE-3", assignee=D, sprint=S5, points="8", components="Quality",
  labels="quality;checks", created="2026-04-27 09:20:00",
  resolved="2026-05-07 16:30:00",
  comments=[
    ("2026-04-29 14:20:00", D, "24 checks in. First full-suite run had three failures, all of them real: the seeded orphan customer ids, the negative quantities, and the missing emails."),
    ("2026-05-01 09:10:00", G, "Two of those three are things we deliberately injected and accept. That is the threshold conversation and it is worth having properly - see PULSE-41."),
    ("2026-05-07 16:28:00", D, "Suite runs in about eleven seconds on the demo preset. Cheap enough to run on every push."),
  ]),

I("PULSE-40", "Story", "Reconciliation checks between layers", "Done",
  """
As the business
I want the layers to prove they agree with each other
So that a number being wrong is detected by the platform, not by a stakeholder.

The five reconciliations
1. Line revenue must equal header revenue per order, within rounding tolerance
2. mart_sales_daily revenue must equal fact_orders revenue for the same range
3. Bronze completed order count must equal silver completed order count
4. Every order header must have at least one order line (the PULSE-23 check)
5. Payment amounts must reconcile to order totals for completed orders
  """,
  parent="PULSE-3", assignee=G, priority="High", sprint=S5, points="5",
  components="Quality", labels="quality;reconciliation",
  created="2026-04-27 09:25:00", resolved="2026-05-08 15:20:00",
  comments=[
    ("2026-04-28 10:15:00", G, "These are the checks that would have caught both of our silent bugs so far. Everything else verifies that data looks reasonable; these verify that two things we computed separately agree."),
    ("2026-05-05 11:30:00", D, "Rounding tolerance on the line-to-header check is 0.01 per order, absolute, not relative. A relative tolerance on a small order is meaningless."),
    ("2026-05-08 15:18:00", G, "All five green. These are severity error, not warning - a reconciliation failure means one of two numbers we publish is wrong."),
  ]),

I("PULSE-41", "Bug", "Quality suite fails every night on 0.07% of customers with no email", "Done",
  """
Observed: the completeness check on customer email fails on every run,
because about 0.07% of customers genuinely have no email address.

Impact: worse than it looks. Two weeks in, people had stopped reading the
quality output entirely, which means the suite is catching nothing regardless
of what it detects.

Cause: zero-tolerance thresholds applied to a check that encodes an accepted
business reality. Customers acquired in-store before email capture was
mandatory do not have an email and never will.

Fix: PULSE-42 - re-tune to a quantified warning threshold, and state in the
check description that it encodes an accepted reality rather than a defect.
  """,
  parent="PULSE-3", assignee=D, reporter=V, priority="High", sprint=S5, points="3",
  components="Quality", labels="quality;alert-fatigue",
  created="2026-05-04 09:15:00", resolved="2026-05-08 14:10:00",
  comments=[
    ("2026-05-04 09:25:00", V, "Raising this as a bug in the suite rather than in the data, because the data is fine. I have not read a quality report in nine days and neither, I suspect, has anyone else. A suite that fires every night is a suite that has been muted."),
    ("2026-05-04 10:40:00", G, "This is the most important ticket in the epic and it is a process bug. A zero-tolerance suite that fails nightly gets ignored, and an ignored suite catches nothing - so the tuning is not a compromise on rigour, it is what buys us any rigour at all."),
    ("2026-05-05 11:05:00", D, "Went through all 24 checks. Four of them encode accepted realities: missing emails, the historic orphan customer ids, weekend FX carry-forward, and the small share of orders with no campaign attribution. Proposing quantified warning thresholds for those four and keeping the other twenty at zero."),
    ("2026-05-08 14:08:00", G, "Approved. Every non-zero threshold gets a comment in the check saying what accepted reality it encodes and who accepted it. A threshold without a reason becomes a threshold nobody dares change."),
  ]),

I("PULSE-42", "Task", "Re-tune checks to quantified warning thresholds", "Done",
  """
Convert the four checks that encode accepted business realities from
zero-tolerance errors into warnings with quantified thresholds.

* customer email completeness: warn above 0.15% missing (current 0.07%)
* orphan customer ids on historic orders: warn above 0.5% (current 0.31%)
* FX carry-forward share: warn above 35% of dates (current ~28%)
* orders with no campaign attribution: warn above 40% (current 34%)

Each threshold carries an inline comment naming the accepted reality and who
accepted it. The remaining twenty checks stay at zero tolerance, severity
error.
  """,
  parent="PULSE-3", assignee=G, sprint=S5, points="3", components="Quality",
  labels="quality;thresholds", created="2026-05-05 11:15:00",
  resolved="2026-05-08 16:05:00",
  comments=[
    ("2026-05-06 15:30:00", G, "Thresholds are set above the current value with headroom, so they detect drift rather than restating today's number. A threshold set exactly at the observed value fails on the first ordinary fluctuation and we are back where we started."),
    ("2026-05-08 16:00:00", V, "Ran clean twice this week - twenty passes, four warnings, no errors. I read the whole report this morning, which is the actual measure of success here."),
  ]),

I("PULSE-43", "Story", "pytest warehouse fixture built from generated data", "Done",
  """
As the team
I want the test suite to build a real warehouse and query it
So that tests exercise the SQL rather than our assumptions about the SQL.

Acceptance criteria
* tests/conftest.py builds a session-scoped warehouse from a small seeded
  generated dataset
* the same DDL and the same transformation code as production
* no mocked query results anywhere in the suite
* full build and teardown under 30 seconds
  """,
  parent="PULSE-11", assignee=D, sprint=S5, points="5", components="Quality",
  labels="testing;fixtures", created="2026-04-28 09:30:00",
  resolved="2026-05-07 15:10:00",
  comments=[
    ("2026-04-30 10:20:00", D, "Session-scoped so we build once and share across the suite. Function scope was correct and took four minutes, which meant nobody would run it locally."),
    ("2026-05-07 15:05:00", G, "Accepted. Every bug we have had so far was in SQL that a mock would have happily agreed with."),
  ]),

I("PULSE-44", "Task", "Run the quality suite in CI", "Done",
  """
Add the quality suite to the CI pipeline after the warehouse build.

Acceptance criteria
* the suite runs on every push after the gold build
* a severity-error failure fails the build; a warning does not
* the results summary is printed in the job output, readable without
  downloading an artifact
  """,
  parent="PULSE-10", assignee=V, sprint=S5, points="3", components="CI;Quality",
  labels="ci;quality", created="2026-04-28 09:35:00", resolved="2026-05-06 14:20:00",
  comments=[
    ("2026-05-06 14:15:00", V, "Errors fail the build, warnings are printed. Now that the warning set means something (PULSE-42) this split actually works - before the re-tune this would have failed every build on day one."),
  ]),

# ---------------------------------------------------------------- Sprint 6
I("PULSE-45", "Story", "dim_date", "Done",
  """
As the model
I want a full date dimension
So that period comparisons and fiscal reporting stop being ad-hoc SQL.

Acceptance criteria
* database/warehouse/020_dim_date.sql covering the full data range plus two
  years forward
* calendar and fiscal attributes, ISO week, day of week, weekend flag,
  month and quarter start and end flags, holiday flag for the trading regions
* prior-period and prior-year keys precomputed
  """,
  parent="PULSE-4", assignee=D, sprint=S6, points="3", components="Warehouse",
  labels="gold;dimension", created="2026-05-11 09:20:00",
  resolved="2026-05-15 15:30:00",
  comments=[
    ("2026-05-13 10:15:00", D, "Precomputing the prior-period and prior-year keys. Every period-over-period query otherwise reinvents that join and about a third of them get the leap year or the ISO week boundary wrong."),
    ("2026-05-15 15:25:00", G, "Accepted."),
  ]),

I("PULSE-46", "Story", "Seven conformed dimensions with surrogate keys", "Done",
  """
As the model
I want conformed dimensions with surrogate keys
So that facts join consistently and a source key change does not break history.

Dimensions: date, customer, product, store, channel, campaign, geography.

Acceptance criteria
* database/warehouse/021_dimensions.sql
* surrogate integer key on each, natural key retained and indexed
* conformed - one customer dimension shared by every fact that needs it
* documented grain in each file header
  """,
  parent="PULSE-4", assignee=G, sprint=S6, points="8", components="Warehouse",
  labels="gold;dimension", created="2026-05-11 09:25:00",
  resolved="2026-05-21 16:40:00",
  comments=[
    ("2026-05-14 11:30:00", G, "Conformed is the word doing the work. One customer dimension, joined by orders, payments and events alike. The moment there are two, 'customers who bought' and 'customers who clicked' become unjoinable and nobody notices until the funnel numbers disagree."),
    ("2026-05-21 16:35:00", D, "All seven built and joining cleanly. Grain stated at the top of each block."),
  ]),

I("PULSE-47", "Task", "Unknown members on -1 for every dimension", "Done",
  """
Every dimension carries an Unknown member on surrogate key -1. Facts with an
unresolvable natural key join to it rather than being dropped or nulled.

Acceptance criteria
* -1 row in all seven dimensions with descriptive Unknown labels
* fact builds map unresolved keys to -1, never to null
* a quality check counts fact rows on -1 per dimension, so the volume of
  unresolved keys is a visible number rather than an invisible loss
  """,
  parent="PULSE-4", assignee=G, sprint=S6, points="2", components="Warehouse",
  labels="gold;dimension", created="2026-05-11 09:30:00",
  resolved="2026-05-19 14:20:00",
  comments=[
    ("2026-05-18 10:40:00", G, "The check counting rows on -1 is the point of the whole ticket. An Unknown member without a count is the same silent data loss as an inner join, just with better manners."),
    ("2026-05-19 14:15:00", D, "0.31% of order facts land on customer -1, which matches the seeded orphan ids exactly. Good - it means the number is real and we know what it is."),
  ]),

I("PULSE-48", "Story", "fact_orders at header grain", "Done",
  """
As the model
I want an order-grain fact table
So that order-level metrics are computed at order level.

Acceptance criteria
* one row per order
* net_amount, gross_amount, discount, shipping, tax, cost_amount
* is_revenue flag implementing the agreed revenue definition
* cancelled, returned and pending orders present and flagged, not filtered
* dimension keys resolved to surrogates, unresolved keys on -1
  """,
  parent="PULSE-4", assignee=D, sprint=S6, points="5", components="Warehouse",
  labels="gold;fact", created="2026-05-12 09:15:00", resolved="2026-05-20 15:50:00",
  comments=[
    ("2026-05-15 09:50:00", D, "Non-completed orders stay in the fact, flagged. Operations needs to see cancellations and returns, and filtering them here means building a second pipeline for operations later."),
    ("2026-05-20 15:45:00", G, "Accepted. is_revenue is defined once, in silver, and read here - not restated as a status list."),
  ]),

I("PULSE-49", "Story", "fact_sales at line grain", "Done",
  """
As the model
I want a line-grain sales fact alongside the header-grain order fact
So that product and basket analysis has the right grain to work at.

Acceptance criteria
* database/warehouse/022_fact_sales.sql, one row per order line
* line-level quantity, unit price, discount, net amount and cost
* line revenue sums to header revenue per order, within tolerance, and this
  is check number one in PULSE-40
* the file header states the grain and warns against header-grain metrics
  """,
  parent="PULSE-4", assignee=D, sprint=S6, points="5", components="Warehouse",
  labels="gold;fact", created="2026-05-12 09:20:00", resolved="2026-05-22 16:00:00",
  comments=[
    ("2026-05-18 14:10:00", V, "Genuine question rather than a challenge: two facts holding the same revenue looks like duplication. What stops them drifting apart?"),
    ("2026-05-18 14:35:00", G, "Reconciliation check one, which fails the build if they disagree by more than a penny per order. And the duplication is the point - see PULSE-50. The alternative is one line-grain fact and a standing invitation to compute AOV wrongly."),
    ("2026-05-22 15:55:00", D, "Both facts built, reconciliation green across the full demo range."),
  ]),

I("PULSE-50", "Task", "ADR-003: Two order grains, kept explicit", "Done",
  """
Decision: keep fact_orders at header grain and fact_sales at line grain, and
require every metric to name the grain it is computed at.

Rationale: header-grain metrics - AOV, orders per customer, basket size -
computed from line-grain rows are wrong in a way that produces a plausible
number and no error. Two explicit facts make the mistake structurally
impossible rather than merely discouraged in a code review.

Cost accepted: storage duplication of order-level values, and a reconciliation
check that must stay green.

Rejected alternative: one line-grain fact with a distinct-count discipline.
Rejected because the discipline lives in the head of whoever writes the query.
  """,
  parent="PULSE-4", assignee=G, sprint=S6, points="1", components="Docs",
  labels="adr;decision;modelling", created="2026-05-18 15:00:00",
  resolved="2026-05-21 11:30:00",
  comments=[
    ("2026-05-21 11:25:00", G, "Written up with Deven's duplication question as the rejected alternative, because it is the obvious objection and the ADR should answer it rather than pretend nobody raised it."),
  ]),

# ---------------------------------------------------------------- Sprint 7
I("PULSE-51", "Story", "fact_payments", "Done",
  """
As the business
I want a payment fact at attempt grain
So that gateway performance and payment failure are measurable.

Acceptance criteria
* database/warehouse/023_fact_payments.sql, one row per payment attempt
* attempt sequence number per order
* both success rate denominators supported: per attempt and per order
* gateway, method and failure reason as dimension attributes
  """,
  parent="PULSE-4", assignee=D, sprint=S7, points="5", components="Warehouse",
  labels="gold;fact", created="2026-05-25 09:20:00", resolved="2026-06-02 15:40:00",
  comments=[
    ("2026-05-28 10:30:00", D, "Attempt grain, with the sequence number, so a retried-then-succeeded payment is legible. Aggregating to order grain loses the retry story, which is the part the gateway conversation needs."),
    ("2026-06-02 15:35:00", G, "Accepted. This fact is what the real-time payment monitoring will reconcile against later."),
  ]),

I("PULSE-52", "Story", "fact_inventory and fact_events", "Done",
  """
As the model
I want inventory snapshots and clickstream events as facts
So that stock health and funnel analysis join to the same dimensions as sales.

Acceptance criteria
* 024_fact_inventory.sql - periodic snapshot grain, one row per product,
  location, date
* 025_fact_events.sql - transaction grain, one row per event
* both joined to conformed dimensions
* snapshot grain documented explicitly, because it is not additive over time
  """,
  parent="PULSE-4", assignee=D, sprint=S7, points="5", components="Warehouse",
  labels="gold;fact", created="2026-05-25 09:25:00", resolved="2026-06-04 16:20:00",
  comments=[
    ("2026-05-29 11:15:00", D, "Writing 'this is a periodic snapshot, do not sum stock_on_hand over dates' at the top of the inventory file in as many words. It is the single most common mistake against this table shape."),
    ("2026-06-04 16:15:00", G, "Accepted, and a semi-additive note goes into the KPI document as well."),
  ]),

I("PULSE-53", "Task", "Warehouse indexes and query plan review", "Done",
  """
Index the gold layer and review the plans for the queries the dashboards will
actually run.

Acceptance criteria
* database/warehouse/026_indexes.sql
* foreign key columns on every fact indexed
* date key indexed on every fact
* the ten most common dashboard query shapes reviewed on both engines
* before and after timings recorded in the ticket
  """,
  parent="PULSE-4", assignee=V, sprint=S7, points="3", components="Warehouse;Platform",
  labels="performance", created="2026-05-26 09:15:00", resolved="2026-06-03 14:50:00",
  comments=[
    ("2026-06-01 15:20:00", V, "Sales-by-region-by-month on the largest preset: 8.4s before, 0.6s after. The date key index does nearly all of that on its own."),
    ("2026-06-03 14:45:00", G, "Accepted. Worth rerunning this after the marts land, since the marts will change the query shapes considerably."),
  ]),

I("PULSE-54", "Story", "dim_customer_history with the SCD Type 2 shape", "Done",
  """
As the model
I want a Type 2 customer dimension in place, in the correct shape
So that adding real change capture later is a data problem, not a redesign.

Acceptance criteria
* valid_from, valid_to, is_current, version columns
* one version per customer for now, because the source ships no change history
* documented in the file header: the shape is real, the history is not, and
  what it would take to make it real
  """,
  parent="PULSE-4", assignee=G, sprint=S7, points="5", components="Warehouse",
  labels="gold;scd2", created="2026-05-26 09:20:00", resolved="2026-06-05 15:20:00",
  comments=[
    ("2026-05-29 10:05:00", V, "Is building a Type 2 table with one version per customer worth doing at all right now?"),
    ("2026-05-29 10:40:00", G, "Fair challenge. It is worth it because every consumer downstream writes its joins against the shape, and retrofitting valid_from into thirty existing queries is the expensive version. But I have written honestly in the header that the history is not real yet, so nobody builds a tier-at-time-of-purchase analysis on it and gets a confidently wrong answer. Real change capture is PULSE-119."),
    ("2026-06-05 15:15:00", D, "Built, and the header says exactly that. Accepted."),
  ]),

I("PULSE-55", "Story", "mart_sales_daily and mart_sales_monthly", "Done",
  """
As the business
I want daily and monthly sales marts
So that the recurring questions are answered without touching the facts.

Acceptance criteria
* 031_mart_sales_daily.sql and 032_mart_sales_monthly.sql
* revenue, orders, units, AOV, gross profit, margin percent
* AOV computed at header grain from fact_orders, per PULSE-25 and PULSE-50
* daily mart reconciles to fact_orders - reconciliation check two
* period-over-period and year-over-year comparisons using dim_date keys
  """,
  parent="PULSE-5", assignee=G, sprint=S7, points="5", components="Warehouse",
  labels="mart;sales", created="2026-05-27 09:20:00", resolved="2026-06-05 16:30:00",
  comments=[
    ("2026-06-01 11:40:00", G, "First mart, and the first place the AOV grain trap can actually bite. See PULSE-56 - it bit."),
    ("2026-06-05 16:25:00", D, "Reconciliation check two is green and the daily mart matches the fact across the full range."),
  ]),

I("PULSE-56", "Bug", "AOV reported 40% low - averaged from the line fact", "Done",
  """
Observed: AOV in the first draft of mart_sales_daily reads about 40% below the
figure finance calculates by hand.

Impact: none published - caught before the mart was released. Had it shipped,
it would have been quoted in the monthly review and would have looked entirely
plausible.

Cause: AOV was computed as AVG(net_amount) over fact_sales, which is line
grain. It is the average line value, not the average order value.

Fix: compute from fact_orders at header grain, per the definition written in
PULSE-25 in March. Add a quality check comparing mart AOV against a header
grain recomputation.
  """,
  parent="PULSE-5", assignee=G, reporter=D, priority="Highest", sprint=S7, points="3",
  components="Warehouse", labels="grain;kpi;aov", created="2026-06-01 11:45:00",
  resolved="2026-06-04 12:30:00",
  comments=[
    ("2026-06-01 11:50:00", D, "Spotted it because the number looked low against what finance quotes, not because anything failed. Which is exactly what PULSE-25 said would happen - there is no error for averaging the wrong grain."),
    ("2026-06-01 12:20:00", G, "We wrote the warning down in March and then walked straight into it in June. I am not treating that as a failure of the documentation - the document is how Divya knew to be suspicious. But it is the argument for the check, because documentation does not run nightly."),
    ("2026-06-02 09:35:00", V, "Adding my vote for the check. Two explicit facts (PULSE-50) made the mistake possible to detect; only an assertion makes it impossible to ship."),
    ("2026-06-04 12:25:00", G, "Fixed and the check is in. Retro item: any metric with a grain judgement in its definition gets an assertion when it is first implemented, not when it first goes wrong."),
  ]),

]
