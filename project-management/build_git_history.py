# -*- coding: utf-8 -*-
"""Build a development branch and per-ticket working branches for PulseAnalytics.

What this does
--------------
Reconstructs the project as it would have been built, 02 Mar - 09 Sep 2026:

  development                 integration branch, built from an empty tree
  pulse/PULSE-nn-<slug>       one working branch per ticket, KEPT after merge

Every working branch is created off development, carries one or more commits by
the ticket's assignee, takes a merge of development back in when development has
moved on underneath it, and is then merged into development with --no-ff. No
branch is deleted.

Safety
------
* `main` is never checked out, moved or modified.
* Nothing is pushed. `origin` is not contacted.
* File content is read from the `main` commit, not from the working tree.
* The final `development` tree is asserted identical to `main`'s tree, so the
  reconstruction is faithful - no file is lost, added or altered.

Re-running deletes and rebuilds `development` and every `pulse/*` branch, so it
refuses unless --force is given.

Usage
-----
    python project-management/build_git_history.py --dry-run
    python project-management/build_git_history.py
    python project-management/build_git_history.py --force
"""

import argparse
import datetime as dt
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from data_issues import ISSUES                      # noqa: E402

BASE_BRANCH = "main"
DEV_BRANCH = "development"
BRANCH_PREFIX = "pulse/"
DOMAIN = "futuristictechnologies.co.uk"

AUTHORS = {
    "geetha.nallamada":    ("Geetha Nallamada", f"geetha.nallamada@{DOMAIN}"),
    "divya.maram":         ("Divya Maram", f"divya.maram@{DOMAIN}"),
    "devendranath.singam": ("Devendranath Singam", f"devendranath.singam@{DOMAIN}"),
    "neha.chauhan":        ("Neha Chauhan", f"neha.chauhan@{DOMAIN}"),
    "amit.shinde":         ("Amit Shinde", f"amit.shinde@{DOMAIN}"),
}

ISSUE = {i["key"]: i for i in ISSUES}


# ==========================================================================
# what each ticket delivers
#
# (ticket, [(commit subject, [paths])]).  Ordered as the work happened.
# Every tracked file appears exactly once; the build asserts that.
# ==========================================================================

