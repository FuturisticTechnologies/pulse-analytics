"""Shared presentation helpers for KPI values.

Deliberately **formatting only**. Metric *formulas* live in SQL, in
``database/``, and are documented in docs/kpi-definitions.md - a second Python
implementation of "revenue" or "ROAS" would be exactly the drift this platform
exists to prevent, however convenient it looked.

What belongs here is the arithmetic that is not a business definition (safe
division, percentage change) and the rendering rules that every surface should
share, so a figure looks the same in the insight report, the dashboard tiles and
the API.
"""
from __future__ import annotations

CURRENCY_SYMBOLS = {"USD": "$", "EUR": "EUR ", "GBP": "GBP "}


def safe_divide(numerator, denominator, default: float = 0.0) -> float:
    """Division that yields ``default`` instead of raising or returning inf.

    Used wherever a denominator can legitimately be zero - a channel with no
    spend, a customer with no orders. Returning ``default`` rather than
    ``inf`` matters: an infinity propagates through a chart axis and makes
    every other series invisible.
    """
    try:
        denominator = float(denominator)
    except (TypeError, ValueError):
        return default
    if not denominator:
        return default
    try:
        return float(numerator) / denominator
    except (TypeError, ValueError):
        return default


def pct_change(current, previous, default: float | None = None) -> float | None:
    """Percentage change, or ``default`` when there is no baseline.

    ``None`` rather than ``0`` when the previous period is zero: "no change" and
    "nothing to compare against" are different statements, and showing 0% for
    the second is a small lie that gets repeated in every review.
    """
    try:
        previous = float(previous)
        current = float(current)
    except (TypeError, ValueError):
        return default
    if not previous:
        return default
    return round((current - previous) / previous * 100, 2)


def _is_missing(value) -> bool:
    return value is None or (isinstance(value, float) and value != value)  # NaN


def money(value, currency: str = "USD", decimals: int = 2) -> str:
    if _is_missing(value):
        return "-"
    return CURRENCY_SYMBOLS.get(currency, "") + format(float(value), f",.{decimals}f")


def compact(value, currency: str = "") -> str:
    """Dashboard-friendly short form: $1.2M / 348.0K / 912."""
    if _is_missing(value):
        return "-"
    symbol = CURRENCY_SYMBOLS.get(currency, "") if currency else ""
    value = float(value)
    for threshold, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")):
        if abs(value) >= threshold:
            return symbol + format(value / threshold, ",.1f") + suffix
    return symbol + format(value, ",.0f")


def number(value, decimals: int = 0) -> str:
    if _is_missing(value):
        return "-"
    return format(float(value), f",.{decimals}f")


def percent(value, decimals: int = 1) -> str:
    if _is_missing(value):
        return "-"
    return format(float(value), f",.{decimals}f") + "%"
