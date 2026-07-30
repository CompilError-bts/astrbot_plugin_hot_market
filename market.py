from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

import jieba
from jieba import analyse


@dataclass(frozen=True, slots=True)
class MarketDefinition:
    key: str
    name: str
    prefix: str
    path: str
    aliases: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HotItem:
    source: str
    title: str
    normalized_title: str
    ticker: str
    rank: int
    list_size: int
    link: str
    raw_score: str
    target_price_cents: int


MARKETS: dict[str, MarketDefinition] = {
    "weibo": MarketDefinition(
        key="weibo",
        name="微博",
        prefix="WB",
        path="/v2/weibo",
        aliases=("微博", "wb"),
    ),
    "baidu": MarketDefinition(
        key="baidu",
        name="百度",
        prefix="BD",
        path="/v2/baidu/hot",
        aliases=("百度", "bd"),
    ),
    "bili": MarketDefinition(
        key="bili",
        name="B站",
        prefix="BL",
        path="/v2/bili",
        aliases=("b站", "哔哩", "哔哩哔哩", "bl", "bili"),
    ),
    "douyin": MarketDefinition(
        key="douyin",
        name="抖音",
        prefix="DY",
        path="/v2/douyin",
        aliases=("抖音", "dy"),
    ),
    "zhihu": MarketDefinition(
        key="zhihu",
        name="知乎",
        prefix="ZH",
        path="/v2/zhihu",
        aliases=("知乎", "zh"),
    ),
    "toutiao": MarketDefinition(
        key="toutiao",
        name="头条",
        prefix="TT",
        path="/v2/toutiao",
        aliases=("头条", "今日头条", "tt"),
    ),
    "rednote": MarketDefinition(
        key="rednote",
        name="小红书",
        prefix="XHS",
        path="/v2/rednote",
        aliases=("小红书", "红书", "xhs"),
    ),
}

_MARKET_ALIASES: dict[str, str] = {}
for _key, _market in MARKETS.items():
    _MARKET_ALIASES[_key.casefold()] = _key
    _MARKET_ALIASES[_market.name.casefold()] = _key
    for _alias in _market.aliases:
        _MARKET_ALIASES[_alias.casefold()] = _key


def resolve_market(value: str) -> str | None:
    return _MARKET_ALIASES.get(value.strip().casefold())


def normalize_title(title: str) -> str:
    normalized = unicodedata.normalize("NFKC", title).casefold()
    return re.sub(r"[\W_]+", "", normalized, flags=re.UNICODE)


MAX_TICKER_KEYWORD_CHARS = 8


def _clean_ticker_keyword(value: str) -> str:
    return "".join(character for character in value if character.isalnum()).upper()


def extract_ticker_keywords(title: str, max_chars: int = MAX_TICKER_KEYWORD_CHARS) -> str:
    """Extract a short readable code with jieba's mature TF-IDF algorithm."""
    weighted_keywords = analyse.extract_tags(
        title,
        topK=4,
        withWeight=False,
    )
    candidates = list(weighted_keywords)
    if not candidates:
        candidates = list(jieba.cut(title, cut_all=False))

    code = ""
    seen: set[str] = set()
    for candidate in candidates:
        keyword = _clean_ticker_keyword(str(candidate))
        if not keyword or keyword in seen:
            continue
        seen.add(keyword)
        remaining = max_chars - len(code)
        if remaining <= 0:
            break
        code += keyword[:remaining]

    if not code:
        code = _clean_ticker_keyword(normalize_title(title))[:max_chars]
    return code or "HOT"


def ticker_for(source: str, title: str) -> str:
    market = MARKETS[source]
    return f"{market.prefix}-{extract_ticker_keywords(title)}"


def target_price_cents(
    rank: int,
    list_size: int,
    minimum_cents: int = 500,
    maximum_cents: int = 10_000,
) -> int:
    if rank < 1 or list_size < 1 or rank > list_size:
        raise ValueError("rank must be within the source list")
    strength = ((list_size - rank + 1) / list_size) ** 1.5
    return round(minimum_cents + (maximum_cents - minimum_cents) * strength)


def smooth_price_cents(
    previous_cents: int,
    target_cents: int,
    alpha: float = 0.4,
    movement_limit: float = 0.25,
) -> int:
    if previous_cents <= 0:
        return target_cents
    blended = round(previous_cents * (1 - alpha) + target_cents * alpha)
    lower = max(100, math.floor(previous_cents * (1 - movement_limit)))
    upper = math.ceil(previous_cents * (1 + movement_limit))
    return max(lower, min(upper, blended))


def parse_market_payload(
    source: str,
    payload: Any,
    max_items: int,
) -> list[HotItem]:
    if source not in MARKETS:
        raise ValueError(f"unsupported market: {source}")

    data = payload
    if isinstance(payload, dict):
        if payload.get("code") not in (None, 0, 200):
            raise ValueError(f"API returned code {payload.get('code')}")
        data = payload.get("data", [])
        if isinstance(data, dict):
            for key in ("list", "items", "data"):
                if isinstance(data.get(key), list):
                    data = data[key]
                    break

    if not isinstance(data, list):
        raise ValueError("API data is not a list")

    candidates: list[tuple[dict[str, Any], int]] = []
    for index, raw_item in enumerate(data, start=1):
        if not isinstance(raw_item, dict):
            continue
        title = str(
            raw_item.get("title")
            or raw_item.get("word")
            or raw_item.get("keyword")
            or raw_item.get("name")
            or ""
        ).strip()
        if not title:
            continue
        candidates.append((raw_item, index))
        if len(candidates) >= max_items:
            break

    list_size = len(candidates)
    if list_size == 0:
        return []

    result: list[HotItem] = []
    seen_titles: set[str] = set()
    for raw_item, fallback_rank in candidates:
        title = str(
            raw_item.get("title")
            or raw_item.get("word")
            or raw_item.get("keyword")
            or raw_item.get("name")
        ).strip()
        normalized_title = normalize_title(title)
        if not normalized_title or normalized_title in seen_titles:
            continue
        seen_titles.add(normalized_title)

        raw_rank = raw_item.get("rank", fallback_rank)
        try:
            rank = int(raw_rank)
        except (TypeError, ValueError):
            rank = fallback_rank
        if rank < 1 or rank > list_size:
            rank = fallback_rank

        raw_score = raw_item.get(
            "hot_value",
            raw_item.get("score", raw_item.get("hot", "")),
        )
        result.append(
            HotItem(
                source=source,
                title=title,
                normalized_title=normalized_title,
                ticker=ticker_for(source, title),
                rank=rank,
                list_size=list_size,
                link=str(raw_item.get("link") or raw_item.get("url") or ""),
                raw_score=str(raw_score) if raw_score is not None else "",
                target_price_cents=target_price_cents(rank, list_size),
            )
        )
    return result