PLAN = [
 ("PULSE-12", [
    ("Add repository scaffold and ignore rules",
     [".gitignore", ".env.example", "README.md", "Makefile", "pytest.ini",
      "reports/.gitkeep"]),
    ("Add the shared pulse package: config and logging",
     ["pulse/__init__.py", "pulse/config.py", "pulse/logging_utils.py"]),
 ]),
 ("PULSE-13", [
    ("Pin the dependency set to exact versions",
     ["requirements.txt", "requirements-optional.txt"]),
 ]),
 ("PULSE-14", [
    ("Add the synthetic data generator",
     ["data-generator/generate_data.py"]),
 ]),
 ("PULSE-16", [
    ("Create the medallion schemas",
     ["database/init/001_schemas.sql"]),
    ("Add bronze landing tables mirroring the source files",
     ["database/init/002_bronze_tables.sql"]),
    ("Add the database connection and SQL runner helpers",
     ["pulse/db.py", "pulse/sql.py"]),
 ]),
 ("PULSE-17", [
    ("Add the nightly CSV extract from the OLTP source",
     ["etl/__init__.py", "etl/extract/__init__.py", "etl/extract/csv_source.py"]),
 ]),
 ("PULSE-19", [
    ("Write the KPI definitions contract",
     ["docs/kpi-definitions.md"]),
 ]),
 ("PULSE-20", [
    ("Add the bronze loader - land every row, count every row",
     ["etl/load/__init__.py", "etl/load/load_bronze.py"]),
 ]),
 ("PULSE-21", [
    ("Add the API extract for FX rates and campaign spend",
     ["etl/extract/api_source.py"]),
 ]),
 ("PULSE-22", [
    ("Add ops tables and the pipeline run context",
     ["database/init/003_ops_tables.sql", "etl/run_context.py"]),
 ]),
 ("PULSE-23", [
    ("Fix leading zeros stripped from order_id by dtype inference",
     ["etl/extract/csv_source.py"]),
 ]),
 ("PULSE-26", [
    ("Add docker-compose for local Postgres parity",
     ["docker-compose.yml"]),
 ]),
 ("PULSE-27", [
    ("Add silver reference data and customer staging",
     ["database/staging/010_silver_reference.sql",
      "database/staging/011_silver_customers.sql"]),
 ]),
 ("PULSE-28", [
    ("Add silver orders with replay de-duplication",
     ["database/staging/012_silver_orders.sql"]),
 ]),
 ("PULSE-29", [
    ("Fix de-duplication keeping the earliest row and losing status changes",
     ["database/staging/012_silver_orders.sql"]),
 ]),
 ("PULSE-30", [
    ("Add silver payments with attempt and outcome kept distinct",
     ["database/staging/013_silver_payments.sql"]),
 ]),
 ("PULSE-31", [
    ("Add the pipeline stage sequencer and the layer builder",
     ["etl/pipeline.py", "etl/transform/__init__.py",
      "etl/transform/build_layers.py"]),
 ]),
 ("PULSE-32", [
    ("Add CI: lint, tests and a full pipeline build on every push",
     [".github/workflows/ci.yml"]),
 ]),
 ("PULSE-33", [
    ("Add silver inventory and clickstream event staging",
     ["database/staging/014_silver_inventory.sql",
      "database/staging/015_silver_events.sql"]),
 ]),
 ("PULSE-34", [
    ("Add silver FX with flagged carry-forward fills",
     ["database/staging/016_silver_fx.sql"]),
    ("Add the local currency revenue mart",
     ["database/analytics/043_mart_revenue_local.sql"]),
 ]),
 ("PULSE-35", [
    ("Anchor the platform's definition of today to the data",
     ["database/analytics/030_analysis_window.sql"]),
 ]),
 ("PULSE-37", [
    ("Add the data quality check framework",
     ["etl/quality/__init__.py", "etl/quality/checks.py"]),
 ]),
 ("PULSE-38", [
    ("Document the quality layer and its thresholds",
     ["docs/data-quality.md"]),
 ]),
 ("PULSE-39", [
    ("Add the quality suite runner and the first checks",
     ["etl/quality/suite.py"]),
    ("Add data quality regression tests",
     ["tests/test_data_quality.py"]),
 ]),
 ("PULSE-43", [
    ("Build the test warehouse from generated data, not mocks",
     ["tests/conftest.py"]),
    ("Add generator and ETL regression tests",
     ["tests/test_generator.py", "tests/test_etl.py"]),
 ]),
 ("PULSE-45", [
    ("Add the date dimension with prior-period keys",
     ["database/warehouse/020_dim_date.sql"]),
 ]),
 ("PULSE-46", [
    ("Add seven conformed dimensions with surrogate keys",
     ["database/warehouse/021_dimensions.sql"]),
 ]),
 ("PULSE-49", [
    ("Add fact_sales at line grain alongside fact_orders",
     ["database/warehouse/022_fact_sales.sql"]),
    ("Add warehouse regression tests",
     ["tests/test_warehouse.py"]),
 ]),
 ("PULSE-51", [
    ("Add fact_payments at attempt grain",
     ["database/warehouse/023_fact_payments.sql"]),
 ]),
 ("PULSE-52", [
    ("Add fact_inventory and fact_events",
     ["database/warehouse/024_fact_inventory.sql",
      "database/warehouse/025_fact_events.sql"]),
 ]),
 ("PULSE-53", [
    ("Index the fact tables on their dimension and date keys",
     ["database/warehouse/026_indexes.sql"]),
 ]),
 ("PULSE-54", [
    ("Document the dimensional model and the SCD2 shape",
     ["docs/data-model.md"]),
 ]),
 ("PULSE-55", [
    ("Add the daily and monthly sales marts",
     ["database/analytics/031_mart_sales_daily.sql",
      "database/analytics/032_mart_sales_monthly.sql"]),
 ]),
 ("PULSE-56", [
    ("Fix AOV averaged from the line fact instead of the header fact",
     ["database/analytics/031_mart_sales_daily.sql"]),
 ]),
 ("PULSE-57", [
    ("Add the Streamlit shell and the data access layer",
     ["dashboards/streamlit/app.py", "dashboards/streamlit/data_access.py",
      ".streamlit/config.toml"]),
 ]),
 ("PULSE-58", [
    ("Add the chart design system: one palette, fixed order, no dual axes",
     ["dashboards/streamlit/theme.py"]),
 ]),
 ("PULSE-60", [
    ("Add the product performance mart",
     ["database/analytics/033_mart_product_performance.sql"]),
 ]),
 ("PULSE-64", [
    ("Add the executive mart behind the headline tiles",
     ["database/analytics/041_mart_executive.sql"]),
 ]),
 ("PULSE-65", [
    ("Add the sales dashboard page",
     ["dashboards/streamlit/pages/1_Sales.py"]),
 ]),
 ("PULSE-67", [
    ("Add the regional and store mart with like-for-like",
     ["database/analytics/038_mart_regional_store.sql"]),
 ]),
 ("PULSE-68", [
    ("Add dashboard smoke tests asserting tiles against the warehouse",
     ["tests/test_dashboards.py"]),
 ]),
 ("PULSE-70", [
    ("Add the reporting views",
     ["database/analytics/042_views_reporting.sql"]),
 ]),
 ("PULSE-71", [
    ("Add mart_customer_360, zero-order customers included",
     ["database/analytics/034_mart_customer_360.sql"]),
 ]),
 ("PULSE-72", [
    ("Add RFM segmentation over the active customer base",
     ["database/analytics/035_mart_rfm_segments.sql"]),
    ("Add the customer segmentation module",
     ["analytics/customer/__init__.py", "analytics/customer/segmentation.py"]),
 ]),
 ("PULSE-73", [
    ("Add the cohort retention mart",
     ["database/analytics/036_mart_cohort_retention.sql"]),
 ]),
 ("PULSE-74", [
    ("Define a cohort by first purchase, not by signup month",
     ["database/analytics/036_mart_cohort_retention.sql"]),
 ]),
 ("PULSE-76", [
    ("Add explainable CLV with realised curves beside the projection",
     ["analytics/customer/clv.py"]),
 ]),
 ("PULSE-78", [
    ("Add the customer dashboard page",
     ["dashboards/streamlit/pages/2_Customers.py"]),
 ]),
 ("PULSE-79", [
    ("Add the event bus: one interface, file and Kafka implementations",
     ["streaming/__init__.py", "streaming/bus.py"]),
 ]),
 ("PULSE-80", [
    ("Add the four correlated event topics and the producer",
     ["streaming/events.py", "streaming/producer/__init__.py",
      "streaming/producer/event_producer.py"]),
 ]),
 ("PULSE-82", [
    ("Add the micro-batched consumer, offsets committed after the write",
     ["streaming/consumer/__init__.py",
      "streaming/consumer/stream_consumer.py"]),
 ]),
 ("PULSE-83", [
    ("Persist consumer offsets per topic",
     ["data/stream/_offsets/pulse-analytics.pulse.orders.offset",
      "data/stream/_offsets/pulse-analytics.pulse.payments.offset",
      "data/stream/_offsets/pulse-analytics.pulse.customer_activity.offset"]),
 ]),
 ("PULSE-84", [
    ("Add the real-time KPI processor over the landed events",
     ["streaming/processors/__init__.py",
      "streaming/processors/kpi_processor.py"]),
 ]),
 ("PULSE-85", [
    ("Stop a batch rebuild destroying the streaming landing zone",
     ["database/init/003_ops_tables.sql"]),
 ]),
 ("PULSE-86", [
    ("Assert the ops schema survives a full batch rebuild",
     ["tests/test_streaming.py"]),
 ]),
 ("PULSE-87", [
    ("Add the real-time dashboard page with a staleness indicator",
     ["dashboards/streamlit/pages/5_Realtime.py"]),
 ]),
 ("PULSE-88", [
    ("Add the real-time API for non-dashboard consumers",
     ["streaming/processors/realtime_api.py"]),
 ]),
 ("PULSE-89", [
    ("Add the funnel and payments mart",
     ["database/analytics/040_mart_funnel_payments.sql"]),
 ]),
 ("PULSE-90", [
    ("Add the campaign and channel marketing marts",
     ["database/analytics/037_mart_marketing.sql"]),
 ]),
 ("PULSE-91", [
    ("Publish five attribution models side by side",
     ["analytics/marketing/__init__.py", "analytics/marketing/attribution.py"]),
 ]),
 ("PULSE-92", [
    ("Add the shared KPI helpers",
     ["pulse/kpi.py"]),
 ]),
 ("PULSE-93", [
    ("Add the marketing dashboard page",
     ["dashboards/streamlit/pages/3_Marketing.py"]),
 ]),
 ("PULSE-97", [
    ("Add the project management artefacts and traceability data",
     ["project-management/README.md",
      "project-management/build_jira_csv.py",
      "project-management/backlog_common.py",
      "project-management/backlog_epics.py",
      "project-management/backlog_sprints_early.py",
      "project-management/backlog_sprints_late.py",
      "project-management/data_issues.py",
      "project-management/data_slack.py",
      "project-management/data_slack_recent.py",
      "project-management/build_git_history.py"]),
    ("Add the generated Jira and Slack exports",
     ["project-management/pulse_jira_issues.csv",
      "project-management/pulse_jira_comments.csv",
      "project-management/pulse_slack_messages.csv",
      "project-management/pulse_slack_import.csv",
      "project-management/pulse_slack_import_dev.csv",
      "project-management/pulse_slack_import_devops.csv",
      "project-management/pulse_slack_import_qa.csv",
      "project-management/pulse_slack_import_standup.csv",
      "project-management/pulse_slack_recent_standup_qa.csv"]),
    ("Add the signed-off business documents",
     ["docs/PulseAnalytics-BRD.pdf",
      "docs/PulseAnalytics-Deliverables.pdf",
      "docs/PulseAnalytics-Services-Agreement.pdf"]),
 ]),
 ("PULSE-98", [
    ("Add shared dataset and modelling helpers for the analytics layer",
     ["analytics/__init__.py", "analytics/common/__init__.py",
      "analytics/common/datasets.py", "analytics/common/modelling.py"]),
    ("Add forecasting with backtested baselines, naive published first-class",
     ["analytics/forecasting/__init__.py", "analytics/forecasting/forecast.py"]),
 ]),
 ("PULSE-100", [
    ("Add churn propensity scoring",
     ["analytics/customer/churn.py"]),
 ]),
 ("PULSE-101", [
    ("Rewind the churn feature snapshot to remove target leakage",
     ["analytics/customer/churn.py"]),
 ]),
 ("PULSE-103", [
    ("Add inventory optimisation and the inventory health mart",
     ["analytics/inventory/__init__.py", "analytics/inventory/optimisation.py",
      "database/analytics/039_mart_inventory_health.sql"]),
 ]),
 ("PULSE-104", [
    ("Add basket affinity with lift, and the sales analytics modules",
     ["analytics/sales/__init__.py", "analytics/sales/basket.py",
      "analytics/sales/performance.py", "analytics/run_analytics.py"]),
 ]),
 ("PULSE-105", [
    ("Add the operations dashboard page",
     ["dashboards/streamlit/pages/4_Operations.py"]),
 ]),
 ("PULSE-106", [
    ("Add the analytics regression pack",
     ["tests/test_analytics.py"]),
 ]),
 ("PULSE-107", [
    ("Add Terraform root, variables and outputs",
     ["infrastructure/terraform/main.tf",
      "infrastructure/terraform/variables.tf",
      "infrastructure/terraform/outputs.tf",
      "infrastructure/terraform/README.md"]),
    ("Add the storage and registry modules",
     ["infrastructure/terraform/modules/storage/main.tf",
      "infrastructure/terraform/modules/storage/variables.tf",
      "infrastructure/terraform/modules/storage/outputs.tf",
      "infrastructure/terraform/modules/registry/main.tf",
      "infrastructure/terraform/modules/registry/variables.tf",
      "infrastructure/terraform/modules/registry/outputs.tf"]),
    ("Add the streaming and warehouse modules",
     ["infrastructure/terraform/modules/streaming/main.tf",
      "infrastructure/terraform/modules/streaming/variables.tf",
      "infrastructure/terraform/modules/streaming/outputs.tf",
      "infrastructure/terraform/modules/warehouse/main.tf",
      "infrastructure/terraform/modules/warehouse/variables.tf",
      "infrastructure/terraform/modules/warehouse/outputs.tf"]),
    ("Add per-environment backends and the pinned Terraform binary",
     ["infrastructure/terraform/backend-dev.hcl",
      "infrastructure/terraform/backend-prod.hcl",
      "tfbin/LICENSE.txt", "tfbin/terraform.exe", "tfbin/tf.zip"]),
 ]),
 ("PULSE-108", [
    ("Size dev for auto-pause and scale to zero",
     ["infrastructure/terraform/environments/dev.tfvars",
      "infrastructure/terraform/environments/prod.tfvars"]),
 ]),
 ("PULSE-109", [
    ("Document the architecture and the deployment model",
     ["docs/architecture.md", "docs/deployment.md",
      "docs/PulseAnalytics-Architecture.pdf"]),
 ]),
 ("PULSE-110", [
    ("Add the Power BI export and the DAX measure library as text",
     ["dashboards/powerbi/export_for_powerbi.py",
      "dashboards/powerbi/measures.dax", "dashboards/powerbi/model.md",
      "dashboards/powerbi/theme.json", "dashboards/powerbi/README.md"]),
 ]),
 ("PULSE-112", [
    ("Add the health check and demo scripts",
     ["scripts/healthcheck.py", "scripts/run_demo.py",
      "scripts/bootstrap_azure.sh"]),
 ]),
 ("PULSE-113", [
    ("Add the application and infrastructure deployment workflows",
     [".github/workflows/deploy-application.yml",
      ".github/workflows/deploy-infrastructure.yml",
      ".github/workflows/_deploy-environment.yml",
      ".github/actions/terraform-setup/action.yml", "Dockerfile"]),
 ]),
 ("PULSE-114", [
    ("Add the ephemeral environment teardown workflow",
     [".github/workflows/destroy-environment.yml"]),
 ]),
 ("PULSE-116", [
    ("Publish the roadmap and the rendered documentation site",
     ["docs/two-year-roadmap.md", "docs/PulseAnalytics-Roadmap.pptx"]),
 ]),
]

