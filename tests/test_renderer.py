from __future__ import annotations

import unittest
from datetime import UTC, datetime

from astrbot_plugin_hot_market.renderer import (
    change_percent,
    money,
    prepare_dashboard,
    sparkline_points,
)


class RendererTest(unittest.TestCase):
    def test_money(self) -> None:
        self.assertEqual(money(123_456), "1,234.56")

    def test_change_percent(self) -> None:
        self.assertAlmostEqual(change_percent(125, 100), 25.0)
        self.assertEqual(change_percent(100, 0), 0.0)

    def test_dashboard_contains_fun_market_summary(self) -> None:
        rows = {
            "weibo": [
                {
                    "id": 1,
                    "rank": 1,
                    "title": "小米汽车发布新车",
                    "ticker": "WB-小米汽车",
                    "price_cents": 1_200,
                    "previous_price_cents": 1_000,
                }
            ]
        }
        dashboard = prepare_dashboard(
            rows,
            {1: [1_000, 1_200]},
            10,
            datetime(2026, 7, 30, tzinfo=UTC),
        )
        self.assertEqual(dashboard["stats"]["hot_ticker"], "WB-小米汽车")
        self.assertEqual(dashboard["stats"]["up"], 1)
        self.assertTrue(dashboard["slogan"])
        self.assertEqual(dashboard["markets"][0]["rows"][0]["rank_badge"], "🥇")

    def test_sparkline_handles_flat_and_rising_data(self) -> None:
        flat = sparkline_points([100, 100, 100])
        rising = sparkline_points([100, 110, 130])
        self.assertEqual(len(flat.split()), 3)
        self.assertEqual(len(rising.split()), 3)
        self.assertNotEqual(flat, rising)


if __name__ == "__main__":
    unittest.main()
