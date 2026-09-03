# -*- coding: utf-8 -*-
"""The full PulseAnalytics backlog, assembled and ordered by issue key.

Keys are allocated in creation order, so a low key means an early ticket:
  PULSE-1 .. PULSE-11    epics cut in the inception workshop, 02 Mar 2026
  PULSE-12 .. PULSE-56   sprints 1-7   (three-person team)
  PULSE-57 .. PULSE-94   sprints 8-13  (QA joins 15 Jun)
  PULSE-95               the BA epic, cut 19 Aug ahead of Amit joining
  PULSE-96 .. PULSE-116  sprints 13-15 (BA joins 24 Aug)
  PULSE-117 .. PULSE-123 backlog items, raised at the point of deferral
"""

from backlog_common import PEOPLE, JOINED          # noqa: F401  (re-exported)
from backlog_epics import EPICS
from backlog_sprints_early import EARLY
from backlog_sprints_late import LATE

ISSUES = sorted(
    EPICS + EARLY + LATE,
    key=lambda i: int(i["key"].split("-")[1]),
)
