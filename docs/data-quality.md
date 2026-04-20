# Data quality

64 checks run on every pipeline execution, across bronze, silver and gold.
Results land in `ops.data_quality_results` and a markdown report is written to
`reports/data_quality_report.md`.

```bash
python -m etl.pipeline --quality-only              # re-run against the current warehouse
python -m etl.pipeline --full-refresh --fail-on-error   # CI mode
```

## The shape of a check

A check counts **failing rows** and **total rows**. That shape — rather than a
bare pass/fail — is what makes the output actionable:

> `0.07% of customers have no email (3 of 4000)`

starts a conversation. `EMAIL CHECK FAILED` starts an argument.

```python
Check(
    name="orders.status in accepted set",
    layer="silver", table="orders", dimension="validity",
    severity="error", threshold_pct=0.0,
    failing_sql="SELECT COUNT(*) FILTER (WHERE status NOT IN (...)) AS failed_rows, "
                "COUNT(*) AS total_rows FROM silver.orders",
)
```

Every check reduces to that one contract, so the runner needs no special cases
and a new check is three lines of SQL.

## Six dimensions

The standard data-governance vocabulary, all six covered — asserted by a test,
so the suite cannot quietly stop covering one:

| Dimension | Question | Example |
| --- | --- | --- |
| **Completeness** | is anything missing that should be there | `orders.customer_id` is not null |
| **Validity** | is every value inside its allowed domain | `payments.status` ∈ {captured, failed, refunded} |
| **Uniqueness** | are keys actually unique | `silver.orders.order_id` |
| **Consistency** | do related tables agree | no order line references a missing product |
| **Accuracy** | do derived numbers reconcile with their inputs | line revenue = header revenue |
| **Timeliness** | is the data as fresh as promised | newest order within 2 days of the analysis date |

## Three severities

| Severity | Effect | Meaning |
| --- | --- | --- |
| `error` | exits **2** under `--fail-on-error` | the warehouse is not safe to publish |
| `warning` | recorded, shown on the dashboard, does not block | a known, quantified, accepted reality |
| `info` | tracked for trend only | context |

Exit code **2** is deliberately distinct from **1**. CI needs to tell "the code
broke" from "the data is bad", because those go to different people.

## Why some thresholds are not zero

This is the part most quality suites get wrong.

Where the source system is **known** to be imperfect, the threshold encodes an
accepted business reality:

| Check | Threshold | Why |
| --- | --- | --- |
| `bronze.customers.email` is not null | 2%, warning | the CRM permits an account without an email. It is a marketing problem, not a data-loading failure. |
| `bronze.order_items.quantity` is positive | 2%, warning | a known bug in the returns integration. Silver repairs it; bronze only has to notice. |
| `bronze.orders.order_id` duplicate rate | 2%, warning | the source replays a small number of orders. De-duplicated in silver. |
| no order predates its customer's signup | 0.5%, warning | a customer-master sync lag is real and small |

Setting these to zero would turn known, quantified, accepted realities into
nightly false alarms. **A suite that cries wolf is a suite that gets switched
off**, and a switched-off suite catches nothing at all.

The corresponding **silver** checks have zero tolerance, because silver's whole
job is to have fixed them. That pairing — permissive in bronze, strict in silver
— is what turns "we clean the data" from a comment into a tested claim.

## What is checked where

### Bronze — did the extract arrive intact

Row counts above zero, the not-null keys, the accepted-value domains, and the
*volume* of each known defect. Bronze never rejects a row; it counts what
arrived.

### Silver — did the cleaning actually work

Every promised repair is asserted, not assumed:

```python
expression_holds(
    "customers.loyalty_tier is canonicalised", "silver", "customers",
    "loyalty_tier = TRIM(loyalty_tier) AND loyalty_tier <> UPPER(loyalty_tier)",
    dimension="validity",
    details="'GOLD  ' and 'gold' must both have become 'Gold'.",
)
```

Plus full referential integrity across the cleaned model, and temporal
consistency across tables (no order before its customer existed; no line before
its product launched).

### Gold — is the warehouse safe to publish

Surrogate-key uniqueness, no fact row on the Unknown member, plausible ranges —
and, most importantly, **five reconciliation checks**:

| Check | Catches |
| --- | --- |
| line revenue = order revenue | a grain error between `fact_sales` and `fact_orders` |
| daily mart = `fact_orders` | a mart drifting from the fact it is built on |
| monthly mart = daily mart | an aggregation bug between mart levels |
| customer 360 = `fact_orders` | revenue belonging to nobody |
| `fact_orders` count = `silver.orders` count | the star schema dropping or duplicating orders |

These are the checks that catch a **silently wrong number** — the failure mode
that is invisible in a dashboard until someone acts on it.

## Failure handling

A check whose own SQL is broken is recorded as a **failed check**, not raised:

```python
result = {
    ...,
    "status": "fail",
    "details": f"check could not execute: {exc}",
}
```

One broken assertion must not hide the other sixty-three.

Writing results to `ops.data_quality_results` is likewise best-effort. A broken
audit table must never be the reason a good data load is rolled back.

## The suite is falsifiable

`tests/test_data_quality.py::test_the_suite_would_catch_a_real_defect`
introduces a genuine defect (a duplicated dimension row), asserts the suite goes
red, then repairs it.

Without that test, the suite is unfalsifiable: it has only ever been observed to
pass, so its passing means nothing.

## Reading the output

**In the terminal** — every failure, with counts:

```
Data quality: 100.0% pass (0 of 64 checks failed)
```

**In `reports/data_quality_report.md`** — a summary by dimension, the failing
checks with observed vs threshold, then every check.

**On the Operations dashboard** — pass rate, error and warning counts, a
stacked bar by dimension, and the full table. The header traffic light on every
page reads from the same `ops.v_data_quality_summary` view.

**Via the API** — `GET /api/quality/summary`.

## Adding a check

```python
# etl/quality/suite.py
def gold_checks() -> list[Check]:
    return [
        ...,
        expression_holds(
            "margin is plausible", "gold", "fact_sales",
            "margin_pct BETWEEN -100 AND 100",
            dimension="validity",
            details="A margin outside this range means unit cost or price is wrong.",
        ),
    ]
```

Use the constructors — `not_null`, `unique`, `accepted_values`,
`expression_holds`, `foreign_key`, `row_count_at_least`, `reconciles`,
`fresh_within_days` — rather than writing raw SQL. They keep the vocabulary
consistent and the intent readable.

A check needs three things to earn its place: a **name a non-engineer
understands**, a **`details` string that says what to do about a failure**, and
a **threshold that is deliberate**. If you cannot justify the threshold, you do
not yet understand the check.

## What this does not do

- **No profiling or drift detection.** Distribution shift, cardinality change
  and schema drift are all worth catching. The `ops.data_quality_results`
  history is the right place to build them from, and they are not built.
- **No alerting.** Results are recorded and surfaced. Routing an error to a
  pager needs the Terraform action group wired to a real rota.
- **No quarantine.** Failing rows are counted, not diverted to a quarantine
  table for reprocessing. At this data volume, fixing forward is cheaper.
