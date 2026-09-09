# PulseAnalytics — Jira backlog and Slack transcript

Generated project-management artefacts for PulseAnalytics, covering the project
from its start on **01 Mar 2026** to the current sprint (today: 09 Sep 2026).
Content is derived from [docs/two-year-roadmap.md](../docs/two-year-roadmap.md)
and the actual repository — every ticket references real files, marts and
modules.

## The team

| Person | Role | On the project from |
| --- | --- | --- |
| Geetha Nallamada | Sr. Data Analyst (tech lead, metric owner) | 01 Mar 2026 |
| Divya Maram | Data Analyst | 01 Mar 2026 |
| Devendranath Singam | DevOps Engineer | 01 Mar 2026 |
| Neha Chauhan | QA Analyst | 15 Jun 2026 |
| Amit Shinde | Business Analyst | 24 Aug 2026 |

The generator **enforces** the joining dates: no ticket is assigned to, and no
comment or Slack message is written by, someone who had not yet joined. The
build fails if that is ever violated.

## Working hours

Every timestamp in every file — ticket created/resolved/updated dates, issue
comments and Slack messages — falls **Monday to Friday, 09:00–17:00**. The
build fails otherwise.

The transcript is authored with natural times and normalised at build time by a
single monotonic remap shared across all three files, so relative ordering,
thread parents, comment sequence and "resolved after created" all survive the
shift. Of 900 timestamps, 40 moved:

- **26 evening** (17:00–17:45) pulled back to the last free minutes before
  17:00 — mostly sprint-close and merge messages
- **5 at 06:00** — the automated nightly quality digests, which now post at
  09:00 as a morning summary of the overnight run
- **4 on two Saturdays** moved to the preceding Friday, same time of day
- 5 more nudged by a minute to keep strict ordering after the above

Nothing else changed. The result spans 09:00 to 16:59 with no weekend
activity.

## Files

| File | What it is |
| --- | --- |
| `pulse_jira_issues.csv` | 123 issues (12 epics, 74 stories, 28 tasks, 9 bugs) with inline `Comment` columns — the Jira import file |
| `pulse_jira_comments.csv` | the same 294 comments in long form, one row per comment, with author role — for reading and analysis |
| `pulse_slack_messages.csv` | 420 Slack messages, keyed to the Jira issues they discuss — the readable version |
| `pulse_slack_import.csv` | the same 420 messages in Slack's CSV import format, with the ticket key in the message text — all four channels |
| `pulse_slack_recent_standup_qa.csv` | **196 messages, 09 Jul – 09 Sep 2026, standup + QA only** — the two-month history batch, importable on its own |
| `pulse_slack_import_dev.csv` | 144 messages for `#pulseanalytics-dev` alone |
| `pulse_slack_import_devops.csv` | 18 messages for `#pulseanalytics-devops` alone |
| `pulse_slack_import_qa.csv` | 75 messages for `#pulseanalytics-qa` alone |
| `pulse_slack_import_standup.csv` | 183 messages for `#pulseanalytics-standup` alone |

Regenerate with:

```
python project-management/build_jira_csv.py
```

Source data lives in `backlog_common.py` (people, sprints), `backlog_epics.py`,
`backlog_sprints_early.py` (sprints 1–7), `backlog_sprints_late.py`
(sprints 8–15 and the backlog), `data_slack.py` (the main transcript) and
`data_slack_recent.py` (the two-month standup and QA history).

## Importing into Jira

Jira Cloud → Settings → System → **External System Import** → CSV.

1. Set the **date format** to `yyyy-MM-dd HH:mm:ss`.
2. Map `Epic Link` to **Parent** (team-managed projects) or **Epic Link**
   (company-managed projects).
3. Map every one of the five `Comment` columns to the **Comment** field. Each
   cell is `date;author;body`, which Jira parses natively.
4. `Assignee` / `Reporter` are usernames — map them to your real accounts, or
   let Jira create them.
5. `Labels` and `Components` are `;`-delimited.

## Importing into Slack

Settings → **Import/Export Data** → Import → CSV/text file.

