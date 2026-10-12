# Ad Campaign Performance Analyzer

A Streamlit dashboard for comparing campaign spend, clicks, conversions, revenue, and ROI across Facebook, Instagram, Pinterest, and Twitter.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The project disables Streamlit's optional first-run email prompt. If a previous run is still waiting at `Email:`, press Enter with the field blank, or stop it and run the command again.

The app loads `data/campaign_performance.csv` by default. Use the sidebar to upload another CSV with the same columns, or download the included sample.

## Data model

The included CSV contains **1,000 distinct campaigns**, one row per campaign. `date` is the campaign reporting date. Time Series groups campaign results by that date, so it shows portfolio trends rather than changes within an individual campaign.

Required columns: `date`, `campaign_id`, `campaign_name`, `channel`, `audience`, `goal`, `spend_usd`, `impressions`, `clicks`, `conversions`, `revenue_usd`.

ROI is `(revenue_usd - spend_usd) / spend_usd × 100`. The dashboard calculates ROI from summed revenue and spend after filtering and grouping. ROI is undefined when spend is zero. Conversion rate is `conversions / clicks × 100`; cost per conversion is `spend_usd / conversions`.

To recreate the sample CSV deterministically:

```bash
python3 generate_sample_data.py
```

Run the dashboard checks with:

```bash
python -m unittest discover -s tests -v
```
