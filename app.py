"""Streamlit dashboard for campaign performance across advertising channels."""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from analytics import by_campaign, by_channel, by_time, filter_campaigns, load_campaigns, totals


SAMPLE_CSV = Path(__file__).parent / "data" / "campaign_performance.csv"
CHANNEL_ORDER = ["Facebook", "Instagram", "Pinterest", "Twitter"]
CHANNEL_COLORS = {
    "Facebook": "#2563eb",
    "Instagram": "#d9468f",
    "Pinterest": "#dc2626",
    "Twitter": "#0891b2",
}
METRICS = {
    "Spend (USD)": ("spend_usd", "Spend (USD)"),
    "Clicks (count)": ("clicks", "Clicks (count)"),
    "Conversions (count)": ("conversions", "Conversions (count)"),
    "Revenue (USD)": ("revenue_usd", "Revenue (USD)"),
    "ROI (%)": ("roi_pct", "ROI (%)"),
    "Conversion rate (%)": ("conversion_rate_pct", "Conversion rate (%)"),
    "Cost per conversion (USD)": ("cost_per_conversion_usd", "Cost per conversion (USD)"),
}


def money(value):
    return f"${value:,.2f}"


def percent(value):
    return "N/A" if pd.isna(value) else f"{value:,.1f}%"


def chart_style(fig, height=330):
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=18, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#334155"),
        legend_title_text="",
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#e7edf4", zerolinecolor="#e7edf4")
    return fig


def show_chart(fig):
    st.plotly_chart(chart_style(fig), config={"displayModeBar": False})


def overview(data):
    summary = totals(data)
    st.subheader("Overview")
    st.caption(f"{len(data):,} campaigns · All figures reflect the global filters")
    metric_columns = st.columns(5)
    values = [
        ("Spend (USD)", money(summary["spend_usd"])),
        ("Clicks (count)", f"{summary['clicks']:,.0f}"),
        ("Conversions (count)", f"{summary['conversions']:,.0f}"),
        ("Revenue (USD)", money(summary["revenue_usd"])),
        ("ROI (%)", percent(summary["roi_pct"])),
    ]
    for column, (label, value) in zip(metric_columns, values):
        column.metric(label, value)

    st.markdown("#### Spend and conversions over time")
    st.caption("Weekly totals by campaign reporting date. Partial weeks include only dates in the selected range.")
    weekly = by_time(data, "Week")
    left, right = st.columns(2)
    with left:
        fig = px.bar(weekly, x="period", y="spend_usd", labels={"period": "Week of", "spend_usd": "Spend (USD)"})
        fig.update_traces(marker_color="#2563eb", hovertemplate="Week of %{x|%b %d, %Y}<br>Spend: $%{y:,.2f}<extra></extra>")
        show_chart(fig)
    with right:
        fig = px.line(weekly, x="period", y="conversions", markers=True,
                      labels={"period": "Week of", "conversions": "Conversions (count)"})
        fig.update_traces(line_color="#16a34a", hovertemplate="Week of %{x|%b %d, %Y}<br>Conversions: %{y:,.0f}<extra></extra>")
        show_chart(fig)


