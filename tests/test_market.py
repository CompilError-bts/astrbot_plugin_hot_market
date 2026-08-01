from __future__ import annotations

import unittest

from astrbot_plugin_hot_market.market import (
    bullish_drift_price_cents,
    extract_ticker_keywords,
    normalize_title,
    parse_market_payload,
    resolve_market,
    smooth_price_cents,
    target_price_cents,
    ticker_for,
)


class MarketRulesTest(unittest.TestCase):
    def test_market_aliases(self) -> None:
        self.assertEqual(resolve_market("微博"), "weibo")
        self.assertEqual(resolve_market("B站"), "bili")
        self.assertEqual(resolve_market("dy"), "douyin")
        self.assertIsNone(resolve_market("不存在"))

    def test_title_normalization_and_ticker_are_stable(self) -> None:
        first = normalize_title("  AI，正在改变世界！ ")
        second = normalize_title("ＡＩ 正在改变世界")
        self.assertEqual(first, second)
        self.assertEqual(
            ticker_for("weibo", first),
            ticker_for("weibo", second),
        )
        self.assertTrue(ticker_for("weibo", first).startswith("WB-"))

    def test_keyword_ticker_is_short_and_readable(self) -> None:
        keyword = extract_ticker_keywords("小米汽车发布全新车型")
        ticker = ticker_for("weibo", "小米汽车发布全新车型")
        self.assertTrue(keyword)
        self.assertLessEqual(len(keyword), 5)
        self.assertEqual(ticker, f"WB-{keyword}")
        self.assertIn("小米", ticker)

    def test_rank_price_is_monotonic(self) -> None:
        prices = [target_price_cents(rank, 30) for rank in range(1, 31)]
        self.assertEqual(prices, sorted(prices, reverse=True))
        self.assertEqual(prices[0], 10_000)
        self.assertGreaterEqual(prices[-1], 500)

    def test_smoothing_limits_one_tick_move(self) -> None:
        self.assertEqual(smooth_price_cents(1_000, 10_000), 1_250)
        self.assertEqual(smooth_price_cents(10_000, 100), 7_500)

    def test_bullish_drift_moves_slightly_and_respects_cap(self) -> None:
        self.assertEqual(bullish_drift_price_cents(10_000, 10_000), 10_002)
        self.assertEqual(bullish_drift_price_cents(10_199, 10_000), 10_200)
        self.assertEqual(bullish_drift_price_cents(10_200, 10_000), 10_200)

    def test_generic_api_payload_parser(self) -> None:
        payload = {
            "code": 200,
            "data": [
                {
                    "title": "热点一",
                    "hot_value": 123,
                    "link": "https://a.test",
                    "desc": "热点一的摘要",
                    "cover": "https://a.test/cover.jpg",
                },
                {"rank": 2, "title": "热点二", "score": "99w"},
            ],
        }
        items = parse_market_payload("weibo", payload, 30)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].rank, 1)
        self.assertEqual(items[1].raw_score, "99w")
        self.assertGreater(items[0].target_price_cents, items[1].target_price_cents)

        self.assertEqual(items[0].summary, "热点一的摘要")
        self.assertEqual(items[0].image_url, "https://a.test/cover.jpg")
        self.assertEqual(items[1].summary, "")
        self.assertEqual(items[1].image_url, "")

if __name__ == "__main__":
    unittest.main()
