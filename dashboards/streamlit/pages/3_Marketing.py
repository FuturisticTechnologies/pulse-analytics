"""Marketing dashboard - what the spend bought."""
from __future__ import annotations

import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from analytics.marketing import attribution              # noqa: E402
from dashboards.streamlit import data_access as data     # noqa: E402
from dashboards.streamlit import theme                   # noqa: E402

st.set_page_config(page_title="PulseAnalytics - Marketing", page_icon="◑", layout="wide")
st.markdown(theme.KPI_CSS, unsafe_allow_html=True)

st.title("Marketing")
if not data.require_warehouse():
    st.stop()

campaigns = data.campaigns()
channels = data.channels()
acquisition = data.acquisition_channels()

spend = float(campaigns["spend"].sum())
revenue = float(campaigns["revenue"].sum())
profit = float(campaigns["gross_profit"].sum())
new_customers = int(campaigns["new_customers"].sum())
profitable = int((campaigns["verdict"] == "Profitable").sum())

tiles = [
    ("Spend", theme.compact_money(spend), None, f"{len(campaigns)} campaigns"),
    ("Attributed revenue", theme.compact_money(revenue), None, "last-touch"),
    ("ROAS", f"{revenue / spend:.2f}x" if spend else "-", None,
     f"profit ROAS {profit / spend:.2f}x" if spend else ""),
    ("Net contribution", theme.compact_money(profit - spend),
     theme.delta_text((profit - spend) / spend * 100 if spend else 0),
     "gross profit minus spend"),
    ("CAC", theme.money(spend / new_customers) if new_customers else "-", None,
     f"{theme.number(new_customers)} new customers"),
    ("Profitable campaigns", f"{profitable} / {len(campaigns)}", None,
     "profit ROAS above 1.0"),
]
for column, (label, value, delta, sub) in zip(st.columns(6), tiles):
    column.markdown(theme.kpi_tile(label, value, delta, sub), unsafe_allow_html=True)
st.write("")

tab_channels, tab_campaigns, tab_attribution, tab_budget = st.tabs(
    ["Channels", "Campaigns", "Attribution models", "Budget"]
)

# --------------------------------------------------------------------------- #
with tab_channels:
    def roas_chart() -> go.Figure:
        """Profit ROAS by channel, with break-even marked.

        One series, one colour. The threshold line - not a colour ramp - carries
        "is this good", so hue stays free and the comparison stays honest.
        """
        frame = channels.sort_values("profit_roas")
        figure = go.Figure(go.Bar(
            x=frame["profit_roas"], y=frame["channel"], orientation="h",
            marker=dict(color=theme.series_colour(0)),
            text=[f"{v:.2f}x" for v in frame["profit_roas"]],
            textposition="outside", textfont=dict(color=theme.INK_SECONDARY, size=12),
            hovertemplate="%{y}<br>profit ROAS %{x:.2f}x<extra></extra>",
        ))
        figure.update_traces(marker_cornerradius=4)
        figure.add_vline(x=1.0, line=dict(color=theme.STATUS["critical"], width=2))
        figure.add_annotation(x=1.0, y=1.04, yref="paper", text="Break-even",
                              showarrow=False, xanchor="left", xshift=6,
                              font=dict(color=theme.STATUS["critical"], size=12))
        figure.update_layout(hovermode="closest")
        figure.update_xaxes(showgrid=True, gridcolor=theme.GRIDLINE, showline=False)
        return theme.apply(figure, "Profit ROAS by marketing channel",
                           height=360, legend=False)

    def spend_revenue_chart() -> go.Figure:
        """Spend against attributed revenue - both dollars, so one axis."""
        frame = channels.sort_values("revenue", ascending=False)
        figure = go.Figure()
        figure.add_trace(go.Bar(
            x=frame["channel"], y=frame["spend"], name="Spend",
            marker=dict(color=theme.series_colour(1)),
            hovertemplate="%{x}<br>%{y:$,.0f}<extra>Spend</extra>",
        ))
        figure.add_trace(go.Bar(
            x=frame["channel"], y=frame["revenue"], name="Attributed revenue",
            marker=dict(color=theme.series_colour(0)),
            hovertemplate="%{x}<br>%{y:$,.0f}<extra>Revenue</extra>",
        ))
        figure.update_traces(marker_cornerradius=4)
        figure.update_layout(barmode="group", bargap=0.30, bargroupgap=0.08)
        return theme.apply(figure, "Spend vs attributed revenue", height=360,
                           y_prefix="$")

    left, right = st.columns(2)
    left.plotly_chart(roas_chart(), width="stretch")
    right.plotly_chart(spend_revenue_chart(), width="stretch")
    st.dataframe(channels, width="stretch", hide_index=True)

    st.subheader("Where customers actually came from")
    st.caption("Acquisition channel is recorded on the customer record, so this "
               "view is independent of campaign attribution.")
    st.dataframe(acquisition, width="stretch", hide_index=True)

