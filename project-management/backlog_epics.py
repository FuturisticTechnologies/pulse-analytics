# -*- coding: utf-8 -*-
"""Epics. PULSE-1..PULSE-11 were cut in the inception workshop on 02 Mar 2026.
PULSE-95 was added in August, ahead of the BA joining."""

from backlog_common import I, G, D, V, N, S1, S2, S4, S5, S6, S7, S10, S11, S13, S14

EPICS = [

I("PULSE-1", "Epic", "Platform Foundations and Bronze Ingestion", "Done",
  """
Land source data reliably before anything is modelled on top of it.

Scope: repo and environment, the synthetic data generator we build against
until prod access lands, the bronze landing zone, the CSV and API extracts,
and the run context that records what ran.

Out of scope: any transformation that changes a value. Bronze rejects nothing.
  """,
  epic_name="Foundations & Bronze", assignee=V, priority="Highest", sprint=S1,
  components="ETL;Platform", labels="year1;foundation",
  created="2026-03-02 09:15:00", resolved="2026-04-02 17:20:00",
  comments=[
    ("2026-03-02 09:40:00", G, "Framing for this epic: the only success criterion is that a row which existed in the source exists in bronze, unaltered. No filtering, no coercion, no helpful cleanup. Everything else is Silver's job."),
    ("2026-03-02 11:05:00", V, "Agreed. I want ops.pipeline_runs in scope here too, otherwise we will be debugging loads by reading log files by hand in three weeks."),
    ("2026-04-02 17:19:00", V, "Closing. Bronze lands 8 source files nightly, run context records rows in/out per stage, and PULSE-23 is why the loader now has an explicit dtype map."),
  ]),

I("PULSE-2", "Epic", "Silver Layer and Metric Definitions", "Done",
  """
Repair the data once, in one place, and write down what every number means
before anyone builds a chart on it.

Scope: silver staging for customers, orders, payments, inventory, events and
FX; docs/kpi-definitions.md as the contract; gold.analysis_window as the
platform definition of "today".
  """,
  epic_name="Silver & Definitions", assignee=G, priority="Highest", sprint=S2,
  components="ETL;Docs", labels="year1;definitions",
  created="2026-03-02 09:16:00", resolved="2026-04-24 16:40:00",
  comments=[
    ("2026-03-02 10:12:00", G, "Deliberate sequencing note for anyone reading this later: no dashboard ships out of this epic. If we build a dashboard on a metric nobody has agreed to, we lock in the disagreement and then spend two years defending it."),
    ("2026-03-18 14:30:00", D, "Finance and marketing quoted three different revenue figures for February in the same meeting. That is the argument for this epic in one slide."),
    ("2026-04-24 16:39:00", G, "Done. Six weeks with no dashboard and a weekly CSV instead. Every metric argument since has been resolvable by pointing at kpi-definitions.md."),
  ]),

I("PULSE-3", "Epic", "Data Quality and Pipeline Observability", "Done",
  """
Make it possible to answer "is the number wrong, or is the pipeline wrong?"
without reading SQL.

Scope: the check framework, the first suite of checks, the reconciliation
checks, and ops.data_quality_results as durable history.

Out of scope for now: paging anyone. Results are recorded and reviewed on
Monday until somebody actually depends on the warehouse.
  """,
  epic_name="Quality & Observability", assignee=D, priority="High", sprint=S4,
  components="Quality;ETL", labels="year1;quality",
  created="2026-03-02 09:17:00", resolved="2026-05-08 16:10:00",
  comments=[
    ("2026-03-02 10:25:00", V, "I want the alerting story explicitly deferred rather than silently dropped. Paging a rota that does not exist is theatre."),
    ("2026-04-15 09:50:00", G, "Deferred and written down as PULSE-120 so it stays visible in the backlog instead of becoming folklore."),
    ("2026-05-08 16:09:00", D, "Closed with 24 checks, 5 reconciliations and a history table. The threshold re-tune in PULSE-42 is the reason anyone still reads the output."),
  ]),

I("PULSE-4", "Epic", "Kimball Star Schema (Gold)", "Done",
  """
Stop answering every new question with bespoke SQL.

Scope: conformed dimensions with surrogate keys and Unknown members, facts at
their correct grains, indexes, and the SCD2-shaped customer history table.
  """,
  epic_name="Star Schema", assignee=G, priority="High", sprint=S6,
  components="Warehouse", labels="year1;modelling",
  created="2026-03-02 09:18:00", resolved="2026-06-05 17:00:00",
  comments=[
    ("2026-05-11 09:30:00", G, "The shape we agreed: seven dimensions, five facts, surrogate keys everywhere, Unknown member on -1 so an unmatched fact row never silently disappears from an inner join."),
    ("2026-06-05 16:58:00", G, "Closing. 'Revenue by region by month for electronics' went from a day of bespoke SQL to about four minutes. That was the point."),
  ]),

I("PULSE-5", "Epic", "Sales and Executive Reporting", "In Progress",
  """
The first dashboards, and the design system they are built on.

Scope: the Streamlit shell and data access layer, theme.py as the chart
contract, the executive and sales pages, the sales marts behind them, and the
Power BI export for stakeholders who live in Power BI.
  """,
  epic_name="Sales & Exec Reporting", assignee=D, priority="High", sprint=S7,
  components="Dashboards;Warehouse", labels="year1;reporting",
  created="2026-03-02 09:19:00",
  comments=[
    ("2026-06-08 10:15:00", G, "theme.py lands before the first chart, not after the thirtieth. Retrofitting consistency across a built dashboard estate costs an order of magnitude more than starting with it."),
    ("2026-09-02 11:20:00", D, "Remaining in this epic: the operations page (PULSE-105) and the Power BI export (PULSE-110, PULSE-111). Everything else has shipped."),
  ]),

I("PULSE-6", "Epic", "Customer Analytics", "Done",
  """
Move from what we sold to who keeps buying, who left, and what an acquired
customer is worth.

Scope: mart_customer_360, RFM segmentation, cohort retention, monthly churn,
CLV curves and the customer dashboard page.
  """,
  epic_name="Customer Analytics", assignee=G, priority="High", sprint=S10,
  components="Warehouse;Analytics;Dashboards", labels="year1;customer",
  created="2026-03-02 09:20:00", resolved="2026-07-31 16:30:00",
  comments=[
    ("2026-07-06 09:25:00", G, "Every metric in this epic is recency-based, so every one of them depends on PULSE-35. If analysis_window is wrong, all of this is wrong and it will look entirely plausible."),
    ("2026-07-31 16:29:00", G, "Closed. The cohort definition bug (PULSE-74) was worth the epic on its own - it turned a retention panic into an activation workstream."),
  ]),

I("PULSE-7", "Epic", "Real-Time Streaming", "Done",
  """
Payment failures are currently found the next morning. A gateway degradation
on a Friday evening costs a full night of orders.

Scope: the event bus abstraction with file and Kafka implementations, four
correlated topics, a micro-batched consumer, the ops landing tables, the
real-time KPI window and the real-time dashboard page.
  """,
  epic_name="Real-Time Streaming", assignee=V, priority="High", sprint=S11,
  components="Streaming;Platform", labels="year2;streaming",
  created="2026-03-02 09:21:00", resolved="2026-08-14 17:45:00",
  comments=[
    ("2026-07-20 09:40:00", V, "Two rules for this epic. One: event time, never wall-clock time, or we can never replay a stream and get the same KPIs back. Two: the consumer owns no metric definitions - it lands events and recomputes a window, and every metric stays in SQL next to the batch ones."),
    ("2026-07-20 10:05:00", G, "Seconding rule two hard. Revenue must not mean two different things depending on which pipeline produced it."),
    ("2026-08-14 17:44:00", V, "Closed. PULSE-85 was the ugly one and it is why ops.* is now CREATE TABLE IF NOT EXISTS with a test behind it."),
  ]),

I("PULSE-8", "Epic", "Marketing Analytics and Attribution", "Done",
  """
Marketing reports a blended ROAS of 4.2 and nobody can say what it is
attributed on. The number is being used to set budget.

Scope: campaign, channel and acquisition marts; five attribution models
published side by side; LTV:CAC by acquisition channel; the marketing
dashboard page, with every approximate number labelled as approximate.
  """,
  epic_name="Marketing & Attribution", assignee=G, priority="High", sprint=S13,
  components="Warehouse;Analytics;Dashboards", labels="year2;marketing",
  created="2026-03-02 09:22:00", resolved="2026-08-28 17:10:00",
  comments=[
    ("2026-08-03 10:30:00", G, "We are not picking an attribution model. We publish five and let the spread between them be the finding. Any single number here would be a confident answer to a question we cannot actually answer."),
    ("2026-08-28 17:09:00", G, "Closed. An influencer channel with a large upper_funnel_bias was being starved by a last-touch budget. A single ROAS figure would have hidden that completely."),
  ]),

I("PULSE-9", "Epic", "Predictive Analytics", "In Progress",
  """
Everything is retrospective. Purchasing over-orders on gut feel and retention
finds out about churn after it has happened.

Scope: demand forecasting with honest baselines, churn propensity scoring,
inventory optimisation, and product affinity.

Constraint agreed up front: the output has to survive contact with someone who
then has to do something about it. Explainability beats a marginally better
score.
  """,
  epic_name="Predictive Analytics", assignee=G, priority="High", sprint=S14,
  components="Analytics", labels="year2;ml",
  created="2026-03-02 09:23:00",
  comments=[
    ("2026-08-31 09:35:00", G, "Backtest everything against a seasonal naive baseline and publish the baseline as a first-class result. If next-week-looks-like-last-week wins, we need to know that before we deploy a model that adds nothing."),
    ("2026-09-07 15:40:00", D, "Forecasting has shipped. Churn is in review after the leakage fix. Inventory and basket are the remaining two."),
  ]),

I("PULSE-10", "Epic", "Platform Engineering, CI/CD and Cloud", "In Progress",
  """
Everything runs on three laptops. There is no shared always-on environment and
no answer to "what happens when one of us is away".

Scope: local parity with docker-compose, CI on every push, Terraform for the
Azure footprint, deployment workflows, and the operational scripts.
  """,
  epic_name="Platform & CI/CD", assignee=V, priority="High", sprint=S1,
  components="Platform;CI", labels="devops;infrastructure",
  created="2026-03-02 09:24:00",
  comments=[
    ("2026-03-02 11:30:00", V, "This epic runs the whole length of the project rather than as a phase at the end. A deployment story started in month seven is a deployment story that discovers the code cannot be deployed."),
    ("2026-09-04 16:15:00", V, "Terraform apply is green in dev. Deployment workflows and the ops scripts are the last two blocks, planned for Sprint 15."),
  ]),

I("PULSE-11", "Epic", "Quality Engineering and Release Assurance", "In Progress",
  """
Test the platform the way it will actually fail: on real generated data, with
the same SQL, end to end.

Scope: the pytest warehouse fixture, per-layer regression packs, dashboard
smoke tests, CI gating and the UAT process.

Staffed from 15 Jun 2026 when the QA analyst joins; until then the developers
own their own tests.
  """,
  epic_name="Quality Engineering", assignee=D, priority="Medium", sprint=S5,
  components="Quality;CI", labels="qa;testing",
  created="2026-03-02 09:25:00",
  comments=[
    ("2026-03-02 11:45:00", G, "No mocks. A mocked warehouse tests our assumptions about SQL, which is exactly the thing that keeps being wrong. Tests build a real warehouse from generated data."),
    ("2026-06-16 10:20:00", N, "Picking this epic up. First thing I want is a written regression scope per layer, so that covered means something other than a count of tests."),
    ("2026-09-07 16:05:00", N, "Bronze through gold and the dashboards have regression packs. The analytics pack (PULSE-106) is in progress; UAT (PULSE-115) is next sprint."),
  ]),

I("PULSE-95", "Epic", "Business Analysis and Stakeholder Enablement", "In Progress",
  """
Cut when the BA role was approved, ahead of Amit joining on 24 Aug 2026.

Scope: requirements traceability from the BRD through to marts and dashboard
tiles, the stakeholder-facing KPI catalogue, UAT facilitation, and owning the
backlog conversation with finance, marketing and operations.

Why it exists late: for the first six months the analytics lead carried the
stakeholder relationship directly. That stopped scaling at three consumer
teams.
  """,
  epic_name="Business Analysis", assignee=G, priority="Medium", sprint=S13,
  components="Docs", labels="ba;stakeholders",
  created="2026-08-19 14:00:00",
  comments=[
    ("2026-08-19 14:10:00", G, "Creating this now so there is a real backlog waiting on day one rather than two weeks of shadowing. Amit starts 24 Aug."),
    ("2026-09-01 09:30:00", V, "Access requests raised for Amit: Jira, Confluence, the dev warehouse read role and the Power BI workspace. Warehouse read is the slow one, it needs the data owner to approve."),
  ]),

]
