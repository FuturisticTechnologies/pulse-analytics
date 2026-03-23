"""Extract: the external API arm of the architecture.

Pulls daily FX rates so regional revenue can be restated in local currency.

Two properties matter more than the data itself:

1. **It degrades, it does not fail.** A public endpoint is not part of our SLA.
   If the call times out, is rate-limited, or the machine is offline (CI, a
   plane, a locked-down corporate network), the extractor falls back to a
   deterministic synthetic curve and marks every row with ``source='fallback'``.
   The pipeline stays green and the dashboard can *see* that the rates are
   stand-ins - which is far better than a silent failure or a hard stop.

2. **It is honest about provenance.** Every row carries its source, so nobody
   ever presents a fallback rate as a market rate.
"""
from __future__ import annotations

import json
import math
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta

import pandas as pd

from pulse.logging_utils import get_logger

log = get_logger("etl.extract.api")

# Free, keyless, and widely mirrored. Swapped for the corporate rates provider
# in production by changing this constant and nothing else.
FX_ENDPOINT = "https://api.frankfurter.app/latest?from=USD&to={symbols}"
QUOTE_CURRENCIES = ["EUR", "GBP", "CAD", "SGD", "BRL", "MXN"]

# Plausible mid-market anchors, used when the network is unavailable.
FALLBACK_ANCHORS = {
    "EUR": 0.92, "GBP": 0.79, "CAD": 1.36, "SGD": 1.34, "BRL": 5.05, "MXN": 17.2,
}


def _fetch_live(timeout: float = 4.0) -> dict[str, float] | None:
    """One attempt at the live endpoint. Returns None on any failure."""
    url = FX_ENDPOINT.format(symbols=",".join(QUOTE_CURRENCIES))
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        rates = payload.get("rates") or {}
        if not rates:
            return None
        log.info("fetched live FX rates for %d currencies", len(rates))
        return {code: float(value) for code, value in rates.items()}
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        log.warning("FX endpoint unavailable (%s) - using deterministic fallback", exc)
        return None


def _synthetic_series(anchor: float, day_index: int) -> float:
    """A smooth, deterministic wobble around the anchor: +/-2%, ~90-day period."""
    return round(anchor * (1.0 + 0.02 * math.sin(day_index / 14.3)), 6)


def fetch_fx_rates(
    days: int = 30,
    as_of: date | None = None,
    allow_network: bool = True,
) -> pd.DataFrame:
    """Return a tidy FX table: one row per day per currency.

    The live endpoint gives today's rate only, so history is back-filled with
    the synthetic curve anchored on the live value - a documented approximation
    that keeps the shape of the data honest without pretending to be a
    historical rates feed.
    """
    as_of = as_of or date.today()
    live = _fetch_live() if allow_network else None
    anchors = live or FALLBACK_ANCHORS
    source = "frankfurter.app" if live else "fallback"

    rows: list[dict] = []
    loaded_at = datetime.now()
    for offset in range(days):
        rate_date = as_of - timedelta(days=offset)
        for currency in QUOTE_CURRENCIES:
            anchor = anchors.get(currency, FALLBACK_ANCHORS[currency])
            rate = anchor if (live and offset == 0) else _synthetic_series(anchor, offset)
            rows.append({
                "rate_date": rate_date,
                "base_currency": "USD",
                "quote_currency": currency,
                "rate": rate,
                "source": source if offset == 0 else f"{source}+interpolated",
                "_loaded_at": loaded_at,
                "_source_file": "api:fx_rates",
            })

    frame = pd.DataFrame(rows)
    frame["rate_date"] = pd.to_datetime(frame["rate_date"])
    log.info("extracted %-22s %9s rows (source=%s)", "fx_rates", format(len(frame), ","), source)
    return frame
