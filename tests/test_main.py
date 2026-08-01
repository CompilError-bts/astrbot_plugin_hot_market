from __future__ import annotations

import asyncio
import unittest
from typing import Any

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