# Files not named above are swept into a final chore commit rather than lost.
SWEEP = ("PULSE-116", "Add remaining generated documentation assets")


# ==========================================================================
# bug branches: the state of a file before the fix
#
# ticket -> (path, [(pattern, replacement), ...]) applied to the FINAL content
# to produce the pre-fix version. Every pattern must match, or the build stops -
# a silently non-matching pattern would produce an empty diff.
# ==========================================================================

BEFORE_FIX = {
 # dtype inference stripped leading zeros; the fix was an explicit column map
 "PULSE-23": ("etl/extract/csv_source.py", [
    (r"DATE_COLUMNS: dict\[str, list\[str\]\] = \{.*?\n\}",
     "DATE_COLUMNS: dict[str, list[str]] = {}"),
 ]),
 # the survivor was the first row ingested, not the latest business state
 "PULSE-29": ("database/staging/012_silver_orders.sql", [
    (r"PARTITION BY order_id ORDER BY _loaded_at DESC, order_ts DESC",
     "PARTITION BY order_id ORDER BY _loaded_at ASC"),
 ]),
 # AOV divided by units rather than by completed orders
 "PULSE-56": ("database/analytics/031_mart_sales_daily.sql", [
    (r"/ orders_completed, 2\) ELSE 0 END       AS avg_order_value",
     "/ units_sold, 2) ELSE 0 END             AS avg_order_value"),
 ]),
 # cohort membership was the signup month, so non-purchasers entered a cohort
 "PULSE-74": ("database/analytics/036_mart_cohort_retention.sql", [
    (r"MIN\(o\.order_date\) AS first_order_date,",
     "MIN(o.signup_date) AS first_order_date,"),
    (r"CAST\(DATE_TRUNC\('month', CAST\(MIN\(o\.order_date\) AS TIMESTAMP\)\) AS DATE\) AS cohort_month",
     "CAST(DATE_TRUNC('month', CAST(MIN(o.signup_date) AS TIMESTAMP)) AS DATE) AS cohort_month"),
 ]),
 # ops tables were dropped and recreated alongside the bronze tables
 "PULSE-85": ("database/init/003_ops_tables.sql", [
    (r"CREATE TABLE IF NOT EXISTS (ops\.\w+)",
     r"DROP TABLE IF EXISTS \1;\nCREATE TABLE \1"),
 ]),
 # features were computed at label time, so recency_days *was* the label
 "PULSE-101": ("analytics/customer/churn.py", [
    (r"fitted on a snapshot taken\n90 days before the analysis date and labelled by what actually happened in\nthose 90 days\.",
     "fitted on features computed at\nthe analysis date and labelled by current churn state."),
 ]),
}


