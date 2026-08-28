"""Generate Jira import CSVs + a Slack transcript for PulseAnalytics.

Project start: 2026-03-01.  Everything below is generated from the roadmap in
docs/two-year-roadmap.md, compressed onto the real team and the real calendar.

Outputs (project-management/):
  pulse_jira_issues.csv    Jira Cloud CSV import file (epics, stories, tasks,
                           bugs) with inline Comment columns.
  pulse_jira_comments.csv  the same comments, long form, one row per comment.
  pulse_slack_messages.csv readable Slack transcript keyed to the Jira issues.
  pulse_slack_import.csv   the same messages in Slack's CSV import format.

Import notes for Jira Cloud (External System Import -> CSV):
  * Date format:  yyyy-MM-dd HH:mm:ss
  * Map every "Comment" column to the Comment field.
  * Map "Epic Link" to Parent (team-managed) or Epic Link (company-managed).

Import notes for Slack (Settings -> Import/Export Data -> CSV):
  * Slack reads columns positionally: timestamp, channel, username, message.
    Column order matters more than the header row - if the channel is not in
    column 2, Slack offers to create one channel per value it finds there.
  * Timestamps are Unix epoch seconds (UTC). Set SLACK_EPOCH = False below to
    emit ISO instead, if your workspace's importer expects that.
  * Channel names come from SLACK_CHANNELS - edit that map to match the
    channels that already exist in the workspace.
"""

import csv
import datetime as dt
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from data_issues import ISSUES, PEOPLE, JOINED          # noqa: E402
from data_slack import SLACK                            # noqa: E402
from data_slack_recent import RECENT                    # noqa: E402

# The recent-history batch is part of the transcript for validation and for the
# readable file, and is also exported on its own so it can be imported on top
# of a workspace that already holds the main transcript.
SLACK.extend(RECENT)

PROJECT_START = dt.date(2026, 3, 1)

# --------------------------------------------------------------------------
# Slack target channels
#
# Left: the channel the transcript was written against.
# Right: the channel that exists in the workspace. Edit this map only - the
# transcript itself does not change, so a remap is one edit and a rerun.
#
# Every internal channel must appear here, and every target channel must
# already exist in Slack (the importer will not create them).
# --------------------------------------------------------------------------

SLACK_CHANNELS = {
    "#pulse-general":      "#pulseanalytics-standup",
    "#pulse-eng":          "#pulseanalytics-dev",
    "#pulse-data-quality": "#pulseanalytics-qa",
    "#pulse-standup":      "#pulseanalytics-standup",
    "#pulse-releases":     "#pulseanalytics-devops",
    "#pulse-stakeholders": "#pulseanalytics-standup",
}

# Engineering talk about the platform epic - Terraform, CI, docker-compose,
# deployment, repo and branch conventions - reads as devops rather than as
# day-to-day development, so it is routed with the release traffic instead of
# with the pull requests and SQL reviews. Set to None to send all of
# #pulse-eng to its channel in SLACK_CHANNELS above.
PLATFORM_EPIC = "PULSE-10"
PLATFORM_CHANNEL = "#pulseanalytics-devops"

# Slack's importer reads columns positionally, not by header name.
SLACK_IMPORT_COLUMNS = ["timestamp", "channel", "username", "message"]
SLACK_EPOCH = True   # False emits "yyyy-MM-dd HH:mm:ss" instead of epoch seconds


def _epic_of():
    """issue key -> the epic it belongs to (an epic maps to itself)."""
    return {i["key"]: (i["parent"] or i["key"]) for i in ISSUES}


EPIC_OF = _epic_of()


_BY_TS = {}


def target_channel(msg):
    """The workspace channel a message lands in.

    A reply always follows its thread parent, so the platform rule can never
    split a conversation across two channels.
    """
    if not _BY_TS:
        for other in SLACK:
            _BY_TS.setdefault(other["ts"], other)

    parent = _BY_TS.get(msg.get("thread") or "")
    if parent is not None and parent is not msg:
        return target_channel(parent)

    if (PLATFORM_EPIC
            and msg["channel"] == "#pulse-eng"
            and msg.get("issue")
            and EPIC_OF.get(msg["issue"]) == PLATFORM_EPIC):
        return PLATFORM_CHANNEL

    return SLACK_CHANNELS[msg["channel"]]


# --------------------------------------------------------------------------
# business hours: everything happens Mon-Fri, 09:00-17:00
#
# The transcript is written with natural times; this pass moves the handful
# that fall outside working hours. It is a single monotonic remap applied to
# every timestamp in the dataset - Jira created/resolved/updated dates, issue
# comments and Slack messages alike - so relative ordering, thread parents and
# cross-references between them all survive.
# --------------------------------------------------------------------------

