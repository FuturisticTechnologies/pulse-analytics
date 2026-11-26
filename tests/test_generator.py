"""The generator's contract.

If the dataset is not internally consistent, every downstream test is testing
the wrong thing. These assertions are the ones the rest of the suite relies on.
"""
from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture(scope="module")
def tables(raw_dir):
    return {
        name: pd.read_csv(raw_dir / f"{name}.csv")
        for name in ["regions", "stores", "products", "customers", "campaigns",
                     "orders", "order_items", "payments", "inventory_snapshots",
                     "customer_events"]
    }


def test_every_table_is_written(raw_dir, tables):
    assert (raw_dir / "_manifest.json").exists()
    for name, frame in tables.items():
        assert not frame.empty, f"{name} is empty"


def test_generation_is_deterministic(tmp_path, generator_module):
    """Same seed, same bytes. Without this, nothing else is reproducible -
    not a test, not a dashboard screenshot, not a reported KPI."""
    first, second = tmp_path / "a", tmp_path / "b"
    args = ["--seed", "99", "--customers", "60", "--products", "12",
            "--orders", "200", "--events", "300", "--campaigns", "3"]
    generator_module.main(args + ["--output", str(first)])
    generator_module.main(args + ["--output", str(second)])

    for name in ["orders", "order_items", "customers", "payments"]:
        left = (first / f"{name}.csv").read_text(encoding="utf-8")
        right = (second / f"{name}.csv").read_text(encoding="utf-8")
        assert left == right, f"{name}.csv differs between two identical runs"


def test_orders_reference_real_customers_and_stores(tables):
    orders = tables["orders"]
    assert orders["customer_id"].isin(tables["customers"]["customer_id"]).all()
    assert orders["store_id"].isin(tables["stores"]["store_id"]).all()


def test_order_items_reference_real_orders_and_products(tables):
    items = tables["order_items"]
    assert items["order_id"].isin(tables["orders"]["order_id"]).all()
    assert items["product_id"].isin(tables["products"]["product_id"]).all()


def test_payments_reference_real_orders(tables):
    assert tables["payments"]["order_id"].isin(tables["orders"]["order_id"]).all()


def test_no_order_predates_its_customer(tables):
    orders = tables["orders"].merge(
        tables["customers"][["customer_id", "signup_date"]], on="customer_id"
    )
    order_date = pd.to_datetime(orders["order_date"])
    signup = pd.to_datetime(orders["signup_date"])
    assert (order_date >= signup).all()


def test_no_product_sold_before_launch(tables):
    merged = (
        tables["order_items"]
        .merge(tables["orders"][["order_id", "order_date"]], on="order_id")
        .merge(tables["products"][["product_id", "launch_date"]], on="product_id")
    )
    assert (pd.to_datetime(merged["order_date"])
            >= pd.to_datetime(merged["launch_date"])).all()


def test_products_are_never_priced_below_cost(tables):
    products = tables["products"]
    assert (products["unit_cost"] < products["unit_price"]).all()


def test_two_full_years_of_history(tables):
    dates = pd.to_datetime(tables["orders"]["order_date"])
    assert (dates.max() - dates.min()).days >= 700


def test_data_quality_defects_are_actually_injected(tables):
    """The dirty data has to really be there, or the quality layer is theatre."""
    assert tables["customers"]["email"].isna().any(), "no missing emails injected"
    assert (tables["order_items"]["quantity"] < 0).any(), "no negative quantities"
    assert tables["orders"]["order_id"].duplicated().any(), "no duplicate orders"
    orphans = ~tables["customer_events"]["customer_id"].isin(
        tables["customers"]["customer_id"]
    )
    assert orphans.any(), "no orphan events injected"
    messy = tables["customers"]["loyalty_tier"].dropna()
    assert (messy != messy.str.strip()).any(), "no whitespace noise in loyalty_tier"


def test_inventory_is_simulated_against_real_demand(tables):
    """Stock must respond to sales, or the whole inventory layer is vacuous."""
    inventory = tables["inventory_snapshots"]
    assert inventory["is_stockout"].any(), "a two-year run with no stockout at all"
    assert (inventory["on_hand_units"] <= inventory["reorder_point"]).any(), \
        "no product ever crosses its reorder point"
    # Reorder points must be in the same order of magnitude as weekly demand.
    busy = inventory[inventory["units_sold"] > 0]
    assert busy["reorder_point"].median() < busy["units_sold"].max() * 20


