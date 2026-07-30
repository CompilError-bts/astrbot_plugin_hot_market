from __future__ import annotations

import html
from datetime import datetime
from typing import Any

from .market import MARKETS

MARKET_TEMPLATE = """
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  width: 780px;
  padding: 28px;
  color: #e8edf6;
  background:
    radial-gradient(circle at 82% 5%, rgba(60, 122, 255, .24), transparent 30%),
    radial-gradient(circle at 8% 92%, rgba(0, 209, 178, .14), transparent 32%),
    linear-gradient(145deg, #0b1020, #11182a 55%, #0c1322);
  font-family: "Noto Sans SC", "Microsoft YaHei", "PingFang SC", sans-serif;
}
.header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 20px;
}
.brand { font-size: 28px; font-weight: 800; letter-spacing: .5px; }
.brand span { color: #6ca0ff; }
.subtitle { color: #8792a8; font-size: 13px; margin-top: 5px; }
.time { color: #8792a8; font-size: 12px; text-align: right; }
.market {
  margin-top: 16px;
  border: 1px solid rgba(130, 151, 190, .16);
  background: rgba(17, 25, 44, .72);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 12px 35px rgba(0, 0, 0, .2);
}
.market-title {
  padding: 15px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(130, 151, 190, .12);
}
.market-name { font-size: 19px; font-weight: 800; }
.market-code { color: #748098; font-size: 12px; }
.row {
  min-height: 68px;
  padding: 10px 16px;
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr) 112px 88px 74px;
  gap: 10px;
  align-items: center;
  border-bottom: 1px solid rgba(130, 151, 190, .08);
}
.row:last-child { border-bottom: 0; }
.rank {
  width: 28px; height: 28px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  color: #8190aa; background: rgba(255, 255, 255, .04);
  font-size: 13px; font-weight: 800;
}
.rank.top { color: #0d1423; background: linear-gradient(145deg, #f5d777, #dfaa42); }
.topic { min-width: 0; }
.topic-title {
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  font-size: 15px; font-weight: 700; color: #f0f3f9;
}
.ticker { color: #69768d; font-size: 11px; margin-top: 5px; letter-spacing: .3px; }
.spark { width: 108px; height: 34px; }
.spark polyline { fill: none; stroke-width: 2.2; stroke-linecap: round; stroke-linejoin: round; }
.spark.up polyline { stroke: #34d399; }
.spark.down polyline { stroke: #fb7185; }
.spark.flat polyline { stroke: #94a3b8; }
.price { text-align: right; font-size: 16px; font-weight: 800; font-variant-numeric: tabular-nums; }
.change { text-align: right; font-size: 13px; font-weight: 800; font-variant-numeric: tabular-nums; }
.up { color: #34d399; }
.down { color: #fb7185; }
.flat { color: #94a3b8; }
.empty { color: #7f8ba0; padding: 22px; text-align: center; }
.footer {
  margin-top: 18px; color: #66738b; font-size: 11px;
  display: flex; justify-content: space-between;
}
</style>
</head>
<body>
  <div class="header">
    <div>
      <div class="brand">热搜<span>交易所</span></div>
      <div class="subtitle">各平台独立定价 · 虚拟资产，仅供娱乐</div>
    </div>
    <div class="time">
      行情 {{ updated_at }}<br>
      每 {{ refresh_minutes }} 分钟更新
    </div>
  </div>

  {% for market in markets %}
  <section class="market">
    <div class="market-title">
      <div class="market-name">{{ market.name }}股市</div>
      <div class="market-code">{{ market.prefix }} MARKET · TOP {{ market.rows|length }}</div>
    </div>
    {% if market.rows %}
      {% for item in market.rows %}
      <div class="row">
        <div class="rank {% if item.rank <= 3 %}top{% endif %}">{{ item.rank }}</div>
        <div class="topic">
          <div class="topic-title">{{ item.title }}</div>
          <div class="ticker">{{ item.ticker }}</div>
        </div>
        <svg class="spark {{ item.change_class }}" viewBox="0 0 108 34" aria-hidden="true">
          <polyline points="{{ item.sparkline }}"></polyline>
        </svg>
        <div class="price">{{ item.price }}</div>
        <div class="change {{ item.change_class }}">{{ item.change }}</div>
      </div>
      {% endfor %}
    {% else %}
      <div class="empty">暂时没有可用行情</div>
    {% endif %}
  </section>
  {% endfor %}

  <div class="footer">
    <span>/热市 买入 股票代码 金额</span>
    <span>Powered by 60s API · AstrBot</span>
  </div>
</body>
</html>
"""


