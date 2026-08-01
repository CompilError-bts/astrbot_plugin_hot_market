from __future__ import annotations

import unittest
from datetime import UTC, datetime

from astrbot_plugin_hot_market.renderer import (
    change_percent,
    compact_money,
    format_market_text,
    format_stock_detail_text,
    money,
    prepare_dashboard,
    prepare_stock_detail,
    sparkline_points,
)


class RendererTest(unittest.TestCase):
    def test_money(self) -> None:
        self.assertEqual(money(123_456), "1,234.56")

    def test_compact_money_uses_ten_thousand_unit(self) -> None:
        self.assertEqual(compact_money(999_999), "9,999.99")
        self.assertEqual(compact_money(1_000_000), "1万")
        self.assertEqual(compact_money(1_250_000), "1.25万")
        self.assertEqual(compact_money(-1_250_000), "-1.25万")

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
        summary_rows = {
            "weibo": [
                rows["weibo"][0],
                {
                    "id": 2,
                    "rank": None,
                    "status": "fading",
                    "title": "昨日热点",
                    "ticker": "WB-昨日热点",
                    "price_cents": 970,
                    "previous_price_cents": 1_000,
                },
            ]
        }
        dashboard = prepare_dashboard(
            rows,
            {1: [1_000, 1_200]},
            10,
            datetime(2026, 7, 30, tzinfo=UTC),
            summary_rows=summary_rows,
        )
        self.assertEqual(dashboard["stats"]["hot_ticker"], "WB-小米汽车")
        self.assertEqual(dashboard["stats"]["up"], 1)
        self.assertEqual(dashboard["stats"]["down"], 1)
        self.assertEqual(dashboard["stats"]["total"], 2)
        self.assertEqual(dashboard["stats"]["active"], 1)
        self.assertEqual(dashboard["stats"]["fading"], 1)
        self.assertTrue(dashboard["slogan"])
        self.assertEqual(dashboard["markets"][0]["rows"][0]["rank_badge"], "🥇")

    def test_full_market_text_marks_fading_stocks(self) -> None:
        text = format_market_text(
            {
                "weibo": [
                    {
                        "rank": 1,
                        "status": "active",
                        "missing_count": 0,
                        "title": "今日热点",
                        "ticker": "WB-今日热点",
                        "price_cents": 1_200,
                        "previous_price_cents": 1_000,
                    },
                    {
                        "rank": None,
                        "status": "fading",
                        "missing_count": 1,
                        "title": "昨日热点",
                        "ticker": "WB-昨日热点",
                        "price_cents": 970,
                        "previous_price_cents": 1_000,
                    },
                ]
            },
            None,
        )
        self.assertIn("共 2 只｜在榜 1｜离榜观察 1", text)
        self.assertIn("#01 WB-今日热点", text)
        self.assertIn("离榜1轮 WB-昨日热点", text)
        self.assertIn("仅可卖出", text)

    def test_sparkline_handles_flat_and_rising_data(self) -> None:
        flat = sparkline_points([100, 100, 100])
        rising = sparkline_points([100, 110, 130])
        self.assertEqual(len(flat.split()), 3)
        self.assertEqual(len(rising.split()), 3)
        self.assertNotEqual(flat, rising)

    def test_stock_detail_contains_large_trend_chart_data(self) -> None:
        detail = prepare_stock_detail(
            {
                "source": "weibo",
                "rank": 1,
                "status": "active",
                "title": "小米汽车发布新车",
                "ticker": "WB-小米汽车",
                "price_cents": 1_200,
                "previous_price_cents": 1_100,
                "updated_at": "2026-07-30T13:30:00+00:00",
            },
            [1_000, 1_100, 1_200],
        )
        self.assertEqual(detail["ticker"], "WB-小米汽车")
        self.assertEqual(detail["rank_text"], "榜单 #1")
        self.assertEqual(detail["change_class"], "up")
        self.assertEqual(detail["trend_class"], "up")
        self.assertEqual(len(detail["sparkline"].split()), 3)
        self.assertTrue(detail["area"].startswith("18,202 "))
        self.assertEqual(detail["point_count"], 3)

    def test_stock_detail_text_contains_summary_and_original_link(self) -> None:
        stock = {
            "source": "baidu",
            "rank": 2,
            "status": "active",
            "title": "测试热点",
            "ticker": "BD-测试热点",
            "price_cents": 1_200,
            "previous_price_cents": 1_100,
            "summary": "这是榜单提供的摘要。",
            "link": "https://example.test/topic",
        }
        text = format_stock_detail_text(stock, [1_000, 1_100, 1_200])
        self.assertIn("📰 BD-测试热点 · 热搜资讯", text)
        self.assertIn("摘要：这是榜单提供的摘要。", text)
        self.assertIn("原文：https://example.test/topic", text)

    def test_stock_detail_text_gracefully_handles_missing_info(self) -> None:
        stock = {
            "source": "weibo",
            "rank": None,
            "status": "fading",
            "title": "旧热点",
            "ticker": "WB-旧热点",
            "price_cents": 970,
            "previous_price_cents": 1_000,
            "summary": "",
            "link": "",
        }
        text = format_stock_detail_text(stock, [1_000, 970])
        self.assertIn("该平台榜单暂未提供摘要", text)
        self.assertIn("该平台榜单暂未提供原文链接", text)
        self.assertIn("排名：已离榜｜状态：离榜观察", text)


if __name__ == "__main__":
    unittest.main()
