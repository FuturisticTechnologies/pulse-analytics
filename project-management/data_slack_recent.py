# -*- coding: utf-8 -*-
"""Two months of standup and QA history: 09 Jul 2026 - 09 Sep 2026.

Written as a separate batch so it can be exported on its own and imported on
top of a workspace that already has the main transcript, without duplicating
anything.

Routing: #pulse-standup -> #pulseanalytics-standup, #pulse-data-quality ->
#pulseanalytics-qa.

Team available in this window: Geetha, Divya, Devendranath and Neha
throughout; Amit from 24 Aug 2026 only. All weekdays, 09:00-17:00.

Sprints covered
  S10  06-17 Jul   customer analytics
  S11  20-31 Jul   customer dashboard, streaming foundations
  S12  03-14 Aug   streaming ops, the ops.stream_events incident
  S13  17-28 Aug   marketing attribution, BA onboarding
  S14  31 Aug-11 Sep  predictive analytics, cloud
"""

from data_slack import M, STD, DQ
from backlog_common import G, D, V, N, A

RECENT = [

# ======================================================= Sprint 10, week 2
M(STD, "2026-07-09 09:15:00", G,
  "Standup. Yesterday: customer_360 grain and the zero-order decision. Today: "
  "cohort retention SQL (PULSE-73). No blockers."),
M(STD, "2026-07-09 09:17:00", D,
  "Yesterday: RFM quintile logic (PULSE-72). Today: segment naming and getting "
  "the boundaries into the KPI doc. No blockers.", issue="PULSE-72"),
M(STD, "2026-07-09 09:19:00", V,
  "Yesterday: reran the index review now the marts exist (PULSE-53). Today: "
  "reading up on Redpanda ahead of the streaming sprint. No blockers."),
M(STD, "2026-07-09 09:21:00", N,
  "Yesterday: scoped the customer regression pack (PULSE-77). Today: the "
  "determinism assertion. Blocked until RFM lands, so I am writing it against "
  "customer_360 first.", issue="PULSE-77"),

M(STD, "2026-07-10 09:15:00", G,
  "Standup. Yesterday: cohort SQL. Today: period-number arithmetic, which is "
  "the part I expect to get wrong. No blockers.", issue="PULSE-73"),
M(STD, "2026-07-10 09:17:00", D,
  "Yesterday: RFM PR up for review. Today: churn window rules per segment "
  "(PULSE-75). No blockers.", issue="PULSE-75"),
M(STD, "2026-07-10 09:19:00", V,
  "Yesterday: Redpanda reading. Today: drafting the bus interface so we can "
  "argue about it before anything is written against it.", issue="PULSE-79"),
M(STD, "2026-07-10 09:21:00", N,
  "Yesterday: reviewing the RFM PR. Today: same, plus the customer_360 row "
  "count assertion. No blockers.", issue="PULSE-72"),

M(STD, "2026-07-13 09:15:00", G,
  "Standup. Yesterday: cohort build running end to end. Today: looking at a "
  "60% cliff between period 0 and period 1 that I cannot explain. Not blocked, "
  "but that is the whole day.", issue="PULSE-73"),
M(STD, "2026-07-13 09:17:00", D,
  "Yesterday: churn window rules. Today: mart_churn_monthly build. No "
  "blockers.", issue="PULSE-75"),
M(STD, "2026-07-13 09:19:00", V,
  "Yesterday: bus interface draft. Today: writing it up properly plus the "
  "file-based implementation. No blockers.", issue="PULSE-79"),
M(STD, "2026-07-13 09:21:00", N,
  "Yesterday: RFM review done. Today: customer pack assertions. No blockers.",
  issue="PULSE-77"),

M(STD, "2026-07-14 09:15:00", G,
  "Standup. Yesterday: found the cohort cliff - it is the definition, not the "
  "data. Cohorts are on signup month and most signups never buy. Today: "
  "rebuilding on first purchase month and writing up PULSE-74.",
  issue="PULSE-74"),
M(STD, "2026-07-14 09:17:00", D,
  "Yesterday: churn mart. Today: same, plus reviewing the cohort fix. Worth "
  "saying that is the second definition bug this quarter that produced a "
  "plausible wrong answer.", issue="PULSE-74"),
M(STD, "2026-07-14 09:19:00", V,
  "Yesterday: file bus implementation. Today: offsets and the consumer group "
  "bookkeeping. No blockers.", issue="PULSE-79"),
M(STD, "2026-07-14 09:21:00", N,
  "Yesterday: customer pack. Today: adding a cohort size assertion off the "
  "back of PULSE-74. It cannot catch a bad definition but it will catch a "
  "regression away from the good one.", issue="PULSE-74"),

M(STD, "2026-07-15 09:15:00", G,
  "Standup. Yesterday: cohort rebuild. Today: CLV curves (PULSE-76). No "
  "blockers.", issue="PULSE-76"),
M(STD, "2026-07-15 09:17:00", D,
  "Yesterday: churn mart nearly done. Today: finishing it and starting the "
  "customer dashboard page layout. No blockers."),
M(STD, "2026-07-15 09:19:00", V,
  "Yesterday: offset handling. Today: Kafka implementation against a local "
  "Redpanda container. No blockers.", issue="PULSE-79"),
M(STD, "2026-07-15 09:21:00", N,
  "Yesterday: cohort assertion written. Today: running the whole customer pack "
  "against a fresh build. No blockers.", issue="PULSE-77"),

M(STD, "2026-07-16 09:15:00", G,
  "Standup. Yesterday: CLV realised curves. Today: projection horizon and "
  "labelling it on the chart. No blockers.", issue="PULSE-76"),
M(STD, "2026-07-16 09:17:00", D,
  "Yesterday: churn mart merged. Today: customer dashboard page. No blockers.",
  issue="PULSE-78"),
M(STD, "2026-07-16 09:19:00", V,
  "Yesterday: Kafka implementation. Today: same consumer code against both "
  "buses, which is the thing that has to work. No blockers.",
  issue="PULSE-79"),
M(STD, "2026-07-16 09:21:00", N,
  "Yesterday: full customer pack run. Today: writing up what it does and does "
  "not cover for the sprint review.", issue="PULSE-77"),

M(STD, "2026-07-17 09:15:00", G,
  "Standup, and sprint review at 14:00. Yesterday: CLV done. Today: review "
  "prep. The cohort finding is the headline and I want it presented as an "
  "activation problem, not as a fix we quietly made.", issue="PULSE-74"),
M(STD, "2026-07-17 09:17:00", D,
  "Yesterday: dashboard page started. Today: review prep, then carrying the "
  "page into next sprint.", issue="PULSE-78"),
M(STD, "2026-07-17 09:19:00", V,
  "Yesterday: both bus implementations passing the same tests. Today: review, "
  "then streaming properly from Monday.", issue="PULSE-79"),
M(STD, "2026-07-17 09:21:00", N,
  "Yesterday: coverage write-up. Today: review. Customer marts are covered; "
  "the analytics modules still are not, and that gap is growing.",
  issue="PULSE-77"),

M(STD, "2026-07-17 15:30:00", G,
  "Sprint 10 review done. Closed: customer_360, RFM, cohort retention, churn "
  "monthly, CLV, and the customer regression pack. Carrying the dashboard page "
  "into Sprint 11."),
M(STD, "2026-07-17 16:10:00", G,
  "Retro, three things. Kept: raising PULSE-74 as a finding rather than a "
  "silent fix. Changed: Neha reviews definition changes before they land, not "
  "after. Tried: pairing on the cohort SQL, which found the period arithmetic "
  "bug in about ten minutes.", reactions=":+1: 3"),

# ============================================================== Sprint 11
M(STD, "2026-07-20 09:15:00", G,
  "Sprint 11 planning at 10:00. Two workstreams: finish the customer dashboard "
  "and start streaming for real. Standup: today is planning and the cohort "
  "write-up for the business."),
M(STD, "2026-07-20 09:17:00", D,
  "Yesterday off. Today: planning, then the customer dashboard page.",
  issue="PULSE-78"),
M(STD, "2026-07-20 09:19:00", V,
  "Today: planning, then the four event topics and the producer. The two rules "
  "I want agreed in planning are event time only, and no metric definitions in "
  "the consumer.", issue="PULSE-80"),
M(STD, "2026-07-20 09:21:00", N,
  "Today: planning. I want the streaming test approach agreed up front rather "
  "than retrofitted, because a broker in CI would make everything slow and "
  "flaky."),
M(STD, "2026-07-20 12:15:00", G,
  "Sprint 11 committed: PULSE-78 through PULSE-83. 34 points, which is above "
  "our average, but PULSE-81 and PULSE-83 are small. Both streaming rules "
  "agreed and written into the epic.", reactions=":+1: 3"),

M(STD, "2026-07-21 09:15:00", G,
  "Standup. Yesterday: planning. Today: reviewing the customer dashboard and "
  "writing the cohort finding up for the business. No blockers."),
M(STD, "2026-07-21 09:17:00", D,
  "Yesterday: dashboard layout. Today: the cohort heatmap - sequential ramp, "
  "single hue, magnitude only. No blockers.", issue="PULSE-78"),
M(STD, "2026-07-21 09:19:00", V,
  "Yesterday: topic schemas. Today: making the producer emit correlated events "
  "rather than four independent streams. No blockers.", issue="PULSE-80"),
M(STD, "2026-07-21 09:21:00", N,
  "Yesterday: streaming test approach. Today: writing it up, then reviewing "
  "the bus PR. No blockers.", issue="PULSE-79"),

M(STD, "2026-07-23 09:15:00", G,
  "Standup. Yesterday: cohort write-up sent. Today: reviewing the consumer "
  "design. No blockers."),
M(STD, "2026-07-23 09:17:00", D,
  "Yesterday: heatmap and CLV curves on the page. Today: churn trend section "
  "and the definition text on the page. No blockers.", issue="PULSE-78"),
M(STD, "2026-07-23 09:19:00", V,
  "Yesterday: correlation in the producer. Today: consumer, micro-batching and "
  "the offset ordering. No blockers.", issue="PULSE-82"),
M(STD, "2026-07-23 09:21:00", N,
  "Yesterday: bus review. Today: the crash test - kill the consumer mid-batch "
  "and assert no duplicates and no gaps. Blocked until the consumer exists, so "
  "writing it against the interface.", issue="PULSE-82"),

M(STD, "2026-07-27 09:15:00", G,
  "Standup. Yesterday: reviewed the customer page end to end. Today: mart "
  "reconciliation checks for the streaming layer, so real-time and batch "
  "revenue have to agree. No blockers."),
M(STD, "2026-07-27 09:17:00", D,
  "Yesterday: churn trend section. Today: empty states and the segment "
  "membership rule on the cohort chart. No blockers.", issue="PULSE-78"),
M(STD, "2026-07-27 09:19:00", V,
  "Yesterday: micro-batching. Today: the write-then-commit ordering, which is "
  "the part that has to be right. No blockers.", issue="PULSE-82"),
M(STD, "2026-07-27 09:21:00", N,
  "Yesterday: crash test scaffolding. Today: running it. No blockers.",
  issue="PULSE-82"),

M(STD, "2026-07-29 09:15:00", G,
  "Standup. Yesterday: reconciliation checks drafted. Today: same. No "
  "blockers."),
M(STD, "2026-07-29 09:17:00", D,
  "Yesterday: empty states. Today: verifying every figure on the customer page "
  "against the marts before it goes for review.", issue="PULSE-78"),
M(STD, "2026-07-29 09:19:00", V,
  "Yesterday: commit ordering. Today: consumer PR up, and event-time windowing "
  "after that. No blockers.", issue="PULSE-82"),
M(STD, "2026-07-29 09:21:00", N,
  "Yesterday: crash test passed on the current build. Today: running it "
  "against an earlier build to check the test can actually fail - it did, "
  "which is what I wanted to see.", issue="PULSE-82", reactions=":100: 2"),

M(STD, "2026-07-31 09:15:00", G,
  "Standup, sprint review at 14:00. Yesterday: reconciliation. Today: review "
  "prep. Good sprint - streaming went from nothing to a working consumer."),
M(STD, "2026-07-31 09:17:00", D,
  "Yesterday: page verification. Today: review. Customer dashboard is done, "
  "which closes the customer epic.", issue="PULSE-6"),
M(STD, "2026-07-31 09:19:00", V,
  "Yesterday: consumer merged. Today: event-time windowing and the replay "
  "test, then review.", issue="PULSE-83"),
M(STD, "2026-07-31 09:21:00", N,
  "Yesterday: crash test. Today: replay test with Deven, then review.",
  issue="PULSE-83"),
M(STD, "2026-07-31 15:20:00", G,
  "Sprint 11 review done. All six stories closed and the customer epic is "
  "complete. Retro Monday morning since we ran long.",
  reactions=":tada: 3"),

# ============================================================== Sprint 12
M(STD, "2026-08-03 09:15:00", G,
  "Sprint 11 retro at 09:30, then Sprint 12 planning at 11:00. Focus this "
  "sprint: land the streaming ops tables and the real-time page."),
M(STD, "2026-08-03 10:20:00", G,
  "Retro. Kept: agreeing the streaming rules in planning rather than "
  "discovering them in review. Changed: Neha gets test-approach input at "
  "planning, not after the design lands. Tried: writing tests against the "
  "interface before the implementation, which worked well enough to keep.",
  reactions=":+1: 3"),
M(STD, "2026-08-03 12:30:00", G,
  "Sprint 12 committed: PULSE-84 through PULSE-89. 28 points."),
M(STD, "2026-08-03 12:35:00", V,
  "Flagging a risk I have no evidence for yet: we have never tested what a "
  "full batch rebuild does to the streaming tables. Probably fine.",
  reactions=":eyes: 2"),

M(STD, "2026-08-04 09:15:00", G,
  "Standup. Yesterday: planning and retro. Today: the SQL for the real-time "
  "KPI window - all definitions stay in SQL. No blockers.", issue="PULSE-84"),
M(STD, "2026-08-04 09:17:00", D,
  "Yesterday: planning. Today: real-time dashboard page layout. No blockers.",
  issue="PULSE-87"),
M(STD, "2026-08-04 09:19:00", V,
  "Yesterday: planning. Today: ops.stream_events and ops.realtime_kpis. No "
  "blockers.", issue="PULSE-84"),
M(STD, "2026-08-04 09:21:00", N,
  "Yesterday: planning. Today: test scope for the streaming ops tables. No "
  "blockers."),

M(STD, "2026-08-06 09:15:00", G,
  "Standup. Yesterday: KPI window SQL. Today: the reconciliation between "
  "real-time and batch for a closed day. No blockers.", issue="PULSE-84"),
M(STD, "2026-08-06 09:17:00", D,
  "Yesterday: page layout. Today: something is wrong - the real-time page is "
  "showing zeros this morning and I ran a full rebuild last night. "
  "Investigating before anything else.", issue="PULSE-85"),
M(STD, "2026-08-06 09:19:00", V,
  "Yesterday: ops tables landing events. Today: was going to be the API, now "
  "it is helping Divya with whatever that is.", issue="PULSE-85"),
M(STD, "2026-08-06 09:21:00", N,
  "Yesterday: test scope. Today: same, and I have a bad feeling this is the "
  "gap I flagged in my first week.", issue="PULSE-86"),

M(STD, "2026-08-07 09:15:00", G,
  "Standup. Yesterday was the ops.stream_events incident - four hours of "
  "events gone, no error anywhere. Today: back to the reconciliation work "
  "while Deven fixes the coupling.", issue="PULSE-85"),
M(STD, "2026-08-07 09:17:00", D,
  "Yesterday: found it and handed it over. Today: real-time page, properly "
  "this time.", issue="PULSE-87"),
M(STD, "2026-08-07 09:19:00", V,
  "Yesterday: root cause - ops DDL was in the bronze init path with DROP and "
  "CREATE. Today: moving it out and making everything IF NOT EXISTS.",
  issue="PULSE-85"),
M(STD, "2026-08-07 09:21:00", N,
  "Yesterday: confirmed my test fails against main, which is what I wanted "
  "before fixing anything. Today: the DDL scan alongside it.",
  issue="PULSE-86"),

M(STD, "2026-08-10 09:15:00", G,
  "Standup. Yesterday: reconciliation. Today: same. The incident write-up goes "
  "into the retro rather than being absorbed quietly - two failures at once, "
  "destructive DDL and cross-layer coupling.", issue="PULSE-85"),
M(STD, "2026-08-10 09:17:00", D,
  "Yesterday: real-time page tiles. Today: the staleness indicator, which I "
  "think matters more than the tiles.", issue="PULSE-87"),
M(STD, "2026-08-10 09:19:00", V,
  "Yesterday: fix drafted. Today: PR up, plus grepping the repo for every "
  "other DROP TABLE.", issue="PULSE-85"),
M(STD, "2026-08-10 09:21:00", N,
  "Yesterday: DDL scan. Today: reviewing the fix and running both tests "
  "against it.", issue="PULSE-86"),

M(STD, "2026-08-12 09:15:00", G,
  "Standup. Yesterday: reviewed the fix. Today: real-time to batch "
  "reconciliation is green for a closed day, so writing that up. No blockers.",
  issue="PULSE-84"),
M(STD, "2026-08-12 09:17:00", D,
  "Yesterday: staleness indicator. Today: funnel and payments mart. No "
  "blockers.", issue="PULSE-89"),
M(STD, "2026-08-12 09:19:00", V,
  "Yesterday: PULSE-85 merged. Today: the real-time API, which is deliberately "
  "boring - it reads the table and returns it.", issue="PULSE-88"),
M(STD, "2026-08-12 09:21:00", N,
  "Yesterday: both tests green. Today: testing the staleness behaviour by "
  "stopping the producer.", issue="PULSE-87"),

M(STD, "2026-08-14 09:15:00", G,
  "Standup, review at 14:00. Yesterday: reconciliation write-up. Today: "
  "review. This closes the streaming epic, incident included.",
  issue="PULSE-7"),
M(STD, "2026-08-14 09:17:00", D,
  "Yesterday: funnel mart. Today: finishing it, then review.",
  issue="PULSE-89"),
M(STD, "2026-08-14 09:19:00", V,
  "Yesterday: API merged. Today: review. Also want to reopen the alerting "
  "conversation - a stalled consumer is still found by someone opening the "
  "dashboard.", issue="PULSE-120"),
M(STD, "2026-08-14 09:21:00", N,
  "Yesterday: staleness verified. Today: review, then the coverage gaps "
  "write-up."),
M(STD, "2026-08-14 15:40:00", G,
  "Sprint 12 review done. Streaming epic closed. PULSE-85 was the ugly one and "
  "it is the reason ops.* is now protected by a test.", reactions=":tada: 3"),

# ============================================================== Sprint 13
M(STD, "2026-08-17 09:15:00", G,
  "Sprint 13 planning at 10:00. Marketing attribution this sprint, and Amit "
  "starts a week today so there is onboarding in the plan as real work rather "
  "than as an afterthought."),
M(STD, "2026-08-17 09:17:00", D,
  "Today: planning, then the acquisition channel mart.", issue="PULSE-92"),
M(STD, "2026-08-17 09:19:00", V,
  "Today: planning. Access requests for Amit are in - warehouse read is the "
  "slow one, it needs the data owner.", issue="PULSE-95"),
M(STD, "2026-08-17 09:21:00", N,
  "Today: planning. I want the marketing numbers verified against the marts "
  "before that page goes anywhere near a budget conversation."),
M(STD, "2026-08-17 12:20:00", G,
  "Sprint 13 committed: PULSE-90 through PULSE-94, plus onboarding. The "
  "attribution story is the big one and we are publishing five models rather "
  "than picking one.", issue="PULSE-91", reactions=":+1: 3"),

M(STD, "2026-08-19 09:15:00", G,
  "Standup. Yesterday: campaign and channel marts. Today: attribution module - "
  "five models over one touchpoint builder. No blockers.", issue="PULSE-91"),
M(STD, "2026-08-19 09:17:00", D,
  "Yesterday: acquisition mart. Today: LTV to CAC by channel with payback. No "
  "blockers.", issue="PULSE-92"),
M(STD, "2026-08-19 09:19:00", V,
  "Yesterday: access requests. Today: back on Terraform ahead of Sprint 14. No "
  "blockers.", issue="PULSE-107"),
M(STD, "2026-08-19 09:21:00", N,
  "Yesterday: marketing test scope. Today: verifying the campaign mart columns "
  "against the KPI doc. No blockers.", issue="PULSE-90"),

M(STD, "2026-08-21 09:15:00", G,
  "Standup. Yesterday: attribution models running. Today: the "
  "upper_funnel_bias measure, which is where the interesting finding is. No "
  "blockers.", issue="PULSE-91"),
M(STD, "2026-08-21 09:17:00", D,
  "Yesterday: LTV to CAC. Today: two channels have strong first-order ROAS and "
  "poor LTV to CAC, so writing that up. No blockers.", issue="PULSE-92"),
M(STD, "2026-08-21 09:19:00", V,
  "Yesterday: Terraform modules. Today: same. No blockers.",
  issue="PULSE-107"),
M(STD, "2026-08-21 09:21:00", N,
  "Yesterday: column verification. Today: found the models were not summing to "
  "the same total - Divya spotted it first in review and it turned out to be a "
  "rounding accumulation in time decay.", issue="PULSE-91"),

M(STD, "2026-08-24 09:15:00", G,
  "Standup, and Amit joins us today as BA. Yesterday: attribution assertions "
  "in. Today: walking Amit through the KPI contract, then the marketing page.",
  issue="PULSE-96", reactions=":wave: 3"),
M(STD, "2026-08-24 09:17:00", D,
  "Yesterday: acquisition write-up. Today: marketing dashboard page. No "
  "blockers.", issue="PULSE-93"),
M(STD, "2026-08-24 09:19:00", V,
  "Yesterday: Terraform. Today: getting Amit's environment up first. Warehouse "
  "read came through on Friday.", issue="PULSE-96"),
M(STD, "2026-08-24 09:21:00", N,
  "Yesterday: attribution verification. Today: verifying the five-model output "
  "against attribution.py directly.", issue="PULSE-91"),

M(STD, "2026-08-26 09:15:00", G,
  "Standup. Yesterday: onboarding and the marketing page review. Today: "
  "labelling the incrementality proxy where it appears.", issue="PULSE-94"),
M(STD, "2026-08-26 09:17:00", D,
  "Yesterday: marketing page. Today: finishing it. No blockers.",
  issue="PULSE-93"),
M(STD, "2026-08-26 09:19:00", V,
  "Yesterday: Amit set up. Today: Terraform cost pass - the first draft prices "
  "at about GBP 600 a month for dev, which is not going to survive contact "
  "with finance.", issue="PULSE-108"),
M(STD, "2026-08-26 09:21:00", N,
  "Yesterday: model verification, all match. Today: the marketing page figures "
  "against the marts.", issue="PULSE-93"),
M(STD, "2026-08-26 09:23:00", A,
  "First standup from me. Yesterday: stakeholder conversations with finance "
  "and marketing. Today: same with operations, then writing up the gap list.",
  issue="PULSE-96"),

M(STD, "2026-08-28 09:15:00", G,
  "Standup, review at 14:00. Yesterday: proxy labelling done. Today: review. "
  "This closes the marketing epic and answers the ROAS-of-4.2 question.",
  issue="PULSE-8"),
M(STD, "2026-08-28 09:17:00", D,
  "Yesterday: marketing page finished. Today: review, then predictive work "
  "from Monday.", issue="PULSE-93"),
M(STD, "2026-08-28 09:19:00", V,
  "Yesterday: cost pass. Today: review. Dev is heading towards GBP 30 with "
  "auto-pause and scale to zero.", issue="PULSE-108"),
M(STD, "2026-08-28 09:21:00", N,
  "Yesterday: page verified. Today: review, then planning the analytics "
  "regression pack - it is the last uncovered layer.", issue="PULSE-106"),
M(STD, "2026-08-28 09:23:00", A,
  "Yesterday: operations conversations. Today: finishing the gap list for the "
  "review. Eleven asks, and seven are already answerable.", issue="PULSE-96"),

# ============================================================== Sprint 14
M(STD, "2026-08-31 09:15:00", G,
  "Sprint 13 retro at 09:30, Sprint 14 planning at 11:00. Predictive analytics "
  "and cloud this sprint. Everything gets backtested against a seasonal naive "
  "baseline.", issue="PULSE-9"),
M(STD, "2026-08-31 10:15:00", G,
  "Retro. Kept: publishing five attribution models instead of picking one - "
  "the spread was the finding. Changed: Amit joins planning from now on rather "
  "than receiving the outcome. Tried: the cross-model total assertion, which "
  "caught a 0.4% rounding drift nobody would have seen on a chart.",
  reactions=":+1: 4"),
M(STD, "2026-08-31 12:40:00", G,
  "Sprint 14 committed: forecasting, churn, inventory, basket, the operations "
  "page, Terraform and the analytics regression pack. It is a lot and I expect "
  "we carry two of them."),

M(STD, "2026-09-01 09:15:00", G,
  "Standup. Yesterday: planning. Today: forecasting - Holt-Winters first, then "
  "the baselines. No blockers.", issue="PULSE-98"),
M(STD, "2026-09-01 09:17:00", D,
  "Yesterday: planning. Today: churn feature engineering. No blockers.",
  issue="PULSE-100"),
M(STD, "2026-09-01 09:19:00", V,
  "Yesterday: planning. Today: Terraform modules up for review. No blockers.",
  issue="PULSE-107"),
M(STD, "2026-09-01 09:21:00", N,
  "Yesterday: planning. Today: analytics regression pack, starting with "
  "forecast completeness. No blockers.", issue="PULSE-106"),
M(STD, "2026-09-01 09:23:00", A,
  "Yesterday: planning. Today: traceability matrix - 34 of 41 requirements "
  "mapped so far. No blockers.", issue="PULSE-97"),

M(STD, "2026-09-03 09:15:00", G,
  "Standup. Yesterday: Holt-Winters at 12.4% MAPE, which sounds fine until you "
  "have something to compare it to. Today: backtesting against seasonal naive.",
  issue="PULSE-98"),
M(STD, "2026-09-03 09:17:00", D,
  "Yesterday: churn features. Today: first model scored 0.94 AUC, which I do "
  "not believe. Investigating leakage before anything else.",
  issue="PULSE-101"),
M(STD, "2026-09-03 09:19:00", V,
  "Yesterday: Terraform review comments. Today: fixing them - Divya caught a "
  "public network access flag defaulting to true, which was me testing "
  "connectivity and forgetting.", issue="PULSE-107"),
M(STD, "2026-09-03 09:21:00", N,
  "Yesterday: forecast completeness assertions. Today: temporal validation for "
  "the churn features, which looks timely.", issue="PULSE-106"),
M(STD, "2026-09-03 09:23:00", A,
  "Yesterday: traceability. Today: same. Three requirements have a dashboard "
  "tile and no test, and one has a test and no definition.", issue="PULSE-97"),

M(STD, "2026-09-04 09:15:00", G,
  "Standup. Yesterday: the naive baseline beats Holt-Winters on the daily "
  "series and loses on the weekly. Today: per-series selection by backtest, "
  "and publishing all three.", issue="PULSE-98"),
M(STD, "2026-09-04 09:17:00", D,
  "Yesterday: confirmed leakage - features computed at the same moment as the "
  "label, so recency_days was the label. Today: rewinding the snapshot 90 "
  "days.", issue="PULSE-101"),
M(STD, "2026-09-04 09:19:00", V,
  "Yesterday: Terraform fixes. Today: apply is green in dev, so writing ADR-006 "
  "on managed Postgres over Synapse.", issue="PULSE-109"),
M(STD, "2026-09-04 09:21:00", N,
  "Yesterday: temporal validation assertion written. Today: it passes after "
  "Divya's fix. Moving on to the basket assertions.", issue="PULSE-106"),
M(STD, "2026-09-04 09:23:00", A,
  "Yesterday: traceability gaps. Today: starting the stakeholder KPI catalogue "
  "structure.", issue="PULSE-116"),

M(STD, "2026-09-07 09:15:00", G,
  "Standup. Yesterday: forecasting merged. Today: ADR-005 on the linear churn "
  "model, and starting basket affinity.", issue="PULSE-102"),
M(STD, "2026-09-07 09:17:00", D,
  "Yesterday: rewound snapshot. Today: 0.71 AUC and it actually predicts. "
  "Putting it up for review.", issue="PULSE-100"),
M(STD, "2026-09-07 09:19:00", V,
  "Yesterday: ADR-006. Today: test tfvars, then the deploy workflows. "
  "Reminder that PULSE-120 alerting is still blocked on a rota, not on work.",
  issue="PULSE-120"),
M(STD, "2026-09-07 09:21:00", N,
  "Yesterday: basket fixture hand-worked. Today: the assertion against it. "
  "Blocked on PULSE-104 for the rest.", issue="PULSE-106"),
M(STD, "2026-09-07 09:23:00", A,
  "Yesterday: catalogue structure. Today: same. Blocked on the operations page "
  "for seven traceability rows.", issue="PULSE-105"),

M(STD, "2026-09-09 09:15:00", G,
  "Standup. Yesterday: reviewing churn, ADR-005 drafted. Today: finishing the "
  "review and starting basket affinity properly. No blockers.",
  issue="PULSE-104"),
M(STD, "2026-09-09 09:17:00", D,
  "Yesterday: churn in review. Today: inventory optimisation, now unblocked by "
  "the forecast. The operations page is behind it.", issue="PULSE-103"),
M(STD, "2026-09-09 09:19:00", V,
  "Yesterday: test tfvars. Today: deploy workflow draft, and I want the "
  "rollback path exercised before we call it done.", issue="PULSE-113"),
M(STD, "2026-09-09 09:21:00", N,
  "Yesterday: basket assertion. Today: analytics pack, then starting the UAT "
  "scenarios. Expected results come from the KPI doc, not from the "
  "dashboards.", issue="PULSE-115"),
M(STD, "2026-09-09 09:23:00", A,
  "Yesterday: KPI catalogue. Today: same, plus lining up UAT sessions with "
  "finance and marketing first - they have the most at stake in the "
  "definitions.", issue="PULSE-115"),

M(STD, "2026-09-09 14:20:00", G,
  "Mid-sprint check. Forecasting done, churn in review, ADR-006 done. "
  "Inventory, basket and the operations page are the three at risk. If we "
  "carry two, I would rather carry basket and the operations page than ship "
  "the inventory numbers without a service level agreed.",
  reactions=":+1: 3"),

# ======================================================== QA / data quality
M(DQ, "2026-07-09 09:05:00", D,
  "[automated] Nightly quality suite - run 2026-07-09. 24 checks, 20 pass, "
  "4 WARN, 0 fail. All four warnings within threshold."),
M(DQ, "2026-07-09 10:30:00", N,
  "Picking up the customer marts regression pack (PULSE-77). Scope is "
  "customer_360, RFM, cohort retention and churn monthly. Starting with the "
  "assertion I care most about: two runs on the same data produce identical "
  "output.", issue="PULSE-77"),
M(DQ, "2026-07-10 09:05:00", D,
  "[automated] Nightly quality suite - run 2026-07-10. 24 checks, 20 pass, "
  "4 WARN, 0 fail."),
M(DQ, "2026-07-10 14:15:00", N,
  "customer_360 row count assertion is in - it must equal distinct customers "
  "in the dimension. Passing, including the zero-order customers that stay in "
  "deliberately.", issue="PULSE-71"),
M(DQ, "2026-07-13 09:05:00", D,
  "[automated] Nightly quality suite - run 2026-07-13. 24 checks, 20 pass, "
  "4 WARN, 0 fail. FX carry-forward at 28.4%, threshold 35%."),
M(DQ, "2026-07-13 11:40:00", N,
  "RFM segment sizes sum to the active customer count, and I ran the "
  "segmentation twice on the same dataset and got identical sizes. That is "
  "only true because of the analysis window, so it is really a test of "
  "ADR-002.", issue="PULSE-72", reactions=":100: 1"),
M(DQ, "2026-07-14 15:10:00", N,
  "Adding a cohort size assertion after PULSE-74: cohort size must equal the "
  "count of customers whose first order falls in that month. It cannot catch a "
  "bad definition, but it will catch a regression away from the good one.",
  issue="PULSE-74"),
M(DQ, "2026-07-15 09:05:00", D,
  "[automated] Nightly quality suite - run 2026-07-15. 24 checks, 20 pass, "
  "4 WARN, 0 fail."),
M(DQ, "2026-07-16 10:20:00", N,
  "Every recency metric now has a paired assertion: it must change when "
  "analysis_window moves, and must not change otherwise. Caught nothing, which "
  "is the correct outcome.", issue="PULSE-77"),
M(DQ, "2026-07-17 09:05:00", D,
  "[automated] Nightly quality suite - run 2026-07-17. 24 checks, 20 pass, "
  "4 WARN, 0 fail."),
M(DQ, "2026-07-17 11:30:00", N,
  "Customer pack complete and in CI: 19 assertions across four marts. "
  "Coverage summary for the review - bronze, silver, gold, marts and "
  "dashboards are covered. Analytics modules and streaming are not.",
  issue="PULSE-77"),
M(DQ, "2026-07-17 11:45:00", G,
  "Noted, and streaming becomes coverable next sprint. The analytics gap is "
  "the one that will bite us, because a wrong model output looks exactly like "
  "a right one.", thread="2026-07-17 11:30:00", issue="PULSE-77"),

M(DQ, "2026-07-21 09:05:00", D,
  "[automated] Nightly quality suite - run 2026-07-21. 24 checks, 20 pass, "
  "4 WARN, 0 fail."),
M(DQ, "2026-07-21 14:40:00", N,
  "Streaming test approach for the sprint: everything runs against the file "
  "bus in CI, and the Kafka path gets exercised locally against Redpanda. Same "
  "consumer code either way, so we are not testing a stand-in.",
  issue="PULSE-79"),
M(DQ, "2026-07-23 09:05:00", D,
  "[automated] Nightly quality suite - run 2026-07-23. 24 checks, 20 pass, "
  "4 WARN, 0 fail. Unattributed orders at 34.6%, threshold 40% - worth "
  "watching, it has drifted up half a point this month."),
M(DQ, "2026-07-23 10:15:00", G,
  "Good catch on the drift. Not actionable yet, but that is exactly the "
  "pattern PULSE-121 would catch automatically instead of relying on someone "
  "reading carefully.", thread="2026-07-23 09:05:00", issue="PULSE-121"),
M(DQ, "2026-07-28 09:05:00", D,
  "[automated] Nightly quality suite - run 2026-07-28. 24 checks, 20 pass, "
  "4 WARN, 0 fail."),
M(DQ, "2026-07-29 15:20:00", N,
  "Consumer crash test: kill mid-batch, restart, assert no duplicates and no "
  "gaps. Passes on the current build. I also ran it against the earlier build "
  "where the offset commit came first and it failed, so the test is doing real "
  "work rather than agreeing with the implementation.", issue="PULSE-82",
  reactions=":100: 2"),
M(DQ, "2026-07-31 09:05:00", D,
  "[automated] Nightly quality suite - run 2026-07-31. 24 checks, 20 pass, "
  "4 WARN, 0 fail."),
M(DQ, "2026-07-31 14:30:00", N,
  "Replay test in: the same seeded stream produces identical KPI output across "
  "two runs. That is the assertion that makes the whole real-time layer "
  "testable.", issue="PULSE-83"),

M(DQ, "2026-08-04 09:05:00", D,
  "[automated] Nightly quality suite - run 2026-08-04. 24 checks, 20 pass, "
  "4 WARN, 0 fail."),
M(DQ, "2026-08-04 13:20:00", N,
  "Test scope for the streaming ops tables. Three things I want asserted: "
  "events land once, the KPI window recomputes from what landed, and the ops "
  "tables survive a batch rebuild. The third one has no coverage at all today."),
M(DQ, "2026-08-05 09:05:00", D,
  "[automated] Nightly quality suite - run 2026-08-05. 24 checks, 20 pass, "
  "4 WARN, 0 fail."),
M(DQ, "2026-08-07 09:30:00", N,
  "Following up on yesterday's incident. PULSE-86 is written and it fails "
  "against main, which is what I wanted to confirm before anyone fixes "
  "anything - otherwise I am only asserting that the fix works.",
  issue="PULSE-86", reactions=":100: 2"),
M(DQ, "2026-08-07 10:10:00", G,
  "That sequencing is right and I want it to be the habit: for a silent "
  "failure, write the failing test first. It is the only way to know the test "
  "would have caught it.", thread="2026-08-07 09:30:00", issue="PULSE-86"),
M(DQ, "2026-08-10 09:05:00", D,
  "[automated] Nightly quality suite - run 2026-08-10. 24 checks, 20 pass, "
  "4 WARN, 0 fail."),
M(DQ, "2026-08-12 11:20:00", N,
  "Both PULSE-86 assertions green on the fix branch: the behavioural test "
  "(land events, rebuild, counts unchanged) and the DDL scan. The scan is the "
  "one that catches someone reintroducing the pattern in a file that is not "
  "wired in yet.", issue="PULSE-86"),
M(DQ, "2026-08-13 09:05:00", D,
  "[automated] Nightly quality suite - run 2026-08-13. 25 checks, 21 pass, "
  "4 WARN, 0 fail. New check: real-time to batch revenue reconciliation for a "
  "closed day.", issue="PULSE-84"),
M(DQ, "2026-08-13 14:50:00", N,
  "Staleness tested by stopping the producer. The page flags stale after the "
  "threshold rather than presenting an old window as current. That was the "
  "behaviour I was most worried about on that page.", issue="PULSE-87"),
M(DQ, "2026-08-14 09:05:00", D,
  "[automated] Nightly quality suite - run 2026-08-14. 25 checks, 21 pass, "
  "4 WARN, 0 fail."),
M(DQ, "2026-08-14 15:10:00", N,
  "Coverage after this sprint: streaming is now covered end to end, including "
  "the failure modes. Remaining gap is the analytics modules - forecasting, "
  "churn, inventory, basket. All four land next sprint or the one after.",
  issue="PULSE-106"),

M(DQ, "2026-08-18 09:05:00", D,
  "[automated] Nightly quality suite - run 2026-08-18. 25 checks, 21 pass, "
  "4 WARN, 0 fail."),
M(DQ, "2026-08-19 14:20:00", N,
  "Marketing test scope. The thing I want covered is not the arithmetic, it is "
  "that every revenue column names its attribution basis. A column called "
  "revenue in a marketing mart is the bug.", issue="PULSE-90"),
M(DQ, "2026-08-21 09:05:00", D,
  "[automated] Nightly quality suite - run 2026-08-21. 25 checks, 21 pass, "
  "4 WARN, 0 fail."),
M(DQ, "2026-08-21 15:30:00", N,
  "Added the cross-model assertion Divya suggested: all five attribution "
  "models must sum to the same total attributed revenue. Time decay was out by "
  "0.4% from a rounding accumulation. Fixed and green.", issue="PULSE-91",
  reactions=":eyes: 2"),
M(DQ, "2026-08-25 09:05:00", D,
  "[automated] Nightly quality suite - run 2026-08-25. 25 checks, 21 pass, "
  "4 WARN, 0 fail."),
M(DQ, "2026-08-26 15:40:00", N,
  "Every figure on the marketing page verified against the marts, and every "
  "model column against attribution.py directly. All match, model ordering is "
  "fixed per the design system.", issue="PULSE-93"),
M(DQ, "2026-08-27 11:15:00", A,
  "Joining this channel. From the business side the check I would want is that "
  "the incrementality proxy can never appear without its caveat next to it - "
  "the caveat is the thing that gets lost in a screenshot.", issue="PULSE-94"),
M(DQ, "2026-08-27 11:40:00", N,
  "That is testable and worth doing. Adding an assertion that the proxy tile "
  "renders its limitation text, so removing the caveat fails the build.",
  thread="2026-08-27 11:15:00", issue="PULSE-94", reactions=":100: 3"),
M(DQ, "2026-08-28 09:05:00", D,
  "[automated] Nightly quality suite - run 2026-08-28. 25 checks, 21 pass, "
  "4 WARN, 0 fail."),

M(DQ, "2026-09-01 09:05:00", D,
  "[automated] Nightly quality suite - run 2026-09-01. 25 checks, 21 pass, "
  "4 WARN, 0 fail."),
M(DQ, "2026-09-01 13:30:00", N,
  "Starting the analytics regression pack (PULSE-106). This is the last "
  "uncovered layer and it is the one where a wrong answer looks most like a "
  "right one.", issue="PULSE-106"),
M(DQ, "2026-09-03 09:05:00", D,
  "[automated] Nightly quality suite - run 2026-09-03. 25 checks, 21 pass, "
  "4 WARN, 0 fail."),
M(DQ, "2026-09-03 14:10:00", N,
  "Adding temporal validation to the analytics pack after the churn AUC came "
  "in at 0.94: maximum feature timestamp must precede the label window start. "
  "It is mechanical, but leakage is subtle to spot and trivial to assert.",
  issue="PULSE-101", reactions=":+1: 3"),
M(DQ, "2026-09-04 09:05:00", D,
  "[automated] Nightly quality suite - run 2026-09-04. 25 checks, 21 pass, "
  "4 WARN, 0 fail."),
M(DQ, "2026-09-04 10:25:00", N,
  "Temporal validation passing against the rewound snapshot. Forecast "
  "completeness in too - one row per series per horizon step, no gaps, and "
  "every model reports its backtest error including the naive baseline.",
  issue="PULSE-106"),
M(DQ, "2026-09-04 10:50:00", G,
  "The baseline being a required field rather than an optional one is the "
  "right call. It makes it impossible to publish a forecast without saying "
  "what it beat.", thread="2026-09-04 10:25:00", issue="PULSE-99"),
M(DQ, "2026-09-07 09:05:00", D,
  "[automated] Nightly quality suite - run 2026-09-07. 25 checks, 21 pass, "
  "4 WARN, 0 fail. Email completeness 0.08%, threshold 0.15%."),
M(DQ, "2026-09-07 14:40:00", N,
  "Hand-worked a basket lift example against a small fixture so the assertion "
  "checks arithmetic I have verified myself, rather than checking the "
  "implementation against itself.", issue="PULSE-106"),
M(DQ, "2026-09-08 09:05:00", D,
  "[automated] Nightly quality suite - run 2026-09-08. 25 checks, 21 pass, "
  "4 WARN, 0 fail."),
M(DQ, "2026-09-08 15:20:00", N,
  "Analytics pack status: forecasting and churn covered, basket blocked on "
  "PULSE-104, inventory blocked on PULSE-103. Also picking up the three "
  "traceability rows Amit found with a tile and no test.", issue="PULSE-106"),
M(DQ, "2026-09-09 09:05:00", D,
  "[automated] Nightly quality suite - run 2026-09-09. 25 checks, 21 pass, "
  "4 WARN, 0 fail."),
M(DQ, "2026-09-09 11:30:00", N,
  "Starting the UAT pack (PULSE-115). Scripted scenarios per stakeholder "
  "group, in business language, with expected results derived from the KPI "
  "document rather than from the current dashboard output - otherwise we are "
  "only testing that the dashboard agrees with itself.", issue="PULSE-115"),
M(DQ, "2026-09-09 11:55:00", A,
  "I will facilitate those sessions and take the sign-offs into the "
  "traceability matrix. Finance and marketing first.",
  thread="2026-09-09 11:30:00", issue="PULSE-115", reactions=":+1: 2"),
M(DQ, "2026-09-09 14:05:00", N,
  "One thing for the retro: every defect we have found this year has been "
  "silent - a wrong number rather than a crash. Nine bugs, and the only ones a "
  "person noticed first were the ones where the number looked odd. That is an "
  "argument for more assertions between layers, not more unit tests.",
  reactions=":100: 3"),

]