def money(cents: int) -> str:
    return f"{cents / 100:,.2f}"


def change_percent(current_cents: int, previous_cents: int) -> float:
    if previous_cents <= 0:
        return 0.0
    return (current_cents - previous_cents) / previous_cents * 100


def sparkline_points(
    prices: list[int],
    width: int = 108,
    height: int = 34,
    padding: int = 3,
) -> str:
    if not prices:
        prices = [0, 0]
    elif len(prices) == 1:
        prices = [prices[0], prices[0]]

    minimum = min(prices)
    maximum = max(prices)
    usable_width = width - padding * 2
    usable_height = height - padding * 2
    points: list[str] = []
    for index, price in enumerate(prices):
        x = padding + usable_width * index / (len(prices) - 1)
        if maximum == minimum:
            y = height / 2
        else:
            y = padding + usable_height * (maximum - price) / (maximum - minimum)
        points.append(f"{x:.1f},{y:.1f}")
    return " ".join(points)


def prepare_dashboard(
    market_rows: dict[str, list[dict[str, Any]]],
    histories: dict[int, list[int]],
    refresh_minutes: int,
    updated_at: datetime | None,
) -> dict[str, Any]:
    markets: list[dict[str, Any]] = []
    for source, rows in market_rows.items():
        definition = MARKETS[source]
        prepared_rows: list[dict[str, Any]] = []
        for row in rows:
            current = int(row["price_cents"])
            previous = int(row["previous_price_cents"])
            percentage = change_percent(current, previous)
            if percentage > 0.005:
                change_class = "up"
                change = f"+{percentage:.1f}%"
            elif percentage < -0.005:
                change_class = "down"
                change = f"{percentage:.1f}%"
            else:
                change_class = "flat"
                change = "0.0%"
            prepared_rows.append(
                {
                    "rank": int(row["rank"]),
                    "title": html.escape(str(row["title"])),
                    "ticker": html.escape(str(row["ticker"])),
                    "price": money(current),
                    "change": change,
                    "change_class": change_class,
                    "sparkline": sparkline_points(
                        histories.get(int(row["id"]), [current])
                    ),
                }
            )
        markets.append(
            {
                "key": source,
                "name": definition.name,
                "prefix": definition.prefix,
                "rows": prepared_rows,
            }
        )

    return {
        "markets": markets,
        "refresh_minutes": refresh_minutes,
        "updated_at": (
            updated_at.astimezone().strftime("%m-%d %H:%M")
            if updated_at
            else "尚未更新"
        ),
    }


def format_market_text(
    market_rows: dict[str, list[dict[str, Any]]],
    updated_at: datetime | None,
) -> str:
    lines = ["📈 热搜交易所"]
    if updated_at:
        lines.append(f"行情时间：{updated_at.astimezone().strftime('%m-%d %H:%M')}")
    for source, rows in market_rows.items():
        lines.append(f"\n【{MARKETS[source].name}股市】")
        if not rows:
            lines.append("暂无行情")
            continue
        for row in rows:
            percentage = change_percent(
                int(row["price_cents"]),
                int(row["previous_price_cents"]),
            )
            sign = "+" if percentage > 0 else ""
            title = str(row["title"])
            if len(title) > 24:
                title = f"{title[:23]}…"
            lines.append(
                f"{row['rank']:>2}. {row['ticker']} "
                f"{money(int(row['price_cents']))} "
                f"{sign}{percentage:.1f}%\n    {title}"
            )
    return "\n".join(lines)
