# KPI definitions

This is the contract. Every metric below is defined **once** here, implemented
once in SQL, and read by the dashboards, the API, the Python models and the DAX
library. Where a definition has a judgement call in it, the judgement is stated
rather than buried.

The rule this document exists to enforce: **if two people could disagree about
what a number means, it is defined here, and nothing computes its own version.**

---

## Anchoring: what "today" means

Every recency-based metric anchors to `gold.analysis_window.as_of_date` — the
latest order date present in the data — **not** the wall clock.

| | |
| --- | --- |
| **Why** | the same dataset must produce the same segments today and in six months, so a screenshot, a test and a report all agree |
| **Where** | `database/analytics/030_analysis_window.sql` |
| **Live feed** | point `as_of_date` at `CURRENT_DATE`; nothing else changes |

---

## Revenue and profit

### Revenue

**Net amount of completed orders**: gross minus discounts, excluding shipping
and tax.

```sql
SUM(net_amount) FILTER (WHERE is_revenue)     -- is_revenue = status 'completed'
```

- **Excludes** cancelled, returned and pending orders — but they stay in the
  fact table, flagged. Operations needs to see them.
- **Excludes** shipping and tax, which are pass-throughs, not earnings.
- **Where**: `gold.fact_orders.net_amount`, `gold.mart_sales_daily.revenue`
- **DAX**: `Revenue`

### Gross profit

```
gross_profit = net_amount − cost_amount
```

Product cost only. No fulfilment, marketing or overhead — the source system does
not carry them, and inventing an allocation would be a fabricated number
presented as a measured one.

### Gross margin %

```
gross_margin_pct = gross_profit / revenue × 100
```

Denominator is **net** revenue, not gross. Using gross would flatter the margin
by the size of the discount.

### Average order value (AOV)

```
avg_order_value = revenue / completed orders
```

Computed at the **order header** grain. Averaging the line fact answers a
different question (average line value) and gives a materially smaller number.
This is why `fact_orders` exists separately from `fact_sales`.

### Discount rate %

```
discount_rate_pct = discounts / (revenue + discounts) × 100
```

Discounts as a share of what the order *would* have been — the denominator is
gross, because "we discounted 12% of list" is the question being asked.

---

## Customers

### Lifecycle status

Measured from `as_of_date` minus the customer's last completed order.

| Status | Rule |
| --- | --- |
| Prospect | never ordered |
| New | exactly one order, within 90 days |
| Active | ordered within 90 days |
| At Risk | 91–180 days |
| Lapsed | 181–365 days |
| Churned | more than 365 days, or `is_churned` past the 90-day window |

`New` deliberately wins over `Active`, so acquisition and retention cohorts are
not double-counted.

### Churn

**No completed order in `CHURN_WINDOW_DAYS` (default 90).**

```
is_churned = (as_of_date − last_order_date) > 90
```

- 90 days is a *choice*, set by `PULSE_CHURN_WINDOW_DAYS`. For a business whose
  natural purchase cadence is quarterly it would be far too aggressive. It is
  configurable precisely because it is not universal.
- The **monthly churn rate** in `mart_churn_monthly` is a different, flow-based
  measure: customers active last month who did not order this month, over
  customers active last month. Both are legitimate; they answer different
  questions, so both are published with distinct names.

### Repeat rate

```
repeat_rate_pct = customers with ≥2 orders / customers with ≥1 order × 100
```

Denominator is **purchasers**, not all customers. Including never-purchasers
would conflate activation with retention.

### Customer lifetime value

Three figures, deliberately, because a single CLV always hides an assumption:

| Measure | Definition | Assumption |
| --- | --- | --- |
| **Historic CLV** | lifetime gross profit to date | none — it is observed |
| **Predicted CLV** | monthly ARPU × margin × expected remaining months, discounted at 1%/month | monthly retention holds flat; geometric survival `r/(1−r)`, capped at 36 months |
| **Cohort-curve CLV** | extrapolate mature cohorts' cumulative-LTV shape onto young ones | new cohorts behave like old ones |

Where the three diverge sharply is a finding, not a bug — usually it means
retention has genuinely changed between cohorts. Churned customers get
`predicted_clv = 0`; there is no remaining value to discount.

- **Where**: `analytics/customer/clv.py`, `mart_customer_360.projected_annual_value`

### RFM

Quintiles (`NTILE(5)`), not fixed thresholds — absolute cut-offs stop being
meaningful the moment the business grows.

| | |
| --- | --- |
| **R** | days since last order, **inverted** (5 = most recent) |
| **F** | lifetime completed orders |
| **M** | lifetime net revenue |

Only purchasers are scored. Including never-purchasers would drag every quintile
boundary towards zero.

