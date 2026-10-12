"""Behavior checks for the sample data, shared filters, and Streamlit views."""

import io
import unittest
from datetime import date
from pathlib import Path

from streamlit.testing.v1 import AppTest

from analytics import by_campaign, by_channel, by_time, filter_campaigns, load_campaigns, totals


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "campaign_performance.csv"


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_campaigns(SAMPLE)

    def test_sample_has_one_row_per_campaign_and_four_channels(self):
        self.assertEqual(len(self.data), 1000)
        self.assertEqual(self.data["campaign_id"].nunique(), 1000)
        self.assertEqual(
            set(self.data["channel"]), {"Facebook", "Instagram", "Pinterest", "Twitter"}
        )

    def test_filtered_views_reconcile_and_roi_uses_aggregate_totals(self):
        filtered = filter_campaigns(
            self.data, "2026-03-01", "2026-06-30", ["Facebook", "Pinterest"],
            ["Parents", "Small Businesses"], ["Leads", "Sales"]
        )
        self.assertGreater(len(filtered), 0)
        summary = totals(filtered)
        for view in [by_channel(filtered), by_campaign(filtered), by_time(filtered, "Week")]:
            for column in ["spend_usd", "clicks", "conversions", "revenue_usd"]:
                self.assertAlmostEqual(view[column].sum(), summary[column], places=2)
        expected_roi = (summary["revenue_usd"] - summary["spend_usd"]) / summary["spend_usd"] * 100
        self.assertAlmostEqual(summary["roi_pct"], expected_roi)

    def test_empty_filter_and_invalid_duplicate_campaign(self):
        filtered = filter_campaigns(
            self.data, "2026-01-01", "2026-09-30", [], ["Parents"], ["Sales"]
        )
        self.assertTrue(filtered.empty)
        duplicate = self.data.iloc[[0, 0]].to_csv(index=False)
        with self.assertRaisesRegex(ValueError, "campaign_id must appear only once"):
            load_campaigns(io.StringIO(duplicate))

    def test_streamlit_views_search_and_empty_state(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertEqual(
            [tab.label for tab in app.tabs],
            ["Overview", "Platform Comparison", "Campaign Details", "Time Series"],
        )
        self.assertEqual(len(app.get("plotly_chart")), 6)
        self.assertEqual(app.metric[0].value, "$483,200.37")

        app.text_input[0].set_value("CMP-0001").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.dataframe[1].value["campaign_id"].tolist(), ["CMP-0001"])

        app.multiselect[0].set_value(["Facebook"]).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "$125,414.88")
        self.assertEqual(app.dataframe[0].value["channel"].tolist(), ["Facebook"])

        app.text_input[0].set_value("").run()
        app.multiselect[1].set_value(["Parents"]).run()
        app.multiselect[2].set_value(["Sales"]).run()
        app.date_input[0].set_value((date(2026, 3, 1), date(2026, 6, 30))).run()
        expected = filter_campaigns(
            self.data, date(2026, 3, 1), date(2026, 6, 30),
            ["Facebook"], ["Parents"], ["Sales"]
        )
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, f"${totals(expected)['spend_usd']:,.2f}")
        self.assertEqual(len(app.dataframe[1].value), len(expected))
        self.assertEqual(app.dataframe[0].value["channel"].tolist(), ["Facebook"])
        self.assertEqual(len(app.get("plotly_chart")), 6)

        app.multiselect[0].set_value([]).run()
        self.assertFalse(app.exception)
        self.assertIn("No campaigns match", app.info[0].value)
        self.assertEqual(len(app.get("plotly_chart")), 0)


if __name__ == "__main__":
    unittest.main()
