from __future__ import annotations

import tempfile
from dataclasses import replace
import unittest
from pathlib import Path

from astrbot_plugin_hot_market.market import parse_market_payload
from astrbot_plugin_hot_market.storage import MarketDatabase, TradeError


def sample_items():
    return parse_market_payload(
        "weibo",
        {
            "code": 200,
            "data": [
                {"title": f"测试热点{i}", "hot_value": 10_000 - i} for i in range(1, 11)
            ],
        },
        30,
    )


class StorageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = MarketDatabase(Path(self.temp_dir.name) / "market.db")

    def tearDown(self) -> None:
        self.database.close()
        self.temp_dir.cleanup()

    def test_snapshot_buy_sell_and_group_isolation(self) -> None:
        stats = self.database.apply_market_snapshot("weibo", sample_items())
        self.assertEqual(stats["listed"], 10)
        stock = self.database.market_rows("weibo", 10)[5]

        bought = self.database.buy(
            group_id="group-a",
            user_id="user-1",
            user_name="Alice",
            ticker=stock["ticker"],
            budget_cents=30_000,
            starting_cash_cents=100_000,
            fee_rate=0.005,
            max_position_ratio=0.35,
        )
        self.assertGreater(bought["shares"], 0)

        portfolio = self.database.portfolio(
            "group-a",
            "user-1",
            "Alice",
            100_000,
        )
        self.assertEqual(len(portfolio["positions"]), 1)

        isolated = self.database.portfolio(
            "group-b",
            "user-1",
            "Alice",
            100_000,
        )
        self.assertEqual(isolated["net_asset_cents"], 100_000)
        self.assertEqual(isolated["positions"], [])

        sold = self.database.sell(
            group_id="group-a",
            user_id="user-1",
            user_name="Alice",
            ticker=stock["ticker"],
            shares_to_sell=None,
            starting_cash_cents=100_000,
            fee_rate=0.005,
        )
        self.assertEqual(sold["shares"], bought["shares"])
        self.assertEqual(
            self.database.portfolio(
                "group-a",
                "user-1",
                "Alice",
                100_000,
            )["positions"],
            [],
        )

    def test_ticker_collision_gets_stable_suffix(self) -> None:
        first, second = sample_items()[:2]
        second = replace(second, ticker=first.ticker)
        self.database.apply_market_snapshot("weibo", [first, second])
        tickers = [row["ticker"] for row in self.database.market_rows("weibo", 10)]
        self.assertEqual(len(set(tickers)), 2)
        self.assertIn(first.ticker, tickers)
        self.assertTrue(any(ticker.startswith(f"{first.ticker}-") for ticker in tickers))

    def test_legacy_ticker_alias_survives_keyword_migration(self) -> None:
        current = sample_items()[0]
        legacy = replace(current, ticker="WB-ABC12345")
        self.database.apply_market_snapshot("weibo", [legacy])
        legacy_stock = self.database.stock(legacy.ticker)

        self.database.apply_market_snapshot("weibo", [current])
        migrated = self.database.stock(current.ticker)
        via_legacy_alias = self.database.stock(legacy.ticker)
        self.assertEqual(migrated["id"], legacy_stock["id"])
        self.assertEqual(via_legacy_alias["id"], migrated["id"])
        self.assertEqual(migrated["ticker"], current.ticker)

    def test_unchanged_ranks_drift_up_without_flat_market(self) -> None:
        items = sample_items()
        self.database.apply_market_snapshot("weibo", items)
        before = {
            row["ticker"]: int(row["price_cents"])
            for row in self.database.market_rows("weibo", 20)
        }

        self.database.apply_market_snapshot("weibo", items)
        after = {
            row["ticker"]: int(row["price_cents"])
            for row in self.database.market_rows("weibo", 20)
        }

        self.assertEqual(before.keys(), after.keys())
        self.assertTrue(all(after[ticker] > price for ticker, price in before.items()))

    def test_rankings_and_analysis_only_include_trading_participants(self) -> None:
        self.database.apply_market_snapshot("weibo", sample_items())
        stock = self.database.market_rows("weibo", 10)[0]
        self.database.portfolio(
            "group",
            "spectator",
            "只看不买",
            100_000,
        )
        self.assertEqual(self.database.leaderboard("group"), [])
        self.assertEqual(self.database.analysis_members("group"), [])
        self.assertEqual(self.database.group_ids_with_participants(), [])

        self.database.buy(
            group_id="group",
            user_id="trader",
            user_name="参与者",
            ticker=stock["ticker"],
            budget_cents=30_000,
            starting_cash_cents=100_000,
            fee_rate=0.005,
            max_position_ratio=0.35,
        )

        ranking = self.database.leaderboard("group")
        analysis = self.database.analysis_members("group")
        self.assertEqual([row["user_id"] for row in ranking], ["trader"])
        self.assertEqual([row["user_id"] for row in analysis], ["trader"])
        self.assertEqual(self.database.group_ids_with_participants(), ["group"])

    def test_delist_alert_groups_holders_and_resets_after_relisting(self) -> None:
        items = sample_items()
        self.database.apply_market_snapshot("weibo", items)
        stock = self.database.market_rows("weibo", 10)[0]
        initial_price = int(stock["price_cents"])
        for user_id, user_name in (("u1", "甲"), ("u2", "乙")):
            self.database.buy(
                group_id="group",
                user_id=user_id,
                user_name=user_name,
                ticker=stock["ticker"],
                budget_cents=30_000,
                starting_cash_cents=100_000,
                fee_rate=0.005,
                max_position_ratio=0.35,
            )

        remaining = items[1:]
        self.database.apply_market_snapshot(
            "weibo",
            remaining,
            delist_after_misses=3,
        )
        faded = self.database.stock(stock["ticker"])
        self.assertEqual(faded["status"], "fading")
        self.assertEqual(
            faded["price_cents"],
            round(initial_price * 0.97),
        )
        tradable = self.database.tradable_market_rows("weibo")
        self.assertEqual(len(tradable), len(items))
        self.assertEqual(tradable[-1]["ticker"], stock["ticker"])
        self.assertEqual(tradable[-1]["status"], "fading")

        alerts = self.database.claim_delist_alerts("group")
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["ticker"], stock["ticker"])
        self.assertEqual(
            [member["user_id"] for member in alerts[0]["members"]],
            ["u1", "u2"],
        )
        self.assertEqual(self.database.claim_delist_alerts("group"), [])

        self.database.apply_market_snapshot("weibo", items)
        self.database.apply_market_snapshot(
            "weibo",
            remaining,
            delist_after_misses=3,
        )
        repeated_alerts = self.database.claim_delist_alerts("group")
        self.assertEqual(len(repeated_alerts), 1)
        self.assertEqual(
            [member["user_id"] for member in repeated_alerts[0]["members"]],
            ["u1", "u2"],
        )

    def test_position_limit_is_enforced(self) -> None:
        self.database.apply_market_snapshot("weibo", sample_items())
        stock = self.database.market_rows("weibo", 10)[0]
        with self.assertRaises(TradeError):
            self.database.buy(
                group_id="group",
                user_id="user",
                user_name="Bob",
                ticker=stock["ticker"],
                budget_cents=90_000,
                starting_cash_cents=100_000,
                fee_rate=0.005,
                max_position_ratio=0.35,
            )

    def test_missing_stock_decays_and_delists(self) -> None:
        self.database.apply_market_snapshot("weibo", sample_items())
        ticker = self.database.market_rows("weibo", 1)[0]["ticker"]
        initial_price = int(self.database.stock(ticker)["price_cents"])
        self.database.apply_market_snapshot(
            "weibo",
            [],
            delist_after_misses=3,
        )
        fading = self.database.stock(ticker)
        self.assertEqual(fading["price_cents"], round(initial_price * 0.97))
        for _ in range(2):
            self.database.apply_market_snapshot(
                "weibo",
                [],
                delist_after_misses=3,
            )
        stock = self.database.stock(ticker)
        self.assertEqual(stock["status"], "delisted")
        self.assertEqual(stock["price_cents"], 100)
        self.assertEqual(self.database.tradable_market_rows("weibo"), [])


if __name__ == "__main__":
    unittest.main()
