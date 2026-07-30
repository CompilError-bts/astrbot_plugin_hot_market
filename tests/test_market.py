from __future__ import annotations

import unittest

from astrbot_plugin_hot_market.market import (
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

    def test_rank_price_is_monotonic(self) -> None:
        prices = [target_price_cents(rank, 30) for rank in range(1, 31)]
        self.assertEqual(prices, sorted(prices, reverse=True))
        self.assertEqual(prices[0], 10_000)
        self.assertGreaterEqual(prices[-1], 500)

    def test_smoothing_limits_one_tick_move(self) -> None:
        self.assertEqual(smooth_price_cents(1_000, 10_000), 1_250)
        self.assertEqual(smooth_price_cents(10_000, 100), 7_500)

    def test_generic_api_payload_parser(self) -> None:
        payload = {
            "code": 200,
            "data": [
                {"title": "热点一", "hot_value": 123, "link": "https://a.test"},
                {"rank": 2, "title": "热点二", "score": "99w"},
            ],
        }
        items = parse_market_payload("weibo", payload, 30)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].rank, 1)
        self.assertEqual(items[1].raw_score, "99w")
        self.assertGreater(items[0].target_price_cents, items[1].target_price_cents)


if __name__ == "__main__":
    unittest.main()
