# -*- coding: utf-8 -*-
"""Slack transcript for PulseAnalytics, 01 Mar 2026 onwards.

Channels
  #pulse-general        project-wide announcements and decisions
  #pulse-eng            day-to-day engineering
  #pulse-data-quality   quality suite output and the conversations about it
  #pulse-standup        written standups
  #pulse-releases       merges, deploys and CI
  #pulse-stakeholders   shared with finance, marketing and operations

`thread` carries the timestamp of the parent message for threaded replies.
Neha joins 15 Jun 2026 and Amit 24 Aug 2026; neither appears before their date.
"""

from backlog_common import G, D, V, N, A

GEN = "#pulse-general"
ENG = "#pulse-eng"
DQ = "#pulse-data-quality"
STD = "#pulse-standup"
REL = "#pulse-releases"
STK = "#pulse-stakeholders"


def M(channel, ts, author, text, thread=None, issue=None, reactions=""):
    return dict(channel=channel, ts=ts, author=author, text=text,
                thread=thread or "", issue=issue or "", reactions=reactions)


SLACK = [

# ============================================================== Sprint 1
M(GEN, "2026-03-02 09:02:00", G,
  "Morning both, and welcome to day one of PulseAnalytics. Kickoff at 9.30, "
  "then the epic-cutting workshop straight after. Two things I want us to "
  "agree before we write any code: what we are building first, and what we "
  "are deliberately not building yet.", reactions=":wave: 2"),
M(GEN, "2026-03-02 09:05:00", V,
  "Ready. I have a blank repo and strong opinions about .gitignore."),
M(GEN, "2026-03-02 09:06:00", D,
  "Same, minus the gitignore opinions. I have been through the BRD twice - "
  "the recurring theme is that nobody trusts the current numbers rather than "
  "that they are missing numbers."),
M(GEN, "2026-03-02 12:40:00", G,
  "Workshop done. Eleven epics, PULSE-1 through PULSE-11. The sequencing "
  "argument we settled on: ingest, then define, then trust, then model, then "
  "show. Dashboards are epic five of eleven and that is deliberate.",
  issue="PULSE-1", reactions=":white_check_mark: 2"),
M(GEN, "2026-03-02 12:44:00", V,
  "The bit I want to flag for future-us: PULSE-10 runs the whole length of "
  "the project rather than being a deployment phase at the end. A deployment "
  "story started in month seven is a deployment story that discovers the code "
  "cannot be deployed.", thread="2026-03-02 12:40:00", issue="PULSE-10"),
M(GEN, "2026-03-02 12:51:00", D,
  "And no dashboard until epic five. I want that written somewhere more "
  "durable than a Slack message, because in about four weeks somebody is "
  "going to ask why there is nothing to look at.",
  thread="2026-03-02 12:40:00"),
M(GEN, "2026-03-02 12:55:00", G,
  "It is in the PULSE-2 epic description as an explicit non-goal. And you are "
  "right that someone will ask - the answer is that a dashboard built on a "
  "metric nobody has agreed to just locks in the disagreement.",
  thread="2026-03-02 12:40:00", issue="PULSE-2"),

M(ENG, "2026-03-03 10:18:00", V,
  "Repo layout pushed for PULSE-12. data/ is gitignored in full - generated "
  "warehouses are large, they change every run, and a committed .duckdb is a "
  "merge conflict nobody can resolve.", issue="PULSE-12"),
M(ENG, "2026-03-03 15:25:00", D,
  "Cloned clean and the quickstart worked, except DuckDB wants to download an "
  "extension on first run so it needs network. Added a README line rather "
  "than vendoring it.", thread="2026-03-03 10:18:00", issue="PULSE-12"),
M(ENG, "2026-03-03 11:45:00", V,
  "Bronze design question while I am in 002_bronze_tables.sql - every column "
  "lands as text, including things that are obviously integers. Any "
  "objections?", issue="PULSE-16"),
M(ENG, "2026-03-03 11:52:00", G,
  "None. A cast at the bronze boundary is a silent filter - anything that "
  "will not cast becomes a null or an exception and the original is gone "
  "either way.", thread="2026-03-03 11:45:00", issue="PULSE-16"),
M(ENG, "2026-03-04 10:50:00", V,
  "Honest admission for ADR-001: my instinct was to filter bad rows at load. "
  "It felt tidy. Geetha talked me out of it and I would like the rejected "
  "version recorded rather than quietly overwritten.", issue="PULSE-18",
  reactions=":100: 2"),
M(ENG, "2026-03-04 11:02:00", G,
  "Recorded as the rejected alternative. An ADR that only records the winning "
  "argument is half an ADR.", thread="2026-03-04 10:50:00", issue="PULSE-18"),

M(STD, "2026-03-05 09:30:00", G,
  "Standup. Yesterday: metric workshop prep, ADR-001 drafted. Today: the "
  "workshop with finance, sales and marketing. Blockers: none, though I "
  "expect the workshop to produce some."),
M(STD, "2026-03-05 09:32:00", D,
  "Yesterday: generator schema for customers, products, orders. Today: "
  "correlations - seasonality, weekday, tier effects. No blockers.",
  issue="PULSE-14"),
M(STD, "2026-03-05 09:34:00", V,
  "Yesterday: repo scaffold merged, deps pinned. Today: bronze DDL. Blocked "
  "on nothing, but prod access is still with the security review and nobody "
  "will give me a date."),

M(GEN, "2026-03-05 16:30:00", G,
  "Metric workshop report, and it went worse than I hoped, which is the good "
  "outcome. Finance excludes shipping from revenue. Marketing includes it. "
  "The board deck has been built from the marketing figure for two quarters. "
  "That is about a 6% difference on the monthly number.", issue="PULSE-19",
  reactions=":grimacing: 2 :eyes: 1"),
M(GEN, "2026-03-05 16:36:00", D,
  "Nobody had noticed because the two figures have never appeared on the same "
  "page as each other.", thread="2026-03-05 16:30:00", issue="PULSE-19"),
M(GEN, "2026-03-05 16:41:00", V,
  "Asking the uncomfortable question early: are we the team that tells the "
  "board the last two decks were 6% high?", thread="2026-03-05 16:30:00"),
M(GEN, "2026-03-05 16:52:00", G,
  "Yes, but framed as 'here is the standard definition and here is the "
  "restated series', not as an accusation. Restating is a one-off cost. Two "
  "live definitions is a permanent one, and it gets more expensive every "
  "month we leave it.", thread="2026-03-05 16:30:00",
  reactions=":+1: 2"),

M(ENG, "2026-03-10 09:40:00", V,
  "PULSE-17 detail worth flagging: a missing source file is an error, but a "
  "present file with zero rows is a warning with the count recorded. A silent "
  "zero-row extract looks exactly like a quiet business day until someone "
  "asks why last Tuesday is missing.", issue="PULSE-17"),
M(ENG, "2026-03-10 09:55:00", V,
  "Ran the largest generator preset overnight - 4.2m order lines in about "
  "nine minutes, deterministic across two machines with the same seed. That "
  "is good enough to load test against.", issue="PULSE-14",
  reactions=":rocket: 1"),
M(ENG, "2026-03-11 10:30:00", D,
  "Seeding the deliberate defects into the generator now: replayed orders, "
  "negative quantities, loyalty tier case drift, 0.07% of customers with no "
  "email, a few orphan customer ids, weekend FX gaps. Each at a documented "
  "rate so a test can assert both that we caught them and how many there "
  "should be.", issue="PULSE-15"),
M(ENG, "2026-03-11 10:38:00", G,
  "That last part is what makes the quality epic testable rather than "
  "aspirational.", thread="2026-03-11 10:30:00", issue="PULSE-15"),

M(REL, "2026-03-13 17:05:00", V,
  "Sprint 1 close. Merged: PULSE-12, 13, 14, 15, 16, 17, 18, 19. No CI yet, "
  "which is the biggest gap and is PULSE-32 next sprint.",
  reactions=":tada: 2"),

# ============================================================== Sprint 2
M(ENG, "2026-03-19 11:10:00", D,
  "Something is off. Order line count does not match the header count and the "
  "gap is suspiciously stable at about 1.2%. Digging.", issue="PULSE-23"),
M(ENG, "2026-03-19 11:32:00", D,
  "Found it - every missing order id starts with a zero. 0004821 is landing "
  "in bronze as 4821.", thread="2026-03-19 11:10:00", issue="PULSE-23",
  reactions=":face_palm: 1"),
M(ENG, "2026-03-19 11:50:00", V,
  "That is the CSV reader inferring dtypes. Which is exactly the failure "
  "ADR-001 predicted, three days after we wrote ADR-001. Nothing errored, "
  "nothing was logged, the rows just quietly stopped matching.",
  thread="2026-03-19 11:10:00", issue="PULSE-23"),
M(ENG, "2026-03-20 09:35:00", G,
  "Raising this to High. Silent data loss is top of the list of things I do "
  "not want in this platform. Please also add a check that asserts header to "
  "line join completeness, so this class of thing cannot come back "
  "unnoticed.", thread="2026-03-19 11:10:00", issue="PULSE-23"),
M(ENG, "2026-03-23 14:45:00", V,
  "Fixed with an explicit dtype map. The join completeness assertion goes "
  "into the reconciliation set in PULSE-40.", thread="2026-03-19 11:10:00",
  issue="PULSE-23", reactions=":white_check_mark: 2"),

M(STK, "2026-03-24 14:00:00", G,
  "Weekly numbers CSV attached, week ending 20 Mar. Still no dashboard, "
  "deliberately - we are agreeing definitions first, and the CSV plus a "
  "conversation is doing that job better than a chart would. Revenue here is "
  "on the agreed definition: net of discounts, excluding shipping and tax.",
  reactions=":+1: 3"),
M(STK, "2026-03-24 15:20:00", G,
  "To the question from finance in the thread - yes, this figure will differ "
  "from the marketing dashboard by roughly 6%, and that difference is the "
  "shipping treatment. It is written up in docs/kpi-definitions.md and I am "
  "happy to walk anyone through it.", thread="2026-03-24 14:00:00",
  issue="PULSE-24"),

M(ENG, "2026-03-24 16:15:00", V,
  "docker-compose with Postgres is up. From here I would like us both running "
  "against both engines locally. The gap we do not want is SQL that works in "
  "DuckDB, ships, and meets Postgres for the first time in the cloud.",
  issue="PULSE-26"),
M(ENG, "2026-03-27 12:20:00", D,
  "Two divergences already - date_trunc argument order and a window frame "
  "default. Both documented in the DDL rather than branched on.",
  thread="2026-03-24 16:15:00", issue="PULSE-26"),

M(GEN, "2026-03-18 09:45:00", G,
  "Writing the AOV definition into the KPI doc now, before the facts exist. "
  "AOV is revenue over distinct completed orders, header grain, never "
  "averaged from lines. Flagging it early because there is no error message "
  "for averaging the wrong grain - you just get a plausible wrong number.",
  issue="PULSE-25", reactions=":pushpin: 2"),
M(GEN, "2026-03-18 09:52:00", D,
  "Noted. I suspect we will still hit it once anyway.",
  thread="2026-03-18 09:45:00", issue="PULSE-25"),

M(REL, "2026-03-27 17:10:00", V,
  "Sprint 2 close. Bronze loads all eight sources, run context is recording, "
  "revenue and AOV definitions signed off by finance. One bug found and "
  "fixed (PULSE-23) and it was a silent one."),

# ============================================================== Sprint 3
M(ENG, "2026-04-01 11:25:00", D,
  "About 0.9% of orders arrive more than once - the source replays on retry. "
  "Collapsing on order_id with a window over ingest time.", issue="PULSE-28"),
M(ENG, "2026-04-06 15:55:00", G,
  "Careful with the survivor rule there. Ingest order and business order are "
  "not the same thing, and the difference is the status field. If an order "
  "was replayed as pending then completed, keeping the first row loses the "
  "revenue.", thread="2026-04-01 11:25:00", issue="PULSE-29"),
M(ENG, "2026-04-06 16:10:00", D,
  "You are right and it is doing exactly that. About 0.3% of completed orders "
  "silently excluded. Raised as PULSE-29.", thread="2026-04-01 11:25:00",
  issue="PULSE-29", reactions=":eyes: 2"),
M(ENG, "2026-04-07 09:20:00", V,
  "Second silent bug in three weeks, and both were caught by comparing counts "
  "across layers rather than by anything failing. That feels like it should "
  "shape the quality epic.", thread="2026-04-01 11:25:00"),
M(ENG, "2026-04-07 09:35:00", G,
  "Agreed, and it does - the reconciliation checks in PULSE-40 are precisely "
  "that idea made systematic. Everything else verifies that data looks "
  "reasonable. Reconciliations verify that two things we computed separately "
  "agree.", thread="2026-04-01 11:25:00", issue="PULSE-40",
  reactions=":100: 1"),

M(ENG, "2026-03-31 09:45:00", V,
  "Pipeline skeleton is six stages run in sequence. Explicitly not adding an "
  "orchestrator - six stages and one schedule do not need Dagster. I am "
  "keeping the stage boundaries clean so it becomes a wrapper when we do need "
  "it, and I will raise the ticket now with the trigger condition written "
  "down.", issue="PULSE-31"),
M(ENG, "2026-04-09 16:20:00", V,
  "PULSE-117 raised. Trigger: the moment there are two schedules with a "
  "dependency between them. Raising it at the point of deciding not to do it, "
  "so it is a ticket rather than a recurring conversation with no memory.",
  issue="PULSE-117", reactions=":brain: 2"),

M(REL, "2026-04-10 17:25:00", V,
  "CI is live. Lint, tests and a full pipeline build on generated data, "
  "against both DuckDB and containerised Postgres, under ten minutes. Red "
  "build blocks merge.", issue="PULSE-32", reactions=":rocket: 2"),
M(REL, "2026-04-10 17:28:00", D,
  "First run caught a Postgres-only cast error, which is exactly what it is "
  "for.", thread="2026-04-10 17:25:00", issue="PULSE-32"),

# ============================================================== Sprint 4
M(ENG, "2026-04-14 09:40:00", G,
  "Starting gold.analysis_window. It is one table and about eleven lines of "
  "SQL and I think it will end up being the highest-leverage thing in the "
  "warehouse. Every recency metric anchors to MAX(order_date), not to the "
  "clock, so a screenshot from April still matches the warehouse in "
  "September.", issue="PULSE-35", reactions=":pushpin: 2"),
M(ENG, "2026-04-17 11:25:00", V,
  "The test that greps the analytics SQL for CURRENT_DATE is what makes it "
  "stick. A convention without an assertion is a suggestion, and someone will "
  "write CURRENT_DATE at 6pm on a Friday.", thread="2026-04-14 09:40:00",
  issue="PULSE-35"),
M(ENG, "2026-04-24 14:30:00", D,
  "Merged with the test. It already caught one usage in a draft mart I had "
  "open.", thread="2026-04-14 09:40:00", issue="PULSE-35",
  reactions=":white_check_mark: 2"),

M(ENG, "2026-04-16 10:45:00", D,
  "Check framework design note: every check carries a plain-language "
  "description of what a failure means in business terms. A check called "
  "chk_cust_email_not_null tells whoever reads the alert nothing about "
  "whether to care.", issue="PULSE-37"),
M(ENG, "2026-04-20 09:30:00", V,
  "And the results table appends rather than overwrites. A check that has "
  "been drifting for three weeks is a different problem from one that broke "
  "last night, and you cannot tell them apart from a snapshot.",
  issue="PULSE-38"),
M(ENG, "2026-04-23 11:50:00", G,
  "That history is also the foundation drift detection will need eventually. "
  "Raising PULSE-121 now, while we are building the table, because it would "
  "be irritating to want it in six months with nothing to compare against.",
  issue="PULSE-121"),

M(ENG, "2026-04-15 10:55:00", G,
  "FX decision: convert at the rate on the order date, not today's rate. "
  "Restating history every time the currency moves makes last month's report "
  "disagree with itself and no explanation of that is ever satisfying.",
  issue="PULSE-34"),
M(ENG, "2026-04-20 14:10:00", D,
  "Carry-forward fills are flagged in a column so a check can count them. "
  "About 28% of dates are carried, which is just what weekends are.",
  thread="2026-04-15 10:55:00", issue="PULSE-34"),

# ============================================================== Sprint 5
M(DQ, "2026-04-29 06:00:00", D,
  "[automated] Nightly quality suite - run 2026-04-29. 24 checks, 21 pass, "
  "3 FAIL. Failing: chk_customer_email_completeness (0.07% missing), "
  "chk_orders_customer_fk (0.31% orphan), chk_line_quantity_positive "
  "(0.04% negative).", issue="PULSE-39"),
M(DQ, "2026-04-30 06:00:00", D,
  "[automated] Nightly quality suite - run 2026-04-30. 24 checks, 21 pass, "
  "3 FAIL. Same three.", issue="PULSE-39"),
M(DQ, "2026-05-01 06:00:00", D,
  "[automated] Nightly quality suite - run 2026-05-01. 24 checks, 21 pass, "
  "3 FAIL. Same three.", issue="PULSE-39"),
M(DQ, "2026-05-04 06:00:00", D,
  "[automated] Nightly quality suite - run 2026-05-04. 24 checks, 21 pass, "
  "3 FAIL. Same three.", issue="PULSE-39"),
M(DQ, "2026-05-04 09:20:00", V,
  "I want to name something. That is the ninth consecutive night with the "
  "same three failures, and I have not opened one of these messages in over a "
  "week. Neither, I suspect, has anyone else. A suite that fires every night "
  "is a suite that has been muted, and a muted suite catches nothing "
  "regardless of what it detects. Raising it as PULSE-41.",
  issue="PULSE-41", reactions=":eyes: 2 :100: 1"),
M(DQ, "2026-05-04 10:45:00", G,
  "This is the most important ticket in the quality epic and it is a process "
  "bug rather than a data bug. The data is fine - customers acquired in-store "
  "before email capture was mandatory genuinely have no email and never will. "
  "Zero tolerance on a check that encodes an accepted business reality is how "
  "you train people to ignore alerts.", thread="2026-05-04 09:20:00",
  issue="PULSE-41"),
M(DQ, "2026-05-05 11:10:00", D,
  "Went through all 24. Four encode accepted realities: missing emails, "
  "historic orphan ids, weekend FX carry-forward, and orders with no campaign "
  "attribution. Proposing quantified warning thresholds on those four with "
  "headroom above the current value, and the other twenty stay at zero.",
  thread="2026-05-04 09:20:00", issue="PULSE-42"),
M(DQ, "2026-05-05 11:25:00", G,
  "Approved, with one addition: every non-zero threshold gets an inline "
  "comment saying what accepted reality it encodes and who accepted it. A "
  "threshold without a reason becomes a threshold nobody dares to change.",
  thread="2026-05-04 09:20:00", issue="PULSE-42", reactions=":+1: 2"),
M(DQ, "2026-05-06 15:35:00", G,
  "Also worth saying explicitly: thresholds sit above the current value with "
  "headroom, so they detect drift rather than restate today's number. A "
  "threshold set exactly at the observed value fails on the first ordinary "
  "fluctuation and we are straight back here.",
  thread="2026-05-04 09:20:00", issue="PULSE-42"),
M(DQ, "2026-05-08 06:00:00", D,
  "[automated] Nightly quality suite - run 2026-05-08. 24 checks, 20 pass, "
  "4 WARN, 0 fail. Warnings: email completeness 0.07% (threshold 0.15%), "
  "orphan customer fk 0.31% (0.5%), FX carry-forward 28.1% (35%), "
  "unattributed orders 34.2% (40%).", issue="PULSE-42"),
M(DQ, "2026-05-08 16:02:00", V,
  "I read that whole report this morning, which is the actual measure of "
  "success here.", thread="2026-05-08 06:00:00", issue="PULSE-42",
  reactions=":tada: 2"),

M(ENG, "2026-05-05 11:35:00", D,
  "Rounding tolerance on the line-to-header reconciliation is 0.01 per order, "
  "absolute rather than relative. A relative tolerance on a small order is "
  "meaningless.", issue="PULSE-40"),
M(ENG, "2026-04-30 10:25:00", D,
  "Test fixture is session-scoped. Function scope was correct and took four "
  "minutes, which meant nobody would ever run it locally, which makes it "
  "worse than incorrect.", issue="PULSE-43"),

# ============================================================== Sprint 6
M(ENG, "2026-05-14 11:35:00", G,
  "Conformed is the word doing the work in PULSE-46. One customer dimension, "
  "joined by orders, payments and events alike. The moment there are two, "
  "'customers who bought' and 'customers who clicked' become unjoinable and "
  "nobody notices until the funnel numbers disagree.", issue="PULSE-46"),
M(ENG, "2026-05-18 10:45:00", G,
  "The check counting fact rows on surrogate key -1 is the whole point of the "
  "Unknown member. An Unknown member without a count is the same silent data "
  "loss as an inner join, just with better manners.", issue="PULSE-47"),
M(ENG, "2026-05-19 14:20:00", D,
  "0.31% of order facts land on customer -1, which matches the seeded orphan "
  "ids exactly. Good - the number is real and we know what it is.",
  thread="2026-05-18 10:45:00", issue="PULSE-47", reactions=":+1: 1"),

M(ENG, "2026-05-18 14:15:00", V,
  "Genuine question rather than a challenge: two facts holding the same "
  "revenue looks like duplication to me. What stops them drifting apart?",
  issue="PULSE-49"),
M(ENG, "2026-05-18 14:40:00", G,
  "Reconciliation check one, which fails the build if they disagree by more "
  "than a penny per order. And the duplication is the point - one line-grain "
  "fact plus a distinct-count discipline means the discipline lives in the "
  "head of whoever writes the query. Two explicit facts make the AOV mistake "
  "structurally impossible rather than discouraged in review.",
  thread="2026-05-18 14:15:00", issue="PULSE-50"),
M(ENG, "2026-05-18 14:48:00", V,
  "That is a good answer and I would like it in the ADR, including my "
  "objection. It is the obvious challenge and the ADR should answer it rather "
  "than pretend nobody raised it.", thread="2026-05-18 14:15:00",
  issue="PULSE-50", reactions=":100: 1"),

# ============================================================== Sprint 7
M(ENG, "2026-05-29 10:10:00", V,
  "Is building a Type 2 customer dimension with exactly one version per "
  "customer worth doing right now?", issue="PULSE-54"),
M(ENG, "2026-05-29 10:45:00", G,
  "Fair challenge. It is worth it because every downstream consumer writes "
  "its joins against the shape, and retrofitting valid_from into thirty "
  "existing queries is the expensive version. But the file header says "
  "plainly that the shape is real and the history is not, so nobody builds a "
  "tier-at-time-of-purchase analysis on it and gets a confidently wrong "
  "answer. Real change capture is PULSE-119.",
  thread="2026-05-29 10:10:00", issue="PULSE-54"),

M(ENG, "2026-06-01 11:45:00", D,
  "AOV in the draft sales mart is about 40% below what finance calculates by "
  "hand. Checking.", issue="PULSE-56"),
M(ENG, "2026-06-01 11:58:00", D,
  "It is the grain. I computed AVG(net_amount) over fact_sales, which is line "
  "grain. That is the average line value, not the average order value. "
  "Exactly the thing we wrote down in March.", thread="2026-06-01 11:45:00",
  issue="PULSE-56", reactions=":face_palm: 2"),
M(ENG, "2026-06-01 12:25:00", G,
  "We documented the trap in March and walked into it in June. I am not "
  "treating that as a documentation failure though - the document is how you "
  "knew to be suspicious of the number. But documentation does not run "
  "nightly, so it needs an assertion behind it.",
  thread="2026-06-01 11:45:00", issue="PULSE-56"),
M(ENG, "2026-06-02 09:40:00", V,
  "Adding my vote for the check. Two explicit facts made the mistake possible "
  "to detect. Only an assertion makes it impossible to ship.",
  thread="2026-06-01 11:45:00", issue="PULSE-56"),
M(ENG, "2026-06-04 12:30:00", G,
  "Fixed and the check is in. Retro item: any metric with a grain judgement "
  "in its definition gets an assertion when it is first implemented, not when "
  "it first goes wrong.", thread="2026-06-01 11:45:00", issue="PULSE-56",
  reactions=":white_check_mark: 2"),

M(GEN, "2026-06-05 17:05:00", G,
  "Star schema is done. 'Revenue by region by month for electronics' went "
  "from a day of bespoke SQL to about four minutes. Next sprint we finally "
  "build a dashboard - fourteen weeks in, which was the plan.",
  issue="PULSE-4", reactions=":tada: 2 :chart_with_upwards_trend: 1"),

# ============================================================== Sprint 8
M(GEN, "2026-06-09 09:15:00", G,
  "Neha Chauhan joins us as QA analyst on Monday 15 June. Access requests are "
  "in, runbook is being written, and her first week is deliberately narrow: "
  "build the warehouse, run the suite, and write down what is not covered. "
  "I would rather have her gap analysis than her agreement.",
  issue="PULSE-61", reactions=":wave: 2"),
M(GEN, "2026-06-09 09:35:00", V,
  "GitHub and Slack are instant. The warehouse read role needs the data owner "
  "and took nine days for Divya, so it is raised now rather than on the "
  "fifteenth.", thread="2026-06-09 09:15:00", issue="PULSE-61"),

M(ENG, "2026-06-09 11:20:00", G,
  "theme.py before the first chart, not after the thirtieth. One palette, one "
  "hue per entity across every page, fixed categorical order, sequential "
  "ramps for magnitude only, and no dual axes ever. Retrofitting consistency "
  "across a built estate costs an order of magnitude more and half of it "
  "never gets done.", issue="PULSE-58"),
M(ENG, "2026-06-12 14:25:00", D,
  "Fixed categorical order has already earned itself. A bar chart sorted by "
  "value redrew in a different order between two refreshes and I misread the "
  "change as a data problem for about ten minutes.",
  thread="2026-06-09 11:20:00", issue="PULSE-58"),

M(GEN, "2026-06-15 09:35:00", N,
  "Morning all - Neha here, first day. Thanks for the runbook, it is the most "
  "organised onboarding I have had. Starting by building the warehouse "
  "locally and running the suite end to end.", reactions=":wave: 3"),
M(GEN, "2026-06-15 14:25:00", N,
  "Warehouse built on the second attempt. First failed because I had not run "
  "the generator first - obvious in hindsight, worth one line in the runbook "
  "for the next person.", issue="PULSE-62"),
M(GEN, "2026-06-15 14:31:00", V,
  "Added. Thank you - that is exactly the kind of thing that is invisible "
  "once you know it.", thread="2026-06-15 14:25:00", issue="PULSE-62"),

M(ENG, "2026-06-17 11:45:00", N,
  "Read through the KPI document and the four ADRs. The thing that stands out "
  "is that most of your past bugs were silent rather than loud - wrong "
  "numbers rather than crashes. So my gap analysis is going to be mostly "
  "about assertions between layers rather than more unit tests.",
  issue="PULSE-62", reactions=":100: 2"),
M(ENG, "2026-06-19 16:30:00", N,
  "Gap analysis done. Three areas with no coverage at all: the dashboards, "
  "the analytics modules, and anything asserting that the ops tables survive "
  "a full warehouse rebuild. The third one worries me most, because a rebuild "
  "is routine and the streaming layer will land in those tables.",
  issue="PULSE-62", reactions=":eyes: 2"),
M(ENG, "2026-06-19 16:50:00", G,
  "That third one is a good instinct and it is now PULSE-86. Welcome aboard - "
  "that is a better first-week output than I asked for.",
  thread="2026-06-19 16:30:00", issue="PULSE-86"),

M(ENG, "2026-06-17 10:15:00", N,
  "Framing I want to check with you both: the quality suite asserts things "
  "about the data on every run, the test suite asserts things about the code "
  "on every push. Both matter, they are not substitutes, and that distinction "
  "was not obvious to me from the outside.", issue="PULSE-63"),
M(ENG, "2026-06-17 10:32:00", D,
  "That is clearer than how we have been describing it internally. Worth "
  "putting in the README, not just the strategy doc.",
  thread="2026-06-17 10:15:00", issue="PULSE-63", reactions=":+1: 2"),

# ============================================================== Sprint 9
M(ENG, "2026-06-30 10:25:00", N,
  "Raising PULSE-66 - the revenue and margin chart on the sales page uses a "
  "secondary y-axis, and ADR-004 says never. Raising it from the written rule "
  "rather than from taste, which is much easier to have a conversation "
  "about.", issue="PULSE-66"),
M(ENG, "2026-06-30 11:45:00", D,
  "Guilty. It was the quickest way to get both series in one place and I "
  "talked myself into it. Splitting into two aligned charts.",
  thread="2026-06-30 10:25:00", issue="PULSE-66", reactions=":+1: 2"),
M(ENG, "2026-06-30 12:02:00", G,
  "This is the ADR earning its keep in a code review, which is exactly what "
  "it is for. The series cross in September in the demo data and that "
  "crossing point is pure artefact of the two scales.",
  thread="2026-06-30 10:25:00", issue="PULSE-66"),

M(ENG, "2026-06-29 15:20:00", N,
  "Executive page went from 1.1s to 4.6s on the largest preset after the "
  "region filter landed. Not visible at all on the demo data, which is why it "
  "is worth testing against something bigger.", issue="PULSE-69"),
M(ENG, "2026-07-02 11:25:00", V,
  "Filter was applied in Python after loading the full result set, and the "
  "cache key did not include the filter values so every change was a cache "
  "miss on a full scan. Pushed into SQL, back to 0.9s.",
  thread="2026-06-29 15:20:00", issue="PULSE-69"),

M(STK, "2026-07-03 16:00:00", G,
  "The executive and sales dashboards are live. Four months in, and the "
  "reason they took four months is the reason you can trust them: every tile "
  "traces to a written definition that finance, sales and marketing all "
  "signed off in March. If you disagree with a number, the argument starts at "
  "the definition rather than at the chart.", issue="PULSE-64",
  reactions=":tada: 5 :clap: 3"),
M(STK, "2026-07-03 16:20:00", G,
  "One thing to be aware of: every page shows an 'as of' date. That is the "
  "latest date in the data, not today's date. It means a screenshot you take "
  "today will still match the warehouse in six months, which is deliberate.",
  thread="2026-07-03 16:00:00", issue="PULSE-35"),

# ============================================================= Sprint 10
M(ENG, "2026-07-08 10:25:00", G,
  "Zero-order customers stay in customer_360. They are the denominator of "
  "activation, and filtering them out here is exactly how an activation "
  "problem becomes invisible.", issue="PULSE-71"),
M(ENG, "2026-07-13 14:30:00", G,
  "The cohort chart has a 60% cliff between period 0 and period 1 and I "
  "cannot explain it. Something is wrong with the definition rather than the "
  "data.", issue="PULSE-74"),
M(ENG, "2026-07-13 15:10:00", G,
  "Got it. Cohorts are built on signup month, and a large share of signups "
  "never purchase at all. They enter a cohort and leave without ever having "
  "been a customer. The cliff is the activation rate wearing a retention "
  "costume - and it was three days from being presented to the board as a "
  "retention crisis.", thread="2026-07-13 14:30:00", issue="PULSE-74",
  reactions=":exploding_head: 2 :eyes: 1"),
M(ENG, "2026-07-13 15:25:00", D,
  "Second time a definition choice has produced a plausible and completely "
  "misleading picture. AOV was the first. Both caught by someone thinking a "
  "number looked odd, not by anything automated.",
  thread="2026-07-13 14:30:00", issue="PULSE-74"),
M(ENG, "2026-07-14 09:25:00", G,
  "And I do not think that is fully fixable with assertions. A definition can "
  "be internally consistent and still answer the wrong question. What we can "
  "do is require every cohort-shaped metric to state its membership rule on "
  "the chart itself, so a reader can catch what a test cannot.",
  thread="2026-07-13 14:30:00", issue="PULSE-74"),
M(ENG, "2026-07-14 15:35:00", N,
  "I can assert the mechanical half: cohort size must equal the count of "
  "customers whose first order is in that month. It will not catch a bad "
  "definition but it will catch a regression away from the good one.",
  thread="2026-07-13 14:30:00", issue="PULSE-74", reactions=":+1: 2"),
M(ENG, "2026-07-16 12:05:00", G,
  "Both done. And the activation finding goes to the business as a finding "
  "rather than being quietly absorbed into a definition change - it is "
  "genuinely the more useful of the two discoveries.",
  thread="2026-07-13 14:30:00", issue="PULSE-74"),

M(ENG, "2026-07-09 10:45:00", D,
  "Churn in a non-contractual business is a judgement, not an observation - "
  "nobody cancels, they just stop. Writing the window rule down with its "
  "arbitrariness admitted rather than presenting it as measured fact.",
  issue="PULSE-75"),
M(ENG, "2026-07-11 11:25:00", G,
  "CLV uses an explainable formula rather than a fitted probabilistic model. "
  "Marketing has to defend an acquisition budget with this number, and a "
  "number they cannot explain is a number they cannot defend.",
  issue="PULSE-76"),
M(ENG, "2026-07-14 15:40:00", N,
  "Determinism assertion is in the customer pack - two runs on the same data "
  "must produce byte-identical output. It is the property that makes every "
  "other test meaningful and it is invisible until it breaks.",
  issue="PULSE-77", reactions=":100: 1"),

# ============================================================= Sprint 11
M(ENG, "2026-07-22 10:35:00", V,
  "Streaming design, two rules. One: event time, never wall-clock time, or we "
  "can never replay a stream and get the same KPIs back. Two: the consumer "
  "owns no metric definitions - it lands events and recomputes a window, and "
  "every metric stays in SQL next to the batch ones.", issue="PULSE-7",
  reactions=":+1: 3"),
M(ENG, "2026-07-22 10:48:00", G,
  "Seconding rule two hard. Revenue must not mean two different things "
  "depending on which pipeline produced it. That is the failure mode that "
  "ends with two dashboards disagreeing in a board meeting.",
  thread="2026-07-22 10:35:00", issue="PULSE-7"),
M(ENG, "2026-07-23 09:55:00", V,
  "Rule one is just ADR-002 applied to streaming. Same principle, same "
  "reason: anchor to the data, not to the clock.",
  thread="2026-07-22 10:35:00", issue="PULSE-83"),

M(ENG, "2026-07-22 11:20:00", V,
  "Bus abstraction with a file implementation and a Kafka implementation. "
  "Without the file version, CI needs a broker, every test becomes slow and "
  "flaky, and streaming ends up as the untested corner of the platform.",
  issue="PULSE-79"),
M(ENG, "2026-07-28 14:15:00", N,
  "That is the difference between me being able to test this path and not. "
  "Running the consumer against files in CI is the same code path as against "
  "Redpanda.", thread="2026-07-22 11:20:00", issue="PULSE-79"),
M(ENG, "2026-07-27 11:25:00", V,
  "At-least-once with idempotent writes keyed on event id, rather than "
  "chasing exactly-once. Exactly-once here would mean a distributed "
  "transaction across the broker and the warehouse, for a KPI window that "
  "recomputes anyway.", issue="PULSE-82"),
M(ENG, "2026-07-30 15:15:00", N,
  "Crash test written - kill the consumer mid-batch, restart, assert no "
  "duplicates and no gaps. It passes now, and it failed against an earlier "
  "build where the commit came before the write, so the test is doing real "
  "work rather than confirming what we already believed.",
  thread="2026-07-27 11:25:00", issue="PULSE-82", reactions=":100: 2"),

# ============================================================= Sprint 12
M(DQ, "2026-08-06 09:35:00", D,
  "Real-time page is showing zeros this morning. I ran a full rebuild last "
  "night to pick up the new mart.", issue="PULSE-85"),
M(DQ, "2026-08-06 09:50:00", D,
  "ops.stream_events is empty. About four hours of landed events are gone. "
  "The rebuild succeeded, the quality suite passed, and nothing anywhere "
  "logged an error.", thread="2026-08-06 09:35:00", issue="PULSE-85",
  reactions=":rotating_light: 3"),
M(DQ, "2026-08-06 10:35:00", V,
  "Found it. The ops tables were created in the same file as the bronze "
  "tables with DROP TABLE IF EXISTS then CREATE. So a routine batch rebuild "
  "drops and recreates the streaming landing zone as a side effect. That has "
  "been sitting there since PULSE-22 in March.",
  thread="2026-08-06 09:35:00", issue="PULSE-85"),
M(DQ, "2026-08-06 10:52:00", V,
  "A batch job that can destroy the streaming layer is exactly the kind of "
  "coupling that causes a 3am page. In a deployed system this is a hole in "
  "the record that nothing can reconstruct.",
  thread="2026-08-06 09:35:00", issue="PULSE-85"),
M(DQ, "2026-08-06 11:20:00", G,
  "Retro item, properly. Two failures at once - destructive DDL and "
  "cross-layer coupling - and neither the quality suite nor the test suite "
  "could see it, because both only look at the warehouse after a successful "
  "build.", thread="2026-08-06 09:35:00", issue="PULSE-85"),
M(DQ, "2026-08-06 14:25:00", N,
  "This is the gap I flagged in my first week. Writing the test now, and I "
  "want to confirm it fails against current main before I fix anything - "
  "otherwise I am only asserting that the fix works.",
  thread="2026-08-06 09:35:00", issue="PULSE-86", reactions=":100: 3"),
M(DQ, "2026-08-06 15:10:00", N,
  "Confirmed failing against main. Good.", thread="2026-08-06 09:35:00",
  issue="PULSE-86"),
M(DQ, "2026-08-11 15:20:00", V,
  "Fixed. ops DDL is out of the bronze path entirely, everything is CREATE "
  "TABLE IF NOT EXISTS, and Neha's test is green. I also grepped the whole "
  "repo for DROP TABLE - two other places, both in test teardown, both fine.",
  thread="2026-08-06 09:35:00", issue="PULSE-85",
  reactions=":white_check_mark: 3"),
M(DQ, "2026-08-11 15:35:00", N,
  "Adding the DDL scan alongside the behavioural test. The behavioural test "
  "catches it happening; the scan catches someone reintroducing the pattern "
  "in a file that is not wired in yet.", thread="2026-08-06 09:35:00",
  issue="PULSE-86"),

M(ENG, "2026-08-10 11:35:00", D,
  "The staleness indicator on the real-time page is the important part of it. "
  "A live dashboard silently showing a fifteen-minute-old number is worse "
  "than one that says the feed is down, because people act on it.",
  issue="PULSE-87"),
M(ENG, "2026-08-13 14:20:00", N,
  "Tested by stopping the producer. It flags stale after the threshold and "
  "stops presenting the window as current.", thread="2026-08-10 11:35:00",
  issue="PULSE-87", reactions=":+1: 2"),

M(GEN, "2026-08-12 09:35:00", V,
  "Reopening the alerting conversation now that streaming is live. A stalled "
  "consumer is currently discovered by someone opening the dashboard. "
  "PULSE-120 is still blocked on a rota rather than on the work - the "
  "technical part is about two days.", issue="PULSE-120"),

M(STK, "2026-08-14 16:45:00", G,
  "Real-time monitoring is live. The original problem was that a payment "
  "gateway degradation on a Friday evening cost a full night of orders before "
  "anyone knew. That is now visible within minutes on the operations page. "
  "Worth noting we do not yet page anyone - there is no rota, and an alert "
  "with no owner trains people to ignore alerts.", issue="PULSE-7",
  reactions=":tada: 4"),

# ============================================================= Sprint 13
M(ENG, "2026-08-18 11:20:00", G,
  "Attribution approach: we are not picking a model. Five models, side by "
  "side, one row per channel and one column per model. No model here is "
  "correct, and publishing one would be a confident answer to a question we "
  "cannot answer - which would then immediately become 'the number'.",
  issue="PULSE-91", reactions=":100: 2"),
M(ENG, "2026-08-19 10:35:00", G,
  "Related discipline: the attribution basis goes in the column name. "
  "revenue_last_touch, not revenue. A column called revenue in a marketing "
  "mart is a lie by omission, because it is always attributed somehow.",
  issue="PULSE-90"),
M(ENG, "2026-08-21 14:25:00", D,
  "Unattributed revenue gets its own line rather than being distributed "
  "proportionally. It is 34% of the total. Spreading it would have hidden the "
  "single most important caveat about this whole mart.",
  thread="2026-08-19 10:35:00", issue="PULSE-90"),
M(ENG, "2026-08-24 15:35:00", D,
  "The spread is the finding. One influencer channel comes out at 1.8x ROAS "
  "on last touch and 6.1x on first touch, and it has had its budget cut for "
  "two quarters on the last-touch number.", issue="PULSE-91",
  reactions=":eyes: 3"),

M(GEN, "2026-08-19 14:15:00", G,
  "Amit Shinde joins as our BA on Monday 24 August. I have cut PULSE-95 as "
  "his epic now so there is a real backlog waiting on day one rather than two "
  "weeks of shadowing. For the first six months I carried the stakeholder "
  "relationship directly and it stopped scaling at three consumer teams.",
  issue="PULSE-95", reactions=":wave: 3"),

M(GEN, "2026-08-24 09:40:00", A,
  "Hello all - Amit, first day. Starting with the KPI document, because from "
  "the outside it looks like the closest thing here to a requirements "
  "baseline, which is an unusual and good sign.", reactions=":wave: 4"),
M(ENG, "2026-08-25 10:25:00", A,
  "Walked through the attribution work this morning. From the business side "
  "the useful reframing might be: the question is not which model is right, "
  "it is which channels the models disagree about - because those are the "
  "ones where the budget decision is actually a bet rather than a "
  "calculation.", issue="PULSE-91", reactions=":100: 3 :bulb: 2"),
M(ENG, "2026-08-25 11:10:00", G,
  "That is a better articulation than mine and it is going on the dashboard.",
  thread="2026-08-25 10:25:00", issue="PULSE-91"),

M(ENG, "2026-08-26 10:20:00", A,
  "On labelling the incrementality proxy - put it next to the number rather "
  "than in a tooltip or a footnote. In my experience the footnote does not "
  "survive the screenshot, and the screenshot is what reaches the decision.",
  issue="PULSE-94", reactions=":+1: 3"),

M(GEN, "2026-08-28 16:50:00", A,
  "End of first week. Gap list from the stakeholder conversations: eleven "
  "asks, seven of which are already answerable by a mart the asker did not "
  "know existed, three need new work, and one is genuinely unanswerable "
  "today - revenue by the loyalty tier held at the time of purchase.",
  issue="PULSE-96", reactions=":eyes: 3"),
M(GEN, "2026-08-28 17:05:00", G,
  "That last one is PULSE-119 and it has been in the backlog since May with "
  "exactly that justification. Good to have it confirmed by a real "
  "stakeholder ask rather than by our own guess.",
  thread="2026-08-28 16:50:00", issue="PULSE-119"),
M(GEN, "2026-08-28 17:12:00", A,
  "And seven of eleven being discovery rather than delivery is its own "
  "finding. That is what PULSE-116 is for.", thread="2026-08-28 16:50:00",
  issue="PULSE-116"),

M(STK, "2026-08-28 17:20:00", G,
  "Marketing analytics is live, and it answers the question that started it: "
  "the blended ROAS of 4.2 was a blend of five different numbers between 1.8 "
  "and 6.1, depending on attribution model. All five are on the page. The "
  "spread is the useful part.", issue="PULSE-8", reactions=":tada: 4"),

# ============================================================= Sprint 14
M(ENG, "2026-09-01 11:25:00", G,
  "First forecast run: Holt-Winters, MAPE 12.4%. Which reads as respectable "
  "until you have something to compare it against.", issue="PULSE-98"),
M(ENG, "2026-09-02 10:20:00", D,
  "Backtested it against seasonal naive. The naive baseline wins on the daily "
  "series at 11.8%. Holt-Winters wins clearly on the weekly aggregate. So the "
  "honest answer is that it depends on the series, which is not the answer "
  "anyone wants.", thread="2026-09-01 11:25:00", issue="PULSE-98",
  reactions=":eyes: 2"),
M(ENG, "2026-09-02 14:35:00", G,
  "Which is exactly why the baseline gets published as a first-class result, "
  "same table, same chart, same visual weight. Presenting Holt-Winters alone "
  "would have shipped a model that adds nothing at daily grain and nobody "
  "would have known.", thread="2026-09-01 11:25:00", issue="PULSE-99",
  reactions=":100: 3"),
M(ENG, "2026-09-05 11:30:00", G,
  "Same visual weight deliberately. A baseline rendered as a faint dashed "
  "line is a baseline being argued against rather than reported.",
  thread="2026-09-01 11:25:00", issue="PULSE-99"),

M(ENG, "2026-09-03 10:25:00", D,
  "Churn model scores 0.94 AUC. Raising a bug against my own work - 0.94 on a "
  "churn model built in an afternoon is not a good sign, it is a symptom.",
  issue="PULSE-101", reactions=":eyes: 3"),
M(ENG, "2026-09-03 10:52:00", D,
  "Leakage, as suspected. Features were computed at the same moment as the "
  "label, so recency_days effectively was the label. A customer is labelled "
  "churned because they have not purchased recently, and I handed the model "
  "exactly that.", thread="2026-09-03 10:25:00", issue="PULSE-101"),
M(ENG, "2026-09-03 11:45:00", G,
  "Correct instinct and worth saying plainly: a model that scores far better "
  "than the problem is hard is nearly always answering an easier question "
  "than the one you asked.", thread="2026-09-03 10:25:00", issue="PULSE-101",
  reactions=":100: 2"),
M(ENG, "2026-09-04 09:40:00", N,
  "Adding a temporal validation assertion to the analytics pack - maximum "
  "feature timestamp must precede the label window start. Mechanical, but "
  "this class of bug is subtle to spot and trivial to assert.",
  thread="2026-09-03 10:25:00", issue="PULSE-106", reactions=":+1: 3"),
M(ENG, "2026-09-07 15:15:00", D,
  "Rebuilt with a 90-day rewind. 0.71 AUC, top decile carries about 3.4x the "
  "base churn rate, and it actually predicts. Neha's assertion is green.",
  thread="2026-09-03 10:25:00", issue="PULSE-100",
  reactions=":white_check_mark: 3"),

M(ENG, "2026-09-07 15:35:00", G,
  "Writing ADR-005 while the numbers are fresh: logistic regression over the "
  "gradient-boosted model, which scored about 0.03 AUC better. The retention "
  "team has to know why a customer is at risk in order to write a campaign. "
  "A ranked list from a black box tells them who but not what to say.",
  issue="PULSE-102", reactions=":+1: 2"),
M(ENG, "2026-09-08 10:15:00", G,
  "With a revisit condition: when an action exists that needs only the "
  "ranking and not the reason. This is a decision about the current use case, "
  "not a permanent position on model families.", thread="2026-09-07 15:35:00",
  issue="PULSE-102"),

M(ENG, "2026-09-02 09:45:00", V,
  "First Terraform draft priced out at roughly GBP 600 a month for a dev "
  "environment nobody uses at night - provisioned SQL and premium Databricks. "
  "That is how a platform gets switched off by finance in month three.",
  issue="PULSE-108", reactions=":grimacing: 2"),
M(ENG, "2026-09-08 11:25:00", V,
  "Serverless Postgres with auto-pause, Container Apps scaled to zero, "
  "smallest Databricks cluster with aggressive auto-termination, lifecycle "
  "rules to cool storage after 30 days. Dev is now about GBP 31. The estimate "
  "is committed next to the Terraform so a change that increases it shows up "
  "in the diff.", thread="2026-09-02 09:45:00", issue="PULSE-108",
  reactions=":money_with_wings: 2 :+1: 2"),

M(ENG, "2026-09-03 10:45:00", G,
  "ADR-006 on managed Postgres over Synapse is up. The part that makes it "
  "useful is the revisit trigger with real numbers on it - gold over roughly "
  "500GB, or p95 dashboard latency past 3s. Without that the conversation "
  "reopens every quarter on vibes.", issue="PULSE-109", reactions=":+1: 2"),

M(ENG, "2026-09-01 10:35:00", A,
  "Traceability draft covers 34 of 41 requirements. The empty cells are the "
  "useful part - three requirements have a dashboard tile and no test, and "
  "one has a test and no definition, which is the more interesting way "
  "round.", issue="PULSE-97", reactions=":eyes: 2"),
M(ENG, "2026-09-03 11:20:00", N,
  "The three with a tile and no test are going into the analytics regression "
  "pack this sprint.", thread="2026-09-01 10:35:00", issue="PULSE-106"),

M(STD, "2026-09-08 09:30:00", G,
  "Standup. Yesterday: ADR-005 drafted, reviewing churn. Today: churn review "
  "and starting basket affinity. No blockers."),
M(STD, "2026-09-08 09:32:00", D,
  "Yesterday: churn rebuilt with the rewind, 0.71 AUC, moved to review. "
  "Today: starting inventory optimisation, now unblocked by the forecast "
  "landing Friday. Operations page is behind it.", issue="PULSE-103"),
M(STD, "2026-09-08 09:34:00", V,
  "Yesterday: dev Terraform apply green, cost pass done. Today: test tfvars, "
  "then deployment workflows. Blocker to flag - PULSE-120 alerting is still "
  "waiting on a rota, and it is the largest operational gap we have.",
  issue="PULSE-120"),
M(STD, "2026-09-08 09:36:00", N,
  "Yesterday: hand-worked the basket lift fixture. Today: analytics "
  "regression pack, blocked on PULSE-104 for the basket assertions. UAT pack "
  "planning after that.", issue="PULSE-106"),
M(STD, "2026-09-08 09:38:00", A,
  "Yesterday: traceability, 34 of 41. Today: KPI catalogue structure. Blocked "
  "on the operations page for seven traceability rows - not urgent, but it is "
  "why the matrix will not close this sprint.", issue="PULSE-97"),

M(GEN, "2026-09-08 11:40:00", G,
  "Halfway point note, six months in. Two things I would keep if we started "
  "again: the six weeks with no dashboard, and anchoring everything to the "
  "data instead of the clock. Both felt slow at the time and both are why "
  "nobody argues with the numbers now.", reactions=":100: 4 :clap: 2"),
M(GEN, "2026-09-08 11:48:00", N,
  "From four months in - the thing that struck me most is that nearly every "
  "bug here has been silent. Not crashes, wrong numbers. That changed how I "
  "test: assertions between layers rather than more unit tests.",
  thread="2026-09-08 11:40:00", reactions=":100: 2"),
M(GEN, "2026-09-08 11:55:00", A,
  "And from two weeks in - the platform's problem is no longer trust, it is "
  "discovery. Seven of my eleven stakeholder gaps were things that already "
  "exist. That is a much better problem to have than the reverse.",
  thread="2026-09-08 11:40:00", issue="PULSE-116", reactions=":+1: 3"),

]

