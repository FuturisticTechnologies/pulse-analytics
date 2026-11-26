"""PulseAnalytics synthetic data generator.

Produces two full years of realistic retail/e-commerce history as CSV files in
``data/raw``. The data is deterministic for a given seed, so every run of the
pipeline, every test and every dashboard screenshot reproduces exactly.

What "realistic" means here:
  * a growth trend plus weekly and yearly seasonality (Black Friday, December),
  * repeat-purchase behaviour that follows a power law (a few whales, a long
    tail of one-time buyers),
  * customers who churn - their order rate decays after a personal "last active"
    point, which is what makes retention/cohort analysis interesting,
  * marketing campaigns that measurably lift orders while they run,
  * payment failures, refunds and back-orders,
  * a small, controlled amount of dirty data so the data-quality layer and the
    bronze -> silver cleaning step have something real to do.

Usage:
    python data-generator/generate_data.py --orders 60000
    python data-generator/generate_data.py --preset small     # fast CI dataset
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pulse.config import GENERATOR, PATHS  # noqa: E402
from pulse.logging_utils import banner, get_logger, timed  # noqa: E402

log = get_logger("generator")

# --------------------------------------------------------------------------- #
# Reference data
# --------------------------------------------------------------------------- #
REGIONS = [
    (1, "North America", "USA", "America/New_York", 1.00),
    (2, "West Coast", "USA", "America/Los_Angeles", 0.85),
    (3, "Western Europe", "Germany", "Europe/Berlin", 0.70),
    (4, "United Kingdom", "United Kingdom", "Europe/London", 0.55),
    (5, "APAC", "Singapore", "Asia/Singapore", 0.45),
    (6, "LATAM", "Brazil", "America/Sao_Paulo", 0.30),
]

STORE_TYPES = ["Online", "Flagship", "Outlet", "Partner"]

CATEGORIES = {
    "Electronics": (["Laptops", "Phones", "Audio", "Wearables"], 180.0, 1400.0, 0.68),
    "Home & Kitchen": (["Cookware", "Furniture", "Decor", "Appliances"], 25.0, 480.0, 0.55),
    "Apparel": (["Tops", "Outerwear", "Footwear", "Accessories"], 18.0, 220.0, 0.48),
    "Sports": (["Fitness", "Outdoor", "Cycling", "Team Sports"], 22.0, 640.0, 0.58),
    "Beauty": (["Skincare", "Fragrance", "Haircare", "Cosmetics"], 9.0, 130.0, 0.42),
    "Grocery": (["Coffee", "Snacks", "Beverages", "Pantry"], 4.0, 60.0, 0.72),
}

BRANDS = [
    "Northwind", "Lumen", "Kestrel", "Aurora", "Vantage", "Halcyon",
    "Cobalt", "Meridian", "Sable", "Nimbus", "Torrent", "Pioneer",
]

ACQUISITION_CHANNELS = ["Organic Search", "Paid Search", "Social", "Email", "Referral", "Direct", "Affiliate"]
CHANNEL_WEIGHTS = np.array([0.24, 0.18, 0.16, 0.12, 0.10, 0.14, 0.06])

ORDER_CHANNELS = ["Web", "Mobile App", "In-Store", "Marketplace", "Phone"]
ORDER_CHANNEL_WEIGHTS = np.array([0.42, 0.31, 0.15, 0.09, 0.03])

PAYMENT_METHODS = ["Credit Card", "Debit Card", "PayPal", "Apple Pay", "Bank Transfer", "Gift Card"]
PAYMENT_WEIGHTS = np.array([0.38, 0.19, 0.18, 0.14, 0.07, 0.04])

FAILURE_REASONS = [
    "insufficient_funds", "card_expired", "do_not_honor",
    "network_timeout", "fraud_suspected", "invalid_cvc",
]

# Why an order was cancelled or returned. Codes are what the order system
# records; silver.orders maps them to labels and groups. A small share is left
# blank on purpose - the source does not force agents to pick a reason, and the
# dashboard has to show that gap rather than hide it.
CANCELLATION_REASONS = [
    "customer_request", "payment_failed", "out_of_stock",
    "delivery_too_slow", "duplicate_order", "fraud_review",
]
CANCELLATION_REASON_WEIGHTS = np.array([0.38, 0.17, 0.16, 0.13, 0.09, 0.07])

RETURN_REASONS = [
    "size_or_fit", "not_as_described", "damaged_in_transit",
    "defective", "changed_mind", "wrong_item_sent", "arrived_late",
]
RETURN_REASON_WEIGHTS = np.array([0.24, 0.19, 0.14, 0.13, 0.13, 0.10, 0.07])

MISSING_REASON_SHARE = 0.04

LOYALTY_TIERS = ["Bronze", "Silver", "Gold", "Platinum"]

MARKETING_CHANNELS = ["Paid Search", "Social", "Email", "Display", "Affiliate", "Influencer"]

EVENT_TYPES = [
    "app_open", "page_view", "product_view", "search",
    "add_to_cart", "checkout_start", "purchase", "support_ticket", "review_submitted",
]
EVENT_WEIGHTS = np.array([0.14, 0.30, 0.21, 0.11, 0.10, 0.055, 0.045, 0.02, 0.02])

DEVICES = ["ios", "android", "desktop", "tablet"]
DEVICE_WEIGHTS = np.array([0.33, 0.30, 0.30, 0.07])

FIRST_NAMES = [
    "Ava", "Liam", "Noah", "Mia", "Elena", "Omar", "Priya", "Sofia", "Lucas", "Hana",
    "Jonas", "Amara", "Diego", "Ines", "Kofi", "Mei", "Ruben", "Zara", "Nils", "Ayla",
    "Tomas", "Nora", "Ibrahim", "Leila", "Marco", "Yuki", "Anders", "Sasha", "Rohan", "Clara",
]
LAST_NAMES = [
    "Okafor", "Lindqvist", "Moreau", "Sharma", "Rossi", "Nakamura", "Silva", "Novak",
    "Haddad", "Fischer", "Andersen", "Costa", "Weber", "Kaur", "Petrov", "Dubois",
    "Marino", "Olsen", "Chen", "Vargas", "Bauer", "Ferreira", "Kowalski", "Ibrahim",
]

CITY_BY_REGION = {
    1: ["New York", "Chicago", "Toronto", "Boston", "Atlanta"],
    2: ["San Francisco", "Seattle", "Los Angeles", "Portland"],
    3: ["Berlin", "Munich", "Amsterdam", "Paris", "Madrid"],
    4: ["London", "Manchester", "Edinburgh"],
    5: ["Singapore", "Sydney", "Tokyo", "Seoul"],
    6: ["Sao Paulo", "Mexico City", "Bogota"],
}

# Marketing economics, held constant across every preset. Both are business
# realities rather than arbitrary constants: roughly a third of orders traceable
# to a campaign is typical last-touch coverage, and a blended ROAS around 3 is
# what a healthy retailer runs at.
TARGET_ATTRIBUTION_SHARE = 0.32
TARGET_BLENDED_ROAS = 3.2

PRESETS = {
    "small": dict(customers=400, products=60, orders=3000, events=6000, campaigns=12),
    "medium": dict(customers=4000, products=320, orders=60000, events=150000, campaigns=48),
    "large": dict(customers=20000, products=900, orders=250000, events=700000, campaigns=96),
}


# --------------------------------------------------------------------------- #
# Seasonality
# --------------------------------------------------------------------------- #
def daily_demand_curve(days: pd.DatetimeIndex) -> np.ndarray:
    """Relative order intensity per calendar day.

    Trend (business grows ~35% year over year) x weekly shape (weekend lift)
    x yearly shape (spring dip, Q4 peak) x named promo spikes.
    """
    n = len(days)
    t = np.arange(n)

    trend = 1.0 + 0.35 * (t / max(n - 1, 1))

    weekday = days.dayofweek.to_numpy()
    weekly = np.array([0.95, 0.92, 0.96, 1.02, 1.14, 1.22, 1.05])[weekday]

    doy = days.dayofyear.to_numpy()
    yearly = 1.0 + 0.18 * np.sin(2 * np.pi * (doy - 80) / 365.25)

    month = days.month.to_numpy()
    day = days.day.to_numpy()
    holiday = np.ones(n)
    holiday[(month == 11) & (day >= 20) & (day <= 30)] = 2.35      # Black Friday / Cyber week
    holiday[(month == 12) & (day >= 1) & (day <= 22)] = 1.75       # Christmas run-up
    holiday[(month == 12) & (day >= 24) & (day <= 26)] = 0.45      # shutdown
    holiday[(month == 1) & (day <= 10)] = 0.72                     # January hangover
    holiday[(month == 7) & (day >= 10) & (day <= 18)] = 1.45       # summer sale

    return trend * weekly * yearly * holiday


# --------------------------------------------------------------------------- #
# Generator
# --------------------------------------------------------------------------- #
class PulseDataGenerator:
    def __init__(
        self,
        seed: int,
        n_customers: int,
        n_products: int,
        n_orders: int,
        n_events: int,
        n_campaigns: int,
        start: date,
        end: date,
        dirty_rate: float = 0.004,
    ) -> None:
        self.rng = np.random.default_rng(seed)
        self.seed = seed
        self.n_customers = n_customers
        self.n_products = n_products
        self.n_orders = n_orders
        self.n_events = n_events
        self.n_campaigns = n_campaigns
        self.start = pd.Timestamp(start)
        self.end = pd.Timestamp(end)
        self.dirty_rate = dirty_rate
        self.days = pd.date_range(self.start, self.end, freq="D")
        self.n_days = len(self.days)
        self.tables: dict[str, pd.DataFrame] = {}

    # ------------------------------------------------------------- reference
    def build_regions(self) -> pd.DataFrame:
        frame = pd.DataFrame(
            REGIONS, columns=["region_id", "region_name", "country", "timezone", "demand_index"]
        )
        self.tables["regions"] = frame
        return frame

    def build_stores(self) -> pd.DataFrame:
        records = []
        store_id = 1
        for region_id, region_name, country, _tz, _idx in REGIONS:
            cities = CITY_BY_REGION[region_id]
            n_stores = 2 if region_id in (1, 3) else 1
            records.append(
                dict(
                    store_id=store_id,
                    store_name=f"{region_name} Online",
                    store_type="Online",
                    region_id=region_id,
                    city=cities[0],
                    country=country,
                    opened_date=(self.start - timedelta(days=int(self.rng.integers(400, 1200)))).date(),
                    floor_sqm=None,
                )
            )
            store_id += 1
            for i in range(n_stores):
                store_type = STORE_TYPES[1 + (i % 3)]
                records.append(
                    dict(
                        store_id=store_id,
                        store_name=f"{cities[(i + 1) % len(cities)]} {store_type}",
                        store_type=store_type,
                        region_id=region_id,
                        city=cities[(i + 1) % len(cities)],
                        country=country,
                        opened_date=(self.start - timedelta(days=int(self.rng.integers(100, 1500)))).date(),
                        floor_sqm=int(self.rng.integers(180, 1400)),
                    )
                )
                store_id += 1
        frame = pd.DataFrame(records)
        self.tables["stores"] = frame
        return frame

    def build_products(self) -> pd.DataFrame:
        rng = self.rng
        n = self.n_products
        category_names = list(CATEGORIES)
        cat_idx = rng.choice(len(category_names), size=n, p=[0.19, 0.17, 0.22, 0.14, 0.13, 0.15])
        categories = [category_names[i] for i in cat_idx]

        subcategories, prices, costs = [], [], []
        for category in categories:
            subs, low, high, cost_ratio = CATEGORIES[category]
            subcategories.append(subs[int(rng.integers(0, len(subs)))])
            # log-uniform price so each category has a realistic long tail
            price = float(np.exp(rng.uniform(np.log(low), np.log(high))))
            price = round(price, 2)
            ratio = float(np.clip(rng.normal(cost_ratio, 0.06), 0.25, 0.92))
            prices.append(price)
            costs.append(round(price * ratio, 2))

        launch_offsets = rng.integers(-540, self.n_days - 30, size=n)
        launch_dates = [(self.start + timedelta(days=int(o))).date() for o in launch_offsets]

        frame = pd.DataFrame(
            {
                "product_id": np.arange(1, n + 1),
                "sku": [f"PA-{c[:3].upper()}-{i:05d}" for i, c in zip(range(1, n + 1), categories)],
                "product_name": [
                    f"{BRANDS[int(rng.integers(0, len(BRANDS)))]} {sub[:-1] if sub.endswith('s') else sub} {int(rng.integers(100, 999))}"
                    for sub in subcategories
                ],
                "category": categories,
                "subcategory": subcategories,
                "brand": [BRANDS[int(rng.integers(0, len(BRANDS)))] for _ in range(n)],
                "unit_price": prices,
                "unit_cost": costs,
                "launch_date": launch_dates,
                "is_active": rng.random(n) > 0.08,
                "weight_kg": np.round(rng.gamma(2.0, 0.6, n) + 0.1, 3),
            }
        )
        # popularity drives which products actually sell (Zipf-like)
        popularity = rng.pareto(1.3, n) + 0.15
        frame["popularity"] = popularity / popularity.sum()
        self.tables["products"] = frame
        return frame

    def build_customers(self) -> pd.DataFrame:
        rng = self.rng
        n = self.n_customers
        region_weights = np.array([r[4] for r in REGIONS])
        region_weights = region_weights / region_weights.sum()
        region_ids = rng.choice([r[0] for r in REGIONS], size=n, p=region_weights)

        # 30% of the base existed before the window; the rest sign up over time
        pre_existing = rng.random(n) < 0.30
        signup_offsets = np.where(
            pre_existing,
            -rng.integers(1, 900, size=n),
            rng.integers(0, self.n_days, size=n),
        )
        signup_dates = [self.start + timedelta(days=int(o)) for o in signup_offsets]

        first = rng.choice(FIRST_NAMES, n)
        last = rng.choice(LAST_NAMES, n)
        emails = [
            f"{f.lower()}.{l.lower()}{i}@{'example.com' if i % 3 else 'mail.test'}"
            for i, (f, l) in enumerate(zip(first, last), start=1)
        ]

        # personal purchase propensity: a few whales, a long tail
        propensity = rng.pareto(1.6, n) + 0.2
        # personal churn point: after this day the customer mostly stops buying
        lifespan_days = rng.gamma(shape=2.2, scale=210, size=n)

        frame = pd.DataFrame(
            {
                "customer_id": np.arange(1, n + 1),
                "first_name": first,
                "last_name": last,
                "email": emails,
                "phone": [f"+1-555-{int(x):04d}" for x in rng.integers(0, 9999, n)],
                "signup_date": [d.date() for d in signup_dates],
                "region_id": region_ids,
                "city": [CITY_BY_REGION[int(r)][int(rng.integers(0, len(CITY_BY_REGION[int(r)])))] for r in region_ids],
                "acquisition_channel": rng.choice(ACQUISITION_CHANNELS, n, p=CHANNEL_WEIGHTS),
                "birth_year": rng.integers(1955, 2006, n),
                "gender": rng.choice(["F", "M", "X"], n, p=[0.48, 0.47, 0.05]),
                "loyalty_tier": rng.choice(LOYALTY_TIERS, n, p=[0.52, 0.28, 0.15, 0.05]),
                "marketing_opt_in": rng.random(n) < 0.63,
                "propensity": propensity,
                "lifespan_days": lifespan_days,
                "signup_day_index": signup_offsets,
            }
        )
        self.tables["customers"] = frame
        return frame

    def build_campaigns(self) -> pd.DataFrame:
        rng = self.rng
        n = self.n_campaigns
        starts = np.sort(rng.integers(0, self.n_days - 14, size=n))
        durations = rng.integers(7, 45, size=n)
        channels = rng.choice(MARKETING_CHANNELS, n, p=[0.28, 0.24, 0.18, 0.12, 0.10, 0.08])

        # Spend is sized RELATIVE to the business, not from a fixed range, and
        # the absolute level is set later by rescale_campaign_economics() once
        # the realised revenue is known. Hard-coded budgets make ROAS collapse
        # on a small dataset and explode on a large one, so the marketing
        # dashboard is nonsense at every preset except the one it was tuned for.
        #
        # What is fixed HERE is the relative split between campaigns: longer
        # campaigns get more, with a lognormal spread.
        weights = durations * np.exp(rng.normal(0.0, 0.5, n))
        spend = np.round(weights / weights.sum(), 6)      # provisional shares
        budgets = np.round(spend / rng.uniform(0.72, 1.02, n), 6)
        cpm = rng.uniform(4.0, 22.0, n)
        ctr = rng.uniform(0.004, 0.062, n)
        impressions = (spend / cpm * 1000).astype(int)
        clicks = (impressions * ctr).astype(int)

        frame = pd.DataFrame(
            {
                "campaign_id": np.arange(1, n + 1),
                "campaign_name": [
                    f"{channels[i]} {(self.start + timedelta(days=int(starts[i]))).strftime('%Y-%m')} {['Prospecting','Retargeting','Loyalty','Winback','Launch'][i % 5]}"
                    for i in range(n)
                ],
                "channel": channels,
                "objective": rng.choice(
                    ["Acquisition", "Retention", "Awareness", "Conversion"], n, p=[0.42, 0.24, 0.16, 0.18]
                ),
                "start_date": [(self.start + timedelta(days=int(s))).date() for s in starts],
                "end_date": [
                    (self.start + timedelta(days=int(min(s + d, self.n_days - 1)))).date()
                    for s, d in zip(starts, durations)
                ],
                "budget": budgets,
                "spend": spend,
                "impressions": impressions,
                "clicks": clicks,
                "target_segment": rng.choice(
                    ["All", "New", "Lapsed", "VIP", "High Value"], n, p=[0.34, 0.22, 0.18, 0.12, 0.14]
                ),
                "start_day_index": starts,
                "end_day_index": np.minimum(starts + durations, self.n_days - 1),
                "uplift": rng.uniform(0.05, 0.55, n),
                "cpm": cpm,
                "ctr": ctr,
            }
        )
        self.tables["campaigns"] = frame
        return frame

    def rescale_campaign_economics(self, target_roas: float = TARGET_BLENDED_ROAS) -> None:
        """Set campaign spend from the revenue campaigns are actually credited with.

        Budgets have to be sized against the business, not fixed in advance, or
        every derived metric breaks the moment the dataset changes size. And the
        denominator has to be ATTRIBUTED revenue, not total revenue: spend as a
        flat share of total revenue leaves ROAS at the mercy of how much of the
        calendar the campaigns happen to cover.

        Sizing spend as `attributed revenue / target ROAS` fixes the blended
        ROAS by construction, and lets spend-as-a-share-of-revenue fall out of
        the attribution coverage - which is the direction the causality actually
        runs in a real business.

        Called after orders and lines exist, so the denominator is real. Each
        campaign's relative share, CPM and CTR were fixed at build time and are
        preserved - only the scale changes.
        """
        campaigns = self.tables["campaigns"]
        orders = self.tables["orders"]

        completed = orders["status"] == "completed"
        attributed = completed & orders["campaign_id"].notna()
        attributed_revenue = float(orders.loc[attributed, "items_net"].sum())
        total_revenue = float(orders.loc[completed, "items_net"].sum())
        if attributed_revenue <= 0:
            return

        target_spend = attributed_revenue / target_roas
        shares = campaigns["spend"].to_numpy(dtype=float)
        shares = shares / shares.sum()

        campaigns["spend"] = np.round(target_spend * shares, 2)
        # Campaigns usually come in a little under budget.
        campaigns["budget"] = np.round(
            campaigns["spend"] / self.rng.uniform(0.72, 1.02, len(campaigns)), 2
        )
        campaigns["impressions"] = (campaigns["spend"] / campaigns["cpm"] * 1000).astype(int)
        campaigns["clicks"] = (campaigns["impressions"] * campaigns["ctr"]).astype(int)

        log.info(
            "marketing: %s spend across %d campaigns -> blended ROAS %.1f "
            "(%.0f%% of orders attributed, spend = %.1f%% of revenue)",
            format(campaigns["spend"].sum(), ",.0f"),
            len(campaigns),
            target_roas,
            attributed.sum() / max(completed.sum(), 1) * 100,
            target_spend / total_revenue * 100,
        )

    # ---------------------------------------------------------------- orders
    def build_orders(self) -> pd.DataFrame:
        rng = self.rng
        customers = self.tables["customers"]
        stores = self.tables["stores"]
        campaigns = self.tables["campaigns"]

        # 1. how many orders land on each calendar day
        demand = daily_demand_curve(self.days)
        campaign_boost = np.ones(self.n_days)
        for row in campaigns.itertuples(index=False):
            campaign_boost[row.start_day_index : row.end_day_index + 1] += row.uplift * 0.25
        demand = demand * campaign_boost
        day_probs = demand / demand.sum()
        order_days = rng.choice(self.n_days, size=self.n_orders, p=day_probs)
        order_days.sort()

        # 2. who placed each order - weighted by propensity, must exist and be
        #    within their active lifespan on that day
        signup_idx = customers["signup_day_index"].to_numpy()
        lifespan = customers["lifespan_days"].to_numpy()
        base_weights = customers["propensity"].to_numpy()
        base_probs = base_weights / base_weights.sum()

        chosen = rng.choice(self.n_customers, size=self.n_orders, p=base_probs)
        for _ in range(24):
            cust_signup = signup_idx[chosen]
            cust_end = cust_signup + lifespan[chosen]
            # reactivation: 8% of the time a lapsed customer comes back anyway
            reactivated = rng.random(self.n_orders) < 0.08
            invalid = (order_days < cust_signup) | ((order_days > cust_end) & ~reactivated)
            if not invalid.any():
                break
            chosen[invalid] = rng.choice(self.n_customers, size=int(invalid.sum()), p=base_probs)
        # any stragglers snap to a customer who definitely existed by then
        cust_signup = signup_idx[chosen]
        still_invalid = order_days < cust_signup
        if still_invalid.any():
            early = np.where(signup_idx <= 0)[0]
            pool = early if len(early) else np.arange(self.n_customers)
            chosen[still_invalid] = rng.choice(pool, size=int(still_invalid.sum()))

        customer_ids = customers["customer_id"].to_numpy()[chosen]
        region_ids = customers["region_id"].to_numpy()[chosen]

        # 3. store: online store of the customer's region most of the time
        online_by_region = (
            stores[stores["store_type"] == "Online"].set_index("region_id")["store_id"].to_dict()
        )
        physical_by_region: dict[int, list[int]] = {}
        for row in stores[stores["store_type"] != "Online"].itertuples(index=False):
            physical_by_region.setdefault(int(row.region_id), []).append(int(row.store_id))

        order_channels = rng.choice(ORDER_CHANNELS, self.n_orders, p=ORDER_CHANNEL_WEIGHTS)
        store_ids = np.empty(self.n_orders, dtype=int)
        for i, (region, channel) in enumerate(zip(region_ids, order_channels)):
            region = int(region)
            if channel == "In-Store" and physical_by_region.get(region):
                options = physical_by_region[region]
                store_ids[i] = options[int(rng.integers(0, len(options)))]
            else:
                store_ids[i] = online_by_region[region]

        # 4. timestamps - shopping peaks at lunchtime and in the evening
        hour_weights = np.array(
            [0.6, 0.4, 0.3, 0.3, 0.4, 0.8, 1.4, 2.4, 3.6, 4.4, 5.0, 5.6,
             6.2, 5.8, 5.2, 5.0, 5.4, 6.4, 7.2, 7.6, 6.8, 5.2, 3.4, 1.8]
        )
        hour_probs = hour_weights / hour_weights.sum()
        hours = rng.choice(24, size=self.n_orders, p=hour_probs)
        minutes = rng.integers(0, 60, self.n_orders)
        seconds = rng.integers(0, 60, self.n_orders)
        order_dates = self.start + pd.to_timedelta(order_days, unit="D")
        order_ts = order_dates + pd.to_timedelta(hours, unit="h") + pd.to_timedelta(minutes, unit="m") + pd.to_timedelta(seconds, unit="s")

        # 5. campaign attribution: an order inside a campaign window may be attributed
        # Attribution coverage is held at a constant share of orders, whatever
        # the dataset size.
        #
        # The naive version - "attribute each in-window order with probability
        # p" - looks correct and is not: at the `small` preset a dozen short
        # campaigns cover a third of the calendar, while at `large` a hundred
        # overlapping ones cover nearly all of it. Coverage then swings from
        # 15% to 90%, and every marketing metric derived from it swings with
        # it. Normalising against the observed in-window share keeps the
        # attribution rate - and therefore ROAS, CAC and channel mix - stable
        # across every preset.
        campaign_id = np.full(self.n_orders, np.nan)
        strength = np.zeros(self.n_orders)
        in_any_window = np.zeros(self.n_orders, dtype=bool)

        for row in campaigns.itertuples(index=False):
            in_window = (order_days >= row.start_day_index) & (order_days <= row.end_day_index)
            in_any_window |= in_window
            # Overlapping campaigns: the strongest one wins the touch, which is
            # what a last-touch tracker with a recency tiebreak would record.
            claim = in_window & (rng.random(self.n_orders) * row.uplift > strength)
            strength[claim] = rng.random(int(claim.sum())) * row.uplift
            campaign_id[claim] = row.campaign_id

        in_window_share = float(in_any_window.mean())
        keep_probability = (
            min(TARGET_ATTRIBUTION_SHARE / in_window_share, 0.9)
            if in_window_share > 0 else 0.0
        )
        dropped = in_any_window & (rng.random(self.n_orders) >= keep_probability)
        campaign_id[dropped] = np.nan

        # The cap is one-sided: a sparse campaign calendar cannot reach the
        # target, and inventing attributions for orders outside every campaign
        # window would be worse than under-shooting.
        log.info(
            "attribution: %.0f%% of orders in a campaign window, %.0f%% attributed "
            "(cap %.0f%%)",
            in_window_share * 100,
            float((~np.isnan(campaign_id)).mean()) * 100,
            TARGET_ATTRIBUTION_SHARE * 100,
        )

        # 6. status - most complete, some cancelled/returned/pending
        status = rng.choice(
            ["completed", "completed", "completed", "completed", "completed",
             "completed", "completed", "completed", "cancelled", "returned"],
            self.n_orders,
        )
        recent = order_days > (self.n_days - 4)
        status[recent & (rng.random(self.n_orders) < 0.35)] = "pending"

        status_reason = self._status_reasons(status)

        orders = pd.DataFrame(
            {
                "order_id": np.arange(1, self.n_orders + 1),
                "customer_id": customer_ids,
                "store_id": store_ids,
                "order_ts": order_ts,
                "order_date": order_dates.date if hasattr(order_dates, "date") else order_dates,
                "channel": order_channels,
                "status": status,
                "status_reason": status_reason,
                "currency": "USD",
                "campaign_id": campaign_id,
                "region_id": region_ids,
                "_day_index": order_days,
            }
        )
        orders["order_date"] = pd.to_datetime(orders["order_ts"]).dt.date
        self.tables["orders"] = orders
        return orders

    def _status_reasons(self, status: np.ndarray) -> np.ndarray:
        """Reason code for cancelled and returned orders, None for the rest.

        Drawn from a dedicated random stream rather than ``self.rng`` so that
        adding the column does not shift a single draw anywhere else - every
        other table is byte-identical to what the same seed produced before.
        """
        rng = np.random.default_rng([self.seed, 105])
        n = len(status)
        reasons = np.full(n, None, dtype=object)

        cancelled = status == "cancelled"
        returned = status == "returned"
        reasons[cancelled] = rng.choice(
            CANCELLATION_REASONS, int(cancelled.sum()), p=CANCELLATION_REASON_WEIGHTS
        )
        reasons[returned] = rng.choice(
            RETURN_REASONS, int(returned.sum()), p=RETURN_REASON_WEIGHTS
        )
        not_recorded = (cancelled | returned) & (rng.random(n) < MISSING_REASON_SHARE)
        reasons[not_recorded] = None
        return reasons

    def build_order_items(self) -> pd.DataFrame:
        rng = self.rng
        orders = self.tables["orders"]
        products = self.tables["products"]
        n_orders = len(orders)

        basket_sizes = 1 + rng.poisson(1.15, n_orders)
        basket_sizes = np.clip(basket_sizes, 1, 8)
        total_items = int(basket_sizes.sum())

        order_ids = np.repeat(orders["order_id"].to_numpy(), basket_sizes)
        order_day_index = np.repeat(orders["_day_index"].to_numpy(), basket_sizes)

        product_idx = rng.choice(len(products), size=total_items, p=products["popularity"].to_numpy())
        # a product cannot be sold before it launched - resample the offenders
        launch_day = np.array(
            [(pd.Timestamp(d) - self.start).days for d in products["launch_date"]]
        )
        for _ in range(12):
            invalid = order_day_index < launch_day[product_idx]
            if not invalid.any():
                break
            product_idx[invalid] = rng.choice(
                len(products), size=int(invalid.sum()), p=products["popularity"].to_numpy()
            )
        invalid = order_day_index < launch_day[product_idx]
        if invalid.any():
            oldest = np.argsort(launch_day)[: max(5, len(products) // 10)]
            product_idx[invalid] = rng.choice(oldest, size=int(invalid.sum()))

        quantity = 1 + rng.poisson(0.55, total_items)
        quantity = np.clip(quantity, 1, 12)

        list_price = products["unit_price"].to_numpy()[product_idx]
        unit_cost = products["unit_cost"].to_numpy()[product_idx]

        # discounting: most lines full price, promo days discount harder
        discount_rate = np.zeros(total_items)
        has_discount = rng.random(total_items) < 0.34
        discount_rate[has_discount] = rng.choice([0.05, 0.10, 0.15, 0.20, 0.25, 0.35], has_discount.sum())
        seasonal_promo = np.isin(
            pd.to_datetime(self.start + pd.to_timedelta(order_day_index, unit="D")).month, [11, 12, 7]
        )
        discount_rate = np.where(seasonal_promo, np.minimum(discount_rate + 0.08, 0.5), discount_rate)

        gross = np.round(list_price * quantity, 2)
        discount_amount = np.round(gross * discount_rate, 2)
        line_amount = np.round(gross - discount_amount, 2)
        line_cost = np.round(unit_cost * quantity, 2)

        items = pd.DataFrame(
            {
                "order_item_id": np.arange(1, total_items + 1),
                "order_id": order_ids,
                "product_id": products["product_id"].to_numpy()[product_idx],
                "quantity": quantity,
                "unit_price": list_price,
                "unit_cost": unit_cost,
                "discount_amount": discount_amount,
                "gross_amount": gross,
                "line_amount": line_amount,
                "line_cost": line_cost,
            }
        )
        self.tables["order_items"] = items

        # roll item totals back onto the order header
        totals = items.groupby("order_id", as_index=False).agg(
            items_gross=("gross_amount", "sum"),
            items_discount=("discount_amount", "sum"),
            items_net=("line_amount", "sum"),
            items_cost=("line_cost", "sum"),
            item_count=("quantity", "sum"),
        )
        orders = self.tables["orders"].merge(totals, on="order_id", how="left")
        shipping = np.where(orders["items_net"] > 75, 0.0, np.round(rng.uniform(3.5, 14.9, len(orders)), 2))
        shipping = np.where(orders["channel"] == "In-Store", 0.0, shipping)
        tax = np.round(orders["items_net"] * 0.0825, 2)
        orders["gross_amount"] = orders["items_gross"].round(2)
        orders["discount_amount"] = orders["items_discount"].round(2)
        orders["shipping_amount"] = shipping
        orders["tax_amount"] = tax
        orders["net_amount"] = (orders["items_net"] + shipping).round(2)
        orders["total_amount"] = (orders["net_amount"] + tax).round(2)
        orders["cost_amount"] = orders["items_cost"].round(2)
        orders["item_count"] = orders["item_count"].fillna(0).astype(int)
        self.tables["orders"] = orders
        return items

    def build_payments(self) -> pd.DataFrame:
        rng = self.rng
        orders = self.tables["orders"]
        billable = orders[orders["status"] != "cancelled"].copy()
        n = len(billable)

        methods = rng.choice(PAYMENT_METHODS, n, p=PAYMENT_WEIGHTS)
        # failure rate depends on method - bank transfer and credit card differ
        method_failure = {
            "Credit Card": 0.045, "Debit Card": 0.055, "PayPal": 0.022,
            "Apple Pay": 0.014, "Bank Transfer": 0.075, "Gift Card": 0.030,
        }
        fail_prob = np.array([method_failure[m] for m in methods])
        failed = rng.random(n) < fail_prob

        records = []
        payment_id = 1
        base_ts = pd.to_datetime(billable["order_ts"]).to_numpy()
        amounts = billable["total_amount"].to_numpy()
        order_ids = billable["order_id"].to_numpy()
        statuses = billable["status"].to_numpy()

        for i in range(n):
            ts = pd.Timestamp(base_ts[i]) + timedelta(seconds=int(rng.integers(20, 900)))
            if failed[i]:
                records.append(
                    dict(
                        payment_id=payment_id, order_id=int(order_ids[i]),
                        payment_method=methods[i], payment_ts=ts,
                        amount=round(float(amounts[i]), 2), status="failed",
                        failure_reason=FAILURE_REASONS[int(rng.integers(0, len(FAILURE_REASONS)))],
                        attempt_number=1,
                    )
                )
                payment_id += 1
                # 70% of failures are retried and most of those succeed
                if rng.random() < 0.70:
                    retry_ts = ts + timedelta(minutes=int(rng.integers(2, 240)))
                    retry_ok = rng.random() < 0.82
                    records.append(
                        dict(
                            payment_id=payment_id, order_id=int(order_ids[i]),
                            payment_method=methods[i], payment_ts=retry_ts,
                            amount=round(float(amounts[i]), 2),
                            status="captured" if retry_ok else "failed",
                            failure_reason=None if retry_ok else "do_not_honor",
                            attempt_number=2,
                        )
                    )
                    payment_id += 1
            else:
                records.append(
                    dict(
                        payment_id=payment_id, order_id=int(order_ids[i]),
                        payment_method=methods[i], payment_ts=ts,
                        amount=round(float(amounts[i]), 2), status="captured",
                        failure_reason=None, attempt_number=1,
                    )
                )
                payment_id += 1
                if statuses[i] == "returned":
                    refund_ts = ts + timedelta(days=int(rng.integers(2, 30)))
                    records.append(
                        dict(
                            payment_id=payment_id, order_id=int(order_ids[i]),
                            payment_method=methods[i], payment_ts=refund_ts,
                            amount=-round(float(amounts[i]), 2), status="refunded",
                            failure_reason=None, attempt_number=1,
                        )
                    )
                    payment_id += 1

        frame = pd.DataFrame(records)
        self.tables["payments"] = frame
        return frame

    def build_inventory(self) -> pd.DataFrame:
        """Weekly on-hand snapshots per product, driven by actual sales."""
        rng = self.rng
        products = self.tables["products"]
        orders = self.tables["orders"][["order_id", "_day_index"]]
        items = self.tables["order_items"].merge(orders, on="order_id", how="left")
        items["week_index"] = items["_day_index"] // 7
        weekly_sales = (
            items.groupby(["product_id", "week_index"], as_index=False)["quantity"].sum()
            .rename(columns={"quantity": "units_sold"})
        )

        n_weeks = self.n_days // 7
        product_grid, week_grid = np.meshgrid(
            products["product_id"].to_numpy(), np.arange(n_weeks), indexing="ij"
        )
        grid = pd.DataFrame(
            {"product_id": product_grid.ravel(), "week_index": week_grid.ravel()}
        )
        grid = grid.merge(weekly_sales, on=["product_id", "week_index"], how="left")
        grid["units_sold"] = grid["units_sold"].fillna(0).astype(int)

        # Stock is SIMULATED against each product's own realised demand rather
        # than assigned from a formula. Decoupling the two - the obvious
        # shortcut - produces a warehouse where every product looks massively
        # overstocked and no reorder point is ever crossed, which makes the
        # whole inventory analytics layer vacuous.
        #
        # Policy simulated per product: continuous review, order-up-to.
        #   reorder point   = 2 weeks of average demand x 1.4 safety factor
        #   order quantity  = ~4 weeks of cover
        demand_matrix = (
            grid.pivot(index="product_id", columns="week_index", values="units_sold")
            .fillna(0).astype(int)
        )
        product_ids = demand_matrix.index.to_numpy()
        demand_values = demand_matrix.to_numpy()
        mean_weekly = demand_values.mean(axis=1)

        reorder_points = np.maximum(2, np.ceil(mean_weekly * 2 * 1.4)).astype(int)
        order_quantities = np.maximum(4, np.ceil(mean_weekly * 4)).astype(int)

        on_hand_out = np.zeros_like(demand_values)
        restock_out = np.zeros_like(demand_values)
        stockout_out = np.zeros(demand_values.shape, dtype=bool)

        for i in range(len(product_ids)):
            reorder_point = int(reorder_points[i])
            order_quantity = int(order_quantities[i])
            # Start somewhere plausible rather than exactly on policy.
            on_hand = int(order_quantity + reorder_point * rng.uniform(0.6, 1.6))
            for week in range(demand_values.shape[1]):
                on_hand = max(0, on_hand - int(demand_values[i, week]))
                on_hand_out[i, week] = on_hand
                stockout_out[i, week] = on_hand == 0
                if on_hand <= reorder_point:
                    # Replenishment arrives with a little supplier variability.
                    received = int(order_quantity * rng.uniform(0.85, 1.25))
                    restock_out[i, week] = received
                    on_hand += received

        simulated = pd.DataFrame({
            "product_id": np.repeat(product_ids, demand_values.shape[1]),
            "week_index": np.tile(np.arange(demand_values.shape[1]), len(product_ids)),
            "on_hand_units": on_hand_out.ravel(),
            "restock_units": restock_out.ravel(),
            "is_stockout": stockout_out.ravel(),
            "reorder_point": np.repeat(reorder_points, demand_values.shape[1]),
        })
        grid = grid.merge(simulated, on=["product_id", "week_index"], how="left")
        grid["snapshot_date"] = [
            (self.start + timedelta(days=int(w) * 7 + 6)).date() for w in grid["week_index"]
        ]
        grid["inventory_id"] = np.arange(1, len(grid) + 1)
        frame = grid[
            ["inventory_id", "snapshot_date", "product_id", "on_hand_units",
             "reorder_point", "units_sold", "restock_units", "is_stockout"]
        ]
        self.tables["inventory_snapshots"] = frame
        return frame

    def build_events(self) -> pd.DataFrame:
        rng = self.rng
        customers = self.tables["customers"]
        products = self.tables["products"]
        n = self.n_events

        demand = daily_demand_curve(self.days)
        day_probs = demand / demand.sum()
        event_days = rng.choice(self.n_days, size=n, p=day_probs)

        signup_idx = customers["signup_day_index"].to_numpy()
        probs = customers["propensity"].to_numpy()
        probs = probs / probs.sum()
        chosen = rng.choice(self.n_customers, size=n, p=probs)
        for _ in range(10):
            invalid = event_days < signup_idx[chosen]
            if not invalid.any():
                break
            chosen[invalid] = rng.choice(self.n_customers, size=int(invalid.sum()), p=probs)
        invalid = event_days < signup_idx[chosen]
        if invalid.any():
            event_days[invalid] = np.maximum(signup_idx[chosen[invalid]], 0)

        event_types = rng.choice(EVENT_TYPES, n, p=EVENT_WEIGHTS)
        needs_product = np.isin(event_types, ["product_view", "add_to_cart", "purchase", "review_submitted"])
        product_ids = np.where(
            needs_product,
            products["product_id"].to_numpy()[
                rng.choice(len(products), size=n, p=products["popularity"].to_numpy())
            ],
            np.nan,
        )

        seconds = rng.integers(0, 86400, n)
        ts = self.start + pd.to_timedelta(event_days, unit="D") + pd.to_timedelta(seconds, unit="s")

        frame = pd.DataFrame(
            {
                "event_id": np.arange(1, n + 1),
                "customer_id": customers["customer_id"].to_numpy()[chosen],
                "event_ts": ts,
                "event_type": event_types,
                "session_id": [f"s-{int(x):09d}" for x in rng.integers(0, 10**9, n)],
                "device": rng.choice(DEVICES, n, p=DEVICE_WEIGHTS),
                "product_id": product_ids,
                "page_url": ["/" + t.replace("_", "-") for t in event_types],
                "duration_seconds": np.round(rng.gamma(2.0, 22.0, n), 1),
            }
        ).sort_values("event_ts", ignore_index=True)
        self.tables["customer_events"] = frame
        return frame

    # ------------------------------------------------------------------ dirt
    def inject_data_quality_issues(self) -> dict[str, int]:
        """Introduce a small, deterministic amount of realistic dirt.

        The bronze -> silver step cleans these and etl/quality reports them, so
        the platform demonstrates a genuine data-quality story rather than
        pretending source systems are perfect.
        """
        rng = self.rng
        stats: dict[str, int] = {}

        customers = self.tables["customers"]
        n_null_email = max(1, int(len(customers) * self.dirty_rate * 2))
        idx = rng.choice(len(customers), n_null_email, replace=False)
        customers.loc[customers.index[idx], "email"] = None
        stats["customers_missing_email"] = n_null_email

        # whitespace + case noise in a categorical column
        n_messy = max(1, int(len(customers) * self.dirty_rate * 3))
        idx = rng.choice(len(customers), n_messy, replace=False)
        customers.loc[customers.index[idx], "loyalty_tier"] = (
            customers.loc[customers.index[idx], "loyalty_tier"].str.upper() + "  "
        )
        stats["customers_messy_tier"] = n_messy

        items = self.tables["order_items"]
        n_neg = max(1, int(len(items) * self.dirty_rate))
        idx = rng.choice(len(items), n_neg, replace=False)
        items.loc[items.index[idx], "quantity"] = -items.loc[items.index[idx], "quantity"]
        stats["order_items_negative_quantity"] = n_neg

        orders = self.tables["orders"]
        n_dupe = max(1, int(len(orders) * self.dirty_rate))
        dupes = orders.sample(n=n_dupe, random_state=self.seed).copy()
        self.tables["orders"] = pd.concat([orders, dupes], ignore_index=True)
        stats["orders_duplicate_rows"] = n_dupe

        events = self.tables["customer_events"]
        n_orphan = max(1, int(len(events) * self.dirty_rate))
        idx = rng.choice(len(events), n_orphan, replace=False)
        events.loc[events.index[idx], "customer_id"] = 10**7  # referential orphan
        stats["events_orphan_customer"] = n_orphan

        return stats

    # ------------------------------------------------------------------ save
    def write(self, output_dir: Path) -> dict[str, int]:
        output_dir.mkdir(parents=True, exist_ok=True)
        drop_cols = {
            "orders": ["_day_index", "items_gross", "items_discount", "items_net", "items_cost", "region_id"],
            "customers": ["propensity", "lifespan_days", "signup_day_index"],
            "products": ["popularity"],
            "campaigns": ["start_day_index", "end_day_index", "uplift", "cpm", "ctr"],
            "regions": ["demand_index"],
        }
        counts: dict[str, int] = {}
        for name, frame in self.tables.items():
            out = frame.drop(columns=[c for c in drop_cols.get(name, []) if c in frame.columns])
            path = output_dir / f"{name}.csv"
            out.to_csv(path, index=False)
            counts[name] = len(out)
            log.info("wrote %-20s %9s rows -> %s", name, format(len(out), ","), path.name)
        return counts

    def run(self, output_dir: Path | None = None) -> dict[str, int]:
        with timed(log, "reference data"):
            self.build_regions()
            self.build_stores()
            self.build_products()
            self.build_customers()
            self.build_campaigns()
        with timed(log, "orders and items"):
            self.build_orders()
            self.build_order_items()
            # Now that revenue exists, size the marketing spend against it.
            self.rescale_campaign_economics()
        with timed(log, "payments"):
            self.build_payments()
        with timed(log, "inventory snapshots"):
            self.build_inventory()
        with timed(log, "customer events"):
            self.build_events()
        with timed(log, "data-quality injection"):
            self.dq_stats = self.inject_data_quality_issues()
        return self.write(output_dir or PATHS.raw)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the PulseAnalytics dataset")
    parser.add_argument("--preset", choices=sorted(PRESETS), help="dataset size preset")
    parser.add_argument("--seed", type=int, default=GENERATOR.seed)
    parser.add_argument("--customers", type=int, default=GENERATOR.customers)
    parser.add_argument("--products", type=int, default=GENERATOR.products)
    parser.add_argument("--orders", type=int, default=GENERATOR.orders)
    parser.add_argument("--events", type=int, default=GENERATOR.events)
    parser.add_argument("--campaigns", type=int, default=GENERATOR.campaigns)
    parser.add_argument("--end-date", default=GENERATOR.end_date.isoformat())
    parser.add_argument("--dirty-rate", type=float, default=0.004)
    parser.add_argument("--output", default=str(PATHS.raw))
    args = parser.parse_args(argv)
    if args.preset:
        for key, value in PRESETS[args.preset].items():
            setattr(args, key, value)
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    end = date.fromisoformat(args.end_date)
    start = end - timedelta(days=729)
    print(banner("PulseAnalytics - synthetic data generator"))
    log.info("window %s -> %s (%d days)", start, end, (end - start).days + 1)

    generator = PulseDataGenerator(
        seed=args.seed,
        n_customers=args.customers,
        n_products=args.products,
        n_orders=args.orders,
        n_events=args.events,
        n_campaigns=args.campaigns,
        start=start,
        end=end,
        dirty_rate=args.dirty_rate,
    )
    counts = generator.run(Path(args.output))

    manifest = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "seed": args.seed,
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "row_counts": counts,
        "injected_quality_issues": generator.dq_stats,
    }
    manifest_path = Path(args.output) / "_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    log.info("manifest -> %s", manifest_path)
    print("\nTotal rows: " + format(sum(counts.values()), ",") + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
