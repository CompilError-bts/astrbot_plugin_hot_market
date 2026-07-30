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
  width: 860px;
  padding: 30px;
  color: #edf3ff;
  background:
    radial-gradient(circle at 84% 4%, rgba(74, 128, 255, .30), transparent 28%),
    radial-gradient(circle at 7% 86%, rgba(0, 220, 173, .18), transparent 30%),
    linear-gradient(145deg, #080d1b, #111a31 55%, #0a1425);
  font-family: "Noto Sans SC", "Microsoft YaHei", "PingFang SC", sans-serif;
}
.header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 18px;
}
.brand { font-size: 31px; font-weight: 900; letter-spacing: .8px; }
.brand span { color: #72a7ff; }
.subtitle { color: #8d9ab2; font-size: 13px; margin-top: 5px; }
.time { color: #91a0ba; font-size: 12px; text-align: right; line-height: 1.7; }
.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.8fr) repeat(3, minmax(0, .72fr));
  gap: 10px;
  margin-bottom: 18px;
}
.slogan-card, .stat-card {
  min-height: 94px;
  border: 1px solid rgba(135, 165, 220, .18);
  border-radius: 16px;
  background: linear-gradient(145deg, rgba(28, 42, 76, .92), rgba(15, 25, 47, .88));
  box-shadow: 0 12px 34px rgba(0, 0, 0, .22);
}
.slogan-card { padding: 15px 17px; }
.eyebrow { color: #72a7ff; font-size: 11px; font-weight: 800; letter-spacing: 1.6px; }
.slogan { margin-top: 7px; font-size: 20px; font-weight: 900; line-height: 1.25; }
.market-mood { color: #9aa8bf; font-size: 12px; margin-top: 7px; }
.stat-card { padding: 13px 12px; text-align: center; display: flex; flex-direction: column; justify-content: center; }
.stat-label { color: #8190aa; font-size: 11px; }
.stat-value { margin-top: 6px; font-size: 18px; font-weight: 900; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.stat-sub { color: #71809a; font-size: 10px; margin-top: 4px; }
.market {
  margin-top: 16px;
  border: 1px solid rgba(130, 157, 205, .18);
  background: rgba(15, 24, 44, .80);
  border-radius: 17px;
  overflow: hidden;
  box-shadow: 0 13px 36px rgba(0, 0, 0, .22);
}
.market-title {
  padding: 14px 17px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(130, 151, 190, .13);
  background: linear-gradient(90deg, rgba(68, 112, 214, .10), transparent);
}
.market-heading { display: flex; align-items: center; gap: 10px; }
.market-name { font-size: 19px; font-weight: 900; }
.mood-pill { padding: 4px 8px; border-radius: 999px; font-size: 10px; font-weight: 800; }
.mood-pill.up { color: #5ee8b1; background: rgba(52, 211, 153, .12); }
.mood-pill.down { color: #ff91a3; background: rgba(251, 113, 133, .12); }
.mood-pill.flat { color: #a7b2c5; background: rgba(148, 163, 184, .12); }
.market-code { color: #74839d; font-size: 11px; }
.row {
  min-height: 78px;
  padding: 11px 16px;
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr) 112px 88px 72px;
  gap: 10px;
  align-items: center;
  border-bottom: 1px solid rgba(130, 151, 190, .08);
}
.row:last-child { border-bottom: 0; }
.rank {
  width: 30px; height: 30px; border-radius: 9px;
  display: flex; align-items: center; justify-content: center;
  color: #8796b0; background: rgba(255, 255, 255, .045);
  font-size: 13px; font-weight: 900;
}
.rank.top { color: #111827; background: linear-gradient(145deg, #ffe58a, #e4ad43); }
.topic { min-width: 0; }
.topic-title {
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  font-size: 15px; font-weight: 750; color: #f3f6fc;
}
.ticker-line { margin-top: 7px; display: flex; align-items: center; gap: 8px; min-width: 0; }
.ticker {
  display: inline-flex; align-items: center;
  padding: 4px 9px; border-radius: 7px;
  color: #071323; background: linear-gradient(135deg, #83b9ff, #62e6cf);
  box-shadow: 0 4px 14px rgba(99, 189, 235, .18);
  font-size: 14px; font-weight: 950; letter-spacing: .5px;
  white-space: nowrap;
}
.quick-buy { color: #7787a3; font-size: 9px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.spark { width: 108px; height: 34px; }
.spark polyline { fill: none; stroke-width: 2.4; stroke-linecap: round; stroke-linejoin: round; }
.spark.up polyline { stroke: #34d399; }
.spark.down polyline { stroke: #fb7185; }
.spark.flat polyline { stroke: #94a3b8; }
.price { text-align: right; font-size: 16px; font-weight: 900; font-variant-numeric: tabular-nums; }
.change { text-align: right; font-size: 13px; font-weight: 900; font-variant-numeric: tabular-nums; }
.up { color: #34d399; }
.down { color: #fb7185; }
.flat { color: #94a3b8; }
.empty { color: #7f8ba0; padding: 22px; text-align: center; }
.footer {
  margin-top: 18px; color: #71809a; font-size: 11px;
  display: flex; justify-content: space-between; align-items: center;
}
.footer strong { color: #8fbaff; }
</style>
</head>
<body>
  <div class="header">
    <div>
      <div class="brand">热搜<span>交易所</span></div>
      <div class="subtitle">热搜即基本面 · 各平台独立定价 · 虚拟盘仅供娱乐</div>
    </div>
    <div class="time">
      行情 {{ updated_at }}<br>
      每 {{ refresh_minutes }} 分钟更新
    </div>
  </div>

  <section class="hero">
    <div class="slogan-card">
      <div class="eyebrow">TODAY'S BELL · 今日钟声</div>
      <div class="slogan">{{ slogan }}</div>
      <div class="market-mood">{{ mood }} · 上涨 {{ stats.up }} / 下跌 {{ stats.down }}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">🔥 热度王</div>
      <div class="stat-value">{{ stats.hot_ticker }}</div>
      <div class="stat-sub">全场最高排名</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">⚡ 波动王</div>
      <div class="stat-value {{ stats.mover_class }}">{{ stats.mover_ticker }}</div>
      <div class="stat-sub">{{ stats.mover_change }}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">📡 在市热点</div>
      <div class="stat-value">{{ stats.total }}</div>
      <div class="stat-sub">只 · 独立交易</div>
    </div>
  </section>

  {% for market in markets %}
  <section class="market">
    <div class="market-title">
      <div class="market-heading">
        <div class="market-name">{{ market.name }}股市</div>
        <div class="mood-pill {{ market.mood_class }}">{{ market.mood }}</div>
      </div>
      <div class="market-code">{{ market.prefix }} MARKET · TOP {{ market.rows|length }}</div>
    </div>
    {% if market.rows %}
      {% for item in market.rows %}
      <div class="row">
        <div class="rank {% if item.rank <= 3 %}top{% endif %}">{{ item.rank_badge }}</div>
        <div class="topic">
          <div class="topic-title">{{ item.title }}</div>
          <div class="ticker-line">
            <span class="ticker">{{ item.ticker }}</span>
            <span class="quick-buy">买100：/热市 买入 {{ item.ticker }} 100</span>
          </div>
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
    <span><strong>记住彩色代码</strong>，一句话完成买入</span>
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
    all_rows: list[dict[str, Any]] = []
    medal = {1: "🥇", 2: "🥈", 3: "🥉"}
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
            rank = int(row["rank"])
            prepared = {
                "rank": rank,
                "rank_badge": medal.get(rank, str(rank)),
                "title": html.escape(str(row["title"])),
                "ticker": html.escape(str(row["ticker"])),
                "price": money(current),
                "change": change,
                "percentage": percentage,
                "change_class": change_class,
                "sparkline": sparkline_points(
                    histories.get(int(row["id"]), [current])
                ),
            }
            prepared_rows.append(prepared)
            all_rows.append(prepared)

        up_count = sum(row["change_class"] == "up" for row in prepared_rows)
        down_count = sum(row["change_class"] == "down" for row in prepared_rows)
        if up_count > down_count:
            market_mood, mood_class = "多头升温", "up"
        elif down_count > up_count:
            market_mood, mood_class = "空头敲钟", "down"
        else:
            market_mood, mood_class = "多空拉锯", "flat"
        markets.append(
            {
                "key": source,
                "name": definition.name,
                "prefix": definition.prefix,
                "rows": prepared_rows,
                "mood": market_mood,
                "mood_class": mood_class,
            }
        )

    up_count = sum(row["change_class"] == "up" for row in all_rows)
    down_count = sum(row["change_class"] == "down" for row in all_rows)
    if up_count > down_count:
        mood = "热钱进场，红榜正在扩散"
    elif down_count > up_count:
        mood = "情绪降温，先看热搜再下单"
    else:
        mood = "多空打平，下一条热搜决定方向"

    hot_row = min(all_rows, key=lambda row: row["rank"], default=None)
    mover_row = max(
        all_rows,
        key=lambda row: abs(float(row["percentage"])),
        default=None,
    )
    slogans = (
        "今天的热搜，明天的谈资，今晚的虚拟财富。",
        "热点会过期，段子会流传，仓位请随缘。",
        "别人追热搜，我们给热搜敲钟上市。",
        "情绪有价格，围观也能成为一门生意。",
        "不预测世界，只交易今天最响的声音。",
    )
    slogan_index = (
        updated_at.astimezone().date().toordinal() if updated_at else 0
    ) % len(slogans)

    return {
        "markets": markets,
        "refresh_minutes": refresh_minutes,
        "updated_at": (
            updated_at.astimezone().strftime("%m-%d %H:%M")
            if updated_at
            else "尚未更新"
        ),
        "slogan": slogans[slogan_index],
        "mood": mood,
        "stats": {
            "total": len(all_rows),
            "up": up_count,
            "down": down_count,
            "hot_ticker": hot_row["ticker"] if hot_row else "--",
            "mover_ticker": mover_row["ticker"] if mover_row else "--",
            "mover_change": mover_row["change"] if mover_row else "暂无波动",
            "mover_class": mover_row["change_class"] if mover_row else "flat",
        },
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
