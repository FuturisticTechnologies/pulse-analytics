# PULA-48: fact_orders at header grain

- Jira: https://futuristic.atlassian.net/browse/PULA-48
- Type: Task
- Priority: Medium
- Status: Done
- Created: 2026-05-12 09:15
- Project: PulseAnalytics (PULA)

## Description

As the model, I want an order-grain fact table, so that order-level metrics are computed at order level.

## Scope and acceptance

- one row per order
- net_amount, gross_amount, discount, shipping, tax, cost_amount
- is_revenue flag implementing the agreed revenue definition
- cancelled, returned and pending orders present and flagged, not filtered
- dimension keys resolved to surrogates, unresolved keys on -1
