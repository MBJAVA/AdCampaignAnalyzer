"""Generate a reproducible CSV with one row per distinct campaign."""

import csv
import random
from datetime import date, timedelta
from pathlib import Path


OUTPUT = Path(__file__).parent / "data" / "campaign_performance.csv"
SEED = 42
ROW_COUNT = 1000

PLATFORMS = ["Facebook", "Instagram", "Pinterest", "Twitter"]
AUDIENCES = ["Young Professionals", "Parents", "Home & Lifestyle", "Small Businesses"]
CAMPAIGNS = [
    ("Brand Discovery", "Awareness"),
    ("New Visitors", "Traffic"),
    ("Lead Builder", "Leads"),
    ("Core Sales", "Sales"),
    ("Seasonal Offers", "Sales"),
    ("Newsletter Growth", "Leads"),
]

GOAL_SETTINGS = {
    "Awareness": (0.009, 0.006, 55),
    "Traffic": (0.015, 0.010, 70),
    "Leads": (0.012, 0.025, 90),
    "Sales": (0.013, 0.022, 125),
}
PLATFORM_SETTINGS = {
    "Facebook": (12.0, 1.00),
    "Instagram": (14.0, 1.08),
    "Pinterest": (10.0, 0.92),
    "Twitter": (11.0, 0.88),
}


def generate_rows():
    rng = random.Random(SEED)
    start = date(2026, 1, 1)
    day_count = (date(2026, 9, 30) - start).days + 1
    for campaign_number in range(1, ROW_COUNT + 1):
        platform_index = (campaign_number - 1) % len(PLATFORMS)
        campaign_index = ((campaign_number - 1) // len(PLATFORMS)) % len(CAMPAIGNS)
        day_index = rng.randrange(day_count)
        platform = PLATFORMS[platform_index]
        campaign_label, goal = CAMPAIGNS[campaign_index]
        audience = AUDIENCES[((campaign_number - 1) // 24 + campaign_index + platform_index) % len(AUDIENCES)]
        cpm, channel_factor = PLATFORM_SETTINGS[platform]
        ctr, conversion_rate, order_value = GOAL_SETTINGS[goal]

        seasonal_factor = 1.12 if day_index >= 180 else 1.0
        spend = round(rng.uniform(120, 850) * seasonal_factor * channel_factor, 2)
        impressions = round(spend / (cpm * rng.uniform(0.87, 1.14)) * 1000)
        clicks = min(impressions, round(impressions * ctr * rng.uniform(0.75, 1.30)))
        conversions = min(clicks, round(clicks * conversion_rate * rng.uniform(0.65, 1.45)))
        revenue = round(conversions * order_value * rng.uniform(0.80, 1.25), 2)

        yield {
            "date": (start + timedelta(days=day_index)).isoformat(),
            "campaign_id": f"CMP-{campaign_number:04d}",
            "campaign_name": f"{platform} | {campaign_label} {campaign_number:04d}",
            "channel": platform,
            "audience": audience,
            "goal": goal,
            "spend_usd": spend,
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "revenue_usd": revenue,
        }


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    rows = list(generate_rows())
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUTPUT}")


if __name__ == "__main__":
    main()
