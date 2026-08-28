# -*- coding: utf-8 -*-
"""Sprints 8-15 and the backlog, 08 Jun 2026 onwards. PULSE-57 .. PULSE-123.

Neha Chauhan (QA) joins 15 Jun 2026, mid Sprint 8.
Amit Shinde (BA) joins 24 Aug 2026, mid Sprint 13.
Today is 08 Sep 2026, inside Sprint 14.
"""

from backlog_common import (I, G, D, V, N, A, S8, S9, S10, S11, S12, S13, S14,
                            S15)

LATE = [

# ---------------------------------------------------------------- Sprint 8
I("PULSE-57", "Story", "Streamlit shell and the data access layer", "Done",
  """
As a stakeholder
I want one application with a page per subject area
So that I am not sent five different links.

Acceptance criteria
* dashboards/streamlit/app.py with multipage navigation
* dashboards/streamlit/data_access.py is the only module that talks to the
  warehouse - no page issues its own SQL
* query results cached with a documented TTL
* the as-of date from gold.analysis_window shown on every page
  """,
  parent="PULSE-5", assignee=D, sprint=S8, points="5", components="Dashboards",
  labels="dashboard", created="2026-06-08 09:20:00", resolved="2026-06-17 16:10:00",
  comments=[
    ("2026-06-10 10:30:00", D, "One data access module rather than SQL scattered through the pages. When a definition changes there is exactly one place to change it, and the pages stay about presentation."),
    ("2026-06-17 16:05:00", G, "Accepted. The as-of date on every page is not optional - if the platform's today is not the calendar's today, the page has to say so out loud."),
  ]),

I("PULSE-58", "Story", "Chart design system in theme.py", "Done",
  """
As a reader of these dashboards
I want every chart to follow the same visual rules
So that I can read a new chart without relearning what the colours mean.

Rules
* one palette, defined once, colour-blind safe, legible in light and dark
* one hue per entity, consistent across every page - a region is the same
  colour everywhere
* fixed categorical order, never sorted by value between renders
* sequential ramps for magnitude only, diverging only around a real midpoint
* no dual axes, ever
* direct labelling in preference to legends where the series count allows
  """,
  parent="PULSE-5", assignee=G, sprint=S8, points="5", components="Dashboards",
  labels="dashboard;design-system", created="2026-06-08 09:25:00",
  resolved="2026-06-18 15:30:00",
  comments=[
    ("2026-06-09 11:15:00", G, "Doing this before the first chart rather than after the thirtieth. Retrofitting consistency across a built estate is an order of magnitude more expensive, and half of it never gets done."),
    ("2026-06-12 14:20:00", D, "Fixed categorical order caught something already. A bar chart sorted by value redrew in a different order between two refreshes and I misread the change as a data problem for about ten minutes."),
    ("2026-06-18 15:25:00", G, "Merged. The no-dual-axis rule is the one I expect to be argued with most, and PULSE-59 records why it holds."),
  ]),

I("PULSE-59", "Task", "ADR-004: No dual axes, fixed categorical order", "Done",
  """
Decision: charts in this platform never use a secondary y-axis, and
categorical series keep a fixed declared order rather than sorting by value.

Rationale for no dual axes: the crossing point of two series on independent
scales is an artefact of the scales chosen, and readers consistently read it
as a real event. Where two measures must be compared, use two aligned charts
or index both to a common base.

Rationale for fixed order: a chart that reorders between renders makes change
detection unreliable, and a reader who has learned a layout should be able to
keep using it.

Cost accepted: some comparisons need two charts where one would have fit.
  """,
  parent="PULSE-5", assignee=G, sprint=S8, points="1", components="Docs",
  labels="adr;decision;design-system", created="2026-06-09 11:30:00",
  resolved="2026-06-15 12:00:00",
  comments=[
    ("2026-06-15 11:55:00", G, "Written up with the alternatives, so that when someone wants revenue and margin on one chart there is a documented answer rather than a debate."),
  ]),

I("PULSE-60", "Story", "mart_product_performance", "Done",
  """
As a category manager
I want product-level performance in one mart
So that assortment decisions do not need bespoke SQL each time.

Acceptance criteria
* 033_mart_product_performance.sql at product and month grain
* revenue, units, margin, return rate, rank within category
* contribution to category revenue, and a Pareto position
* built on fact_sales at line grain, which is the correct grain here
  """,
  parent="PULSE-5", assignee=D, sprint=S8, points="5", components="Warehouse",
  labels="mart;product", created="2026-06-08 09:30:00",
  resolved="2026-06-19 15:00:00",
  comments=[
    ("2026-06-16 10:50:00", D, "Line grain is right for this one, and I have said so in the header. After PULSE-56 I would rather every mart state which fact it is built on and why."),
    ("2026-06-19 14:55:00", G, "Accepted. That header convention should apply to all marts - please add it to the ones already built when you next touch them."),
  ]),

I("PULSE-61", "Task", "Prepare QA onboarding - access, environment and runbook", "Done",
  """
Get everything in place before the QA analyst starts on 15 Jun, so that day
one is doing the job rather than raising access tickets.

Checklist
* Jira, Confluence, GitHub and Slack access requested
* dev warehouse read role approved
* a written runbook: clone, venv, generate data, build warehouse, run tests,
  run the dashboards
* first-week goals agreed and written down
  """,
  parent="PULSE-11", assignee=G, sprint=S8, points="2", components="Platform",
  labels="onboarding", created="2026-06-09 09:00:00", resolved="2026-06-12 16:00:00",
  comments=[
    ("2026-06-09 09:30:00", V, "Access requests are in. GitHub and Slack are instant; the warehouse read role needs the data owner and that took nine days for Divya, so it is raised now."),
    ("2026-06-12 15:55:00", G, "Runbook written and dry-run by Deven from a clean machine. First-week goal is deliberately narrow: build the warehouse, run the suite, and write down what is not covered."),
  ]),

I("PULSE-62", "Task", "QA onboarding - Neha Chauhan", "Done",
  """
First week for the QA analyst joining 15 Jun 2026.

* environment up and warehouse built locally
* full pipeline and quality suite run end to end
* walkthrough of the medallion layers, the KPI contract and the four ADRs
* produce a written gap analysis: what the current tests do not cover
  """,
  parent="PULSE-11", assignee=N, sprint=S8, points="3", components="Quality",
  labels="onboarding", created="2026-06-15 09:30:00", resolved="2026-06-19 16:30:00",
  comments=[
    ("2026-06-15 14:20:00", N, "Environment is up and the warehouse built on the second attempt - the first failed because I had not run the generator first. Worth one line in the runbook, since it is the kind of thing that is obvious once you know it."),
    ("2026-06-17 11:40:00", N, "Read through the KPI document and the ADRs. The thing that stands out is that most of the past bugs were silent rather than loud, so my gap analysis is going to be mostly about assertions between layers rather than more unit tests."),
    ("2026-06-19 16:25:00", N, "Gap analysis written. Three areas with no coverage at all: the dashboards, the analytics modules, and anything asserting that ops tables survive a rebuild. The third one worries me most because a rebuild is routine."),
    ("2026-06-19 16:45:00", G, "That third point is a good instinct and it is now PULSE-86. Welcome aboard."),
  ]),

I("PULSE-63", "Story", "Test strategy and regression scope by layer", "Done",
  """
As the team
I want a written statement of what is tested at each layer
So that "covered" means something specific rather than a count of tests.

Acceptance criteria
* per layer - bronze, silver, gold, marts, analytics, dashboards, streaming -
  what is asserted, what is deliberately not, and why
* the difference between the quality suite and the test suite stated plainly
* the regression pack per layer identified, and gaps listed as tickets
  """,
  parent="PULSE-11", assignee=N, sprint=S8, points="5", components="Quality",
  labels="testing;strategy", created="2026-06-16 09:15:00",
  resolved="2026-06-19 15:40:00",
  comments=[
    ("2026-06-17 10:10:00", N, "Drawing the line as: the quality suite asserts things about the data on every run; the test suite asserts things about the code on every push. Both matter and they are not substitutes, which is not obvious from the outside."),
    ("2026-06-18 14:30:00", D, "That distinction is clearer than how we had been describing it internally. Worth putting in the README rather than only in the strategy doc."),
    ("2026-06-19 15:35:00", G, "Approved."),
  ]),

# ---------------------------------------------------------------- Sprint 9
I("PULSE-64", "Story", "Executive dashboard page", "Done",
  """
As an executive
I want revenue, margin, orders and growth on one page
So that the monthly review starts from an agreed number.

Acceptance criteria
* headline tiles: revenue, gross margin percent, orders, AOV, each with a
  period-over-period comparison
* revenue trend with a prior-year comparison series
* top and bottom performing categories and regions
* every tile traceable to a definition in the KPI document
* as-of date visible
  """,
  parent="PULSE-5", assignee=G, sprint=S9, points="5", components="Dashboards",
  labels="dashboard;executive", created="2026-06-22 09:20:00",
  resolved="2026-07-02 16:00:00",
  comments=[
    ("2026-06-25 11:20:00", G, "Every tile links to its definition. If someone disagrees with a number, the argument should start at the definition rather than at the chart."),
    ("2026-07-01 10:15:00", N, "Tested against a hand-computed set from the generated data. All tiles match. One note: the period-over-period comparison on the first day of a month compares against a single day, which is technically correct and reads as a 90% collapse."),
    ("2026-07-02 15:55:00", G, "Good catch. Added a partial-period label to the comparison rather than hiding it - the reader needs to know the period is incomplete, not be protected from it."),
  ]),

I("PULSE-65", "Story", "Sales dashboard page", "Done",
  """
As a sales manager
I want to explore sales by product, region, channel and time
So that I can answer my own questions without raising a request.

Acceptance criteria
* filters: date range, region, channel, category
* trend, breakdown by dimension, product table with sortable measures
* drill from category to product
* filters reflected in every chart on the page, with the active filter set
  stated in plain language
  """,
  parent="PULSE-5", assignee=D, sprint=S9, points="8", components="Dashboards",
  labels="dashboard;sales", created="2026-06-22 09:25:00",
  resolved="2026-07-03 15:30:00",
  comments=[
    ("2026-06-29 14:40:00", D, "Stating the active filters in a sentence at the top of the page. Screenshots of filtered dashboards get pasted into decks with no indication of what was filtered, and then argued about."),
    ("2026-07-02 11:05:00", N, "Filter combinations tested including the empty result case, which previously rendered an empty chart with no explanation. Now shows a message saying no data matches."),
    ("2026-07-03 15:25:00", G, "Accepted."),
  ]),

I("PULSE-66", "Bug", "Dual-axis chart on the sales page", "Done",
  """
Observed: the revenue-and-margin chart on the sales page uses a secondary
y-axis, against ADR-004.

Impact: the two series cross in September in the demo data. The crossing point
is an artefact of the two scales and reads as a real event.

Fix: split into two aligned charts sharing an x-axis.
  """,
  parent="PULSE-5", assignee=D, reporter=N, priority="Medium", sprint=S9, points="2",
  components="Dashboards", labels="design-system;dashboard",
  created="2026-06-30 10:20:00", resolved="2026-07-02 14:10:00",
  comments=[
    ("2026-06-30 10:25:00", N, "Raising this from ADR-004 rather than from taste. The ADR says never, and reviewing against a written rule is much easier than reviewing against an opinion."),
    ("2026-06-30 11:40:00", D, "Guilty - it was the quickest way to get both series in one place and I talked myself into it. Splitting into two aligned charts."),
    ("2026-07-02 14:05:00", G, "Fixed and verified. This is the ADR earning its keep in a code review, which is exactly what it is for."),
  ]),

I("PULSE-67", "Story", "mart_regional_store", "Done",
  """
As a regional manager
I want regional and store performance in one mart
So that comparisons between stores are consistent.

Acceptance criteria
* 038_mart_regional_store.sql at region, store and month grain
* revenue in reporting and local currency
* like-for-like comparison excluding stores open less than 13 months, with
  the exclusion count exposed rather than silent
  """,
  parent="PULSE-5", assignee=D, sprint=S9, points="5", components="Warehouse",
  labels="mart;regional", created="2026-06-23 09:15:00",
  resolved="2026-07-01 15:20:00",
  comments=[
    ("2026-06-26 10:30:00", D, "Like-for-like exposes how many stores were excluded and why. A like-for-like number without that count is an unfalsifiable claim."),
    ("2026-07-01 15:15:00", G, "Accepted, and local currency alongside reporting currency as agreed in PULSE-34."),
  ]),

I("PULSE-68", "Story", "Dashboard smoke tests", "Done",
  """
As the team
I want automated checks that every page renders and its numbers match the
warehouse
So that a mart change cannot silently break a page.

Acceptance criteria
* tests/test_dashboards.py imports each page and exercises its data functions
* headline tile values asserted against a direct warehouse query
* runs in CI
* a broken page fails the build
  """,
  parent="PULSE-11", assignee=N, sprint=S9, points="5", components="Quality;Dashboards",
  labels="testing;dashboard", created="2026-06-23 09:20:00",
  resolved="2026-07-03 16:10:00",
  comments=[
    ("2026-06-29 11:50:00", N, "Asserting the tile values against a direct query rather than only that the page renders. A page that renders confidently wrong numbers is worse than one that crashes."),
    ("2026-07-03 16:05:00", D, "Merged and green. It caught a stale column reference on the sales page during development, which is the first time a dashboard bug has been caught by CI rather than by a person."),
  ]),

I("PULSE-69", "Bug", "Executive page 4x slower after the region filter landed", "Done",
  """
Observed: executive page load went from about 1.1s to 4.6s on the largest
preset after the region filter was added.

Cause: the filter was applied in Python after loading the full unfiltered
result set, and the cache key did not include the filter values, so every
filter change was a cache miss on a full scan.

Fix: push the filter into SQL, include filter values in the cache key.
  """,
  parent="PULSE-5", assignee=V, reporter=N, priority="Medium", sprint=S9, points="3",
  components="Dashboards;Platform", labels="performance",
  created="2026-06-29 15:10:00", resolved="2026-07-02 11:20:00",
  comments=[
    ("2026-06-29 15:15:00", N, "Noticed on the largest preset, which is why it is worth testing against something bigger than the demo set. On the demo data it is imperceptible."),
    ("2026-07-02 11:15:00", V, "Filter pushed into SQL, cache key fixed. Back to 0.9s, slightly better than before because the filtered query touches less data."),
  ]),

I("PULSE-70", "Story", "mart_executive", "Done",
  """
As the executive page
I want a purpose-built mart
So that headline tiles are one small read rather than several large ones.

Acceptance criteria
* 041_mart_executive.sql, pre-aggregated to the tile grain
* period-over-period and year-over-year precomputed
* reconciles to mart_sales_daily, added as a reconciliation check
  """,
  parent="PULSE-5", assignee=G, sprint=S9, points="3", components="Warehouse",
  labels="mart;executive", created="2026-06-24 09:15:00",
  resolved="2026-07-03 14:40:00",
  comments=[
    ("2026-07-03 14:35:00", G, "Reconciliation against the daily mart added, so a pre-aggregation that drifts from its source fails the build rather than quietly disagreeing with the sales page."),
  ]),

# --------------------------------------------------------------- Sprint 10
I("PULSE-71", "Story", "mart_customer_360", "Done",
  """
As the business
I want one row per customer with their full commercial picture
So that customer questions have a single starting point.

Acceptance criteria
* 034_mart_customer_360.sql, one row per customer
* first and last order date, lifetime orders, lifetime revenue, average order
  value at header grain, tenure, recency, preferred category and channel
* recency anchored to gold.analysis_window
* customers with no orders present, not filtered out
  """,
  parent="PULSE-6", assignee=G, sprint=S10, points="5", components="Warehouse",
  labels="mart;customer", created="2026-07-06 09:20:00",
  resolved="2026-07-15 15:40:00",
  comments=[
    ("2026-07-08 10:20:00", G, "Zero-order customers stay in. They are the denominator of activation, and filtering them here is how activation problems become invisible - see PULSE-74, which is the same mistake in a different costume."),
    ("2026-07-15 15:35:00", D, "Accepted. Every recency column reads analysis_window, verified by the CURRENT_DATE test."),
  ]),

I("PULSE-72", "Story", "mart_rfm_segments", "Done",
  """
As marketing
I want customers scored and segmented on recency, frequency and monetary value
So that campaigns can target behaviour rather than guesswork.

Acceptance criteria
* 035_mart_rfm_segments.sql with quintile scores on each axis
* named segments - Champions, Loyal, At Risk, Hibernating, Lost, New
* segment boundaries defined in the KPI document, not only in SQL
* recency anchored to analysis_window
* segment sizes stable between runs on the same data
  """,
  parent="PULSE-6", assignee=D, sprint=S10, points="5", components="Warehouse",
  labels="mart;customer;rfm", created="2026-07-06 09:25:00",
  resolved="2026-07-16 16:00:00",
  comments=[
    ("2026-07-10 11:30:00", D, "Quintiles over the active customer base rather than fixed thresholds, so the segmentation stays meaningful as the business grows. Documented, because it means a customer can change segment without changing behaviour if the base shifts around them."),
    ("2026-07-14 09:45:00", N, "Ran the segmentation twice on the same dataset and got identical sizes. That is only true because of the analysis window - worth a regression test, so I have put it in the customer pack."),
    ("2026-07-16 15:55:00", G, "Accepted, and the boundary definitions are in the KPI document."),
  ]),

I("PULSE-73", "Story", "mart_cohort_retention", "Done",
  """
As the business
I want monthly acquisition cohorts and their retention curves
So that we can see whether retention is improving.

Acceptance criteria
* 036_mart_cohort_retention.sql at cohort month and period number grain
* cohort defined by first purchase month - see PULSE-74
* retention as active customers in period divided by cohort size
* the same dataset produces the same curve on every run
  """,
  parent="PULSE-6", assignee=G, sprint=S10, points="5", components="Warehouse",
  labels="mart;customer;cohort", created="2026-07-07 09:15:00",
  resolved="2026-07-17 15:10:00",
  comments=[
    ("2026-07-13 14:20:00", G, "First version was built on signup month and produced a retention cliff at month one that nobody could explain. See PULSE-74."),
    ("2026-07-17 15:05:00", D, "Rebuilt on first purchase month. The curve is now smooth and, more importantly, it is stable across runs."),
  ]),

I("PULSE-74", "Bug", "Cohorts defined on signup month show an activation problem as churn", "Done",
  """
Observed: cohorts built on signup month show a retention cliff of roughly 60%
between period 0 and period 1.

Diagnosis: it is not a retention problem. A large share of signups never
purchase at all, so they enter a cohort and leave it without ever having been
a customer. The cliff is the activation rate wearing a retention costume, and
it was about to be presented to the board as a retention crisis.

Fix: define a cohort by the month of first purchase, so cohort membership
means "became a customer". Activation is a separate metric, defined
separately, and it is a real problem worth its own workstream.
  """,
  parent="PULSE-6", assignee=G, reporter=G, priority="High", sprint=S10, points="3",
  components="Warehouse", labels="definitions;cohort;customer",
  created="2026-07-13 14:25:00", resolved="2026-07-16 12:00:00",
  comments=[
    ("2026-07-13 14:50:00", D, "This is the second time a definition choice has produced a plausible and completely misleading picture. The first was AOV. Both were caught by someone thinking the number looked odd rather than by anything automated."),
    ("2026-07-14 09:20:00", G, "Right, and I do not think that is fully fixable with assertions - a definition can be internally consistent and still answer the wrong question. What we can do is require every cohort-shaped metric to state its membership rule on the chart itself, so a reader can catch what a test cannot."),
    ("2026-07-14 15:30:00", N, "I can assert the mechanical part: cohort size must equal the count of customers whose first order falls in that month. That catches a regression even if it cannot catch a bad definition."),
    ("2026-07-16 11:55:00", G, "Both done. And the activation finding goes to the business as a finding rather than being quietly absorbed into a definition change - it is genuinely the more useful discovery of the two."),
  ]),

I("PULSE-75", "Story", "mart_churn_monthly", "Done",
  """
As retention
I want a monthly churn view with a stated definition
So that churn is measurable and arguable on the definition rather than the
number.

Acceptance criteria
* churn defined for a non-contractual business: no purchase within the
  customer's expected repurchase window, defined per segment
* the definition and its judgement calls written into the KPI document
* monthly churned count, churn rate and revenue at risk
* anchored to analysis_window
  """,
  parent="PULSE-6", assignee=D, sprint=S10, points="5", components="Warehouse",
  labels="mart;customer;churn", created="2026-07-07 09:20:00",
  resolved="2026-07-17 16:20:00",
  comments=[
    ("2026-07-09 10:40:00", D, "Churn in a non-contractual setting is a judgement, not an observation. Nobody cancels - they just stop. Writing the window rule down with its arbitrariness admitted rather than presenting it as measured fact."),
    ("2026-07-17 16:15:00", G, "Accepted. Per-segment windows rather than one global window, since a weekly-grocery customer and an annual-electronics customer are not comparable on a single threshold."),
  ]),

I("PULSE-76", "Story", "CLV curves", "Done",
  """
As marketing
I want customer lifetime value by cohort and channel
So that acquisition spend can be judged against what a customer is worth.

Acceptance criteria
* analytics/customer/clv.py with an explainable formula: average order value,
  purchase frequency, expected lifespan, margin
* cumulative realised value curves by cohort, not only a projected figure
* the projection horizon stated and the assumption labelled on the chart
  """,
  parent="PULSE-6", assignee=G, sprint=S10, points="5", components="Analytics",
  labels="customer;clv", created="2026-07-08 09:15:00",
  resolved="2026-07-17 14:50:00",
  comments=[
    ("2026-07-11 11:20:00", G, "An explainable formula over a fitted probabilistic model. Marketing has to defend an acquisition budget with this number, and a number they cannot explain is a number they cannot defend."),
    ("2026-07-15 10:30:00", D, "Realised curves alongside the projection, which is the honest version - the projection is an assumption and the realised curve is a measurement, and they should not look alike on a chart."),
    ("2026-07-17 14:45:00", G, "Accepted."),
  ]),

I("PULSE-77", "Task", "Regression pack for the customer marts", "Done",
  """
Regression coverage for customer_360, RFM, cohort retention and churn.

Assertions
* customer_360 row count equals distinct customers in the dimension
* RFM segment sizes sum to the active customer count
* cohort size equals distinct customers whose first order is in that month
* every recency metric changes when analysis_window moves, and not otherwise
* two consecutive runs on the same data produce identical output
  """,
  parent="PULSE-11", assignee=N, sprint=S10, points="5", components="Quality",
  labels="testing;customer", created="2026-07-08 09:20:00",
  resolved="2026-07-17 16:40:00",
  comments=[
    ("2026-07-14 15:35:00", N, "The determinism assertion is the one I care most about. It is the property that makes every other test meaningful, and it is invisible until it breaks."),
    ("2026-07-17 16:35:00", G, "Agreed and accepted. That assertion is effectively a test of ADR-002 rather than of any one mart."),
  ]),

# --------------------------------------------------------------- Sprint 11
I("PULSE-78", "Story", "Customer dashboard page", "Done",
  """
As marketing and retention
I want the customer analytics on one page
So that segments, cohorts and value are read together.

Acceptance criteria
* RFM segment overview with sizes and revenue contribution
* cohort retention heatmap using a sequential ramp, magnitude only
* CLV curves by cohort, projection visually distinct from realised
* churn trend with the definition stated on the page
* segment membership rule visible on the cohort chart, per PULSE-74
  """,
  parent="PULSE-6", assignee=D, sprint=S11, points="5", components="Dashboards",
  labels="dashboard;customer", created="2026-07-20 09:20:00",
  resolved="2026-07-30 16:00:00",
  comments=[
    ("2026-07-24 11:15:00", D, "Sequential ramp on the heatmap, single hue. Retention is a magnitude, and a diverging palette here would invent a midpoint that does not exist."),
    ("2026-07-29 10:20:00", N, "Verified every figure on the page against the marts. Also checked the empty-segment case, which now renders a labelled empty state rather than a blank panel."),
    ("2026-07-30 15:55:00", G, "Accepted."),
  ]),

I("PULSE-79", "Story", "Event bus abstraction with two implementations", "Done",
  """
As the platform
I want one bus interface with a file-based and a Kafka implementation
So that streaming can be developed and tested without a broker.

Acceptance criteria
* streaming/bus.py defines publish, subscribe and commit
* NDJSON file implementation for local development and CI
* Kafka/Redpanda implementation for the deployed path
* the same consumer code runs against both, unmodified
* offsets persisted per consumer group in both implementations
  """,
  parent="PULSE-7", assignee=V, sprint=S11, points="8", components="Streaming",
  labels="streaming;architecture", created="2026-07-20 09:25:00",
  resolved="2026-07-30 17:00:00",
  comments=[
    ("2026-07-22 10:30:00", V, "One interface, two implementations. Without the file implementation, CI needs a broker and every test becomes slow and flaky, and the streaming layer ends up as the untested corner of the platform."),
    ("2026-07-28 14:10:00", N, "This is the difference between me being able to test the streaming path and not. Running the consumer against files in CI is exactly the same code path as against Redpanda."),
    ("2026-07-30 16:55:00", G, "Accepted."),
  ]),

I("PULSE-80", "Story", "Four correlated event topics and the producer", "Done",
  """
As the platform
I want a producer emitting correlated orders, payments, inventory and
clickstream events
So that the real-time layer can be built and tested against realistic traffic.

Acceptance criteria
* streaming/events.py defines the schemas with an explicit event_time
* correlation is real - a payment event references an order event that exists,
  an inventory movement follows a sale
* configurable rate, and a burst mode for load testing
* a replayable seeded mode producing an identical stream
  """,
  parent="PULSE-7", assignee=V, sprint=S11, points="5", components="Streaming",
  labels="streaming;generator", created="2026-07-21 09:15:00",
  resolved="2026-07-31 15:30:00",
  comments=[
    ("2026-07-24 15:40:00", V, "Correlation matters as much here as in the batch generator. Uncorrelated events make the funnel and the payment success rate meaningless, and both are the metrics this layer exists to serve."),
    ("2026-07-31 15:25:00", D, "Replay mode is what makes the KPI assertions possible - same seed, same stream, same numbers."),
  ]),

I("PULSE-81", "Task", "Redpanda in docker-compose", "Done",
  """
Add Redpanda to docker-compose so the Kafka path is exercised locally with the
same code that will run deployed.

Acceptance criteria
* single-node Redpanda alongside Postgres
* topics created on startup
* documented switch between the file bus and the Kafka bus by environment
  variable only
  """,
  parent="PULSE-10", assignee=V, sprint=S11, points="3", components="Platform;Streaming",
  labels="docker;streaming", created="2026-07-21 09:20:00",
  resolved="2026-07-28 14:30:00",
  comments=[
    ("2026-07-28 14:25:00", V, "Redpanda rather than full Kafka for local - Kafka API compatible, one container, no ZooKeeper. The deployed target is Event Hubs, which speaks the same protocol."),
  ]),

I("PULSE-82", "Story", "Micro-batched consumer with offsets committed after write", "Done",
  """
As the platform
I want a consumer that commits offsets only after a successful write
So that a crash loses no events.

Acceptance criteria
* micro-batches by count or time window, whichever comes first
* offset committed only after the batch is written and the transaction commits
* at-least-once delivery, with idempotent writes keyed on event id
* a crash mid-batch is tested and reprocesses without duplicating
  """,
  parent="PULSE-7", assignee=V, sprint=S11, points="8", components="Streaming",
  labels="streaming;consumer", created="2026-07-22 09:15:00",
  resolved="2026-07-31 16:40:00",
  comments=[
    ("2026-07-27 11:20:00", V, "At-least-once with idempotent writes rather than chasing exactly-once. Exactly-once here would mean a distributed transaction across the broker and the warehouse for a KPI window that recomputes anyway."),
    ("2026-07-30 15:10:00", N, "Wrote the crash test - kill the consumer mid-batch, restart, assert no duplicates and no gaps. It passes, and it failed the first time against an earlier build where the commit came first, so the test is doing real work."),
    ("2026-07-31 16:35:00", G, "Accepted."),
  ]),

I("PULSE-83", "Task", "Event-time windowing, not wall clock", "Done",
  """
All real-time KPI windows are computed on event_time carried in the event, not
on the time the consumer processed it.

Rationale: a replayed stream must reproduce exactly the KPIs it produced live.
Wall-clock windowing makes the real-time layer untestable, because the answer
depends on when you ran it.

Acceptance criteria
* every window derives from event_time
* late-arriving events assigned to their true window within a stated
  allowed-lateness bound, and counted when they fall outside it
* a replay test asserts identical KPIs from an identical stream
  """,
  parent="PULSE-7", assignee=V, sprint=S11, points="5", components="Streaming",
  labels="streaming;reproducibility", created="2026-07-22 09:20:00",
  resolved="2026-07-31 17:00:00",
  comments=[
    ("2026-07-23 09:50:00", V, "This is ADR-002 applied to the streaming layer. Same principle, same reason: anchor to the data, not to the clock."),
    ("2026-07-31 16:58:00", N, "Replay test asserts identical KPI output across two runs of the same seeded stream. Green."),
  ]),

# --------------------------------------------------------------- Sprint 12
I("PULSE-84", "Story", "ops.stream_events and ops.realtime_kpis", "Done",
  """
As the platform
I want landed stream events and a recomputed KPI window in the warehouse
So that real-time metrics are queried the same way as batch metrics.

Acceptance criteria
* ops.stream_events as the landing table, with event id, type, event_time,
  ingest time and payload
* ops.realtime_kpis holding the current window, recomputed per micro-batch
* every KPI defined in SQL, not in the consumer - see the epic
* real-time revenue reconciles to batch revenue for a closed period
  """,
  parent="PULSE-7", assignee=V, sprint=S12, points="5", components="Streaming;Warehouse",
  labels="streaming;ops", created="2026-08-03 09:20:00",
  resolved="2026-08-12 16:00:00",
  comments=[
    ("2026-08-05 10:15:00", V, "The consumer lands events and triggers a recompute. It does not know what revenue means, and it must not - that is the only way one definition survives two pipelines."),
    ("2026-08-12 15:55:00", G, "Reconciliation between the real-time window and the batch fact for a closed day is green. That check is the proof the two pipelines agree."),
  ]),

I("PULSE-85", "Bug", "Batch rebuild silently wipes the streaming landing zone", "Done",
  """
Observed: after a routine full warehouse rebuild, ops.stream_events was empty
and the real-time dashboard showed zeros. No error anywhere.

Impact: about four hours of landed events lost. In a deployed system this is a
3am page and a hole in the record that nothing can reconstruct.

Cause: ops tables were created alongside the bronze tables using DROP TABLE IF
EXISTS followed by CREATE TABLE. The batch rebuild therefore dropped and
recreated the streaming landing zone as a side effect.

Fix
* ops.* tables use CREATE TABLE IF NOT EXISTS and are never dropped by a
  pipeline stage
* ops DDL moved out of the bronze init path entirely
* a test asserts that a full batch rebuild leaves ops.stream_events row counts
  unchanged
  """,
  parent="PULSE-7", assignee=V, reporter=D, priority="Highest", sprint=S12, points="5",
  components="Streaming;ETL", labels="data-loss;coupling",
  created="2026-08-06 09:40:00", resolved="2026-08-11 15:20:00",
  comments=[
    ("2026-08-06 09:45:00", D, "Real-time page was showing zeros this morning. I had run a full rebuild last night to pick up the new mart. Everything looked healthy - the rebuild succeeded, the quality suite passed, and four hours of events were simply gone."),
    ("2026-08-06 10:30:00", V, "Found it. ops tables were being created in the same file as the bronze tables with DROP and CREATE. A batch job that can destroy the streaming layer is exactly the kind of coupling that causes a 3am page, and it has been sitting there since PULSE-22 in March."),
    ("2026-08-06 11:15:00", G, "This one goes in the retro properly. Both destructive DDL and cross-layer coupling, and neither the quality suite nor the test suite could see it because both only look at the warehouse after a successful build."),
    ("2026-08-06 14:20:00", N, "This is the gap I flagged on my first week - nothing asserts that ops tables survive a rebuild (PULSE-86). Writing that test now, and it fails against the current main, which is what I wanted to confirm."),
    ("2026-08-11 15:15:00", V, "Fixed. ops DDL is out of the bronze path, everything is IF NOT EXISTS, and Neha's test is green. Also grepped the whole repo for DROP TABLE - two other places, both in test teardown, both fine."),
  ]),

I("PULSE-86", "Task", "Test that a batch rebuild cannot destroy the ops schema", "Done",
  """
Assert the isolation between the batch and streaming layers.

Assertions
* land events, run a full batch rebuild, assert ops.stream_events row count is
  unchanged
* same for ops.realtime_kpis, ops.pipeline_runs and ops.data_quality_results
* no pipeline stage issues DROP against the ops schema, asserted by scanning
  the DDL
  """,
  parent="PULSE-11", assignee=N, sprint=S12, points="3", components="Quality",
  labels="testing;streaming", created="2026-08-06 14:25:00",
  resolved="2026-08-11 14:40:00",
  comments=[
    ("2026-08-07 10:20:00", N, "The DDL scan is worth having alongside the behavioural test. The behavioural test catches it happening; the scan catches someone reintroducing the pattern in a file that is not yet wired in."),
    ("2026-08-11 14:35:00", V, "Both green. Between this and the CURRENT_DATE scan we now have two structural assertions that catch a whole class of mistake rather than one instance of it."),
  ]),

I("PULSE-87", "Story", "Real-time dashboard page", "Done",
  """
As operations
I want a live view of orders, payments, inventory movement and site activity
So that a gateway degradation is visible within minutes rather than the next
morning.

Acceptance criteria
* current-window KPIs: orders per minute, revenue rate, payment success rate,
  active sessions
* auto-refresh with the last update time and the window shown
* payment success rate against its recent baseline, so a drop is legible
* explicit indication when the stream is stale rather than showing an old
  number as if it were current
  """,
  parent="PULSE-7", assignee=D, sprint=S12, points="5", components="Dashboards;Streaming",
  labels="dashboard;streaming", created="2026-08-04 09:15:00",
  resolved="2026-08-14 16:30:00",
  comments=[
    ("2026-08-10 11:30:00", D, "The staleness indicator is the important part. A real-time dashboard silently showing a fifteen-minute-old number is worse than one that says the feed is down, because people act on it."),
    ("2026-08-13 14:15:00", N, "Tested by stopping the producer. The page flags stale after the configured threshold and stops presenting the window as current."),
    ("2026-08-14 16:25:00", G, "Accepted. This closes the original problem statement - Friday evening gateway degradation is now visible in minutes."),
  ]),

I("PULSE-88", "Story", "Real-time API for non-dashboard consumers", "Done",
  """
As another system
I want to read current real-time KPIs over an API
So that the dashboard is not the only way to consume them.

Acceptance criteria
* streaming/processors/realtime_api.py exposes the current window
* reads ops.realtime_kpis - it does not recompute anything
* window and last-update timestamp included in every response
* stale window returns a clear staleness indicator rather than an old value
  """,
  parent="PULSE-7", assignee=V, sprint=S12, points="3", components="Streaming",
  labels="streaming;api", created="2026-08-04 09:20:00",
  resolved="2026-08-13 15:40:00",
  comments=[
    ("2026-08-13 15:35:00", V, "Reads the same table the dashboard reads. A second consumer that recomputes is a second definition, and we have been strict about that everywhere else."),
  ]),

I("PULSE-89", "Story", "mart_funnel_payments", "Done",
  """
As operations
I want funnel conversion and payment performance in one mart
So that drop-off and payment failure are analysed together.

Acceptance criteria
* 040_mart_funnel_payments.sql
* funnel stages from session through view, cart, checkout to purchase
* payment success rate on both denominators, labelled
* failure reasons broken down by gateway and method
  """,
  parent="PULSE-5", assignee=D, sprint=S12, points="5", components="Warehouse",
  labels="mart;funnel;payments", created="2026-08-05 09:15:00",
  resolved="2026-08-14 15:10:00",
  comments=[
    ("2026-08-11 10:40:00", D, "Both payment success denominators appear on the page with their labels, per PULSE-30. One number here would get quoted in the gateway negotiation and be the wrong one."),
    ("2026-08-14 15:05:00", G, "Accepted."),
  ]),

# --------------------------------------------------------------- Sprint 13
I("PULSE-90", "Story", "mart_campaign_performance and mart_channel_performance", "Done",
  """
As marketing
I want campaign and channel performance with spend, revenue and ROAS
So that budget conversations start from a shared table.

Acceptance criteria
* 037_mart_marketing.sql building both marts
* spend, impressions, clicks, sessions, orders, revenue, ROAS, CPA
* the attribution basis of every revenue column named in the column name
  itself, not only in documentation
* unattributed revenue shown as its own line rather than distributed
  """,
  parent="PULSE-8", assignee=G, sprint=S13, points="5", components="Warehouse",
  labels="mart;marketing", created="2026-08-17 09:20:00",
  resolved="2026-08-26 16:00:00",
  comments=[
    ("2026-08-19 10:30:00", G, "Attribution basis goes in the column name - revenue_last_touch, not revenue. A column called revenue in a marketing mart is a lie by omission, because it is always attributed somehow."),
    ("2026-08-21 14:20:00", D, "Unattributed revenue as its own line, currently 34% of the total. Distributing it proportionally would have hidden the single most important caveat about this whole mart."),
    ("2026-08-26 15:55:00", G, "Accepted."),
  ]),

I("PULSE-91", "Story", "Publish five attribution models side by side", "Done",
  """
As marketing
I want the same revenue attributed five ways, presented together
So that budget decisions account for the uncertainty rather than ignoring it.

Models: first touch, last touch, linear, time decay, position based.

Acceptance criteria
* analytics/marketing/attribution.py computes all five over the same events
* output is one table, one row per channel, one column per model
* an upper_funnel_bias measure: first-touch credit minus last-touch credit,
  which identifies channels that a last-touch budget will systematically
  starve
* no default model, and no blended number anywhere in the output
  """,
  parent="PULSE-8", assignee=G, priority="High", sprint=S13, points="8",
  components="Analytics", labels="marketing;attribution",
  created="2026-08-17 09:25:00", resolved="2026-08-28 16:00:00",
  comments=[
    ("2026-08-18 11:15:00", G, "No model here is correct. Publishing one would be a confident answer to a question we cannot answer, and it would immediately become the number - so we publish five and make the spread the finding."),
    ("2026-08-24 15:30:00", D, "The spread is the finding. One influencer channel comes out at 1.8x ROAS on last touch and 6.1x on first touch. It has been having its budget cut for two quarters on the last-touch figure."),
    ("2026-08-25 10:20:00", A, "Joined yesterday and this is the first thing I have been walked through. From the business side, the useful reframing is that the question is not which model is right - it is which channels the models disagree about, because those are the ones where the budget decision is actually a bet."),
    ("2026-08-25 11:05:00", G, "That is a better articulation than mine and I am putting it on the dashboard."),
    ("2026-08-28 15:55:00", G, "Shipped. The upper_funnel_bias column makes the disagreement sortable, which turns a caveat into something actionable."),
  ]),

I("PULSE-92", "Story", "mart_acquisition_channel and LTV:CAC", "Done",
  """
As marketing
I want lifetime value against acquisition cost by channel
So that acquisition spend is judged on what the customer becomes, not on the
first order.

Acceptance criteria
* 039_mart_acquisition_channel.sql joining first-touch acquisition to CLV
* LTV:CAC ratio per channel with the payback period
* cohort-based realised value alongside the projection
* the projection horizon stated wherever the ratio appears
  """,
  parent="PULSE-8", assignee=D, sprint=S13, points="5", components="Warehouse;Analytics",
  labels="marketing;clv", created="2026-08-18 09:15:00",
  resolved="2026-08-27 15:40:00",
  comments=[
    ("2026-08-24 11:40:00", D, "Two channels have a strong first-order ROAS and a poor LTV:CAC. That inversion is the argument for this mart existing separately from the campaign mart."),
    ("2026-08-27 15:35:00", G, "Accepted, and it fed a concrete reallocation proposal rather than only a chart."),
  ]),

I("PULSE-93", "Story", "Marketing dashboard page", "Done",
  """
As marketing
I want campaign, channel, attribution and acquisition economics on one page
So that the budget conversation happens against one set of numbers.

Acceptance criteria
* campaign table with spend, revenue by named attribution model, ROAS, CPA
* the five-model comparison as a grouped chart, fixed model order
* LTV:CAC by channel with payback
* every approximate number labelled where it appears, including the
  incrementality proxy - see PULSE-94
  """,
  parent="PULSE-8", assignee=D, sprint=S13, points="5", components="Dashboards",
  labels="dashboard;marketing", created="2026-08-18 09:20:00",
  resolved="2026-08-28 16:40:00",
  comments=[
    ("2026-08-26 14:10:00", N, "Checked every figure against the marts and every model column against attribution.py. All match. The model ordering is fixed, per the design system."),
    ("2026-08-28 16:35:00", G, "Accepted. This page closed the ROAS-of-4.2 question that opened the epic - the honest answer being that 4.2 was a blend of five different numbers between 1.8 and 6.1."),
  ]),

I("PULSE-94", "Task", "Label the incrementality proxy where it appears", "Done",
  """
The incrementality measure is a proxy. It cannot separate a campaign's effect
from a seasonal upswing, and it is being used in budget conversations.

Acceptance criteria
* the limitation stated on the dashboard next to the number, not in a
  tooltip and not only in documentation
* the same wording in the KPI document
* PULSE-122 raised for the geo holdout design that would replace it
  """,
  parent="PULSE-8", assignee=G, sprint=S13, points="2", components="Dashboards;Docs",
  labels="marketing;honesty", created="2026-08-19 09:15:00",
  resolved="2026-08-27 12:20:00",
  comments=[
    ("2026-08-19 09:40:00", G, "Stating a limitation costs a line of text. Discovering it in a board meeting costs the platform's credibility, and that is very expensive to get back."),
    ("2026-08-26 10:15:00", A, "Second day and I would add: put it next to the number rather than in a footnote. In my experience the footnote does not survive the screenshot, and the screenshot is what reaches the decision."),
    ("2026-08-27 12:15:00", G, "Done, next to the number. Geo holdout raised as PULSE-122."),
  ]),

I("PULSE-96", "Task", "BA onboarding - Amit Shinde", "Done",
  """
First week for the business analyst joining 24 Aug 2026.

* environment access, warehouse read, Power BI workspace
* walkthrough of the KPI contract, the medallion layers and the six ADRs
* introductions to finance, marketing and operations stakeholders
* first deliverable: a gap list between what stakeholders ask for and what the
  platform currently answers
  """,
  parent="PULSE-95", assignee=A, sprint=S13, points="3", components="Docs",
  labels="onboarding", created="2026-08-24 09:30:00", resolved="2026-08-28 16:50:00",
  comments=[
    ("2026-08-24 16:40:00", A, "Environment is up. Reading the KPI document first, because it looks like the closest thing this platform has to a requirements baseline - which is unusual and, from where I sit, a good sign."),
    ("2026-08-26 15:20:00", A, "Halfway through the stakeholder conversations. The consistent theme is that people trust the numbers and cannot always find them. That is a much better problem than the reverse and it points at discovery and documentation rather than modelling."),
    ("2026-08-28 16:45:00", A, "Gap list written. Eleven asks, of which seven are already answerable by an existing mart that the asker did not know about, three need new work, and one is genuinely unanswerable today - revenue by the loyalty tier held at the time of purchase, which needs SCD2 change capture."),
    ("2026-08-28 17:00:00", G, "That last one is PULSE-119 and it has been in the backlog since May with exactly that justification. Good to have it confirmed by an actual stakeholder ask rather than by our own guess."),
  ]),

# --------------------------------------------------------------- Sprint 14
I("PULSE-97", "Story", "Requirements traceability matrix", "In Progress",
  """
As the team and its stakeholders
I want each business requirement traced to its mart, metric definition,
dashboard tile and test
So that "is this covered?" is answerable without a meeting.

Acceptance criteria
* one row per requirement from the BRD
* columns: KPI definition reference, implementing SQL, dashboard location,
  covering test, status
* gaps visible as empty cells rather than absent rows
* published where stakeholders can read it
  """,
  parent="PULSE-95", assignee=A, sprint=S14, points="5", components="Docs",
  labels="ba;traceability", created="2026-08-25 09:20:00",
  comments=[
    ("2026-09-01 10:30:00", A, "Draft covers 34 of 41 requirements. The empty cells are the useful part - three requirements have a dashboard tile and no test, and one has a test and no definition, which is the more interesting way round."),
    ("2026-09-03 11:15:00", N, "The three with a tile and no test are going into the analytics regression pack this sprint (PULSE-106)."),
    ("2026-09-07 14:40:00", A, "Seven left, all waiting on the operations page landing so I can point at a real tile rather than a planned one."),
  ]),

I("PULSE-98", "Story", "Demand forecasting with backtested baselines", "Done",
  """
As purchasing
I want a demand forecast I can order against
So that stock decisions stop being made on gut feel.

Acceptance criteria
* analytics/forecasting/forecast.py implementing Holt-Winters, linear trend
  and seasonal naive
* model selected per series by backtest against a held-out tail, not by fit
* MAPE and MAE reported per model per series, all models published
* forecast intervals, not only point estimates
  """,
  parent="PULSE-9", assignee=G, sprint=S14, points="8", components="Analytics",
  labels="ml;forecasting", created="2026-08-31 09:20:00",
  resolved="2026-09-04 16:20:00",
  comments=[
    ("2026-09-01 11:20:00", G, "First run was Holt-Winters alone with a MAPE of 12.4%, which reads as respectable until you have something to compare it against."),
    ("2026-09-02 10:15:00", D, "Backtested against seasonal naive and the naive baseline wins on the daily series - 11.8%. Holt-Winters wins clearly on the weekly aggregate. So the honest answer is that it depends on the series, which is not the answer anyone wants and is the one we have."),
    ("2026-09-02 14:30:00", G, "That is exactly why the baseline gets published as a first-class result. Presenting Holt-Winters alone would have shipped a model that adds nothing at daily grain and nobody would have known."),
    ("2026-09-04 16:15:00", G, "Merged. Per-series selection by backtest, all three models and their errors in the output."),
  ]),

I("PULSE-99", "Task", "Report seasonal naive as a first-class result", "Done",
  """
The naive baseline is published alongside every forecast, in the same table
and on the same chart, with the same visual weight.

Rationale: a model is only worth deploying if it beats "next week looks like
last week", and that comparison must be visible rather than available on
request. On the daily series the baseline currently wins.
  """,
  parent="PULSE-9", assignee=G, sprint=S14, points="2", components="Analytics;Docs",
  labels="ml;honesty", created="2026-09-02 14:35:00", resolved="2026-09-05 11:30:00",
  comments=[
    ("2026-09-05 11:25:00", G, "Same visual weight, deliberately. A baseline rendered as a faint dashed line is a baseline that is being argued against rather than reported."),
  ]),

I("PULSE-100", "Story", "Churn propensity scoring", "In Review",
  """
As retention
I want a churn propensity score per customer with the reasons behind it
So that the team can write a campaign against a specific risk driver.

Acceptance criteria
* analytics/customer/churn.py, logistic regression
* features computed from a snapshot rewound 90 days before the label window -
  see PULSE-101
* AUC, precision and recall on a held-out set, plus a lift chart
* coefficients published as part of the deliverable
  """,
  parent="PULSE-9", assignee=D, sprint=S14, points="8", components="Analytics",
  labels="ml;churn", created="2026-08-31 09:25:00",
  comments=[
    ("2026-09-03 10:20:00", D, "First model scored 0.94 AUC, which was the moment to be suspicious rather than pleased. See PULSE-101."),
    ("2026-09-07 15:20:00", D, "Rebuilt with the rewound snapshot. 0.71 AUC, and the lift chart says the top decile contains about 3.4x the base churn rate, which is actionable. In review."),
    ("2026-09-08 09:45:00", G, "Reviewing today. The coefficients need to go in the output as part of the deliverable, not as an appendix - the retention team has to be able to say why a customer is on the list."),
  ]),

I("PULSE-101", "Bug", "Churn model scores 0.94 AUC - target leakage in the feature snapshot", "Done",
  """
Observed: the first churn model reported 0.94 AUC on a held-out set.

Diagnosis: leakage. Features were computed at the same moment as the label, so
recency_days effectively was the label - a customer is labelled churned
because they have not purchased recently, and the model was given exactly that
as a feature.

Impact: none published. Had it shipped, it would have scored beautifully and
predicted nothing, and the retention team would have received a list of
customers who had already left.

Fix: rewind the feature snapshot 90 days before the label window, so features
describe what was knowable at scoring time. Honest AUC is 0.71.
  """,
  parent="PULSE-9", assignee=D, reporter=D, priority="High", sprint=S14, points="5",
  components="Analytics", labels="ml;leakage", created="2026-09-03 10:25:00",
  resolved="2026-09-07 15:10:00",
  comments=[
    ("2026-09-03 10:35:00", D, "Raising this against my own work. 0.94 on a churn model built in an afternoon is not a good sign, it is a symptom."),
    ("2026-09-03 11:40:00", G, "Correct instinct and worth saying plainly: a model that scores far better than the problem is hard is nearly always answering an easier question than the one you asked."),
    ("2026-09-04 09:30:00", N, "Adding a temporal validation assertion to the analytics pack - the maximum feature timestamp must be earlier than the label window start. It is mechanical, but this class of bug is subtle to spot and trivial to assert."),
    ("2026-09-07 15:05:00", D, "Fixed with a 90-day rewind. 0.71 AUC and it actually predicts. Neha's assertion is in and passing."),
  ]),

I("PULSE-102", "Task", "ADR-005: Linear churn model over gradient boosting", "In Progress",
  """
Decision: use logistic regression for churn propensity, not the
gradient-boosted model that scored slightly better.

Rationale: the retention team has to know why a customer is at risk in order
to write a campaign to them. A ranked list from a black box tells them who but
not what to say. The coefficients are part of the deliverable.

Measured cost: about 0.03 AUC.

Revisit when: an action exists that needs only the ranking and not the reason.
  """,
  parent="PULSE-9", assignee=G, sprint=S14, points="1", components="Docs",
  labels="adr;decision;ml", created="2026-09-07 15:30:00",
  comments=[
    ("2026-09-08 10:10:00", G, "Writing this up now while the numbers are fresh. The revisit condition matters - this is a decision for the current use case, not a permanent position on model families."),
  ]),

I("PULSE-103", "Story", "Inventory optimisation", "To Do",
  """
As purchasing
I want safety stock, reorder points, EOQ and an ABC-XYZ classification
So that stock decisions have a defensible basis.

Acceptance criteria
* analytics/inventory/optimisation.py
* safety stock from demand variability and lead time, at a stated service level
* reorder point and economic order quantity per SKU
* ABC by revenue contribution crossed with XYZ by demand variability
* the service level is an input and is stated wherever the output is shown
  """,
  parent="PULSE-9", assignee=D, sprint=S14, points="8", components="Analytics",
  labels="ml;inventory", created="2026-08-31 09:30:00",
  comments=[
    ("2026-09-07 15:45:00", D, "Not started - churn took the sprint. It depends on the forecast output, which landed on Friday, so it is unblocked now."),
  ]),

I("PULSE-104", "Story", "Product affinity with lift", "To Do",
  """
As merchandising
I want product affinity rules that account for base rates
So that recommendations are not just a list of popular products.

Acceptance criteria
* analytics/sales/basket.py at line grain from fact_sales
* support, confidence and lift, with lift as the headline measure
* minimum support threshold stated and configurable
* rules below a lift of 1.0 shown as such rather than filtered away
  """,
  parent="PULSE-9", assignee=G, sprint=S14, points="5", components="Analytics",
  labels="ml;basket", created="2026-08-31 09:35:00",
  comments=[
    ("2026-09-08 09:20:00", G, "Lift rather than confidence as the headline. High confidence on a popular product tells you the product is popular, which merchandising already knows."),
  ]),

I("PULSE-105", "Story", "Operations dashboard page", "To Do",
  """
As operations
I want inventory health, fulfilment and funnel performance on one page
So that operational issues are visible without a request.

Acceptance criteria
* stock health: below reorder point, overstock, ABC-XYZ distribution
* funnel conversion by stage with drop-off
* payment success by gateway, both denominators labelled
* returns and cancellations by reason
  """,
  parent="PULSE-5", assignee=D, sprint=S14, points="5", components="Dashboards",
  labels="dashboard;operations", created="2026-09-01 09:15:00",
  comments=[
    ("2026-09-07 14:50:00", A, "Flagging a dependency from my side - seven traceability rows (PULSE-97) are waiting on this page to point at a real tile."),
    ("2026-09-08 09:30:00", D, "Understood. It is behind PULSE-103 because the stock health section needs the reorder points."),
  ]),

I("PULSE-106", "Task", "Regression pack for the analytics layer", "In Progress",
  """
Regression coverage for forecasting, churn, inventory and basket.

Assertions
* forecast output has one row per series per horizon step, no gaps
* every model reports its backtest error, including the naive baseline
* churn feature snapshot maximum timestamp precedes the label window start
* churn coefficients present in the output
* basket lift computed against the correct base rate on a hand-worked example
* the three traceability rows with a tile and no test are covered
  """,
  parent="PULSE-11", assignee=N, sprint=S14, points="5", components="Quality;Analytics",
  labels="testing;ml", created="2026-09-01 09:20:00",
  comments=[
    ("2026-09-04 09:35:00", N, "Temporal validation assertion is in and passing after the PULSE-101 fix. Forecast completeness is in. Basket assertions are blocked until PULSE-104 lands."),
    ("2026-09-08 10:30:00", N, "Hand-worked the basket lift example against a small fixture so the assertion is checking arithmetic I have verified by hand rather than the implementation against itself."),
  ]),

I("PULSE-107", "Story", "Terraform for the Azure footprint", "In Progress",
  """
As the team
I want the whole environment described as code
So that a shared environment exists and can be rebuilt.

Scope: ADLS Gen2, Event Hubs, Azure Database for PostgreSQL Flexible Server,
Container Registry, Key Vault, Container Apps, Databricks workspace.

Acceptance criteria
* infrastructure/terraform/ with a module per concern
* dev, test and prod tfvars, differing only in sizing
* no secrets in state or in tfvars - Key Vault references throughout
* terraform plan clean and apply verified in dev
  """,
  parent="PULSE-10", assignee=V, sprint=S14, points="13", components="Platform",
  labels="terraform;infrastructure", created="2026-08-31 09:40:00",
  comments=[
    ("2026-09-02 15:10:00", V, "Modules per concern rather than one root. Storage, streaming, warehouse and registry are separately reviewable and separately destroyable, which matters for the ephemeral environments."),
    ("2026-09-04 16:10:00", V, "Apply is green in dev. Databricks workspace is provisioned but nothing runs on it yet - it is there for the migration path, not for today's workload."),
    ("2026-09-08 11:15:00", V, "Test tfvars remaining, then this is done. Cost work is PULSE-108 and it changed several of the defaults."),
  ]),

I("PULSE-108", "Task", "Cost estimate and cheapest-working-defaults pass", "In Progress",
  """
Produce a printed monthly cost estimate per environment and bring dev down to
something defensible.

First draft defaulted to provisioned SQL and premium Databricks: roughly
GBP 600/month for a dev environment that nobody uses at night.

Changes
* serverless PostgreSQL with auto-pause on dev
* Container Apps scaled to zero on dev
* Databricks on the smallest cluster with aggressive auto-termination
* lifecycle rules moving ADLS data to cool storage after 30 days

Target: dev at roughly GBP 30/month, with the estimate committed alongside the
Terraform so the number is reviewable.
  """,
  parent="PULSE-10", assignee=V, sprint=S14, points="3", components="Platform",
  labels="cost;infrastructure", created="2026-09-02 09:15:00",
  comments=[
    ("2026-09-02 09:40:00", V, "GBP 600 a month for a dev environment is how a platform gets switched off by finance in month three. Cheapest working defaults, and the estimate lives next to the code so a change that increases it is visible in the diff."),
    ("2026-09-08 11:20:00", V, "Dev is at about GBP 31 with auto-pause and scale-to-zero. Prod sizing is still being worked through - the tradeoff there is auto-pause cold starts against always-on cost, and that is a conversation with the business rather than a technical call."),
  ]),

I("PULSE-109", "Task", "ADR-006: Managed PostgreSQL over Synapse", "Done",
  """
Decision: Azure Database for PostgreSQL Flexible Server as the warehouse
engine, not Synapse.

Rationale: Synapse is the right answer past roughly a terabyte. Below that it
is a large bill for a warehouse that a single well-indexed relational database
serves faster. Current gold layer is under 40GB at the largest preset.

Migration path kept open: the gold layer is already a star schema, so moving
to a distributed engine is a DDL change and a bulk copy rather than a
remodelling exercise. A real path, kept open, not taken prematurely.

Revisit when: gold exceeds roughly 500GB, or concurrent query load degrades
p95 dashboard latency beyond 3s.
  """,
  parent="PULSE-10", assignee=V, sprint=S14, points="1", components="Docs",
  labels="adr;decision;infrastructure", created="2026-09-01 10:00:00",
  resolved="2026-09-04 12:00:00",
  comments=[
    ("2026-09-03 10:40:00", G, "The revisit trigger with actual numbers is what makes this ADR useful rather than a defence of a past choice. Without it the conversation reopens every quarter on vibes."),
    ("2026-09-04 11:55:00", V, "Written up with both triggers. Databricks stays provisioned for the ML workloads and as the migration landing spot."),
  ]),

# --------------------------------------------------------------- Sprint 15
I("PULSE-110", "Story", "Power BI dataset export and the DAX model as text", "To Do",
  """
As a stakeholder who lives in Power BI
I want the gold model available in Power BI with the same definitions
So that I am not asked to change tools to get the agreed numbers.

Acceptance criteria
* dashboards/powerbi/export_for_powerbi.py exports the model to a documented
  location
* the DAX measure library committed as text, one measure per KPI definition
* every measure references the KPI document
* a reconciliation check comparing DAX output against the SQL implementation
  for the headline measures
  """,
  parent="PULSE-5", assignee=G, sprint=S15, points="8", components="Dashboards",
  labels="powerbi;reporting", created="2026-09-03 09:20:00",
  comments=[
    ("2026-09-03 09:50:00", G, "This is the fourth implementation of the same metric definitions - SQL, Python, the real-time window and now DAX. That is the point at which a semantic layer starts paying for itself, which is PULSE-123."),
    ("2026-09-07 11:30:00", A, "Two of my stakeholder groups work entirely in Power BI. Their concern is not the tooling, it is whether the numbers will match the Streamlit pages - so the reconciliation check is the part of this story that actually matters to them."),
  ]),

I("PULSE-111", "Task", "Keep .pbix out of git", "To Do",
  """
Establish and enforce that no .pbix binary is committed.

Rationale: a binary that cannot be diffed, reviewed or merged does not belong
in version control, and one that is three commits stale is worse than none at
all - people open it and trust it.

Acceptance criteria
* .gitignore excludes *.pbix
* a CI check fails the build if one is added
* the DAX library and the export script are the reviewable artefacts
* the reasoning documented for whoever tries to commit one next
  """,
  parent="PULSE-5", assignee=G, sprint=S15, points="1", components="Dashboards;CI",
  labels="powerbi;governance", created="2026-09-03 09:25:00",
  comments=[
    ("2026-09-07 10:20:00", V, "Making it a CI check rather than a convention. Conventions about binaries lose to convenience roughly every time."),
  ]),

I("PULSE-112", "Story", "Health check and demo scripts", "To Do",
  """
As an operator
I want one command that tells me whether the platform is healthy
So that a new environment can be verified without tribal knowledge.

Acceptance criteria
* scripts/healthcheck.py verifies database connectivity, expected schemas and
  tables, last successful pipeline run, last quality suite result and stream
  freshness
* non-zero exit on failure, with the failing check named
* scripts/run_demo.py builds a warehouse and starts the dashboards from a
  clean checkout in one command
  """,
  parent="PULSE-10", assignee=V, sprint=S15, points="5", components="Platform",
  labels="ops;scripts", created="2026-09-04 09:15:00",
  comments=[
    ("2026-09-07 16:20:00", N, "I would like the health check to be the first thing UAT runs (PULSE-115). If it is red, nothing after it is worth investigating."),
  ]),

I("PULSE-113", "Story", "Application and infrastructure deployment workflows", "To Do",
  """
As the team
I want deployment as a reviewed, repeatable workflow
So that deploying is not a person following notes.

Acceptance criteria
* .github/workflows/deploy-infrastructure.yml - plan on PR, apply on merge
  with an environment approval gate
* .github/workflows/deploy-application.yml - build, push to ACR, deploy to
  Container Apps
* a shared reusable workflow for per-environment differences
* rollback documented and exercised once
  """,
  parent="PULSE-10", assignee=V, sprint=S15, points="8", components="CI;Platform",
  labels="ci;deployment", created="2026-09-04 09:20:00",
  comments=[
    ("2026-09-08 11:25:00", V, "Rollback exercised once before this is called done. An untested rollback is a plan, not a capability, and the difference shows up at the worst possible moment."),
  ]),

I("PULSE-114", "Task", "Ephemeral environment teardown workflow", "To Do",
  """
A destroy workflow so review environments do not accumulate cost.

Acceptance criteria
* .github/workflows/destroy-environment.yml, manually triggered with an
  explicit environment name and a typed confirmation
* refuses to run against prod under any input
* the same modules as the create path, so drift is impossible
  """,
  parent="PULSE-10", assignee=V, sprint=S15, points="3", components="CI;Platform",
  labels="ci;cost", created="2026-09-04 09:25:00",
  comments=[
    ("2026-09-07 15:50:00", V, "Hard refusal on prod as a guard in the workflow itself, not as a note in the description. This is the one workflow where a mistake is unrecoverable."),
  ]),

I("PULSE-115", "Story", "UAT pack and stakeholder sign-off process", "To Do",
  """
As the business
I want a structured UAT pass before anything is called done
So that acceptance is a decision rather than an assumption.

Acceptance criteria
* scripted scenarios per stakeholder group, in business language
* expected results derived from the KPI definitions, not from the dashboards
* a defect log with severity and a defined path back into the backlog
* written sign-off per group, recorded against the traceability matrix
  """,
  parent="PULSE-11", assignee=N, sprint=S15, points="5", components="Quality;Docs",
  labels="uat;testing", created="2026-09-04 09:30:00",
  comments=[
    ("2026-09-07 16:10:00", N, "Expected results come from the KPI document rather than from the current dashboard output. Deriving them from the dashboard tests that the dashboard agrees with itself, which it always will."),
    ("2026-09-08 10:45:00", A, "I will facilitate the sessions and take the sign-offs into the traceability matrix. Finance and marketing first - they have the most at stake in the definitions."),
  ]),

I("PULSE-116", "Story", "Stakeholder KPI catalogue", "To Do",
  """
As a stakeholder
I want a plain-language catalogue of every available metric and where to find
it
So that I stop asking for numbers that already exist.

Acceptance criteria
* every metric in business language with its plain definition, where to see it
  and its known limitations
* derived from docs/kpi-definitions.md rather than restating it, so the two
  cannot drift
* organised by business question, not by warehouse layer

Justification: seven of the eleven gaps in PULSE-96 turned out to be things
the platform already answers.
  """,
  parent="PULSE-95", assignee=A, sprint=S15, points="5", components="Docs",
  labels="ba;documentation", created="2026-09-07 09:20:00",
  comments=[
    ("2026-09-07 09:45:00", A, "Organised by the question a stakeholder is actually asking rather than by mart. Nobody outside the team knows they want mart_customer_360 - they know they want to understand who stopped buying."),
    ("2026-09-08 09:15:00", G, "Strongly agree, and it must generate from the KPI document rather than restate it. Two documents that drift apart are worse than one that is hard to read."),
  ]),

# ----------------------------------------------------------------- Backlog
I("PULSE-117", "Story", "Wrap the pipeline in a real orchestrator", "To Do",
  """
Replace hand-rolled sequencing in etl/pipeline.py with Dagster or Databricks
Jobs.

Why it has waited: the pipeline is a linear DAG of six stages on one schedule.
Hand-rolled orchestration has been sufficient and an orchestrator would have
been complexity without a problem.

Trigger to do it: the moment there are two schedules with a dependency between
them.

Why it will be cheap when we do: the stage boundaries and ops.pipeline_runs
are already shaped for it. This is a wrapper, not a rewrite.
  """,
  parent="PULSE-10", assignee=V, points="8", components="ETL;Platform",
  labels="backlog;orchestration", created="2026-04-09 16:15:00",
  comments=[
    ("2026-04-09 16:20:00", V, "Raising this at the point of deciding not to do it, with the trigger condition written down. Otherwise it becomes a recurring conversation with no memory."),
    ("2026-09-01 14:30:00", G, "Still one schedule. Not yet."),
  ]),

I("PULSE-118", "Story", "Incremental loads", "To Do",
  """
Move from full rebuild to incremental loading using ops.load_watermarks.

Why it has waited: a full rebuild takes eleven seconds on the demo dataset and
about four minutes on the largest preset. Incremental buys nothing yet and
would have added "which rows changed" bugs to a pipeline that had plenty to
prove already.

Trigger: full rebuild exceeding the nightly window, or a business need for
intraday batch refresh.

Groundwork already in place: ops.load_watermarks exists and is populated.
  """,
  parent="PULSE-1", assignee=V, points="8", components="ETL",
  labels="backlog;performance", created="2026-05-06 10:30:00",
  comments=[
    ("2026-05-06 10:40:00", V, "Watermark table is in and being written to, so the data will be there when we need it. Reading it is the part we are deferring."),
  ]),

I("PULSE-119", "Story", "Real change capture for SCD Type 2", "To Do",
  """
Wire genuine change capture into dim_customer_history so that tier, segment
and address changes are versioned.

Why it has waited: the source ships no change history, so there is nothing to
capture. Solving it means either CDC on the source system or a daily
comparison snapshot, and both are conversations with the owning team.

What it unlocks: "revenue by the loyalty tier the customer held at the time of
purchase", which is currently unanswerable and has been asked for by finance.

Confirmed as a real stakeholder ask in PULSE-96.
  """,
  parent="PULSE-4", assignee=G, points="13", components="Warehouse",
  labels="backlog;scd2", created="2026-06-05 15:25:00",
  comments=[
    ("2026-06-05 15:30:00", G, "Raising it now, while building the Type 2 shape, so the reason the history is not real is recorded next to the table that looks like it should have it."),
    ("2026-08-28 17:05:00", A, "Confirmed as a live finance ask during my onboarding gap analysis. Moving it up would need the source team, so it is a scheduling problem more than a technical one."),
  ]),

I("PULSE-120", "Story", "Alerting with a named owner", "To Do",
  """
Route quality failures and pipeline errors to a person who is expected to
respond.

Why it has waited: Terraform creates the action group; nothing routes to it,
because routing to a rota that does not exist is worse than not alerting.
An alert with no owner trains people to ignore alerts.

This is an organisational change first and a technical one second. What is
needed: an agreed rota, an agreed response expectation, and an agreed
definition of what is worth waking someone for.

Technical work once that exists: roughly two days.
  """,
  parent="PULSE-3", assignee=V, priority="Medium", points="3",
  components="Platform;Quality", labels="backlog;alerting;blocked",
  created="2026-04-15 09:55:00",
  comments=[
    ("2026-04-15 10:00:00", G, "Explicitly deferred rather than dropped, and written down so it stays visible instead of becoming folklore."),
    ("2026-08-12 09:30:00", V, "Now that the streaming layer is live this matters more than it did in April. A stalled consumer is currently discovered by someone opening the dashboard."),
    ("2026-09-08 11:30:00", V, "Still blocked on the rota, not on the work. Flagging it for the quarterly review with a note that it is the largest operational gap we have."),
  ]),

I("PULSE-121", "Story", "Drift detection and data profiling", "To Do",
  """
Detect data that is structurally valid and quietly different: a category
disappearing, a distribution shifting, cardinality doubling.

Why it has waited: the quality suite catches broken data, which was the more
urgent problem. Drift is the subtler one and needs a history to compare
against.

The history now exists - ops.data_quality_results has been appending since
April, so there is a real baseline to build on rather than a cold start.
  """,
  parent="PULSE-3", assignee=D, points="8", components="Quality",
  labels="backlog;quality;drift", created="2026-04-23 11:45:00",
  comments=[
    ("2026-04-23 11:50:00", G, "Raising it while building the history table, since the history is the prerequisite and it would be irritating to want this in six months and have nothing to compare against."),
    ("2026-09-04 10:15:00", N, "Five months of history now. This is the highest-value thing left in the quality epic from where I sit - every bug we have found this year was structural, and drift is the class we currently cannot see at all."),
  ]),

I("PULSE-122", "Story", "Geo holdout to replace the incrementality proxy", "To Do",
  """
Replace the incrementality proxy with a geo holdout or matched-market design.

Why it matters: the proxy is the weakest number in the platform and it is used
to argue about budget. It cannot separate a campaign's effect from a seasonal
upswing, and it is labelled as such on the dashboard.

Why it has waited: it needs marketing to agree to withhold spend in selected
markets. That is a commercial conversation, not a sprint.
  """,
  parent="PULSE-8", assignee=A, points="13", components="Analytics",
  labels="backlog;marketing;experimentation", created="2026-08-27 12:25:00",
  comments=[
    ("2026-08-27 12:30:00", G, "Raised alongside labelling the proxy, so the honest caveat comes with a route to removing it rather than being a permanent apology."),
    ("2026-09-07 14:20:00", A, "Taking this one - it is mostly a stakeholder negotiation. Withholding spend in two matched regions for six weeks is a real cost and marketing will need the case made properly. I would rather bring them a designed experiment than an ask."),
  ]),

I("PULSE-123", "Story", "Semantic layer to collapse the metric implementations", "To Do",
  """
Collapse the metric implementations into one definition consumed by every
tool.

Current state: definitions live in one document and four implementations -
SQL marts, Python analytics, the real-time KPI window, and DAX. The
reconciliation checks keep the SQL side honest; the DAX side is verified by
hand.

Why it has waited: with three consumers the reconciliation checks were
sufficient. The DAX library (PULSE-110) makes it four, and hand verification
does not scale past that.

Trigger: a fifth consumer, or the first DAX-versus-SQL discrepancy that
reaches a stakeholder.
  """,
  parent="PULSE-2", assignee=G, points="13", components="Warehouse;Docs",
  labels="backlog;semantic-layer", created="2026-09-03 09:55:00",
  comments=[
    ("2026-09-03 10:00:00", G, "Worth doing when a fourth consumer appears, and PULSE-110 is the fourth. Raising it now rather than after the first discrepancy."),
    ("2026-09-08 09:50:00", A, "From the stakeholder side the risk is specific: the moment a Power BI number disagrees with a Streamlit number in a meeting, the argument stops being about the business and becomes about the platform. That is expensive to recover from."),
  ]),

]