def platform_comparison(data):
    st.subheader("Platform Comparison")
    st.caption("Channel totals and ROI are calculated from the same filtered campaigns.")
    grouped = by_channel(data)
    ordered = [name for name in CHANNEL_ORDER if name in grouped["channel"].tolist()]
    ordered += [name for name in grouped["channel"] if name not in ordered]

    left, right = st.columns(2)
    with left:
        long = grouped.melt(id_vars="channel", value_vars=["spend_usd", "revenue_usd"],
                            var_name="Metric", value_name="USD")
        long["Metric"] = long["Metric"].map({"spend_usd": "Spend", "revenue_usd": "Revenue"})
        fig = px.bar(long, x="channel", y="USD", color="Metric", barmode="group",
                     category_orders={"channel": ordered},
                     color_discrete_map={"Spend": "#2563eb", "Revenue": "#16a34a"},
                     labels={"channel": "Channel", "USD": "USD"})
        fig.update_traces(hovertemplate="%{x}<br>%{fullData.name}: $%{y:,.2f}<extra></extra>")
        show_chart(fig)
    with right:
        fig = px.bar(grouped, x="channel", y="conversions", color="channel",
                     category_orders={"channel": ordered}, color_discrete_map=CHANNEL_COLORS,
                     labels={"channel": "Channel", "conversions": "Conversions (count)"})
        fig.update_layout(showlegend=False)
        fig.update_traces(hovertemplate="%{x}<br>Conversions: %{y:,.0f}<extra></extra>")
        show_chart(fig)

    st.markdown("#### ROI by channel")
    roi_fig = px.bar(grouped, x="roi_pct", y="channel", orientation="h", color="channel",
                     category_orders={"channel": ordered}, color_discrete_map=CHANNEL_COLORS,
                     labels={"channel": "Channel", "roi_pct": "ROI (%)"})
    roi_fig.update_layout(showlegend=False)
    roi_fig.update_traces(hovertemplate="%{y}<br>ROI: %{x:,.1f}%<extra></extra>")
    st.plotly_chart(chart_style(roi_fig, height=230), config={"displayModeBar": False})

    st.markdown("#### Channel metrics")
    display = grouped[["channel", "spend_usd", "clicks", "conversions", "revenue_usd",
                       "roi_pct", "conversion_rate_pct", "cost_per_conversion_usd"]]
    st.dataframe(
        display,
        hide_index=True,
        width="stretch",
        column_config={
            "channel": "Channel",
            "spend_usd": st.column_config.NumberColumn("Spend (USD)", format="$%.2f"),
            "clicks": st.column_config.NumberColumn("Clicks (count)", format="%d"),
            "conversions": st.column_config.NumberColumn("Conversions (count)", format="%d"),
            "revenue_usd": st.column_config.NumberColumn("Revenue (USD)", format="$%.2f"),
            "roi_pct": st.column_config.NumberColumn("ROI (%)", format="%.1f%%"),
            "conversion_rate_pct": st.column_config.NumberColumn("Conversion rate (%)", format="%.1f%%"),
            "cost_per_conversion_usd": st.column_config.NumberColumn("Cost / conversion (USD)", format="$%.2f"),
        },
    )


def campaign_details(data):
    st.subheader("Campaign Details")
    st.caption("Search within campaigns matching the global filters. One CSV row represents one campaign.")
    search = st.text_input("Search campaign name or ID", placeholder="e.g. Seasonal Offers or CMP-0042")
    campaigns = by_campaign(data)
    if search.strip():
        match = (
            campaigns["campaign_name"].str.contains(search.strip(), case=False, regex=False, na=False)
            | campaigns["campaign_id"].str.contains(search.strip(), case=False, regex=False, na=False)
        )
        campaigns = campaigns.loc[match]
    if campaigns.empty:
        st.info("No campaigns match this search. Try another name or campaign ID.")
        return

    st.caption(f"Showing {len(campaigns):,} campaign{'s' if len(campaigns) != 1 else ''}")
    display = campaigns[["campaign_id", "campaign_name", "report_date", "channel",
                         "audience", "goal", "spend_usd", "clicks", "conversions",
                         "revenue_usd", "roi_pct"]]
    st.dataframe(
        display,
        hide_index=True,
        width="stretch",
        height=480,
        column_config={
            "campaign_id": "Campaign ID",
            "campaign_name": "Campaign",
            "report_date": st.column_config.DateColumn("Reporting date", format="YYYY-MM-DD"),
            "channel": "Channel",
            "audience": "Audience",
            "goal": "Goal",
            "spend_usd": st.column_config.NumberColumn("Spend (USD)", format="$%.2f"),
            "clicks": st.column_config.NumberColumn("Clicks (count)", format="%d"),
            "conversions": st.column_config.NumberColumn("Conversions (count)", format="%d"),
            "revenue_usd": st.column_config.NumberColumn("Revenue (USD)", format="$%.2f"),
            "roi_pct": st.column_config.NumberColumn("ROI (%)", format="%.1f%%"),
        },
    )
    st.download_button(
        "Download displayed campaigns (CSV)",
        display.to_csv(index=False).encode("utf-8"),
        file_name="filtered_campaigns.csv",
        mime="text/csv",
    )