FMT = "%Y-%m-%d %H:%M:%S"
DAY_START = dt.time(9, 0)
DAY_END = dt.time(17, 0)          # exclusive; last usable minute is 16:59


def _timestamp_fields():
    """Every (container, key) pair in the dataset holding a timestamp."""
    for issue in ISSUES:
        for field in ("created", "resolved", "updated", "due"):
            if issue.get(field):
                yield issue, field
        for n, (when, who, body) in enumerate(issue["comments"]):
            yield issue["comments"], n
    for msg in SLACK:
        yield msg, "ts"
        if msg.get("thread"):
            yield msg, "thread"


def _read(container, key):
    value = container[key]
    return value[0] if isinstance(value, tuple) else value


def build_business_hours_map():
    """original timestamp -> business-hours timestamp, order preserving."""
    originals = {_read(c, k) for c, k in _timestamp_fields()}

    # 1. a weekend moves back to the preceding Friday, same time of day
    shifted = {}
    for stamp in originals:
        when = dt.datetime.strptime(stamp, FMT)
        if when.weekday() >= 5:
            when -= dt.timedelta(days=when.weekday() - 4)
        shifted[stamp] = when

    # 2. per day, clamp into the window and force strictly increasing minutes
    by_day = {}
    for stamp, when in shifted.items():
        by_day.setdefault(when.date(), []).append((when, stamp))

    mapping = {}
    for day, entries in by_day.items():
        entries.sort()                       # (datetime, original) - deterministic
        floor = dt.datetime.combine(day, DAY_START)
        ceiling = dt.datetime.combine(day, DAY_END) - dt.timedelta(minutes=1)

        # forward: no earlier than 09:00, and at least a minute after the last
        placed = []
        for when, stamp in entries:
            new = max(when, floor)
            if placed and new <= placed[-1][0]:
                new = placed[-1][0] + dt.timedelta(minutes=1)
            placed.append((new, stamp))

        # backward: nothing past 16:59, making room by pulling earlier ones back
        for i in range(len(placed) - 1, -1, -1):
            limit = ceiling if i == len(placed) - 1 else placed[i + 1][0] - dt.timedelta(minutes=1)
            if placed[i][0] > limit:
                placed[i] = (limit, placed[i][1])

        if placed and placed[0][0] < floor:
            raise RuntimeError(f"{day}: {len(placed)} timestamps will not fit in 09:00-17:00")

        for new, stamp in placed:
            mapping[stamp] = new.strftime(FMT)

    return mapping


def apply_business_hours():
    mapping = build_business_hours_map()
    moved = 0
    for container, key in _timestamp_fields():
        value = container[key]
        if isinstance(value, tuple):                 # a comment: (when, who, body)
            when, who, body = value
            if mapping[when] != when:
                moved += 1
            container[key] = (mapping[when], who, body)
        else:
            if mapping[value] != value:
                moved += 1
            container[key] = mapping[value]
    return moved


# --------------------------------------------------------------------------
# validation: nobody speaks before their joining date
# --------------------------------------------------------------------------

def _d(stamp):
    return dt.datetime.strptime(stamp[:10], "%Y-%m-%d").date()


def validate():
    errors = []
    keys = {i["key"] for i in ISSUES}

    for issue in ISSUES:
        created = _d(issue["created"])
        if created < PROJECT_START:
            errors.append(f"{issue['key']}: created {created} before project start")

        for field in ("assignee", "reporter"):
            who = issue.get(field)
            if who and created < JOINED[who]:
                errors.append(
                    f"{issue['key']}: {field} {who} assigned {created}, joined {JOINED[who]}")

        parent = issue.get("parent")
        if parent and parent not in keys:
            errors.append(f"{issue['key']}: unknown parent {parent}")

        for when, who, _ in issue.get("comments", ()):
            if _d(when) < JOINED[who]:
                errors.append(
                    f"{issue['key']}: comment by {who} on {when}, joined {JOINED[who]}")

    for msg in SLACK:
        if _d(msg["ts"]) < JOINED[msg["author"]]:
            errors.append(
                f"slack {msg['ts']}: {msg['author']} posted before joining "
                f"{JOINED[msg['author']]}")
        if msg.get("issue") and msg["issue"] not in keys:
            errors.append(f"slack {msg['ts']}: unknown issue {msg['issue']}")
        if msg["channel"] not in SLACK_CHANNELS:
            errors.append(f"slack {msg['ts']}: {msg['channel']} has no target "
                          f"channel in SLACK_CHANNELS")

    errors += validate_business_hours()
    return errors


