# PULA-41: Quality suite fails every night on 0.07% of customers with no email

- Jira: https://futuristic.atlassian.net/browse/PULA-41
- Type: Task
- Priority: High
- Status: Done
- Created: 2026-05-04 09:15
- Project: PulseAnalytics (PULA)

## Description

The completeness check on customer email fails on every run, because about 0.07% of customers genuinely have no email address. Two weeks in, people had stopped reading the quality output, so the suite caught nothing regardless of what it detected.

## Scope and follow-ups

- Cause: zero-tolerance thresholds applied to a check that encodes an accepted business reality (customers acquired in-store before email capture was mandatory).
- Fix: PULSE-42 - re-tune to a quantified warning threshold, and state in the check description that it encodes an accepted reality rather than a defect.