def time_series(data):
    st.subheader("Time Series")
    st.caption("Performance is grouped by campaign reporting date. Each campaign contributes to one date.")
    left, middle, right = st.columns([1, 1.6, 1])
    with left:
        granularity = st.selectbox("Group by", ["Day", "Week", "Month"], index=1)
    with middle:
        selected_metric = st.selectbox("Metric", list(METRICS), index=2)
    with right:
        split_channel = st.checkbox("Split by channel", value=True)
    metric, axis_label = METRICS[selected_metric]
    series = by_time(data, granularity, split_channel)
    fig = px.line(
        series, x="period", y=metric, color="channel" if split_channel else None,
        markers=True, color_discrete_map=CHANNEL_COLORS if split_channel else None,
        labels={"period": f"{granularity} of reporting date", metric: axis_label, "channel": "Channel"},
        category_orders={"channel": CHANNEL_ORDER},
    )
    if not split_channel:
        fig.update_traces(line_color="#2563eb")
    fig.update_layout(height=450)
    show_chart(fig)
    if metric in {"roi_pct", "conversion_rate_pct", "cost_per_conversion_usd"}:
        st.caption("Rate and cost metrics are recalculated from each period's totals; they are not averages of campaign values.")


def main():
    st.set_page_config(page_title="Ad Campaign Performance Analyzer", page_icon="📊", layout="wide")
    st.title("Ad Campaign Performance Analyzer")
    st.caption("Compare spend, clicks, conversions, revenue, and ROI across your advertising channels.")

    with st.sidebar:
        st.header("Data & filters")
        upload = st.file_uploader("Upload campaign CSV (optional)", type="csv")
        if upload is None:
            source = SAMPLE_CSV
            st.caption("Using the included 1,000-campaign sample CSV.")
            st.download_button("Download sample CSV", SAMPLE_CSV.read_bytes(),
                               file_name="campaign_performance.csv", mime="text/csv")
        else:
            source = upload
            st.caption("Using your uploaded CSV. It needs the same columns as the sample.")

    try:
        data = load_campaigns(source)
    except (ValueError, pd.errors.ParserError, UnicodeDecodeError, OSError) as error:
        st.error(f"Could not load the campaign CSV: {error}")
        st.stop()

    min_date = data["date"].min().date()
    max_date = data["date"].max().date()
    with st.sidebar:
        st.divider()
        dates = st.date_input("Reporting date range", value=(min_date, max_date),
                              min_value=min_date, max_value=max_date)
        channels = st.multiselect("Channel", sorted(data["channel"].unique()),
                                  default=sorted(data["channel"].unique()))
        audiences = st.multiselect("Audience", sorted(data["audience"].unique()),
                                   default=sorted(data["audience"].unique()))
        goals = st.multiselect("Campaign goal", sorted(data["goal"].unique()),
                               default=sorted(data["goal"].unique()))
        st.divider()
        st.caption("ROI (%) = (revenue − spend) ÷ spend × 100. ROI is N/A when spend is zero.")

    if not isinstance(dates, (tuple, list)) or len(dates) != 2:
        st.info("Select both a start and end date to view campaign results.")
        st.stop()
    filtered = filter_campaigns(data, dates[0], dates[1], channels, audiences, goals)
    if filtered.empty:
        st.info("No campaigns match the selected filters. Widen the date range or select more channels, audiences, or goals.")
        st.stop()

    tab_overview, tab_platform, tab_campaign, tab_time = st.tabs(
        ["Overview", "Platform Comparison", "Campaign Details", "Time Series"]
    )
    with tab_overview:
        overview(filtered)
    with tab_platform:
        platform_comparison(filtered)
    with tab_campaign:
        campaign_details(filtered)
    with tab_time:
        time_series(filtered)


if __name__ == "__main__":
    main()
