from __future__ import annotations

import unittest
from datetime import UTC, datetime

from astrbot_plugin_hot_market.daily_analysis import (
    build_daily_analysis_prompt,
    parse_daily_time,
    seconds_until_next_run,
)


class DailyAnalysisTest(unittest.TestCase):
    def test_daily_time_parser(self) -> None:
        self.assertEqual(parse_daily_time("20:30"), (20, 30))
        for invalid in ("8:30", "24:00", "20:60", "tomorrow"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    parse_daily_time(invalid)

    def test_seconds_until_next_run_rolls_to_tomorrow(self) -> None:
        now = datetime(2026, 7, 30, 20, 30, tzinfo=UTC)
        self.assertEqual(seconds_until_next_run(now, 20, 31), 60)
        self.assertEqual(seconds_until_next_run(now, 20, 30), 24 * 60 * 60)

    def test_prompt_contains_member_positions_and_data_boundary(self) -> None:
        prompt = build_daily_analysis_prompt(
            [
                {
                    "user_name": "Alice",
                    "cash_cents": 50_000,
                    "net_asset_cents": 120_000,
                    "positions": [
                        {
                            "ticker": "WB-小米汽车",
                            "title": "小米汽车发布新车",
                            "shares": 10,
                            "profit_cents": 20_000,
                        }
                    ],
                }
            ],
            100_000,
        )
        self.assertIn("Alice", prompt)
        self.assertIn("WB-小米汽车", prompt)
        self.assertIn("<data>", prompt)
        self.assertIn("虚拟盘仅供娱乐", prompt)


if __name__ == "__main__":
    unittest.main()
