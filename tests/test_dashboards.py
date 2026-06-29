"""Dashboard smoke tests and the chart design rules.

Two things are checked:

* **Every page executes.** Streamlit's ``AppTest`` runs each script in-process
  and captures exceptions. A dashboard that throws on load is the most visible
  possible failure, and the cheapest to catch.
* **The design rules hold.** The palette, the fixed categorical order and the
  no-dual-axis rule are asserted rather than trusted, because they are exactly
  the kind of thing that erodes one well-meaning commit at a time.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import pytest

from dashboards.streamlit import theme

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = ROOT / "dashboards" / "streamlit"
PAGES = [DASHBOARD_DIR / "app.py"] + sorted((DASHBOARD_DIR / "pages").glob("*.py"))


# --------------------------------------------------------------------------- #
# Pages run
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_page_runs_without_raising(db, page):
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(page), default_timeout=300).run()
    assert not app.exception, (
        f"{page.name} raised:\n"
        + "\n".join(str(e.value) for e in app.exception)
    )


def test_every_dashboard_audience_has_a_page():
    names = " ".join(p.name.lower() for p in PAGES)
    for audience in ["sales", "customers", "marketing", "operations", "realtime"]:
        assert audience in names, f"no dashboard page for {audience}"


# --------------------------------------------------------------------------- #
# Palette
# --------------------------------------------------------------------------- #
def test_categorical_palette_has_eight_distinct_hues():
    assert len(theme.CATEGORICAL) == 8
    assert len(set(theme.CATEGORICAL)) == 8


def test_every_palette_value_is_a_hex_colour():
    pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
    for colour in (theme.CATEGORICAL + theme.SEQUENTIAL_BLUE
                   + list(theme.STATUS.values())):
        assert pattern.match(colour), f"{colour} is not a hex colour"


def test_series_colour_is_stable_for_an_index():
    """Colour follows the entity, never its rank. A reader who learned
    'Electronics is blue' must not be repainted by a filter."""
    assert theme.series_colour(0) == theme.CATEGORICAL[0]
    assert theme.series_colour(3) == theme.CATEGORICAL[3]
    assert theme.series_colour(8) == theme.CATEGORICAL[0]     # wraps, never invents


def test_sequential_ramp_is_ordered_light_to_dark():
    def luminance(hex_colour: str) -> float:
        r, g, b = (int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    values = [luminance(c) for c in theme.SEQUENTIAL_BLUE]
    assert values == sorted(values, reverse=True), \
        "the sequential ramp must run light to dark, with no reversal"


def test_ordinal_ramp_starts_darker_than_the_sequential_one():
    """Discrete ordered marks must stay readable against the surface."""
    assert theme.ORDINAL_BLUE[0] != theme.SEQUENTIAL_BLUE[0]
    assert theme.ORDINAL_BLUE[0] in theme.SEQUENTIAL_BLUE


def test_diverging_scale_has_a_neutral_midpoint():
    positions = [stop[0] for stop in theme.DIVERGING]
    assert positions == [0.0, 0.5, 1.0]
    midpoint = theme.DIVERGING[1][1]
    r, g, b = (int(midpoint[i:i + 2], 16) for i in (1, 3, 5))
    assert max(r, g, b) - min(r, g, b) < 20, \
        "the diverging midpoint must read as neutral, not as a hue"


def test_status_colours_are_not_reused_as_series_colours():
    """A status colour must never impersonate a series."""
    assert not set(theme.STATUS.values()) & set(theme.CATEGORICAL)


def test_fold_tail_caps_the_number_of_categories():
    frame = pd.DataFrame({
        "category": [f"c{i}" for i in range(12)],
        "revenue": list(range(12, 0, -1)),
    })
    folded = theme.fold_tail(frame, "category", "revenue", keep=7)
    assert len(folded) == 8
    assert folded["category"].iloc[-1] == "Other"
    assert folded["revenue"].sum() == frame["revenue"].sum(), \
        "folding the tail must not lose revenue"


def test_fold_tail_leaves_a_short_list_alone():
    frame = pd.DataFrame({"category": ["a", "b"], "revenue": [2, 1]})
    assert len(theme.fold_tail(frame, "category", "revenue", keep=7)) == 2


# --------------------------------------------------------------------------- #
# Chart chrome
# --------------------------------------------------------------------------- #
def test_template_uses_the_categorical_order():
    assert list(theme.TEMPLATE.layout.colorway) == theme.CATEGORICAL


def test_gridlines_are_solid_hairlines():
    """Dashed gridlines read as 'projection' or 'threshold' when they are only
    a grid."""
    yaxis = theme.TEMPLATE.layout.yaxis
    assert yaxis.gridcolor == theme.GRIDLINE
    assert yaxis.gridwidth == 1
    assert yaxis.griddash in (None, "solid")


def test_apply_sets_a_height_that_includes_the_axis_band():
    figure = theme.apply(go.Figure(), "A title", height=320)
    assert figure.layout.height == 320
    assert figure.layout.margin.b >= 40, \
        "too small a bottom margin clips the x-axis labels"


def test_apply_can_hide_the_legend_for_a_single_series():
    assert theme.apply(go.Figure(), legend=False).layout.showlegend is False
    assert theme.apply(go.Figure(), legend=True).layout.showlegend is True


# --------------------------------------------------------------------------- #
# No dual axes, anywhere
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_no_page_creates_a_secondary_y_axis(page):
    """The single most misleading chart mistake: two y-scales whose alignment is
    arbitrary, inventing a correlation that is not in the data."""
    source = page.read_text(encoding="utf-8")
    for forbidden in ["secondary_y", "yaxis2", "overlaying=", 'overlaying="y"']:
        assert forbidden not in source, (
            f"{page.name} uses {forbidden} - use two charts, or index both "
            f"series to a common base on one axis"
        )


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_pages_use_the_theme_rather_than_raw_hex(page):
    """Every colour must come from the design system, so one change repaints
    the whole platform."""
    source = page.read_text(encoding="utf-8")
    hard_coded = re.findall(r'["\']#[0-9a-fA-F]{6}["\']', source)
    assert not hard_coded, (
        f"{page.name} hard-codes {hard_coded} - use theme.series_colour, "
        f"theme.STATUS or a theme constant"
    )


# --------------------------------------------------------------------------- #
# Formatting helpers
# --------------------------------------------------------------------------- #
def test_compact_money_uses_readable_suffixes():
    assert theme.compact_money(1_500_000) == "$1.5M"
    assert theme.compact_money(2_400) == "$2.4K"
    assert theme.compact_money(750) == "$750"


def test_formatters_render_missing_values_as_a_dash():
    for formatter in (theme.money, theme.compact_money, theme.number, theme.percent):
        assert formatter(None) == "-"
        assert formatter(float("nan")) == "-"


def test_delta_text_carries_direction_in_the_glyph_not_only_the_colour():
    """The tile must still read in greyscale and for a colour-blind viewer."""
    up_label, up_colour = theme.delta_text(12.3)
    down_label, down_colour = theme.delta_text(-4.5)
    assert up_label.startswith("▲") and down_label.startswith("▼")
    assert up_colour == theme.POSITIVE_TEXT
    assert down_colour == theme.NEGATIVE_TEXT


def test_delta_text_can_invert_what_good_means():
    """A rising churn rate is bad. The helper must be told which way is up."""
    _label, colour = theme.delta_text(5.0, higher_is_better=False)
    assert colour == theme.NEGATIVE_TEXT


def test_kpi_tile_renders_all_its_parts():
    html = theme.kpi_tile("Revenue", "$1.2M", ("▲ 8.0%", theme.POSITIVE_TEXT),
                          "vs prior period")
    for fragment in ["Revenue", "$1.2M", "▲ 8.0%", "vs prior period", "pulse-tile"]:
        assert fragment in html


# --------------------------------------------------------------------------- #
# Power BI assets stay in step with the platform
# --------------------------------------------------------------------------- #
def test_powerbi_theme_uses_the_same_palette():
    import json

    theme_file = ROOT / "dashboards" / "powerbi" / "theme.json"
    colours = json.loads(theme_file.read_text(encoding="utf-8"))["dataColors"]
    assert colours == theme.CATEGORICAL, \
        "the Power BI theme has drifted from the Streamlit palette"


def test_dax_library_defines_the_headline_measures():
    dax = (ROOT / "dashboards" / "powerbi" / "measures.dax").read_text(encoding="utf-8")
    for measure in ["Revenue =", "Gross Margin % =", "Average Order Value =",
                    "Churn Rate % =", "ROAS =", "Stock On Hand ="]:
        assert measure in dax, f"measures.dax is missing `{measure}`"


def test_dax_never_divides_by_a_column_or_measure_with_a_slash():
    """DIVIDE returns blank on a zero denominator; `/` returns an error that
    fills the whole visual with red.

    Division by a numeric *literal* (scaling to millions in a label) is fine -
    the denominator cannot be zero - so only division by a reference is flagged.
    """
    dax = (ROOT / "dashboards" / "powerbi" / "measures.dax").read_text(encoding="utf-8")
    body = "\n".join(line for line in dax.splitlines()
                     if not line.strip().startswith("//"))
    offenders = re.findall(r"/\s*(?![0-9])([A-Za-z\[][^\s,)]*)", body)
    assert not offenders, (
        f"these DAX expressions divide by a reference with `/` instead of "
        f"DIVIDE(): {offenders}"
    )
