"""Sales dashboard - what sold, and why the number moved."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from analytics.sales import performance                # noqa: E402
from dashboards.streamlit import data_access as data   # noqa: E402
from dashboards.streamlit import theme                 # noqa: E402

st.set_page_config(page_title="PulseAnalytics - Sales", page_icon="◑", layout="wide")
st.markdown(theme.KPI_CSS, unsafe_allow_html=True)

st.title("Sales")
if not data.require_warehouse():
    st.stop()

daily = data.daily_sales()
monthly = data.monthly_sales()

# --------------------------------------------------------------------------- #
# Filters - one row, above the charts, so the reader sees the scope first.
# --------------------------------------------------------------------------- #
window_options = {
    "Last 30 days": 30, "Last 90 days": 90, "Last 180 days": 180,
    "Last 12 months": 365, "All history": len(daily),
}
filter_row = st.columns([2, 2, 6])
window_label = filter_row[0].selectbox("Period", list(window_options), index=1)
granularity = filter_row[1].selectbox("Granularity", ["Daily", "Weekly", "Monthly"])
window = daily.tail(window_options[window_label])

st.caption(
    f"{window['order_date'].min():%d %b %Y} to {window['order_date'].max():%d %b %Y} "
    f"({len(window)} trading days)"
)

# --------------------------------------------------------------------------- #
# Tiles
# --------------------------------------------------------------------------- #
revenue = float(window["revenue"].sum())
profit = float(window["gross_profit"].sum())
orders = int(window["orders_completed"].sum())
units = int(window["units_sold"].sum())
cancelled = int(window["orders_cancelled"].sum())

tiles = [
    ("Revenue", theme.compact_money(revenue), None, f"{len(window)} days"),
    ("Gross profit", theme.compact_money(profit), None,
     theme.percent(profit / revenue * 100 if revenue else 0) + " margin"),
    ("Orders", theme.number(orders), None, f"{theme.number(units)} units"),
    ("Average order value", theme.money(revenue / orders if orders else 0), None, ""),
    ("Cancellations", theme.number(cancelled), None,
     theme.percent(cancelled / (orders + cancelled) * 100 if orders + cancelled else 0)),
    ("Discounts", theme.compact_money(window["discounts"].sum()), None,
     theme.percent(window["discounts"].sum() / (revenue + window["discounts"].sum()) * 100
                   if revenue else 0) + " of gross"),
]
for column, (label, value, delta, sub) in zip(st.columns(6), tiles):
    column.markdown(theme.kpi_tile(label, value, delta, sub), unsafe_allow_html=True)
st.write("")


# --------------------------------------------------------------------------- #
# Trend
# --------------------------------------------------------------------------- #
def trend_chart() -> go.Figure:
    frame = window.copy()
    if granularity == "Weekly":
        frame = (frame.set_index("order_date")
                 .resample("W-MON")[["revenue", "gross_profit"]].sum().reset_index())
    elif granularity == "Monthly":
        frame = (frame.set_index("order_date")
                 .resample("MS")[["revenue", "gross_profit"]].sum().reset_index())

    figure = go.Figure()
    figure.add_trace(go.Scatter(
        x=frame["order_date"], y=frame["revenue"], name="Revenue",
        mode="lines", line=dict(color=theme.series_colour(0), width=2),
        hovertemplate="%{y:$,.0f}<extra>Revenue</extra>",
    ))
    # Profit is also dollars, so it belongs on the same axis. Two different
    # units would need two charts, never a second y-scale.
    figure.add_trace(go.Scatter(
        x=frame["order_date"], y=frame["gross_profit"], name="Gross profit",
        mode="lines", line=dict(color=theme.series_colour(2), width=2),
        hovertemplate="%{y:$,.0f}<extra>Gross profit</extra>",
    ))
    return theme.apply(figure, f"{granularity} revenue and gross profit",
                       height=360, y_prefix="$")


st.plotly_chart(trend_chart(), width="stretch")


# --------------------------------------------------------------------------- #
# Growth: MoM / YoY, indexed to one axis
# --------------------------------------------------------------------------- #
def yoy_chart() -> go.Figure:
    """Year-on-year comparison by indexing both years to their own January.

    Indexing is what makes two years of different absolute size comparable on
    ONE axis. Plotting raw dollars for both years and a percentage line would
    require a second scale, which is never worth it.
    """
    frame = monthly.copy()
    frame["year"] = frame["month_start"].dt.year
    frame["month_number"] = frame["month_start"].dt.month
    figure = go.Figure()
    for index, (year, group) in enumerate(frame.groupby("year")):
        base = group["revenue"].iloc[0]
        if not base:
            continue
        figure.add_trace(go.Scatter(
            x=group["month_number"], y=(group["revenue"] / base * 100).round(1),
            name=str(year), mode="lines+markers",
            line=dict(color=theme.series_colour(index), width=2),
            marker=dict(size=8),
            hovertemplate="Month %{x}<br>Index %{y:.0f}<extra>" + str(year) + "</extra>",
        ))
    figure.update_xaxes(tickmode="array", tickvals=list(range(1, 13)),
                        ticktext=["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    figure.update_yaxes(title="Index (January = 100)")
    return theme.apply(figure, "Year on year, indexed to each year's January",
                       height=340)


def bridge_chart() -> go.Figure:
    """Waterfall: how the revenue change splits into volume, price and mix."""
    bridge = performance.price_volume_mix(90)
    total = bridge[bridge["category"] == "TOTAL"].iloc[0]
    figure = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "total"],
        x=["Prior 90d", "Volume", "Price", "Mix", "Latest 90d"],
        y=[total["revenue_prior"], total["volume_effect"],
           total["price_effect"], total["mix_effect"], total["revenue_current"]],
        text=[theme.compact_money(v) for v in
              [total["revenue_prior"], total["volume_effect"], total["price_effect"],
               total["mix_effect"], total["revenue_current"]]],
        textposition="outside",
        textfont=dict(color=theme.INK_SECONDARY, size=12),
        # Diverging pair: warm for a decrease, cool for an increase, neutral for
        # the two totals.
        increasing=dict(marker=dict(color=theme.series_colour(0))),
        decreasing=dict(marker=dict(color=theme.STATUS["critical"])),
        totals=dict(marker=dict(color=theme.INK_MUTED)),
        connector=dict(line=dict(color=theme.GRIDLINE, width=1)),
    ))
    figure.update_layout(hovermode="closest")
    return theme.apply(figure, "Revenue bridge - last 90 days vs the 90 before",
                       height=340, legend=False, y_prefix="$")


left, right = st.columns(2)
left.plotly_chart(yoy_chart(), width="stretch")
right.plotly_chart(bridge_chart(), width="stretch")
st.markdown(
    theme.note(
        "Within a category revenue is exactly price x units, so only volume and "
        "price effects exist. <b>Mix</b> appears only at the total, where it "
        "measures revenue moved by customers shifting between categories of "
        "different average price."
    ),
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# Seasonality
# --------------------------------------------------------------------------- #
def weekday_chart() -> go.Figure:
    profile = performance.weekday_profile()
    figure = go.Figure(go.Bar(
        x=profile["weekday"], y=profile["index_vs_average"],
        marker=dict(color=theme.series_colour(0)),
        text=[f"{v:.0f}" for v in profile["index_vs_average"]],
        textposition="outside", textfont=dict(color=theme.INK_SECONDARY, size=12),
        hovertemplate="%{x}<br>%{y:.0f}%% of an average day<extra></extra>",
    ))
    figure.update_traces(marker_cornerradius=4)
    figure.add_hline(y=100, line=dict(color=theme.AXIS, width=1))
    figure.update_layout(hovermode="closest")
    return theme.apply(figure, "Day of week (100 = average day)",
                       height=320, legend=False)


def month_chart() -> go.Figure:
    seasonal = performance.monthly_seasonality()
    figure = go.Figure(go.Bar(
        x=seasonal["month_name"], y=seasonal["seasonal_index"],
        marker=dict(color=theme.series_colour(2)),
        hovertemplate="%{x}<br>%{y:.0f}%% of an average day<extra></extra>",
    ))
    figure.update_traces(marker_cornerradius=4)
    figure.add_hline(y=100, line=dict(color=theme.AXIS, width=1))
    figure.update_layout(hovermode="closest")
    return theme.apply(figure, "Month of year (100 = average day)",
                       height=320, legend=False)


left, right = st.columns(2)
left.plotly_chart(weekday_chart(), width="stretch")
right.plotly_chart(month_chart(), width="stretch")


# --------------------------------------------------------------------------- #
# Products, regions, stores
# --------------------------------------------------------------------------- #
st.subheader("Where the revenue comes from")
tab_products, tab_categories, tab_regions, tab_stores = st.tabs(
    ["Products", "Categories", "Regions", "Stores"]
)

with tab_products:
    products = data.products()
    top = products.nlargest(20, "revenue")
    figure = go.Figure(go.Bar(
        x=top.sort_values("revenue")["revenue"],
        y=top.sort_values("revenue")["product_name"],
        orientation="h", marker=dict(color=theme.series_colour(0)),
        hovertemplate="%{y}<br>%{x:$,.0f}<extra></extra>",
    ))
    figure.update_traces(marker_cornerradius=4)
    figure.update_layout(hovermode="closest")
    figure.update_xaxes(showgrid=True, gridcolor=theme.GRIDLINE, showline=False)
    st.plotly_chart(theme.apply(figure, "Top 20 products by revenue",
                                height=520, legend=False),
                    width="stretch")
    st.dataframe(
        products[["sku", "product_name", "category", "revenue", "gross_profit",
                  "margin_pct", "units_sold", "abc_class", "performance_segment"]]
        .head(200),
        width="stretch", hide_index=True,
    )

with tab_categories:
    subs = data.subcategories()
    figure = go.Figure(go.Treemap(
        labels=subs["subcategory"], parents=subs["category"],
        values=subs["revenue"],
        marker=dict(colors=[theme.series_colour(i) for i in range(len(subs))],
                    line=dict(width=2, color=theme.SURFACE)),
        textinfo="label+value",
        hovertemplate="%{label}<br>%{value:$,.0f}<extra></extra>",
    ))
    st.plotly_chart(theme.apply(figure, "Revenue by category and subcategory",
                                height=480, legend=False),
                    width="stretch")
    st.dataframe(subs, width="stretch", hide_index=True)

with tab_regions:
    regions = data.regions()
    st.dataframe(
        regions[["region_name", "country", "revenue", "gross_profit",
                 "gross_margin_pct", "orders", "customers", "avg_order_value",
                 "revenue_trend_pct", "revenue_share_pct"]],
        width="stretch", hide_index=True,
    )
    local = data.revenue_local()
    st.markdown("**Restated in local currency** (external FX feed)")
    st.dataframe(
        local[["region_name", "currency_code", "revenue_usd", "fx_rate",
               "revenue_local", "fx_rate_date", "fx_source"]],
        width="stretch", hide_index=True,
    )
    st.markdown(
        theme.note(
            "Every converted figure carries the rate and the rate date it used. "
            "A converted number without its rate is unauditable. Rows sourced "
            "from <code>fallback</code> mean the FX endpoint was unreachable and "
            "a deterministic stand-in was used."
        ),
        unsafe_allow_html=True,
    )

with tab_stores:
    stores = data.stores()
    st.dataframe(
        stores[["store_name", "store_type", "city", "country", "revenue",
                "gross_profit", "gross_margin_pct", "orders", "revenue_per_sqm"]],
        width="stretch", hide_index=True,
    )
    st.caption(
        "Revenue per square metre is null for online stores by construction - "
        "dividing by zero floor space would produce an infinite number, and one "
        "nonsense cell is enough to lose trust in a whole dashboard."
    )


# --------------------------------------------------------------------------- #
# Anomalies
# --------------------------------------------------------------------------- #
st.subheader("Anomalous trading days")
anomalies = performance.detect_anomalies()
if anomalies.empty:
    st.info("No day sits beyond 2.5 robust standard deviations of its trend.")
else:
    display = anomalies.tail(20).copy()
    display["order_date"] = pd.to_datetime(display["order_date"]).dt.strftime("%Y-%m-%d")
    st.dataframe(display, width="stretch", hide_index=True)
    st.markdown(
        theme.note(
            "Scored in <b>median absolute deviation</b> units, not standard "
            "deviations. A handful of genuine Black Friday spikes would inflate "
            "sigma enough to hide every ordinary anomaly for the rest of the year."
        ),
        unsafe_allow_html=True,
    )