def validate_business_hours():
    """Every timestamp inside Mon-Fri 09:00-17:00, with ordering intact."""
    errors = []

    def check(stamp, what):
        when = dt.datetime.strptime(stamp, FMT)
        if when.weekday() >= 5:
            errors.append(f"{what}: {stamp} falls on {when:%A}")
        if not (DAY_START <= when.time() < DAY_END):
            errors.append(f"{what}: {stamp} is outside 09:00-17:00")
        return when

    for issue in ISSUES:
        created = check(issue["created"], f"{issue['key']}.created")
        for field in ("resolved", "updated", "due"):
            if issue.get(field):
                when = check(issue[field], f"{issue['key']}.{field}")
                if when < created:
                    errors.append(f"{issue['key']}: {field} precedes created")

        previous = None
        for stamp, who, _ in issue["comments"]:
            when = check(stamp, f"{issue['key']} comment by {who}")
            if when < created:
                errors.append(f"{issue['key']}: comment by {who} precedes created")
            if previous and when < previous:
                errors.append(f"{issue['key']}: comments out of order at {stamp}")
            previous = when

    posted = {}
    for msg in SLACK:
        posted[msg["ts"]] = check(msg["ts"], f"slack {msg['channel']}")
    by_ts = {}
    for msg in SLACK:
        by_ts.setdefault(msg["ts"], msg)
    for msg in SLACK:
        if not msg.get("thread"):
            continue
        if msg["thread"] not in posted:
            errors.append(f"slack {msg['ts']}: thread parent {msg['thread']} not found")
            continue
        if posted[msg["thread"]] > posted[msg["ts"]]:
            errors.append(f"slack {msg['ts']}: reply precedes its thread parent")
        parent = by_ts[msg["thread"]]
        if target_channel(parent) != target_channel(msg):
            errors.append(f"slack {msg['ts']}: thread split across "
                          f"{target_channel(parent)} and {target_channel(msg)}")

    return errors


# --------------------------------------------------------------------------
# writers
# --------------------------------------------------------------------------

ISSUE_COLUMNS = [
    "Issue Type", "Issue Key", "Issue ID", "Summary", "Description",
    "Epic Name", "Epic Link", "Status", "Resolution", "Priority",
    "Assignee", "Reporter", "Story Points", "Sprint", "Components",
    "Labels", "Created", "Updated", "Resolved", "Due Date",
]


def write_issues(path):
    max_comments = max(len(i.get("comments", ())) for i in ISSUES)
    header = ISSUE_COLUMNS + ["Comment"] * max_comments

    with open(path, "w", newline="", encoding="utf-8") as fh:
        out = csv.writer(fh, quoting=csv.QUOTE_MINIMAL)
        out.writerow(header)
        for n, issue in enumerate(ISSUES, start=1):
            comments = [
                f"{when};{who};{body}" for when, who, body in issue.get("comments", ())
            ]
            comments += [""] * (max_comments - len(comments))
            out.writerow([
                issue["type"],
                issue["key"],
                str(10000 + n),
                issue["summary"],
                issue["description"],
                issue.get("epic_name", ""),
                issue.get("parent", ""),
                issue["status"],
                "Done" if issue["status"] == "Done" else "",
                issue.get("priority", "Medium"),
                issue.get("assignee", ""),
                issue.get("reporter", "geetha.nallamada"),
                issue.get("points", ""),
                issue.get("sprint", ""),
                issue.get("components", ""),
                issue.get("labels", ""),
                issue["created"],
                issue.get("updated") or issue.get("resolved") or issue["created"],
                issue.get("resolved", ""),
                issue.get("due", ""),
            ] + comments)
    return len(ISSUES), max_comments


def write_comments(path):
    rows = 0
    with open(path, "w", newline="", encoding="utf-8") as fh:
        out = csv.writer(fh)
        out.writerow([
            "Issue Key", "Issue Type", "Summary", "Sprint",
            "Comment Date", "Author", "Author Name", "Author Role", "Comment Body",
        ])
        for issue in ISSUES:
            for when, who, body in issue.get("comments", ()):
                out.writerow([
                    issue["key"], issue["type"], issue["summary"],
                    issue.get("sprint", ""), when, who,
                    PEOPLE[who]["name"], PEOPLE[who]["role"], body,
                ])
                rows += 1
    return rows


def _ordered_slack():
    """Messages grouped by target channel, threads kept contiguous.

    Slack's CSV import has no thread column, so a threaded reply lands as an
    ordinary message. Sorting on (thread root, own timestamp) keeps each
    thread's replies directly under their parent so the conversation still
    reads as one, rather than being scattered across days of other traffic.
    """
    def key(msg):
        root = msg.get("thread") or msg["ts"]
        return (target_channel(msg), root, msg["ts"])

    return sorted(SLACK, key=key)


