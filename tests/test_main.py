from __future__ import annotations

import asyncio
import unittest
from typing import Any

import astrbot.api.message_components as Comp
from astrbot_plugin_hot_market.main import HotMarketPlugin


def sample_alert() -> dict[str, Any]:
    return {
        "stock_id": 7,
        "ticker": "WB-测试热点",
        "title": "测试热点",
        "source": "weibo",
        "status": "fading",
        "members": [
            {"user_id": "10001", "user_name": "甲", "shares": 3},
            {"user_id": "10002", "user_name": "乙", "shares": 5},
        ],
    }


class StubDatabase:
    def __init__(self) -> None:
        self.claimed_groups: list[str] = []
        self.released: list[tuple[str, int]] = []

    def group_ids_with_participants(self) -> list[str]:
        return ["allowed", "blocked"]

    def claim_delist_alerts(self, group_id: str) -> list[dict[str, Any]]:
        self.claimed_groups.append(group_id)
        return [sample_alert()]

    def release_delist_alert(self, group_id: str, stock_id: int) -> None:
        self.released.append((group_id, stock_id))


class StubContext:
    def __init__(self, sent: bool) -> None:
        self.sent = sent
        self.messages: list[tuple[str, Any]] = []

    async def send_message(self, umo: str, chain: Any) -> bool:
        self.messages.append((umo, chain))
        return self.sent


class StubEvent:
    def __init__(self, platform_name: str) -> None:
        self.platform_name = platform_name

    def get_platform_name(self) -> str:
        return self.platform_name

    def get_self_id(self) -> str:
        return "3141127974"


class FullMarketForwardTest(unittest.TestCase):
    @staticmethod
    def plugin() -> HotMarketPlugin:
        plugin = object.__new__(HotMarketPlugin)
        plugin.full_market_node_chars = 500
        plugin.full_market_nodes_per_forward = 3
        return plugin

    def test_aiocqhttp_uses_batched_multi_node_forwards(self) -> None:
        text = "\n".join("行情行 " + "热点" * 30 for _ in range(80))
        chains = self.plugin()._full_market_chains(StubEvent("aiocqhttp"), text)

        self.assertGreater(len(chains), 1)
        for chain in chains:
            self.assertEqual(len(chain), 1)
            self.assertIsInstance(chain[0], Comp.Nodes)
            self.assertLessEqual(len(chain[0].nodes), 3)
            for node in chain[0].nodes:
                self.assertEqual(node.uin, "3141127974")
                self.assertEqual(node.name, "热搜交易所")
                self.assertEqual(len(node.content), 1)
                self.assertIsInstance(node.content[0], Comp.Plain)
                self.assertLessEqual(len(node.content[0].text), 500)

    def test_reported_15907_character_payload_is_split_safely(self) -> None:
        plugin = self.plugin()
        plugin.full_market_node_chars = 1200
        plugin.full_market_nodes_per_forward = 4

        chains = plugin._full_market_chains(
            StubEvent("aiocqhttp"),
            "热" * 15907,
        )
        nodes = [node for chain in chains for node in chain[0].nodes]

        self.assertEqual(len(nodes), 14)
        self.assertEqual(len(chains), 4)
        self.assertTrue(
            all(len(node.content[0].text) <= 1200 for node in nodes)
        )

    def test_non_qq_platform_keeps_one_plain_message(self) -> None:
        text = "全量行情" * 1000
        chains = self.plugin()._full_market_chains(StubEvent("telegram"), text)

        self.assertEqual(len(chains), 1)
        self.assertEqual(len(chains[0]), 1)
        self.assertIsInstance(chains[0][0], Comp.Plain)
        self.assertEqual(chains[0][0].text, text)


class ProactiveDelistAlertTest(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def plugin(sent: bool = True) -> HotMarketPlugin:
        plugin = object.__new__(HotMarketPlugin)
        plugin.delist_alert_enabled = True
        plugin.allowed_group_umos = ["allowed"]
        plugin._database_lock = asyncio.Lock()
        plugin.database = StubDatabase()
        plugin.context = StubContext(sent)
        return plugin

    async def test_only_authorized_participant_groups_receive_alerts(self) -> None:
        plugin = self.plugin()
        await plugin._send_pending_delist_alerts()

        self.assertEqual(plugin.database.claimed_groups, ["allowed"])
        self.assertEqual(len(plugin.context.messages), 1)
        umo, message_chain = plugin.context.messages[0]
        self.assertEqual(umo, "allowed")
        self.assertEqual(len(message_chain.chain), 5)
        self.assertEqual(plugin.database.released, [])

    async def test_failed_active_send_releases_claim_for_retry(self) -> None:
        plugin = self.plugin(sent=False)
        await plugin._send_pending_delist_alerts()

        self.assertEqual(plugin.database.released, [("allowed", 7)])


if __name__ == "__main__":
    unittest.main()