# ==========================================================================
# Day-to-day development traffic: pull requests, reviews, CI, debugging.
#
# Split out from the narrative messages above because it is a different kind
# of conversation - shorter, more mechanical, and anchored to a branch or a
# build rather than to a decision. Every message names its ticket.
# ==========================================================================

SLACK += [

# ---------------------------------------------------------------- Sprint 1
M(ENG, "2026-03-04 09:25:00", V,
  "Branch convention so the board stays readable: pulse/PULSE-12-short-slug. "
  "The key goes first so a branch list sorts into something you can scan. PR "
  "template is in .github with a checklist - ticket link, what changed, how "
  "it was verified.", issue="PULSE-12"),
M(ENG, "2026-03-06 11:40:00", D,
  "PR #14 up for PULSE-14 - generator schemas for customers, products, orders "
  "and lines. About 400 lines but most of it is the reference tables. Would "
  "like a look at the seeding, since everything downstream depends on it "
  "being reproducible.", issue="PULSE-14"),
M(ENG, "2026-03-06 14:20:00", V,
  "Reviewed PULSE-14. One change requested: the seed is read once at module "
  "import, so two generator calls in the same process share a stream and the "
  "second one is not reproducible on its own. Pass the seed into the "
  "constructor instead.", thread="2026-03-06 11:40:00", issue="PULSE-14",
  reactions=":eyes: 1"),
M(ENG, "2026-03-09 10:05:00", D,
  "Good catch, fixed and pushed. PULSE-14 now takes the seed per call and I "
  "added a test that generates twice in one process and asserts the frames "
  "are identical.", thread="2026-03-06 11:40:00", issue="PULSE-14"),
M(ENG, "2026-03-11 15:30:00", G,
  "Reviewing PULSE-16. The bronze DDL is fine, but every table repeats the "
  "same five metadata columns by hand. If we add a sixth we will miss one - "
  "worth a small generator or at least a comment block that says these five "
  "must stay in step.", issue="PULSE-16"),
M(ENG, "2026-03-11 16:10:00", V,
  "Fair. Pulled them into a template applied per table in PULSE-16, so the "
  "metadata columns are declared once.", thread="2026-03-11 15:30:00",
  issue="PULSE-16"),

# ---------------------------------------------------------------- Sprint 2
M(ENG, "2026-03-17 11:20:00", V,
  "PR up for PULSE-20, the bronze loader. The idempotency is per run_id: a "
  "re-run deletes its own rows and reloads, so a partial load cannot leave "
  "half a file behind. Worth a careful read of the delete predicate.",
  issue="PULSE-20"),
M(ENG, "2026-03-17 14:45:00", D,
  "Read it twice. The predicate is scoped to run_id and source file, which is "
  "right - scoping to run_id alone would have wiped the other seven sources "
  "on a single-file retry. Approving PULSE-20.",
  thread="2026-03-17 11:20:00", issue="PULSE-20", reactions=":+1: 1"),
M(ENG, "2026-03-20 10:15:00", D,
  "Small review note on PULSE-21: the backoff is retrying on 4xx as well as "
  "5xx. A 401 is not going to fix itself in eight seconds, and six retries "
  "against a bad credential is a good way to get the key blocked.",
  issue="PULSE-21", reactions=":eyes: 2"),
M(ENG, "2026-03-20 10:40:00", V,
  "Correct, that is sloppy. Retrying 429 and 5xx only, everything else fails "
  "immediately with the status and endpoint in the message. Pushed to "
  "PULSE-21.", thread="2026-03-20 10:15:00", issue="PULSE-21"),
M(ENG, "2026-03-23 11:30:00", V,
  "PULSE-23 fix is up. The diff is small - an explicit dtype map in the "
  "reader - but I have added the header-to-line count assertion to the same "
  "PR so the fix and the thing that would have caught it land together.",
  issue="PULSE-23", reactions=":+1: 2"),

# ---------------------------------------------------------------- Sprint 3
M(ENG, "2026-04-01 14:50:00", D,
  "PULSE-28 is up. The de-dupe is a ROW_NUMBER over order_id ordered by "
  "updated_at desc, ingested_at desc. Please look hard at the ordering - it "
  "is the whole correctness of the story and I have already had it wrong "
  "once.", issue="PULSE-28"),
M(ENG, "2026-04-02 09:40:00", G,
  "Ordering is right now. One more thing for PULSE-28: the dedupe count needs "
  "to go into the run context, otherwise a sudden jump in replays is "
  "invisible. Right now we would only find out by noticing revenue moved.",
  thread="2026-04-01 14:50:00", issue="PULSE-28"),
M(ENG, "2026-04-07 15:20:00", V,
  "CI on PULSE-31 went red on the Postgres job and green on DuckDB. It is a "
  "cast - Postgres will not implicitly compare a text column to an integer "
  "literal. Not a flake, a real difference, which is the argument for running "
  "both.", issue="PULSE-31", reactions=":eyes: 1"),
M(ENG, "2026-04-08 09:30:00", D,
  "That is the second time this week. Adding a note to the SQL style section "
  "of the README: cast explicitly at the silver boundary, never rely on the "
  "engine to guess. Ticketed under PULSE-31.",
  thread="2026-04-07 15:20:00", issue="PULSE-31"),
M(ENG, "2026-04-09 11:15:00", V,
  "PULSE-32: CI is at nine minutes forty, which is close enough to the ten "
  "minute target to be a problem soon. Most of it is the warehouse build. "
  "Caching the generated dataset between jobs when the seed has not changed "
  "would take a couple of minutes off.", issue="PULSE-32"),

# ---------------------------------------------------------------- Sprint 4
M(ENG, "2026-04-15 14:20:00", G,
  "PULSE-35 is a tiny PR - one view and a test - but it touches every "
  "recency metric we will ever write, so I would rather two reviews than one. "
  "Deven, Divya, when you get a moment.", issue="PULSE-35"),
M(ENG, "2026-04-16 10:50:00", D,
  "Approved PULSE-35. The grep test is doing more work than the view is. One "
  "suggestion: have it fail with the offending file and line rather than just "
  "a count, so the fix is obvious from the CI log.",
  thread="2026-04-15 14:20:00", issue="PULSE-35", reactions=":+1: 2"),
M(ENG, "2026-04-21 15:40:00", V,
  "Review note on PULSE-37: the check API takes a threshold as a bare float, "
  "so 0.15 could be a fraction or a percentage depending on who wrote the "
  "check. Two of the twenty-four already disagree. Make it explicit in the "
  "parameter name or take a typed threshold.", issue="PULSE-37",
  reactions=":eyes: 2"),
M(ENG, "2026-04-22 09:20:00", D,
  "Both of those were mine. Renamed to threshold_pct throughout PULSE-37 and "
  "fixed the two that were wrong. That would have been an interesting bug to "
  "find at 3am.", thread="2026-04-21 15:40:00", issue="PULSE-37"),

# ---------------------------------------------------------------- Sprint 5
M(ENG, "2026-05-05 14:10:00", D,
  "PULSE-39 PR has all 24 checks. It is a big diff but it is 24 near-"
  "identical declarations, so read the first three carefully and skim the "
  "rest - or tell me the declaration shape is wrong and I will redo them all "
  "now rather than at check number sixty.", issue="PULSE-39"),
M(ENG, "2026-05-06 11:30:00", G,
  "Shape is right. Approving PULSE-39. The plain-language failure description "
  "on each one is what will make these readable in six months.",
  thread="2026-05-05 14:10:00", issue="PULSE-39"),
M(ENG, "2026-05-07 10:20:00", D,
  "PULSE-43: got the fixture from four minutes to 26 seconds by moving to "
  "session scope and dropping the largest preset from the default run. The "
  "big dataset is behind a marker for the nightly job.", issue="PULSE-43",
  reactions=":rocket: 2"),

# ---------------------------------------------------------------- Sprint 6
M(ENG, "2026-05-13 15:15:00", G,
  "PULSE-46 is up - all seven dimensions. Reviewing your own conformed "
  "dimensions is hard, so what I actually want checked is whether the "
  "customer dimension can be joined by orders, payments and events without "
  "any of them needing a special case.", issue="PULSE-46"),
M(ENG, "2026-05-14 14:30:00", D,
  "Checked all three join paths on PULSE-46, no special cases. Events needed "
  "the natural key trimmed before matching, which I have pushed into silver "
  "rather than into the join.", thread="2026-05-13 15:15:00",
  issue="PULSE-46", reactions=":+1: 1"),
M(ENG, "2026-05-20 11:40:00", V,
  "PULSE-49 review: fact_sales rebuilds by truncate and insert inside a "
  "transaction, which is fine, but the transaction wraps the whole build and "
  "holds a lock for about ninety seconds on the largest preset. Worth knowing "
  "before this meets a live dashboard.", issue="PULSE-49"),
M(ENG, "2026-05-21 09:50:00", D,
  "Noted on PULSE-49. Leaving it for now since nothing reads the warehouse "
  "during a build, but I have put it in the ticket so it is not a surprise "
  "when something does.", thread="2026-05-20 11:40:00", issue="PULSE-49"),

# ---------------------------------------------------------------- Sprint 7
M(ENG, "2026-06-01 15:25:00", V,
  "PULSE-53 before and after, sales by region by month on the largest preset: "
  "8.4s to 0.6s. The date key index is nearly all of it. EXPLAIN is in the "
  "ticket for both engines.", issue="PULSE-53", reactions=":rocket: 2"),
M(ENG, "2026-06-03 10:30:00", D,
  "PULSE-56 hotfix is up - AOV moves to fact_orders and there is a check "
  "asserting the mart figure against a header-grain recomputation. Deliberately "
  "kept the check in the same PR as the fix.", issue="PULSE-56"),
M(ENG, "2026-06-03 11:05:00", G,
  "Approved PULSE-56. Same-PR is right. A fix without the assertion is a fix "
  "that comes back.", thread="2026-06-03 10:30:00", issue="PULSE-56",
  reactions=":+1: 2"),

# ---------------------------------------------------------------- Sprint 8
M(ENG, "2026-06-11 14:15:00", D,
  "PULSE-57 review request. The rule I am trying to hold is that no page "
  "issues SQL - everything goes through data_access. If you see a query "
  "anywhere in pages/, that is the bug.", issue="PULSE-57"),
M(ENG, "2026-06-12 09:40:00", V,
  "One found in PULSE-57, on the executive page. Also the cache TTL is "
  "hardcoded in three places with two different values, which will be "
  "confusing at exactly the wrong moment.", thread="2026-06-11 14:15:00",
  issue="PULSE-57", reactions=":eyes: 1"),
M(ENG, "2026-06-18 11:20:00", G,
  "PULSE-58 is up. theme.py is small on purpose - a palette, a category "
  "order, and three chart helpers. If a page needs a colour that is not in "
  "here, that is a conversation rather than a local override.",
  issue="PULSE-58"),

# ---------------------------------------------------------------- Sprint 9
M(ENG, "2026-06-24 10:30:00", D,
  "PULSE-65 sales page is up for review. Four filters, and they compose, "
  "which is where I would expect bugs. Worth trying combinations that return "
  "nothing.", issue="PULSE-65"),
M(ENG, "2026-06-25 14:50:00", N,
  "Went through PULSE-65 filter combinations. Empty result renders a blank "
  "chart with no explanation - looks like a loading state. Everything else "
  "held up.", thread="2026-06-24 10:30:00", issue="PULSE-65"),
M(ENG, "2026-07-01 09:45:00", V,
  "PULSE-69 fix is up. Two lines: the filter moves into the SQL and the "
  "filter values go into the cache key. The second one is the actual bug - "
  "the cache was returning a hit for a different filter set.",
  issue="PULSE-69", reactions=":eyes: 2"),
M(ENG, "2026-07-01 10:20:00", N,
  "That is worse than the slowness then - PULSE-69 could have shown one "
  "region's numbers under another region's filter. Did it?",
  thread="2026-07-01 09:45:00", issue="PULSE-69"),
M(ENG, "2026-07-01 10:35:00", V,
  "No - the key was missing the filter but the query was unfiltered too, so "
  "it was returning the full set and filtering after. Slow, not wrong. But "
  "you are right that it was one line away from being wrong, and silently. "
  "Adding a cache key test to PULSE-69.", thread="2026-07-01 09:45:00",
  issue="PULSE-69", reactions=":+1: 2"),

# --------------------------------------------------------------- Sprint 10
M(ENG, "2026-07-10 14:20:00", D,
  "PULSE-72 up for review. The RFM quintiles use NTILE over the active base, "
  "and the segment naming is a CASE ladder. The ladder is ugly but it is "
  "readable and it matches the boundaries in the KPI doc line for line, which "
  "I care about more.", issue="PULSE-72"),
M(ENG, "2026-07-14 11:10:00", G,
  "Approving PULSE-72. Agreed on the ladder - a clever version that does not "
  "visibly match the document is worse.", thread="2026-07-10 14:20:00",
  issue="PULSE-72"),
M(ENG, "2026-07-16 10:40:00", G,
  "PULSE-73 rewritten on first purchase month. Diff is bigger than it looks "
  "because the cohort key changes shape - please check the period number "
  "arithmetic rather than the join.", issue="PULSE-73"),

# --------------------------------------------------------------- Sprint 11
M(ENG, "2026-07-23 14:30:00", V,
  "PULSE-79 bus interface is up. Three methods and two implementations. If "
  "the abstraction is wrong this is the cheapest moment to say so - once the "
  "consumer is written against it, it is not.", issue="PULSE-79"),
M(ENG, "2026-07-24 09:55:00", D,
  "Reviewed PULSE-79. commit() taking the whole batch rather than an offset "
  "is the right call - it keeps the offset bookkeeping inside the bus instead "
  "of in every consumer.", thread="2026-07-23 14:30:00", issue="PULSE-79",
  reactions=":+1: 2"),
M(ENG, "2026-07-29 15:40:00", V,
  "PULSE-82 consumer is up. The bit to review hardest is the ordering: write, "
  "commit transaction, then commit offset. Any other order loses events or "
  "duplicates them, and both failure modes are quiet.", issue="PULSE-82"),
M(ENG, "2026-07-30 11:25:00", N,
  "Reviewed PULSE-82 by trying to break it rather than by reading it. Killed "
  "the process between the transaction commit and the offset commit - it "
  "reprocesses the batch on restart and the idempotent write absorbs it. That "
  "is the behaviour we want.", thread="2026-07-29 15:40:00", issue="PULSE-82",
  reactions=":100: 2"),

# --------------------------------------------------------------- Sprint 12
M(ENG, "2026-08-10 14:35:00", V,
  "PULSE-85 fix is up. Three parts: ops DDL moves to its own file, everything "
  "becomes CREATE TABLE IF NOT EXISTS, and the pipeline no longer runs the "
  "ops DDL at all - it is init-only. Neha's test goes red on main and green "
  "on the branch.", issue="PULSE-85", reactions=":+1: 3"),
M(ENG, "2026-08-11 09:30:00", D,
  "Approved PULSE-85. The part I would not have thought of is making it "
  "init-only rather than just non-destructive. A pipeline that cannot touch "
  "ops at all is a much smaller thing to reason about.",
  thread="2026-08-10 14:35:00", issue="PULSE-85"),
M(ENG, "2026-08-13 11:15:00", V,
  "PULSE-88 is deliberately boring - it reads ops.realtime_kpis and returns "
  "it. If anyone is tempted to add a computed field here, that is the moment "
  "we have two definitions of a metric again.", issue="PULSE-88"),

# --------------------------------------------------------------- Sprint 13
M(ENG, "2026-08-20 15:10:00", G,
  "PULSE-91 is up. Five attribution models over the same event set. The "
  "models share a touchpoint builder and differ only in the credit function, "
  "which keeps the diff between them honest - if they disagree it is the "
  "model, not the plumbing.", issue="PULSE-91"),
M(ENG, "2026-08-21 10:40:00", D,
  "Reviewed PULSE-91. Suggest asserting that the five models each sum to the "
  "same total attributed revenue. If one of them does not, the credit "
  "function is leaking and the comparison is meaningless.",
  thread="2026-08-20 15:10:00", issue="PULSE-91", reactions=":100: 2"),
M(ENG, "2026-08-21 11:15:00", G,
  "Added to PULSE-91, and time decay was out by 0.4% from a rounding "
  "accumulation. Would have been very hard to spot on a chart.",
  thread="2026-08-20 15:10:00", issue="PULSE-91", reactions=":eyes: 2"),

# --------------------------------------------------------------- Sprint 14
M(ENG, "2026-09-02 11:50:00", V,
  "PULSE-107 is up as four Terraform modules. Review them separately if it is "
  "easier - storage and registry are dull, streaming and warehouse are where "
  "the decisions are.", issue="PULSE-107"),
M(ENG, "2026-09-03 14:20:00", D,
  "One thing on PULSE-107: the Postgres module has a public network access "
  "flag defaulting to true. I assume that is for the dev convenience, but it "
  "should not be the default anyone inherits.",
  thread="2026-09-02 11:50:00", issue="PULSE-107", reactions=":eyes: 2"),
M(ENG, "2026-09-03 14:45:00", V,
  "Correct, and thank you - that was me testing connectivity and forgetting. "
  "Default is false in PULSE-107 now, with dev overriding it explicitly in "
  "its tfvars so the exception is visible.", thread="2026-09-02 11:50:00",
  issue="PULSE-107"),
M(ENG, "2026-09-07 11:40:00", D,
  "PULSE-100 churn PR is up for review. The model is twenty lines; the "
  "feature snapshot is a hundred and fifty and that is where the bug was, so "
  "that is where the review time should go.", issue="PULSE-100"),
M(ENG, "2026-09-08 10:55:00", G,
  "Reviewing PULSE-100 now. Coefficients need to come out in the scored "
  "output rather than only in the training log - the retention team cannot "
  "read our logs, and the whole argument for a linear model is that they can "
  "see why.", thread="2026-09-07 11:40:00", issue="PULSE-100",
  reactions=":+1: 2"),
M(ENG, "2026-09-08 11:05:00", V,
  "Draft of the deploy workflows for PULSE-113 is on a branch, not up for "
  "review yet. Plan on PR, apply on merge behind an environment gate. The "
  "rollback path is the part I want people to poke at once it is up.",
  issue="PULSE-113"),

]