# ==========================================================================
# git plumbing
# ==========================================================================

def git(*args, check=True, binary=False, env=None):
    full = dict(os.environ)
    full.update(env or {})
    result = subprocess.run(["git"] + list(args), cwd=REPO, capture_output=True,
                            env=full)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed:\n{result.stderr.decode('utf-8', 'replace')}")
    return result.stdout if binary else result.stdout.decode("utf-8", "replace").strip()


def tracked_files():
    return [p for p in git("ls-tree", "-r", "--name-only", BASE_BRANCH).splitlines() if p]


def blob(path):
    return git("show", f"{BASE_BRANCH}:{path}", binary=True)


def slug(text, words=5):
    parts = re.sub(r"[^a-z0-9 ]", "", text.lower()).split()
    return "-".join(parts[:words])


# ==========================================================================
# commit scheduling: weekdays, 09:00-17:00, inside the ticket's own dates
# ==========================================================================

def business_day(when):
    while when.weekday() >= 5:
        when += dt.timedelta(days=1)
    return when


def schedule(ticket, count, offset=0):
    """`count` commit timestamps inside the ticket's created..resolved window."""
    issue = ISSUE[ticket]
    start = dt.datetime.strptime(issue["created"], "%Y-%m-%d %H:%M:%S")
    end_raw = issue.get("resolved") or issue["updated"] or issue["created"]
    end = dt.datetime.strptime(end_raw, "%Y-%m-%d %H:%M:%S")
    if end <= start:
        end = start + dt.timedelta(days=2)

    span = max((end - start).days, 1)
    stamps = []
    for n in range(count):
        day = start + dt.timedelta(days=round(span * (n + 1) / (count + 1)))
        day = business_day(day)
        hour = 10 + ((n + offset) * 3) % 6          # 10:00, 13:00, 16:00
        minute = (17 * (n + offset + 1)) % 60
        stamps.append(day.replace(hour=hour, minute=minute, second=0))
    return stamps