Import `pulse_slack_import.csv` for everything at once (four channels to map),
or a single-channel file to do one at a time — `pulse_slack_import_dev.csv`
is the dev channel on its own, 144 messages, one channel to map. The
per-channel files are slices of the combined one, so import the combined file
**or** the slices, never both, or every message lands twice.

**Slack reads the columns by position, not by header name**: `timestamp,
channel, username, message`. If the channel is not in column 2, Slack treats
whatever it finds there as channel names and offers to create one per distinct
value — which is how importing the readable transcript by mistake produces one
channel per message, named after its timestamp. If the mapping screen shows
more than four channels, you have the wrong file. **Use
`pulse_slack_import.csv` for the import** and `pulse_slack_messages.csv` for
reading.

- Timestamps are **Unix epoch seconds** (UTC). If your workspace's importer
  wants `yyyy-MM-dd HH:mm:ss` instead, set `SLACK_EPOCH = False` in
  `build_jira_csv.py` and rerun.
- Target channels must **already exist** in the workspace; the importer will
  not create them.
- Usernames are `firstname.lastname` — map them to real accounts during import,
  or switch to email addresses if your workspace matches on email.
- Slack's format has four columns and no room for metadata, so the Jira key is
  written into the message text: 360 of the 420 messages name their ticket,
  either naturally in the sentence or as a `[PULSE-91]` prefix added at build
  time. The 60 without one are greetings, sprint ceremonies and retrospective
  notes that genuinely belong to no single ticket.

### The two-month history batch

`pulse_slack_recent_standup_qa.csv` holds 196 messages from **09 Jul to 09 Sep
2026** for the standup and QA channels only — daily standups, sprint planning,
reviews and retros on one side; nightly quality digests, regression work and
defect follow-up on the other. It is a slice of the combined file, kept separate
so it can be imported on its own into a workspace that already has the main
transcript, without duplicating anything.

Authored in `data_slack_recent.py`, and validated by the same rules as
everything else: weekdays only, 09:00–17:00, and Amit's first message is
26 Aug — two days after he joined.

### Channel routing

The transcript was written against six working channels, remapped onto the
four that exist in the workspace.

| Target channel | Messages | From |
| --- | --- | --- |
| `#pulseanalytics-dev` | 144 | `#pulse-eng` — pull requests, code review, SQL, debugging |
| `#pulseanalytics-devops` | 18 | `#pulse-releases` (4) and the platform half of `#pulse-eng` (14) |
| `#pulseanalytics-qa` | 75 | `#pulse-data-quality` (75) |
| `#pulseanalytics-standup` | 183 | `#pulse-standup` (149), `#pulse-general` (28), `#pulse-stakeholders` (6) |

`#pulse-eng` is split by epic rather than by hand: messages about the platform
epic (PULSE-10 — Terraform, CI, docker-compose, deployment, repo conventions)
go to devops, everything else to dev. Set `PLATFORM_EPIC = None` in
`build_jira_csv.py` to send all engineering traffic to `#pulseanalytics-dev`.

A reply always inherits its thread parent's channel, so the split can never cut
a conversation in half — the build asserts this.

To change the routing, edit `SLACK_CHANNELS` in `build_jira_csv.py` and rerun.
The transcript itself never changes, so a remap is one edit; the build fails if
a source channel has no target.

Slack's CSV import has no thread column, so threaded replies land as ordinary
messages. They are ordered by `(thread root, own timestamp)` within each
channel, which keeps a thread's replies directly under their parent rather than
scattering them across days of other traffic — the alert-fatigue thread and the
`ops.stream_events` incident still read as single conversations.

## Git history

`build_git_history.py` reconstructs the repository as it would have been built,
02 Mar – 09 Sep 2026:

| | |
| --- | --- |
| `development` | integration branch, 229 commits, 135 of them merges |
| `pulse/PULSE-nn-<slug>` | 77 working branches, one per ticket — **kept, never deleted** |

Each working branch is cut off `development`, carries commits by the ticket's
assignee, takes a **merge of `development` back in** when development has moved
on underneath it (58 of the 77 did), and is then merged in with `--no-ff`. The
merge history therefore runs in both directions.

```
python project-management/build_git_history.py --dry-run   # plan only
python project-management/build_git_history.py --force     # rebuild
```

