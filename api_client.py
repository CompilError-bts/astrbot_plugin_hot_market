from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from .market import MARKETS, HotItem, parse_market_payload


class MarketApiError(RuntimeError):
    pass


class MarketApiClient:
    def __init__(self, base_url: str, timeout_seconds: int = 12):
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=max(3, timeout_seconds))
        self._session: aiohttp.ClientSession | None = None
        self._session_lock = asyncio.Lock()

    async def _get_session(self) -> aiohttp.ClientSession:
        async with self._session_lock:
            if self._session is None or self._session.closed:
                self._session = aiohttp.ClientSession(
                    timeout=self.timeout,
                    headers={
                        "Accept": "application/json",
                        "Accept-Encoding": "identity",
                        "User-Agent": "AstrBot-HotMarket/0.1",
                    },
                )
            return self._session

    def _endpoint(self, source: str) -> str:
        path = MARKETS[source].path
        if self.base_url.endswith("/v2") and path.startswith("/v2/"):
            path = path[3:]
        return f"{self.base_url}/{path.lstrip('/')}"

    async def fetch(self, source: str, max_items: int) -> list[HotItem]:
        if source not in MARKETS:
            raise MarketApiError(f"不支持的市场：{source}")
        session = await self._get_session()
        endpoint = self._endpoint(source)
        last_error: Exception | None = None

        for attempt in range(2):
            try:
                async with session.get(endpoint) as response:
                    if response.status != 200:
                        raise MarketApiError(
                            f"{MARKETS[source].name}接口返回 HTTP {response.status}"
                        )
                    payload: Any = await response.json(content_type=None)
                items = parse_market_payload(source, payload, max_items)
                if not items:
                    raise MarketApiError(f"{MARKETS[source].name}接口返回空榜单")
                return items
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
                last_error = exc
                if attempt == 0:
                    await asyncio.sleep(0.5)

        raise MarketApiError(
            f"{MARKETS[source].name}行情获取失败：{last_error}"
        ) from last_error

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
