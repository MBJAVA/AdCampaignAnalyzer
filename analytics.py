"""Shared loading, filtering, and aggregation for every dashboard view."""

import pandas as pd


REQUIRED_COLUMNS = [
    "date", "campaign_id", "campaign_name", "channel", "audience", "goal",
    "spend_usd", "impressions", "clicks", "conversions", "revenue_usd",
]
DIMENSIONS = ["campaign_id", "campaign_name", "channel", "audience", "goal"]
MEASURES = ["spend_usd", "impressions", "clicks", "conversions", "revenue_usd"]


def load_campaigns(source):
    """Read a sample or uploaded CSV and reject records that would skew metrics."""
    data = pd.read_csv(source)
    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    if data.empty:
        raise ValueError("The CSV has no campaign rows.")

    data = data[REQUIRED_COLUMNS].copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    if data["date"].isna().any():
        raise ValueError("The date column contains invalid dates. Use YYYY-MM-DD.")
    for column in DIMENSIONS:
        data[column] = data[column].astype("string").str.strip()
        if data[column].isna().any() or data[column].eq("").any():
            raise ValueError(f"The {column} column contains blank values.")
    for column in MEASURES:
        data[column] = pd.to_numeric(data[column], errors="coerce")
        if data[column].isna().any() or (data[column] < 0).any():
            raise ValueError(f"The {column} column must contain nonnegative numbers.")
    for column in ["impressions", "clicks", "conversions"]:
        if (data[column] % 1 != 0).any():
            raise ValueError(f"The {column} column must contain whole numbers.")
        data[column] = data[column].astype("int64")
    if (data["clicks"] > data["impressions"]).any():
        raise ValueError("Clicks cannot exceed impressions.")
    if (data["conversions"] > data["clicks"]).any():
        raise ValueError("Conversions cannot exceed clicks.")
    if data["campaign_id"].duplicated().any():
        raise ValueError("Each campaign_id must appear only once in a one-row-per-campaign CSV.")
    return data.sort_values("date").reset_index(drop=True)


def filter_campaigns(data, start_date, end_date, channels, audiences, goals):
    return data.loc[
        data["date"].between(pd.Timestamp(start_date), pd.Timestamp(end_date))
        & data["channel"].isin(channels)
        & data["audience"].isin(audiences)
        & data["goal"].isin(goals)
    ].copy()


def add_rates(data):
    """Calculate ratios from aggregate totals; never average row-level ROI."""
    result = data.copy()
    result["roi_pct"] = ((result["revenue_usd"] - result["spend_usd"])
                         / result["spend_usd"].where(result["spend_usd"] != 0) * 100)
    result["conversion_rate_pct"] = (
        result["conversions"] / result["clicks"].where(result["clicks"] != 0) * 100
    )
    result["cost_per_conversion_usd"] = (
        result["spend_usd"] / result["conversions"].where(result["conversions"] != 0)
    )
    return result


def totals(data):
    summed = pd.DataFrame([{column: data[column].sum() for column in MEASURES}])
    return add_rates(summed).iloc[0]


def by_channel(data):
    grouped = data.groupby("channel", as_index=False, observed=True)[MEASURES].sum()
    return add_rates(grouped).sort_values("spend_usd", ascending=False)


def by_campaign(data):
    # The loader enforces one row per campaign, so no campaign aggregation is needed.
    return add_rates(data.rename(columns={"date": "report_date"})).sort_values(
        "spend_usd", ascending=False
    )


def by_time(data, granularity="Day", split_channel=False):
    working = data.copy()
    if granularity == "Week":
        working["period"] = working["date"].dt.to_period("W-SUN").dt.start_time
    elif granularity == "Month":
        working["period"] = working["date"].dt.to_period("M").dt.start_time
    else:
        working["period"] = working["date"]
    keys = ["period", "channel"] if split_channel else ["period"]
    grouped = working.groupby(keys, as_index=False, observed=True)[MEASURES].sum()
    return add_rates(grouped).sort_values(keys)