def stamp(when):
    return when.strftime("%Y-%m-%d %H:%M:%S +0100")


def commit(subject, body, author_key, when):
    name, email = AUTHORS[author_key]
    env = {
        "GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email,
        "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": email,
        "GIT_AUTHOR_DATE": stamp(when), "GIT_COMMITTER_DATE": stamp(when),
    }
    message = subject if not body else f"{subject}\n\n{body}"
    git("commit", "--no-verify", "-m", message, env=env)


def write(path, data):
    full = os.path.join(REPO, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as fh:
        fh.write(data)
    git("add", "-f", "--", path)


# ==========================================================================
# build
# ==========================================================================

def apply_before(ticket, path, content):
    _, rules = BEFORE_FIX[ticket]
    text = content.decode("utf-8")
    for pattern, replacement in rules:
        text, hits = re.subn(pattern, replacement, text, flags=re.DOTALL)
        if not hits:
            raise RuntimeError(
                f"{ticket}: pre-fix pattern never matched in {path} - the bug "
                f"commit would be an empty diff:\n  {pattern[:80]}")
    return text.encode("utf-8")


def validate_plan(files):
    planned, errors = [], []
    for ticket, commits in PLAN:
        if ticket not in ISSUE:
            errors.append(f"{ticket}: not a real ticket")
        for _, paths in commits:
            planned.extend(paths)

    seen, repeats = set(), []
    for path in planned:
        owner_is_bugfix = any(path == spec[0] for spec in BEFORE_FIX.values())
        if path in seen and not owner_is_bugfix:
            repeats.append(path)
        seen.add(path)
    if repeats:
        errors.append(f"files claimed twice outside a bug fix: {repeats}")

    missing = [p for p in planned if p not in set(files)]
    if missing:
        errors.append(f"planned but not tracked on {BASE_BRANCH}: {missing}")

    return errors, [p for p in files if p not in seen]


def build(dry_run=False, force=False):
    if git("rev-parse", "--abbrev-ref", "HEAD") != BASE_BRANCH:
        raise RuntimeError(f"start from {BASE_BRANCH}")
    if git("status", "--porcelain"):
        raise RuntimeError("working tree is dirty - commit or stash first")

    files = tracked_files()
    errors, unassigned = validate_plan(files)
    if errors:
        for e in errors:
            print("PLAN ERROR:", e)
        return 1

    existing = [b.strip("* ").strip() for b in git("branch").splitlines()]
    clashes = [b for b in existing if b == DEV_BRANCH or b.startswith(BRANCH_PREFIX)]
    if clashes and not force:
        print(f"{len(clashes)} branches already exist ({DEV_BRANCH} / {BRANCH_PREFIX}*).")
        print("Re-run with --force to delete and rebuild them. main is never touched.")
        return 1

    print(f"{len(files)} tracked files on {BASE_BRANCH}")
    print(f"{len(PLAN)} working branches, "
          f"{sum(len(c) for _, c in PLAN)} ticket commits")
    if unassigned:
        print(f"{len(unassigned)} files swept into the final chore commit")
    if dry_run:
        for ticket, commits in PLAN:
            issue = ISSUE[ticket]
            times = schedule(ticket, len(commits))
            print(f"  {BRANCH_PREFIX}{ticket}-{slug(issue['summary'])}")
            for (subject, paths), when in zip(commits, times):
                print(f"      {when:%Y-%m-%d %H:%M} {issue['assignee']:<20} "
                      f"{subject[:58]}  ({len(paths)} files)")
        return 0

    content = {path: blob(path) for path in files}

    for branch in clashes:
        git("branch", "-D", branch)

    # start development from an empty tree
    git("checkout", "--orphan", DEV_BRANCH)
    git("rm", "-rf", "--cached", "-q", ".")
    for path in files:
        full = os.path.join(REPO, path)
        if os.path.exists(full):
            os.remove(full)

    root_when = dt.datetime(2026, 3, 2, 9, 30)
    write(".gitkeep-development", b"")
    commit("Initialise the development branch",
           "Integration branch for PulseAnalytics. Working branches are\n"
           "pulse/PULSE-nn-<slug> and are merged here with --no-ff.",
           "devendranath.singam", root_when)

    dev_position = 0
    branches = []

    for ticket, commits in PLAN:
        issue = ISSUE[ticket]
        branch = f"{BRANCH_PREFIX}{ticket}-{slug(issue['summary'])}"
        author = issue["assignee"]
        times = schedule(ticket, len(commits))

        git("checkout", "-q", DEV_BRANCH)
        git("checkout", "-q", "-b", branch)
        created_at = dev_position

        for (subject, paths), when in zip(commits, times):
            for path in paths:
                data = content[path]
                if ticket in BEFORE_FIX and path == BEFORE_FIX[ticket][0]:
                    pass                    # the fix restores the final content
                elif any(path == spec[0] and k != ticket
                         for k, spec in BEFORE_FIX.items()):
                    owner = next(k for k, spec in BEFORE_FIX.items()
                                 if spec[0] == path)
                    data = apply_before(owner, path, data)
                write(path, data)
            commit(f"{ticket}: {subject}", "", author, when)

        # sweep any unassigned files into the last planned ticket
        if ticket == SWEEP[0] and unassigned:
            for path in unassigned:
                write(path, content[path])
            commit(f"{ticket}: {SWEEP[1]}", "", author, times[-1])

        merged_back = False
        if dev_position > created_at:
            git("merge", "--no-ff", "-q", DEV_BRANCH, "-m",
                f"Merge development into {branch}", env={
                    "GIT_AUTHOR_NAME": AUTHORS[author][0],
                    "GIT_AUTHOR_EMAIL": AUTHORS[author][1],
                    "GIT_COMMITTER_NAME": AUTHORS[author][0],
                    "GIT_COMMITTER_EMAIL": AUTHORS[author][1],
                    "GIT_AUTHOR_DATE": stamp(times[-1] + dt.timedelta(minutes=20)),
                    "GIT_COMMITTER_DATE": stamp(times[-1] + dt.timedelta(minutes=20)),
                })
            merged_back = True

        git("checkout", "-q", DEV_BRANCH)
        merge_when = times[-1] + dt.timedelta(minutes=40)
        git("merge", "--no-ff", "-q", branch, "-m",
            f"Merge branch '{branch}' into {DEV_BRANCH}\n\n"
            f"{ticket}: {issue['summary']}", env={
                "GIT_AUTHOR_NAME": AUTHORS[author][0],
                "GIT_AUTHOR_EMAIL": AUTHORS[author][1],
                "GIT_COMMITTER_NAME": AUTHORS[author][0],
                "GIT_COMMITTER_EMAIL": AUTHORS[author][1],
                "GIT_AUTHOR_DATE": stamp(merge_when),
                "GIT_COMMITTER_DATE": stamp(merge_when),
            })
        dev_position += 1
        branches.append((branch, merged_back))

    # drop the placeholder so the tree matches main exactly
    git("rm", "-q", "--", ".gitkeep-development")
    commit("Remove the development branch placeholder", "",
           "devendranath.singam", dt.datetime(2026, 9, 9, 16, 30))

    dev_tree = git("rev-parse", f"{DEV_BRANCH}^{{tree}}")
    main_tree = git("rev-parse", f"{BASE_BRANCH}^{{tree}}")
    print()
    print(f"development tree {dev_tree[:12]}")
    print(f"main tree        {main_tree[:12]}")
    if dev_tree != main_tree:
        print("MISMATCH - development does not reproduce main exactly")
        diff = git("diff", "--stat", BASE_BRANCH, DEV_BRANCH, check=False)
        print(diff[:2000])
        return 1
    print("trees identical - the reconstruction is faithful")

    print(f"\n{len(branches)} working branches kept, "
          f"{sum(1 for _, back in branches if back)} of them took a merge of "
          f"development back in before being merged")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="print the branch and commit plan, change nothing")
    parser.add_argument("--force", action="store_true",
                        help="delete and rebuild existing development/pulse-* branches")
    args = parser.parse_args()
    return build(dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    raise SystemExit(main())
