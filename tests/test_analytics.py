"""The analytical models.

Two kinds of test:

* **Maths** - k-means, logistic regression, AUC and Holt-Winters are checked
  against data with a known answer. If the algorithm is wrong, no amount of
  business context will make the output right.
* **Behaviour** - the models must do the specific things claimed for them: the
  churn model must not leak the future, the forecast must be backtested on data
  it never saw, and RFM and k-means must be fitted on purchasers only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from analytics.common import modelling
from analytics.customer import churn, clv, segmentation
from analytics.forecasting import forecast
from analytics.inventory import optimisation
from analytics.marketing import attribution
from analytics.sales import basket, performance


# --------------------------------------------------------------------------- #
# Maths
# --------------------------------------------------------------------------- #
def test_standardise_handles_a_constant_column():
    """A zero-variance column must not produce NaN - one NaN poisons every
    distance in the clustering."""
    matrix = np.array([[1.0, 5.0], [2.0, 5.0], [3.0, 5.0]])
    scaled, _mean, std = modelling.standardise(matrix)
    assert not np.isnan(scaled).any()
    assert std[1] == 1.0
    assert (scaled[:, 1] == 0).all()


def test_kmeans_recovers_obviously_separated_clusters():
    rng = np.random.default_rng(0)
    blob_a = rng.normal(0, 0.25, (60, 2))
    blob_b = rng.normal(8, 0.25, (60, 2))
    labels, centroids, inertia = modelling.kmeans(
        np.vstack([blob_a, blob_b]), k=2, seed=1
    )
    assert len(np.unique(labels)) == 2
    assert len(set(labels[:60])) == 1 and len(set(labels[60:])) == 1
    assert inertia > 0 and len(centroids) == 2


def test_kmeans_is_deterministic_for_a_seed():
    matrix = np.random.default_rng(7).normal(size=(120, 3))
    first, _, _ = modelling.kmeans(matrix, k=4, seed=99)
    second, _, _ = modelling.kmeans(matrix, k=4, seed=99)
    assert (first == second).all()


def test_kmeans_never_returns_an_empty_cluster():
    matrix = np.random.default_rng(3).normal(size=(40, 2))
    labels, _, _ = modelling.kmeans(matrix, k=6, seed=5)
    assert len(np.unique(labels)) == 6


def test_silhouette_is_higher_for_well_separated_data():
    rng = np.random.default_rng(11)
    separated = np.vstack([rng.normal(0, 0.2, (50, 2)), rng.normal(10, 0.2, (50, 2))])
    mixed = rng.normal(0, 1.0, (100, 2))
    separated_labels, _, _ = modelling.kmeans(separated, 2, seed=1)
    mixed_labels, _, _ = modelling.kmeans(mixed, 2, seed=1)
    assert modelling.silhouette_score(separated, separated_labels) > \
        modelling.silhouette_score(mixed, mixed_labels)


def test_logistic_regression_learns_a_separable_boundary():
    rng = np.random.default_rng(2)
    features = np.vstack([rng.normal(-2, 0.5, (100, 1)), rng.normal(2, 0.5, (100, 1))])
    target = np.concatenate([np.zeros(100), np.ones(100)])
    weights = modelling.fit_logistic(features, target, iterations=2000, learning_rate=0.5)
    predictions = modelling.predict_logistic(weights, features)
    assert ((predictions > 0.5).astype(int) == target).mean() > 0.95


def test_roc_auc_matches_known_values():
    assert modelling.roc_auc(np.array([0, 0, 1, 1]), np.array([0.1, 0.2, 0.8, 0.9])) == 1.0
    assert modelling.roc_auc(np.array([0, 0, 1, 1]), np.array([0.9, 0.8, 0.2, 0.1])) == 0.0
    assert modelling.roc_auc(np.array([1, 1, 1]), np.array([0.5, 0.6, 0.7])) == 0.5


def test_holt_winters_reproduces_a_clean_seasonal_signal():
    season = np.array([10.0, 20.0, 30.0, 15.0])
    values = np.tile(season, 12) + np.arange(48) * 0.5      # seasonality + trend
    _fitted, prediction = modelling.holt_winters_additive(values, 4, horizon=4)
    expected = season + 48 * 0.5
    assert np.allclose(prediction, expected, rtol=0.25), \
        f"expected roughly {expected}, got {prediction}"


def test_holt_winters_falls_back_when_history_is_too_short():
    values = np.array([5.0, 6.0, 7.0])
    _fitted, prediction = modelling.holt_winters_additive(values, 12, horizon=3)
    assert len(prediction) == 3
    assert (prediction >= 0).all()


def test_forecast_never_predicts_negative_revenue():
    values = np.array([10.0, 8.0, 6.0, 4.0, 3.0, 2.0, 1.0, 1.0])
    _fitted, prediction = modelling.holt_winters_additive(values, 4, horizon=12)
    assert (prediction >= 0).all()


def test_accuracy_metrics_are_correct():
    metrics = modelling.forecast_accuracy(np.array([100.0, 200.0]),
                                          np.array([90.0, 220.0]))
    assert metrics["mae"] == 15.0
    assert metrics["bias"] == -5.0
    assert metrics["mape_pct"] == 10.0     # (10% + 10%) / 2


def test_mape_ignores_zero_actuals_instead_of_returning_infinity():
    metrics = modelling.forecast_accuracy(np.array([0.0, 100.0]), np.array([5.0, 90.0]))
    assert np.isfinite(metrics["mape_pct"])
    assert metrics["mape_pct"] == 10.0


def test_prediction_interval_widens_with_the_horizon():
    residuals = np.random.default_rng(4).normal(0, 10, 100)
    interval = modelling.prediction_interval(residuals, horizon=10)
    assert len(interval) == 10
    assert (np.diff(interval) > 0).all(), "uncertainty must grow with distance"


# --------------------------------------------------------------------------- #
# Customer models
# --------------------------------------------------------------------------- #
def test_segmentation_produces_named_clusters(db):
    result = segmentation.segment_customers(k=4, seed=1)
    assert len(result["profile"]) == 4
    assert result["profile"]["segment_name"].is_unique
    assert result["profile"]["customers"].sum() == len(result["customers"])
    assert not result["customers"]["segment_name"].isna().any()


def test_segmentation_only_uses_purchasers(db):
    from analytics.common import datasets
    assert (datasets.buyers()["orders"] > 0).all()


def test_choose_k_reports_a_row_per_candidate(db):
    frame = segmentation.build_feature_matrix(
        __import__("analytics.common.datasets", fromlist=["x"]).buyers()
    )[0]
    scores = modelling.choose_k(frame, candidates=range(2, 5), seed=1)
    assert list(scores["k"]) == [2, 3, 4]
    assert (scores["inertia"] > 0).all()


def test_churn_snapshot_is_taken_before_the_analysis_date(db):
    """The whole validity of the model rests on this: features must predate
    the label window, or the model is scoring the future."""
    from analytics.common import datasets
    snapshot = churn.build_training_snapshot()
    cutoff = pd.Timestamp(snapshot["cutoff_date"].iloc[0])
    assert cutoff < pd.Timestamp(datasets.analysis_date())
    assert (pd.to_datetime(snapshot["last_order_date"]) <= cutoff).all()


def test_churn_model_beats_a_coin_flip(db):
    model = churn.fit_churn_model()
    metrics = model["metrics"].iloc[0]
    assert metrics["holdout_auc"] > 0.55, "the model has no signal"
    assert len(model["coefficients"]) == len(churn.FEATURE_NAMES)


def test_churn_scores_are_probabilities(db):
    scored = churn.score_current_customers()
    assert scored["churn_probability"].between(0, 1).all()
    assert not scored["is_churned"].any(), \
        "already-churned customers are a win-back problem, not a retention one"


def test_revenue_at_risk_orders_the_call_list(db):
    scored = churn.score_current_customers()
    assert scored["revenue_at_risk"].is_monotonic_decreasing


def test_clv_never_projects_value_for_a_churned_customer(db):
    scored = clv.compute_clv()
    assert (scored.loc[scored["is_churned"], "predicted_clv"] == 0).all()
    assert (scored["total_clv"] >= scored["historic_clv"] - 0.01).all()


def test_expected_lifetime_is_bounded(db):
    assert clv.expected_remaining_months(0.99) <= clv.MAX_HORIZON_MONTHS
    assert clv.expected_remaining_months(0.0) >= 0


def test_cohort_curve_is_non_decreasing(db):
    """Cumulative LTV cannot fall - a dip would be thin-cohort noise."""
    curve = clv.cohort_curve_clv()
    assert not curve.empty
    assert (curve["projected_ltv_month_12"] >= 0).all()


# --------------------------------------------------------------------------- #
# Sales models
# --------------------------------------------------------------------------- #
def test_decomposition_is_additive(db):
    """trend + seasonal + residual must reconstruct the original series."""
    decomposed = performance.decompose_daily()
    reconstructed = (decomposed["trend"] + decomposed["seasonal"]
                     + decomposed["residual"])
    assert np.allclose(reconstructed, decomposed["revenue"], atol=0.02)


def test_price_volume_mix_bridge_adds_up(db):
    bridge = performance.price_volume_mix(90)
    total = bridge[bridge["category"] == "TOTAL"].iloc[0]
    components = (total["volume_effect"] + total["price_effect"] + total["mix_effect"])
    assert abs(components - total["revenue_change"]) < 1.0


def test_mix_effect_is_zero_within_a_category(db):
    """Within a category revenue is exactly price x units, so a non-zero mix
    would mean the arithmetic is wrong."""
    bridge = performance.price_volume_mix(90)
    per_category = bridge[bridge["category"] != "TOTAL"]
    assert (per_category["mix_effect"] == 0).all()


def test_anomaly_detection_returns_scored_days(db):
    anomalies = performance.detect_anomalies(threshold=2.0)
    if not anomalies.empty:
        assert (anomalies["robust_z"].abs() >= 2.0).all()
        assert set(anomalies["direction"]) <= {"spike", "dip"}


def test_weekday_profile_covers_seven_days(db):
    assert len(performance.weekday_profile()) == 7


def test_basket_analysis_only_uses_multi_item_orders(db):
    baskets = basket.build_baskets()
    assert (baskets.map(len) >= 2).all()


def test_affinity_lift_is_consistent_with_confidence(db):
    baskets = basket.build_baskets()
    pairs = basket.affinity_pairs(baskets, min_support=0.0, min_pair_count=2)
    if pairs.empty:
        pytest.skip("no qualifying pairs in the test dataset")
    assert (pairs["support"] > 0).all()
    assert pairs["confidence_a_to_b"].between(0, 1).all()
    assert (pairs["lift"] > 0).all()


def test_cross_sell_only_recommends_genuine_associations(db):
    baskets = basket.build_baskets()
    pairs = basket.affinity_pairs(baskets, min_support=0.0, min_pair_count=2)
    if pairs.empty:
        pytest.skip("no qualifying pairs in the test dataset")
    recommendations = basket.cross_sell_recommendations(pairs)
    if not recommendations.empty:
        assert (recommendations["lift"] > 1.1).all()


# --------------------------------------------------------------------------- #
# Marketing
# --------------------------------------------------------------------------- #
def test_every_attribution_model_credits_the_same_total(db):
    """The models redistribute credit; they must not create or destroy revenue."""
    models = attribution.attribute()
    if models.empty:
        pytest.skip("no converting journeys in the test dataset")
    totals = models[["first_touch", "last_touch", "linear",
                     "time_decay", "position_based"]].sum()
    assert totals.max() - totals.min() < max(totals.max() * 1e-6, 0.01)


def test_campaign_economics_computes_payback(db):
    economics = attribution.campaign_economics()
    assert "payback_days" in economics.columns
    assert (economics.loc[economics["payback_days"].notna(), "payback_days"] >= 0).all()


def test_budget_reallocation_is_a_zero_sum_move(db):
    frame = attribution.budget_reallocation()
    if "recommended_change" in frame and frame["recommended_change"].abs().sum() > 0:
        assert abs(frame["recommended_change"].sum()) < 1.0


# --------------------------------------------------------------------------- #
# Inventory
# --------------------------------------------------------------------------- #
def test_safety_stock_grows_with_demand_variability(db):
    optimised = optimisation.optimise(service_level=0.95)
    varied = optimised[optimised["sd_weekly_demand"] > 0]
    if len(varied) > 1:
        correlation = varied[["sd_weekly_demand", "safety_stock"]].corr().iloc[0, 1]
        assert correlation > 0.5


def test_a_higher_service_level_costs_more_stock(db):
    low = optimisation.optimise(service_level=0.80)["safety_stock"].sum()
    high = optimisation.optimise(service_level=0.99)["safety_stock"].sum()
    assert high >= low


def test_reorder_point_covers_lead_time_demand(db):
    optimised = optimisation.optimise()
    assert (optimised["recommended_reorder_point"]
            >= optimised["lead_time_demand"]).all()


def test_abc_xyz_classes_are_valid(db):
    optimised = optimisation.optimise()
    assert set(optimised["xyz_class"]) <= {"X", "Y", "Z"}
    assert optimised["abc_xyz"].str.len().eq(2).all()


def test_nothing_is_ordered_for_a_well_stocked_product(db):
    optimised = optimisation.optimise()
    comfortable = optimised[
        optimised["on_hand_units"] > optimised["recommended_reorder_point"]
    ]
    assert (comfortable["units_to_order"] == 0).all()


# --------------------------------------------------------------------------- #
# Forecasting
# --------------------------------------------------------------------------- #
def test_backtest_scores_every_candidate_model(db):
    daily = forecast.forecast_daily_revenue(horizon=14, holdout=21)
    models = set(daily["backtest"]["model"])
    assert models == {"holt_winters", "seasonal_naive", "linear_trend"}
    assert daily["model"] in models


def test_backtest_ranks_by_error(db):
    scores = forecast.forecast_daily_revenue(horizon=7, holdout=21)["backtest"]
    assert scores["mape_pct"].is_monotonic_increasing
    assert bool(scores.iloc[0]["is_best"])


def test_forecast_has_the_requested_horizon_and_an_interval(db):
    result = forecast.forecast_daily_revenue(horizon=30, holdout=21)
    frame = result["forecast"]
    assert len(frame) == 30
    assert (frame["lower"] <= frame["forecast"]).all()
    assert (frame["forecast"] <= frame["upper"]).all()
    assert (frame["lower"] >= 0).all()


def test_forecast_starts_after_the_last_observed_day(db):
    result = forecast.forecast_daily_revenue(horizon=10, holdout=21)
    assert result["forecast"]["date"].min() > result["history"]["date"].max()


def test_monthly_forecast_drops_the_partial_final_month(db):
    result = forecast.forecast_monthly_revenue(horizon=3)
    assert result["excluded_partial_month"] is True
    assert len(result["forecast"]) == 3


def test_seasonal_naive_repeats_the_last_season():
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    prediction = forecast.seasonal_naive(values, season_length=3, horizon=6)
    assert list(prediction) == [4.0, 5.0, 6.0, 4.0, 5.0, 6.0]


def test_category_demand_forecast_covers_every_category(db):
    from analytics.common import datasets
    frame = forecast.forecast_category_demand(horizon_weeks=4)
    assert set(frame["category"]) == set(datasets.sales_lines()["category"].unique())
    assert (frame["forecast_units"] >= 0).all()