Segments follow the standard 11-cell RFM grid (Champions, Loyal Customers, At
Risk, Cannot Lose Them, …) so the output is legible to a marketing team without
a glossary. Each carries a `recommended_action`, in the warehouse rather than in
a slide, so the CRM export and the dashboard cannot disagree.

---

## Cohorts and retention

### Cohort

**The calendar month of a customer's first completed order** — *not* their
signup month.

A signup that never bought is an activation problem, not a retention one.
Mixing the two is the most common way a cohort chart lies.

### Retention %

```
retention_pct = distinct customers active in month N / cohort size × 100
```

Month 0 is always 100% by construction. No cell is emitted for a month a cohort
could not yet have reached — a zero there would read as "they all left" rather
than "we do not know yet".

### Cumulative LTV

Running sum of cohort revenue divided by cohort size: what one acquired customer
has returned by month N.

---

## Marketing

### Attribution — read this before quoting any ROAS

The warehouse ships **last-touch, campaign-window** attribution: an order is
credited to a campaign when the source system stamped that campaign on it. This
is the honest limit of the available data, and it is stated on the dashboard,
because an unlabelled ROAS number is worse than no ROAS number.

`analytics/marketing/attribution.py` recomputes the same revenue under
**first-touch, linear, time-decay and position-based** models from the
clickstream. No model is correct. The **spread between them** is the finding: a
channel with a large positive `upper_funnel_bias` is under-credited by
last-touch and will be starved by a last-touch budget.

### ROAS

```
roas        = attributed revenue / spend
profit_roas = attributed gross profit / spend
```

`profit_roas > 1` is the meaningful break-even. `roas > 1` only means the
campaign returned more revenue than it cost, which for a 30%-margin business is
still a loss.

### CAC

```
cac = spend / attributed NEW customers
```

New customers, not all attributed customers. Dividing by everyone who ordered
during a campaign counts existing customers as acquisitions and understates CAC.

### LTV : CAC

```
ltv_cac_ratio = average total CLV / CAC
```

Below 1.0 the channel destroys value; 3.0 or better is healthy. Channels with no
measured spend show **blank**, never infinity.

### Incremental revenue (proxy)

```
incremental ≈ revenue during the campaign − (baseline daily revenue × campaign days)
```

Baseline is the 28 days immediately before the campaign. This is a **crude
proxy**, labelled as such wherever it appears. It cannot separate a campaign
from a seasonal upswing. A real answer needs a geo holdout or a matched-market
test, which the source data does not support.

---

## Operations

### Payment success — two rates, on purpose

| Metric | Denominator | Answers |
| --- | --- | --- |
| `attempt_failure_rate_pct` | every attempt | how well is the **gateway** performing |
| `order_success_rate_pct` | distinct orders, final attempt | what did the **customer** experience |

A decline that succeeds on retry is invisible to the customer and very visible
to the gateway. One ambiguous "success rate" would be argued about in every
review, so both are published with explicit names.

**By gateway** (`gold.mart_payment_gateway_success`, Operations page), both
rates are shown side by side with their denominators named:

```
attempt_success_rate_pct = attempts_captured / authorisation_attempts × 100   -- denominator A
order_success_rate_pct   = orders_paid       / orders_attempted       × 100   -- denominator B
```

* Refund rows are **not** authorisation attempts and are in neither denominator.
* An order is counted once, against the gateway of its **final** authorisation
  attempt. Refunds never compete for "final" — before PULA-105 they did, which
  made every captured-then-returned order count as unpaid and understated the
  per-order rate by roughly 12 points on the test dataset.
* The source records the payment method only, so the method is the gateway.
* Published for the last 90 days and for all history.

### Recovery rate

```
recovery_rate_pct = failed attempts where a LATER attempt on the same order was captured / failed attempts × 100
```

High recovery on an issuer decline means the retry logic works. Low recovery on
a technical failure means it does not.

### Inventory

| Metric | Definition | Note |
| --- | --- | --- |
| `days_of_cover` | `on_hand / (weekly sell-through ÷ 7)` | **NULL**, not infinity, when the product sells nothing |
| `is_below_reorder` | `on_hand ≤ reorder_point` | source system's own policy |
| `inventory_turns` | `avg weekly sales × 52 / avg on-hand` | annualised |
| `estimated_lost_revenue` | stockout weeks × trailing average weekly units × unit price | **approximate by design**; assumes demand would have matched trend |
| `safety_stock` | `z × σ(weekly demand) × √lead time` | driven by *variability*, not level — a steady high-volume product needs less buffer than an erratic low-volume one |
| `economic_order_qty` | `√(2 × annual demand × order cost / holding cost)` | order cost £75, holding rate 22%/yr — both assumptions, both editable |

