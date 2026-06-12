"""One design system for every chart in the platform.

Charts are read by people, so the rules here are not decoration:

* **Categorical hues are assigned in fixed order and never cycled.** A series
  keeps its colour when a filter removes its neighbours, so a reader who learned
  "Electronics is blue" is never misled. Past eight series we fold the tail into
  "Other" rather than inventing a ninth hue that nobody could distinguish.
* **The palette is colour-vision-deficiency safe.** The order below was chosen
  so that every adjacent pair separates for the ~8% of men with a CVD, and the
  legend is always present so identity is never carried by colour alone.
* **Sequential = one hue, light to dark. Diverging = two opposite hues with a
  neutral midpoint.** No rainbows: a rainbow ramp makes the reader decode a
  legend to answer "is this bigger".
* **Never two y-axes on one plot.** The alignment between two scales is
  arbitrary, so a dual-axis chart invents a correlation that is not in the data.
  Two measures of different magnitude get two charts, or are indexed to 100.
* **Status colours are reserved** for good / warning / serious / critical and
  are always paired with a word, never used as "series 5".

Everything is exposed as constants and helpers so no page hand-picks a colour.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from pulse import kpi
from pulse.config import CURRENCY

# --------------------------------------------------------------------------- #
# Palette
# --------------------------------------------------------------------------- #
# Fixed categorical order. Index 0 is the default single-series colour.
CATEGORICAL = [
    "#2a78d6",  # blue
    "#eb6834",  # orange
    "#1baf7a",  # aqua
    "#eda100",  # yellow
    "#e87ba4",  # magenta
    "#008300",  # green
    "#4a3aa7",  # violet
    "#e34948",  # red
]

# Single-hue ramp for magnitude (heatmaps, choropleths, ordered intensity).
SEQUENTIAL_BLUE = [
    "#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef",
    "#6da7ec", "#5598e7", "#3987e5", "#2a78d6",
    "#256abf", "#1c5cab", "#184f95", "#104281",
]
# Ordinal marks must stay readable against the surface, so an ordered discrete
# ramp starts darker than the sequential one.
ORDINAL_BLUE = SEQUENTIAL_BLUE[3:]

# Diverging: warm/cool poles with a neutral - never two cool hues.
DIVERGING = [[0.0, "#1c5cab"], [0.5, "#f0efec"], [1.0, "#d03b3b"]]

STATUS = {
    "good": "#0ca30c",
    "warning": "#fab219",
    "serious": "#ec835a",
    "critical": "#d03b3b",
}

# Chrome and ink.
SURFACE = "#fcfcfb"
PAGE = "#f9f9f7"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
AXIS = "#c3c2b7"
POSITIVE_TEXT = "#006300"
NEGATIVE_TEXT = "#d03b3b"

FONT_STACK = 'system-ui, -apple-system, "Segoe UI", sans-serif'


# --------------------------------------------------------------------------- #
# Plotly template
# --------------------------------------------------------------------------- #
def plotly_template() -> go.layout.Template:
    """Recessive chrome, thin marks, generous padding."""
    return go.layout.Template(
        layout=go.Layout(
            colorway=CATEGORICAL,
            font=dict(family=FONT_STACK, size=13, color=INK_SECONDARY),
            paper_bgcolor=SURFACE,
            plot_bgcolor=SURFACE,
            margin=dict(l=8, r=8, t=48, b=8),
            title=dict(font=dict(size=16, color=INK_PRIMARY), x=0, xanchor="left",
                       pad=dict(b=12)),
            hoverlabel=dict(bgcolor=SURFACE, bordercolor=AXIS,
                            font=dict(family=FONT_STACK, size=12, color=INK_PRIMARY)),
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02,
                        xanchor="left", x=0, title_text="",
                        font=dict(size=12, color=INK_SECONDARY)),
            xaxis=dict(
                showgrid=False, zeroline=False,
                linecolor=AXIS, linewidth=1, ticks="outside", ticklen=4,
                tickcolor=AXIS, tickfont=dict(color=INK_MUTED, size=12),
                title=dict(font=dict(color=INK_MUTED, size=12)),
            ),
            yaxis=dict(
                # Solid hairline grid, one shade off the surface. Never dashed:
                # dashing reads as "projection" when it is only a grid.
                showgrid=True, gridcolor=GRIDLINE, gridwidth=1,
                zeroline=False, showline=False,
                tickfont=dict(color=INK_MUTED, size=12),
                title=dict(font=dict(color=INK_MUTED, size=12)),
            ),
        )
    )


TEMPLATE = plotly_template()


def apply(figure: go.Figure, title: str = "", height: int = 340,
          legend: bool = True, y_prefix: str = "") -> go.Figure:
    """Final pass every chart goes through before it is rendered."""
    figure.update_layout(
        template=TEMPLATE,
        title=title,
        height=height,
        showlegend=legend,
        # Height includes the axis band, so the card never grows an inner
        # scrollbar that clips the x labels.
        margin=dict(l=8, r=8, t=48 if title else 16, b=40),
    )
    if y_prefix:
        figure.update_yaxes(tickprefix=y_prefix)
    return figure


# --------------------------------------------------------------------------- #
# Formatting
#
# Delegated to pulse.kpi so a figure renders identically in the dashboard, the
# insight report and the API. Two implementations of "how do we write a
# currency" is how $1.2M and $1,200,000.00 end up on the same slide.
# --------------------------------------------------------------------------- #
def money(value, decimals: int = 0) -> str:
    return kpi.money(value, currency=CURRENCY, decimals=decimals)


def compact_money(value) -> str:
    return kpi.compact(value, currency=CURRENCY)


def number(value, decimals: int = 0) -> str:
    return kpi.number(value, decimals=decimals)


def percent(value, decimals: int = 1) -> str:
    return kpi.percent(value, decimals=decimals)


def delta_text(value, suffix: str = "%", higher_is_better: bool = True) -> tuple[str, str]:
    """Return (label, colour) for a change figure.

    The arrow and the sign carry the meaning; colour only reinforces it, so the
    tile is still readable in greyscale or with a colour-vision deficiency.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "-", INK_MUTED
    value = float(value)
    good = (value >= 0) if higher_is_better else (value <= 0)
    arrow = "▲" if value >= 0 else "▼"
    colour = POSITIVE_TEXT if good else NEGATIVE_TEXT
    return f"{arrow} {abs(value):,.1f}{suffix}", colour


