# -*- coding: utf-8 -*-
"""Shared people, sprint calendar and the issue constructor."""

import datetime as dt

G = "geetha.nallamada"      # Sr. Data Analyst   - tech lead / metric owner
D = "divya.maram"           # Data Analyst
V = "devendranath.singam"   # DevOps Engineer
N = "neha.chauhan"          # QA Analyst         - from 15 Jun 2026
A = "amit.shinde"           # Business Analyst   - from 24 Aug 2026

PEOPLE = {
    G: {"name": "Geetha Nallamada", "role": "Sr. Data Analyst", "slack": "@geetha"},
    D: {"name": "Divya Maram", "role": "Data Analyst", "slack": "@divya"},
    V: {"name": "Devendranath Singam", "role": "DevOps Engineer", "slack": "@deven"},
    N: {"name": "Neha Chauhan", "role": "QA Analyst", "slack": "@neha"},
    A: {"name": "Amit Shinde", "role": "Business Analyst", "slack": "@amit"},
}

JOINED = {
    G: dt.date(2026, 3, 1),
    D: dt.date(2026, 3, 1),
    V: dt.date(2026, 3, 1),
    N: dt.date(2026, 6, 15),
    A: dt.date(2026, 8, 24),
}

# Two-week sprints, Monday start. Project kicks off Sun 01 Mar 2026.
S1 = "Sprint 1 (02 Mar - 13 Mar)"
S2 = "Sprint 2 (16 Mar - 27 Mar)"
S3 = "Sprint 3 (30 Mar - 10 Apr)"
S4 = "Sprint 4 (13 Apr - 24 Apr)"
S5 = "Sprint 5 (27 Apr - 08 May)"
S6 = "Sprint 6 (11 May - 22 May)"
S7 = "Sprint 7 (25 May - 05 Jun)"
S8 = "Sprint 8 (08 Jun - 19 Jun)"
S9 = "Sprint 9 (22 Jun - 03 Jul)"
S10 = "Sprint 10 (06 Jul - 17 Jul)"
S11 = "Sprint 11 (20 Jul - 31 Jul)"
S12 = "Sprint 12 (03 Aug - 14 Aug)"
S13 = "Sprint 13 (17 Aug - 28 Aug)"
S14 = "Sprint 14 (31 Aug - 11 Sep)"   # current sprint
S15 = "Sprint 15 (14 Sep - 25 Sep)"


def I(key, type, summary, status, description, parent=None, epic_name=None,
      assignee=None, reporter=G, priority="Medium", points="", sprint="",
      components="", labels="", created="", resolved="", updated="", due="",
      comments=()):
    """One Jira issue. `parent` is the Epic Link for non-epic issue types."""
    return dict(
        key=key, type=type, summary=summary, status=status,
        description=description.strip(), parent=parent or "",
        epic_name=epic_name or "", assignee=assignee or "", reporter=reporter,
        priority=priority, points=points, sprint=sprint, components=components,
        labels=labels, created=created, resolved=resolved, updated=updated,
        due=due, comments=list(comments),
    )