def _slack_stamp(ts):
    if not SLACK_EPOCH:
        return ts
    when = dt.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    return str(int(when.replace(tzinfo=dt.timezone.utc).timestamp()))


def write_slack(path):
    """Readable transcript - internal channel, target channel, roles, threads."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        out = csv.writer(fh)
        out.writerow([
            "Slack Channel", "Source Channel", "Timestamp", "Author",
            "Author Name", "Author Role", "Thread Parent", "Related Jira Key",
            "Message", "Reactions",
        ])
        for msg in SLACK:
            out.writerow([
                target_channel(msg), msg["channel"], msg["ts"],
                msg["author"], PEOPLE[msg["author"]]["name"],
                PEOPLE[msg["author"]]["role"], msg.get("thread", ""),
                msg.get("issue", ""), msg["text"], msg.get("reactions", ""),
            ])
    return len(SLACK)


def _with_issue_key(msg):
    """Slack's import format has four columns and no room for metadata, so the
    Jira key has to live in the message text or it does not survive at all."""
    text = msg["text"]
    key = msg.get("issue")
    if key and key not in text:
        text = f"[{key}] {text}"
    return text


def _write_import_rows(path, messages):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        out = csv.writer(fh)
        out.writerow(SLACK_IMPORT_COLUMNS)
        for msg in messages:
            out.writerow([
                _slack_stamp(msg["ts"]),
                target_channel(msg),
                msg["author"],
                _with_issue_key(msg),
            ])
    return len(messages)


def _short_name(channel):
    """'#pulseanalytics-devops' -> 'devops', for the per-channel filenames."""
    name = channel.lstrip("#")
    prefix = "pulseanalytics-"
    return name[len(prefix):] if name.startswith(prefix) else name


def write_slack_import(directory):
    """Slack CSV import format. Column ORDER is what Slack reads, not headers.

    Writes the combined file plus one file per target channel, so a single
    channel can be imported on its own without importing the rest.
    """
    messages = _ordered_slack()
    written = [("pulse_slack_import.csv",
                _write_import_rows(os.path.join(directory, "pulse_slack_import.csv"),
                                   messages),
                "all channels")]

    recent = [m for m in messages if id(m) in {id(r) for r in RECENT}]
    written.append(("pulse_slack_recent_standup_qa.csv",
                    _write_import_rows(
                        os.path.join(directory, "pulse_slack_recent_standup_qa.csv"),
                        recent),
                    "last 2 months, standup + qa only"))

    channels = set(SLACK_CHANNELS.values())
    if PLATFORM_EPIC:
        channels.add(PLATFORM_CHANNEL)
    for channel in sorted(channels):
        subset = [m for m in messages if target_channel(m) == channel]
        name = f"pulse_slack_import_{_short_name(channel)}.csv"
        written.append((name,
                        _write_import_rows(os.path.join(directory, name), subset),
                        channel))

    return written


def main():
    moved = apply_business_hours()
    errors = validate()
    if errors:
        print("VALIDATION FAILED")
        for e in errors:
            print("  -", e)
        return 1

    n_issues, max_c = write_issues(os.path.join(HERE, "pulse_jira_issues.csv"))
    n_comments = write_comments(os.path.join(HERE, "pulse_jira_comments.csv"))
    n_slack = write_slack(os.path.join(HERE, "pulse_slack_messages.csv"))
    import_files = write_slack_import(HERE)

    by_type = {}
    for i in ISSUES:
        by_type[i["type"]] = by_type.get(i["type"], 0) + 1
    by_status = {}
    for i in ISSUES:
        by_status[i["status"]] = by_status.get(i["status"], 0) + 1

    print(f"issues        {n_issues}  {dict(sorted(by_type.items()))}")
    print(f"status        {dict(sorted(by_status.items()))}")
    print(f"comments      {n_comments} (max {max_c} on one issue)")
    print(f"slack msgs    {n_slack}")

    routed = {}
    for msg in SLACK:
        target = target_channel(msg)
        routed.setdefault(target, {})
        routed[target][msg["channel"]] = routed[target].get(msg["channel"], 0) + 1
    print("slack routing")
    for target in sorted(routed):
        total = sum(routed[target].values())
        sources = ", ".join(f"{s} {n}" for s, n in sorted(routed[target].items()))
        print(f"  {target:<26} {total:>3}  <- {sources}")

    print("slack import files")
    for name, count, scope in import_files:
        print(f"  {name:<38} {count:>3}  {scope}")

    print(f"hours         {moved} timestamps moved into Mon-Fri 09:00-17:00")
    print("validation    OK - joining dates respected, all timestamps in hours,")
    print("              ordering and thread parents intact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