# --------------------------------------------------------------------------- #
# Components
# --------------------------------------------------------------------------- #
KPI_CSS = f"""
<style>
  .pulse-tile {{
      background: {SURFACE};
      border: 1px solid rgba(11,11,11,0.10);
      border-radius: 10px;
      padding: 14px 16px 12px 16px;
      height: 100%;
  }}
  .pulse-tile .label {{
      font-family: {FONT_STACK};
      font-size: 12px; font-weight: 500; letter-spacing: .02em;
      color: {INK_MUTED}; text-transform: uppercase; margin-bottom: 6px;
  }}
  .pulse-tile .value {{
      font-family: {FONT_STACK};
      font-size: 30px; font-weight: 600; line-height: 1.1;
      color: {INK_PRIMARY};
  }}
  .pulse-tile .delta {{
      font-family: {FONT_STACK};
      font-size: 13px; font-weight: 500; margin-top: 6px;
  }}
  .pulse-tile .sub {{
      font-family: {FONT_STACK};
      font-size: 12px; color: {INK_SECONDARY}; margin-top: 4px;
  }}
  .pulse-note {{
      font-family: {FONT_STACK}; font-size: 12.5px; color: {INK_SECONDARY};
      border-left: 3px solid {CATEGORICAL[0]}; padding: 6px 0 6px 12px;
      margin: 4px 0 14px 0;
  }}
</style>
"""


def kpi_tile(label: str, value: str, delta: tuple[str, str] | None = None,
             sub: str = "") -> str:
    """A stat tile: when the story is one number, the number is the chart."""
    parts = [f'<div class="pulse-tile"><div class="label">{label}</div>',
             f'<div class="value">{value}</div>']
    if delta:
        text, colour = delta
        parts.append(f'<div class="delta" style="color:{colour}">{text}</div>')
    if sub:
        parts.append(f'<div class="sub">{sub}</div>')
    parts.append("</div>")
    return "".join(parts)


def note(text: str) -> str:
    """A short caveat rendered under a chart - where assumptions get stated."""
    return f'<div class="pulse-note">{text}</div>'


def series_colour(index: int) -> str:
    """Fixed-order categorical hue. Never call this with a rank."""
    return CATEGORICAL[index % len(CATEGORICAL)]


def fold_tail(frame: pd.DataFrame, label_column: str, value_column: str,
              keep: int = 7, other_label: str = "Other") -> pd.DataFrame:
    """Keep the top ``keep`` categories and fold the rest into one row.

    Prevents the ninth-colour problem structurally: no chart is ever handed more
    categories than the palette can distinguish.
    """
    if len(frame) <= keep + 1:
        return frame
    ordered = frame.sort_values(value_column, ascending=False)
    head = ordered.head(keep).copy()
    tail = ordered.tail(len(ordered) - keep)
    other = {column: None for column in frame.columns}
    other[label_column] = other_label
    for column in frame.select_dtypes("number").columns:
        other[column] = tail[column].sum()
    return pd.concat([head, pd.DataFrame([other])], ignore_index=True)
