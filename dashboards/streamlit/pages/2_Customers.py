"""Customer dashboard - who they are, what they are worth, who is leaving."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from analytics.customer import churn, clv, segmentation   # noqa: E402
from dashboards.streamlit import data_access as data      # noqa: E402
from dashboards.streamlit import theme                    # noqa: E402

st.set_page_config(page_title="PulseAnalytics - Customers", page_icon="◑", layout="wide")
st.markdown(theme.KPI_CSS, unsafe_allow_html=True)

st.title("Customers")
if not data.require_warehouse():
    st.stop()

customers = data.customers()
buyers = customers[customers["orders"] > 0]
kpis = data.executive_kpis()

tiles = [
    ("Customers", theme.number(len(customers)), None,
     f"{theme.number(len(buyers))} have purchased"),
    ("Repeat rate", theme.percent(kpis["repeat_rate_pct"]), None,
     f"{theme.number(kpis['repeat_customers'])} repeat buyers"),
    ("Average lifetime value", theme.money(kpis["avg_lifetime_revenue"]), None,
     "revenue per purchasing customer"),
    ("Active", theme.number(kpis["active_customers_total"]), None,
     "ordered in the last 90 days"),
    ("At risk", theme.number(kpis["at_risk_customers"]), None,
     "91-180 days since last order"),
    ("Churned", theme.number(kpis["churned_customers"]), None,
     theme.percent(kpis["churn_rate_pct"]) + " of purchasers"),
]
for column, (label, value, delta, sub) in zip(st.columns(6), tiles):
    column.markdown(theme.kpi_tile(label, value, delta, sub), unsafe_allow_html=True)
st.write("")

tab_segments, tab_cohorts, tab_value, tab_churn = st.tabs(
    ["Segments", "Cohorts & retention", "Lifetime value", "Churn risk"]
)

# --------------------------------------------------------------------------- #
# Segments
# --------------------------------------------------------------------------- #
with tab_segments:
    st.subheader("RFM segments")
    rfm = data.rfm_summary()

    def segment_chart() -> go.Figure:
        """Customers and revenue per segment, on ONE axis, indexed to share.

        Customer count and dollars have different units. Rather than a
        dual-axis chart - which would invent a relationship between them -
        both are expressed as a share of their own total, which is the
        comparison the reader actually wants: "this segment is 8% of people
        and 46% of money".
        """
        frame = rfm.sort_values("revenue_share_pct")
        figure = go.Figure()
        figure.add_trace(go.Bar(
            y=frame["rfm_segment"], x=frame["customer_share_pct"], orientation="h",
            name="Share of customers", marker=dict(color=theme.series_colour(0)),
            hovertemplate="%{y}<br>%{x:.1f}% of customers<extra></extra>",
        ))
        figure.add_trace(go.Bar(
            y=frame["rfm_segment"], x=frame["revenue_share_pct"], orientation="h",
            name="Share of revenue", marker=dict(color=theme.series_colour(1)),
            hovertemplate="%{y}<br>%{x:.1f}% of revenue<extra></extra>",
        ))
        figure.update_traces(marker_cornerradius=4)
        # 2px surface gap between adjacent bars, never a border around them.
        figure.update_layout(barmode="group", bargap=0.30, bargroupgap=0.08,
                             hovermode="closest")
        figure.update_xaxes(showgrid=True, gridcolor=theme.GRIDLINE,
                            showline=False, ticksuffix="%")
        return theme.apply(figure, "Segment share of customers vs share of revenue",
                           height=460)

    left, right = st.columns([3, 2])
    left.plotly_chart(segment_chart(), width="stretch")
    right.dataframe(
        rfm[["rfm_segment", "customers", "avg_orders", "avg_lifetime_revenue",
             "revenue_share_pct", "priority"]],
        width="stretch", hide_index=True, height=460,
    )
    st.markdown(
        theme.note(
            "Segments come from quintile RFM scoring in "
            "<code>gold.mart_rfm_segments</code>. Quintiles rather than fixed "
            "thresholds, because absolute cut-offs stop being meaningful the "
            "moment the business grows."
        ),
        unsafe_allow_html=True,
    )

    st.subheader("Behavioural clusters (k-means)")
    with st.spinner("Fitting k-means..."):
        try:
            result = segmentation.segment_customers(k=5)
            profile = result["profile"]
            st.dataframe(
                profile[["segment_name", "customers", "customer_share_pct",
                         "revenue_share_pct", "avg_recency_days", "avg_orders",
                         "avg_lifetime_revenue", "churned_pct"]],
                width="stretch", hide_index=True,
            )
            st.markdown("**Where k-means and RFM disagree**")
            st.dataframe(segmentation.compare_with_rfm(result["customers"]),
                         width="stretch", hide_index=True)
            st.caption(
                "Where the two agree, confidence is high. The off-diagonal cells "
                "are where the interesting customers are - a rule-based grid and "
                "a distance-based clustering disagreeing about someone is a "
                "signal, not an error."
            )
        except Exception as exc:
            st.error(f"Clustering failed: {exc}")

# --------------------------------------------------------------------------- #
# Cohorts
# --------------------------------------------------------------------------- #
with tab_cohorts:
    cohorts = data.cohorts()
    st.subheader("Monthly cohort retention")

    def cohort_heatmap() -> go.Figure:
        """Sequential single-hue ramp: one hue, light to dark.

        A rainbow here would force the reader to decode a legend to answer
        "is this bigger", which is the one question a heatmap must answer at a
        glance.
        """
        grid = cohorts.pivot_table(
            index="cohort_month", columns="months_since",
            values="retention_pct", aggfunc="max",
        ).sort_index()
        figure = go.Figure(go.Heatmap(
            z=grid.to_numpy(),
            x=[f"M{c}" for c in grid.columns],
            y=[d.strftime("%b %Y") for d in grid.index],
            colorscale=[[i / (len(theme.SEQUENTIAL_BLUE) - 1), c]
                        for i, c in enumerate(theme.SEQUENTIAL_BLUE)],
            zmin=0, zmax=float(np.nanmax(grid.to_numpy())) if grid.size else 100,
            xgap=2, ygap=2,      # surface gap between cells, not a border
            colorbar=dict(title="Retained %", thickness=12, outlinewidth=0,
                          tickfont=dict(color=theme.INK_MUTED, size=11)),
            hovertemplate="Cohort %{y}<br>%{x}<br>%{z:.1f}% retained<extra></extra>",
        ))
        figure.update_layout(hovermode="closest")
        figure.update_yaxes(autorange="reversed")
        return theme.apply(figure, "Retention by acquisition cohort",
                           height=520, legend=False)

    st.plotly_chart(cohort_heatmap(), width="stretch")
    st.markdown(
        theme.note(
            "A cohort is the month of a customer's <b>first completed order</b>, "
            "not their signup month. A signup that never bought is an activation "
            "problem, not a retention one, and mixing the two is the most common "
            "way this chart lies."
        ),
        unsafe_allow_html=True,
    )

    st.subheader("Cumulative value per acquired customer")

    def ltv_curves() -> go.Figure:
        recent = sorted(cohorts["cohort_month"].unique())[-6:]
        figure = go.Figure()
        for index, month in enumerate(recent):
            group = cohorts[cohorts["cohort_month"] == month].sort_values("months_since")
            figure.add_trace(go.Scatter(
                x=group["months_since"], y=group["cumulative_ltv"],
                name=pd.Timestamp(month).strftime("%b %Y"),
                mode="lines+markers",
                line=dict(color=theme.series_colour(index), width=2),
                marker=dict(size=8),
                hovertemplate="M%{x}<br>%{y:$,.0f}<extra>"
                              + pd.Timestamp(month).strftime("%b %Y") + "</extra>",
            ))
        figure.update_xaxes(title="Months since first order")
        return theme.apply(figure, "Cumulative LTV curve, last six cohorts",
                           height=380, y_prefix="$")

    left, right = st.columns([3, 2])
    left.plotly_chart(ltv_curves(), width="stretch")
    right.dataframe(
        data.retention_summary()[[
            "cohort_month", "cohort_customers", "m1_retention_pct",
            "m3_retention_pct", "m6_retention_pct", "ltv_to_date",
        ]].tail(14),
        width="stretch", hide_index=True, height=380,
    )

    st.subheader("Monthly churn and retention")
    churn_monthly = data.churn_monthly()
    figure = go.Figure()
    figure.add_trace(go.Scatter(
        x=churn_monthly["activity_month"], y=churn_monthly["retention_rate_pct"],
        name="Retention rate", mode="lines+markers",
        line=dict(color=theme.series_colour(0), width=2), marker=dict(size=8),
        hovertemplate="%{y:.1f}%<extra>Retained</extra>",
    ))
    figure.add_trace(go.Scatter(
        x=churn_monthly["activity_month"], y=churn_monthly["churn_rate_pct"],
        name="Churn rate", mode="lines+markers",
        line=dict(color=theme.STATUS["critical"], width=2), marker=dict(size=8),
        hovertemplate="%{y:.1f}%<extra>Churned</extra>",
    ))
    figure.update_yaxes(ticksuffix="%")
    st.plotly_chart(theme.apply(figure, "Month-over-month customer flow", height=340),
                    width="stretch")

# --------------------------------------------------------------------------- #
# Lifetime value
# --------------------------------------------------------------------------- #
with tab_value:
    with st.spinner("Computing lifetime value..."):
        scored = clv.compute_clv()
        ratios = clv.ltv_to_cac(scored)

    left, right = st.columns(2)

    decile = (scored.groupby("clv_decile", observed=False)["total_clv"]
              .sum().reset_index())
    figure = go.Figure(go.Bar(
        x=decile["clv_decile"].astype(str), y=decile["total_clv"],
        marker=dict(color=theme.series_colour(0)),
        hovertemplate="%{x}<br>%{y:$,.0f}<extra></extra>",
    ))
    figure.update_traces(marker_cornerradius=4)
    figure.update_layout(hovermode="closest")
    left.plotly_chart(
        theme.apply(figure, "Total CLV by decile (D10 = most valuable)",
                    height=340, legend=False, y_prefix="$"),
        width="stretch",
    )

    channel = clv.clv_by_segment(scored).sort_values("avg_total_clv")
    figure = go.Figure(go.Bar(
        x=channel["avg_total_clv"], y=channel["acquisition_channel"],
        orientation="h", marker=dict(color=theme.series_colour(2)),
        text=[theme.money(v) for v in channel["avg_total_clv"]],
        textposition="outside", textfont=dict(color=theme.INK_SECONDARY, size=12),
        hovertemplate="%{y}<br>%{x:$,.0f}<extra></extra>",
    ))
    figure.update_traces(marker_cornerradius=4)
    figure.update_layout(hovermode="closest")
    figure.update_xaxes(showgrid=True, gridcolor=theme.GRIDLINE, showline=False)
    right.plotly_chart(
        theme.apply(figure, "Average CLV by acquisition channel", height=340,
                    legend=False),
        width="stretch",
    )

    st.subheader("LTV : CAC by acquisition channel")
    st.dataframe(ratios, width="stretch", hide_index=True)
    st.markdown(
        theme.note(
            "Below 1.0 the channel destroys value; 3.0 or better is healthy. "
            "Channels with no measured campaign spend show a blank ratio rather "
            "than an infinite one. Predicted CLV assumes the observed monthly "
            "retention rate holds - the assumption most likely to be wrong first."
        ),
        unsafe_allow_html=True,
    )
    st.dataframe(
        scored[["customer_id", "full_name", "loyalty_tier", "orders",
                "lifetime_revenue", "historic_clv", "predicted_clv", "total_clv"]]
        .head(200),
        width="stretch", hide_index=True,
    )

# --------------------------------------------------------------------------- #
# Churn risk
# --------------------------------------------------------------------------- #
with tab_churn:
    with st.spinner("Fitting the churn model..."):
        try:
            model = churn.fit_churn_model()
            risk = churn.score_current_customers(model)
            bands = churn.risk_summary(risk)
        except Exception as exc:
            st.error(f"Churn model failed: {exc}")
            st.stop()

    metrics = model["metrics"].iloc[0]
    left, right = st.columns([2, 3])
    left.markdown(theme.kpi_tile(
        "Holdout AUC", f"{metrics['holdout_auc']:.3f}", None,
        f"trained on a snapshot {int(metrics['observation_window_days'])} days back",
    ), unsafe_allow_html=True)

    coefficients = model["coefficients"].sort_values("coefficient")
    figure = go.Figure(go.Bar(
        x=coefficients["coefficient"], y=coefficients["feature"], orientation="h",
        # Diverging: two opposite hues with the zero line as the neutral midpoint.
        marker=dict(color=[theme.STATUS["critical"] if v > 0 else theme.series_colour(0)
                           for v in coefficients["coefficient"]]),
        hovertemplate="%{y}<br>%{x:.3f}<extra></extra>",
    ))
    figure.update_traces(marker_cornerradius=4)
    figure.update_layout(hovermode="closest")
    figure.add_vline(x=0, line=dict(color=theme.AXIS, width=1))
    figure.update_xaxes(showgrid=True, gridcolor=theme.GRIDLINE, showline=False,
                        title="Standardised coefficient")
    right.plotly_chart(
        theme.apply(figure, "What drives churn (right = raises risk)",
                    height=340, legend=False),
        width="stretch",
    )

    st.markdown(
        theme.note(
            "Features are computed from a snapshot taken 90 days before the "
            "analysis date and labelled by what happened next, so nothing the "
            "model sees was unknowable at prediction time. Training on today's "
            "features against today's label leaks the future and yields a "
            "beautiful AUC with no predictive value."
        ),
        unsafe_allow_html=True,
    )

    st.subheader("Risk bands")
    st.dataframe(bands, width="stretch", hide_index=True)

    st.subheader("Retention call list")
    st.caption("Ordered by projected annual value multiplied by churn probability "
               "- what the customer is worth times how likely we are to lose them.")
    st.dataframe(
        risk[["customer_id", "full_name", "loyalty_tier", "recency_days", "orders",
              "lifetime_revenue", "projected_annual_value", "churn_probability",
              "risk_band", "revenue_at_risk"]].head(100),
        width="stretch", hide_index=True,
    )
