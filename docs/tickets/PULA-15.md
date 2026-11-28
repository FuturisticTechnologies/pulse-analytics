# PULA-15: Seed known defects into the generator

- Jira: https://futuristic.atlassian.net/browse/PULA-15
- Type: Task
- Priority: Medium
- Status: Done
- Created: 2026-03-02 14:10
- Project: PulseAnalytics (PULA)

## Description

The generator must produce dirty data on purpose, so the quality layer has something real to catch and the tests can assert it does.

## Scope and acceptance

- replayed orders: the same order_id landed twice with different ingest times
- negative quantities on a small share of lines
- loyalty tier case and whitespace drift: "Gold", "gold ", "GOLD"
- about 0.07% of customers with no email address
- a handful of orders referencing a customer_id that does not exist
- FX gaps on weekend dates