def test_campaign_spend_scales_with_the_business(tables):
    """Absolute budgets would make ROAS nonsense at any other dataset size."""
    campaigns = tables["campaigns"]
    orders = tables["orders"]
    revenue = orders.loc[orders["status"] == "completed", "net_amount"].sum()
    spend = campaigns["spend"].sum()
    assert 0.02 < spend / revenue < 0.25, (
        f"marketing spend is {spend / revenue:.1%} of revenue - implausible"
    )


def test_attribution_coverage_is_capped_at_the_target(tables, generator_module):
    """Attribution coverage is held AT OR BELOW a fixed share of orders.

    Campaign windows overlap far more at larger presets, so an uncapped
    per-campaign probability sends coverage - and with it ROAS, CAC and the
    channel mix - swinging from 15% to 90% between dataset sizes.

    The cap is one-sided on purpose. A calendar with too few campaigns to reach
    the target simply cannot, and forcing it would mean inventing attributions
    for orders that fall in no campaign window at all. Under-shooting is honest;
    over-shooting is the bug this guards against.
    """
    orders = tables["orders"]
    completed = orders[orders["status"] == "completed"]
    coverage = completed["campaign_id"].notna().mean()
    target = generator_module.TARGET_ATTRIBUTION_SHARE

    assert coverage <= target + 0.03, (
        f"{coverage:.0%} of orders attributed, above the {target:.0%} cap"
    )
    assert coverage > 0.05, (
        f"only {coverage:.0%} of orders attributed - the marketing marts would "
        f"be too thin to mean anything"
    )


def test_blended_roas_is_realistic(tables, generator_module):
    """Spend is sized from ATTRIBUTED revenue at a target ROAS, so the blended
    figure is a business reality rather than an artefact of the dataset size."""
    orders = tables["orders"]
    attributed = orders[(orders["status"] == "completed")
                        & orders["campaign_id"].notna()]
    roas = attributed["net_amount"].sum() / tables["campaigns"]["spend"].sum()
    assert abs(roas - generator_module.TARGET_BLENDED_ROAS) < 0.4, (
        f"blended ROAS is {roas:.2f}, expected around "
        f"{generator_module.TARGET_BLENDED_ROAS}"
    )


def test_only_cancelled_and_returned_orders_carry_a_reason(tables, generator_module):
    orders = tables["orders"]
    exceptions = orders["status"].isin(["cancelled", "returned"])
    assert orders.loc[~exceptions, "status_reason"].isna().all()

    cancelled = orders.loc[orders["status"] == "cancelled", "status_reason"].dropna()
    returned = orders.loc[orders["status"] == "returned", "status_reason"].dropna()
    assert set(cancelled) <= set(generator_module.CANCELLATION_REASONS)
    assert set(returned) <= set(generator_module.RETURN_REASONS)

    # Most exceptions have a reason, but not all - the gap is deliberate.
    missing_share = orders.loc[exceptions, "status_reason"].isna().mean()
    assert 0 < missing_share < 0.15


def test_reason_column_does_not_disturb_any_other_draw(tmp_path, generator_module):
    """The reasons use their own random stream. Adding them must not move a
    single value in any other table, or every published figure would shift."""
    generator_module.main(["--seed", "7", "--customers", "40", "--products", "10",
                           "--orders", "200", "--events", "300", "--campaigns", "3",
                           "--output", str(tmp_path)])
    generator = generator_module.PulseDataGenerator
    original = generator._status_reasons
    try:
        generator._status_reasons = lambda self, status: [None] * len(status)
        generator_module.main(["--seed", "7", "--customers", "40", "--products", "10",
                               "--orders", "200", "--events", "300", "--campaigns", "3",
                               "--output", str(tmp_path / "without")])
    finally:
        generator._status_reasons = original
    with_reasons = pd.read_csv(tmp_path / "orders.csv").drop(columns="status_reason")
    without = pd.read_csv(tmp_path / "without" / "orders.csv").drop(columns="status_reason")
    pd.testing.assert_frame_equal(with_reasons, without)
    for name in ["order_items", "payments", "customers", "customer_events"]:
        pd.testing.assert_frame_equal(pd.read_csv(tmp_path / f"{name}.csv"),
                                      pd.read_csv(tmp_path / "without" / f"{name}.csv"))