Stock balances are **semi-additive**: they sum across products, never across
dates. Every inventory figure reads the latest snapshot per product.

### Conversion funnel

Counted on **sessions**, not events. A visitor who views ten products in one
visit is *one* session that reached product-view, not ten.

Steps are "reached at least this stage", so the funnel is monotonically
decreasing by construction and cannot produce the impossible above-100% step
conversion that event-counted funnels routinely show.

```
cart_abandonment_pct = 100 − (sessions reaching purchase / sessions reaching add-to-cart × 100)
drop_off_pct         = 100 − step_conversion_pct          -- per stage, vs the previous stage
```

### Cancellations and returns by reason

`gold.mart_order_exceptions` — one row per period × outcome × reason, with two
denominators:

| Metric | Denominator | Answers |
| --- | --- | --- |
| `share_of_outcome_pct` | all orders with the same outcome (A) | which reason to fix **first** |
| `rate_of_orders_placed_pct` | all orders placed in the period (B) | did the fix **work** — comparable across periods |

```
cancellation_rate_pct = cancelled orders / orders placed × 100   -- a ratio of counts, never an average of daily rates
return_rate_pct       = returned orders  / orders placed × 100
```

Reason codes are mapped to a label and a group (Product, Fulfilment, Customer,
Payment, Inventory) in `044_mart_order_exceptions.sql`. A blank reason is
reported as **Not recorded** and an unknown code as **Unmapped** — both stay in
the totals. Monthly rates are in `gold.mart_order_exceptions_monthly`.

---

## Forecasting

Two models plus a baseline, all backtested on a held-out tail of the actual
history — never scored on data they were fitted to.

| Model | What it assumes |
| --- | --- |
| Holt-Winters (additive) | level + trend + a repeating seasonal shape |
| Linear trend | the trend continues, no seasonality |
| **Seasonal naive** | next period looks like the last one — the **baseline** |

Seasonal naive is reported as a first-class result, not as filler. A model that
cannot beat it on backtest is not worth deploying, and reporting only the
sophisticated model's error hides that.

Accuracy is reported as MAE, RMSE, MAPE **and bias**. Bias matters
independently: a forecast that is consistently 8% low is a very different
operational problem from one that is noisily wrong.

Every forecast is published with an **80% prediction interval**, widening as
`σ × z × √step`. A single line implies a precision no revenue forecast has. The
interval is an approximation and is labelled as one.

---

## Churn model

Logistic regression on nine behavioural features, producing a **propensity
score**, not a classification.

**The framing matters more than the model.** Features are computed from a
snapshot taken 90 days *before* the analysis date, labelled by what actually
happened in those 90 days. Training on today's features against today's label
leaks the future and produces a beautiful AUC with no predictive value — the
single most common mistake in a churn project.

A linear model is used deliberately. Its coefficients are part of the
deliverable: retention teams act on *why* a customer is at risk, and "recency
dominates, support contacts add materially" is something they can build a
campaign from. Standardised inputs mean |coefficient| is a comparable effect
size.

Already-churned customers are excluded from scoring — they are a win-back
problem, not a retention one, and including them floods the call list with
people it is too late to save.

The call list is ordered by **revenue at risk**:

```
revenue_at_risk = projected_annual_value × churn_probability
```

what the customer is worth, times how likely we are to lose them.

---

## Where each definition lives

| Metric family | SQL | Python | DAX |
| --- | --- | --- | --- |
| Revenue, margin, AOV | `031_mart_sales_daily.sql` | — | `Revenue`, `Gross Margin %` |
| Customer lifecycle, CLV | `034_mart_customer_360.sql` | `analytics/customer/clv.py` | `Churn Rate %` |
| RFM | `035_mart_rfm_segments.sql` | `analytics/customer/segmentation.py` | — |
| Cohorts | `036_mart_cohort_retention.sql` | `analytics/customer/clv.py` | — |
| Marketing | `037_mart_marketing.sql` | `analytics/marketing/attribution.py` | `ROAS`, `CAC` |
| Inventory | `039_mart_inventory_health.sql` | `analytics/inventory/optimisation.py` | `Stock On Hand` |
| Funnel, payments | `040_mart_funnel_payments.sql` | — | `Conversion Rate %` |
| Cancellations, returns | `044_mart_order_exceptions.sql` | — | — |
| Executive | `041_mart_executive.sql` | — | all of the above |

Reconciliation between the SQL implementations is asserted by
`etl/quality/suite.py`. The DAX side is verified by comparing a Power BI card
against the Streamlit executive page — the one step this repository does not
automate, and says so.