**Safety.** `main` is never checked out, moved or modified by the script, and
nothing is pushed. File content is read from the `main` commit rather than the
working tree, and the build asserts the final `development` tree is **byte
identical** to `main`'s — so the reconstruction cannot lose, add or alter a
file. All 188 tracked files are accounted for; the build fails if one is not.

**Authors** are the real addresses, and joining dates hold: Neha's first commit
is after 15 Jun, Amit's after 24 Aug. Every commit outside `main` falls on a
weekday between 09:00 and 17:00, matching the Jira and Slack artefacts.

**The bug branches carry real diffs.** Six tickets fix a file introduced by an
earlier commit, so the earlier commit writes the pre-fix state and the bug
commit restores the final one — PULSE-23 (dtype inference), PULSE-29 (de-dupe
ordering), PULSE-56 (AOV denominator), PULSE-74 (cohort membership), PULSE-85
(`DROP`+`CREATE` on `ops.*`) and PULSE-101 (churn feature snapshot). The build
fails if a pre-fix pattern stops matching, so none of them can silently become
an empty diff.

## Structure

**12 epics.** PULSE-1 to PULSE-11 were cut in the inception workshop on
02 Mar 2026; PULSE-95 (Business Analysis) was added on 19 Aug, ahead of the BA
joining. Issue keys are allocated in creation order, so a low key is an early
ticket.

**15 two-week sprints** from Mon 02 Mar 2026, plus 7 backlog items with no
sprint. Sprint 14 (31 Aug – 11 Sep) is the current one: 95 issues are Done, 10
In Progress, 1 In Review and 17 To Do.

The sequence follows the roadmap: ingest → define → trust → model → show →
predict → deploy. Dashboards are epic five of eleven, deliberately — the first
six weeks produced a weekly CSV and a conversation rather than a chart.

## The bugs are the interesting part

Nine bugs, each one drawn from a real decision recorded in the roadmap, and
most of them **silent** — wrong numbers rather than crashes:

| Key | What went wrong |
| --- | --- |
| PULSE-23 | Bronze load stripped leading zeros from `order_id`; 1.2% of orders stopped joining, no error |
| PULSE-29 | De-dupe kept the earliest replayed row, losing status changes; 0.3% of revenue missing |
| PULSE-41 | Quality suite failed nightly on 0.07% of customers with no email — the team stopped reading it |
| PULSE-56 | AOV 40% low, averaged from the line fact instead of the header fact |
| PULSE-66 | A dual-axis chart shipped against ADR-004 |
| PULSE-69 | Executive page 4× slower after a filter was applied in Python rather than SQL |
| PULSE-74 | Cohorts on signup month showed an activation problem as a retention cliff |
| PULSE-85 | A routine batch rebuild silently wiped the streaming landing zone (`DROP`+`CREATE` on `ops.*`) |
| PULSE-101 | Churn model scored 0.94 AUC — target leakage, `recency_days` was the label |

Six ADRs are captured as tasks (PULSE-18, 36, 50, 59, 102, 109), each recording
the rejected alternative and, where relevant, the condition that would trigger a
revisit.

## What the transcript covers

The six source channels are `#pulse-eng` (day-to-day development),
`#pulse-general` (decisions and announcements), `#pulse-data-quality` (nightly
suite output and the alert-fatigue thread), `#pulse-standup`, `#pulse-releases`
and `#pulse-stakeholders` (shared with finance, marketing and operations). See
the routing table above for how they land in the workspace.

`#pulse-eng` carries two kinds of conversation. The **decisions** — why bronze
rejects nothing, why there are two order grains, why the consumer owns no
metric definitions. And the **development traffic**: pull requests and reviews
(a seed read at import time that broke reproducibility, a retry loop backing
off on 401s, a Terraform module defaulting to public network access), CI
failures, EXPLAIN output, and the reviews that caught real defects — the
attribution model that was out by 0.4% on a rounding accumulation, the cache
key missing its filter values.

Beyond that, the transcript tracks the tickets: the four-day thread where the
quality suite gets muted and re-tuned, the morning `ops.stream_events` came
back empty, and the churn model that scored too well to be true.