# --------------------------------------------------------------------------- #
with tab_campaigns:
    def campaign_scatter() -> go.Figure:
        """Spend against gross profit, one mark per campaign.

        Scatter is an all-pairs form, so it is held to three colours at most -
        here one series, with the break-even diagonal carrying the verdict.
        """
        figure = go.Figure()
        figure.add_trace(go.Scatter(
            x=campaigns["spend"], y=campaigns["gross_profit"],
            mode="markers", name="Campaign",
            marker=dict(size=12, color=theme.series_colour(0),
                        line=dict(width=2, color=theme.SURFACE)),
            customdata=campaigns[["campaign_name", "channel", "profit_roas"]],
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}"
                          "<br>Spend %{x:$,.0f}<br>Profit %{y:$,.0f}"
                          "<br>Profit ROAS %{customdata[2]:.2f}x<extra></extra>",
        ))
        limit = float(max(campaigns["spend"].max(), campaigns["gross_profit"].max()))
        figure.add_trace(go.Scatter(
            x=[0, limit], y=[0, limit], mode="lines", name="Break-even",
            line=dict(color=theme.STATUS["critical"], width=2),
            hoverinfo="skip",
        ))
        figure.update_layout(hovermode="closest")
        figure.update_xaxes(title="Spend", tickprefix="$", showgrid=True,
                            gridcolor=theme.GRIDLINE)
        figure.update_yaxes(title="Gross profit", tickprefix="$")
        return theme.apply(figure, "Campaign profitability - above the line pays "
                                   "for itself", height=420)

    st.plotly_chart(campaign_scatter(), width="stretch")
    st.dataframe(
        campaigns[["campaign_name", "channel", "objective", "start_date", "end_date",
                   "spend", "revenue", "gross_profit", "roas", "profit_roas",
                   "cac", "net_contribution", "verdict"]],
        width="stretch", hide_index=True,
    )

# --------------------------------------------------------------------------- #
with tab_attribution:
    st.subheader("The same revenue, five attribution models")
    with st.spinner("Rebuilding customer journeys from the clickstream..."):
        models = attribution.attribute()

    if models.empty:
        st.info("No converting journeys inside the clickstream lookback window. "
                "Generate a larger dataset to populate this view.")
    else:
        def attribution_chart() -> go.Figure:
            frame = models.head(6)
            model_columns = ["first_touch", "last_touch", "linear",
                             "time_decay", "position_based"]
            labels = ["First touch", "Last touch", "Linear",
                      "Time decay", "Position based"]
            figure = go.Figure()
            for index, (column, label) in enumerate(zip(model_columns, labels)):
                figure.add_trace(go.Bar(
                    x=frame["channel"], y=frame[column], name=label,
                    marker=dict(color=theme.series_colour(index)),
                    hovertemplate="%{x}<br>%{y:$,.0f}<extra>" + label + "</extra>",
                ))
            figure.update_traces(marker_cornerradius=4)
            figure.update_layout(barmode="group", bargap=0.28, bargroupgap=0.06)
            return theme.apply(figure, "Revenue credited to each channel, by model",
                               height=400, y_prefix="$")

        st.plotly_chart(attribution_chart(), width="stretch")
        st.dataframe(models, width="stretch", hide_index=True)
        st.markdown(
            theme.note(
                "No attribution model is correct. The <b>spread between them</b> "
                "is the finding: a channel with a large positive "
                "<code>upper_funnel_bias</code> is under-credited by last touch, "
                "and a last-touch budget will starve it. The warehouse ships "
                "last touch because that is what the source system records."
            ),
            unsafe_allow_html=True,
        )

# --------------------------------------------------------------------------- #
with tab_budget:
    st.subheader("Suggested reallocation")
    reallocation = attribution.budget_reallocation()

    def reallocation_chart() -> go.Figure:
        frame = reallocation.sort_values("recommended_change")
        figure = go.Figure(go.Bar(
            x=frame["recommended_change"], y=frame["channel"], orientation="h",
            marker=dict(color=[theme.series_colour(0) if v > 0
                               else theme.STATUS["critical"]
                               for v in frame["recommended_change"]]),
            text=[theme.compact_money(v) for v in frame["recommended_change"]],
            textposition="outside", textfont=dict(color=theme.INK_SECONDARY, size=12),
            hovertemplate="%{y}<br>%{x:$,.0f}<extra></extra>",
        ))
        figure.update_traces(marker_cornerradius=4)
        figure.add_vline(x=0, line=dict(color=theme.AXIS, width=1))
        figure.update_layout(hovermode="closest")
        figure.update_xaxes(showgrid=True, gridcolor=theme.GRIDLINE, showline=False)
        return theme.apply(figure, "Recommended spend change by channel",
                           height=340, legend=False)

    left, right = st.columns([2, 3])
    right.plotly_chart(reallocation_chart(), width="stretch")
    left.dataframe(reallocation, width="stretch", hide_index=True, height=340)

    projected = float(reallocation["projected_profit_change"].sum())
    left.markdown(theme.kpi_tile(
        "Projected profit change", theme.compact_money(projected), None,
        "if receiving channels hold their efficiency",
    ), unsafe_allow_html=True)

    st.markdown(
        theme.note(
            "Takes 25% of the spend on channels below profit break-even and "
            "moves it to those above, weighted by profit ROAS. The projection "
            "assumes the receiving channel holds its <b>current marginal</b> "
            "efficiency - the assumption that will break first, because "
            "channels saturate. Treat it as a direction, not a forecast."
        ),
        unsafe_allow_html=True,
    )
