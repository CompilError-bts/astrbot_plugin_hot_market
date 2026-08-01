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
      <div class="stat-sub">在榜 {{ stats.active }} · 观察 {{ stats.fading }}</div>
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


STOCK_DETAIL_TEMPLATE = """
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
  padding: 32px;
  color: #eef4ff;
  background:
    radial-gradient(circle at 86% 2%, rgba(71, 127, 255, .34), transparent 30%),
    radial-gradient(circle at 8% 94%, rgba(33, 214, 163, .19), transparent 32%),
    linear-gradient(145deg, #080d1b, #111a31 56%, #091524);
  font-family: "Noto Sans SC", "Microsoft YaHei", "PingFang SC", sans-serif;
}
.top { display: flex; align-items: flex-start; justify-content: space-between; gap: 22px; }
.market { color: #78aaff; font-size: 12px; font-weight: 900; letter-spacing: 1.4px; }
.title { margin-top: 9px; font-size: 27px; font-weight: 900; line-height: 1.3; }
.ticker {
  flex: 0 0 auto; padding: 10px 16px; border-radius: 12px;
  color: #071323; background: linear-gradient(135deg, #88bdff, #61e5ca);
  font-size: 23px; font-weight: 950; letter-spacing: .8px;
  box-shadow: 0 10px 28px rgba(87, 190, 218, .22);
}
.quote {
  margin-top: 22px; padding: 21px 23px; border-radius: 20px;
  border: 1px solid rgba(138, 166, 220, .18);
  background: linear-gradient(145deg, rgba(26, 41, 75, .93), rgba(14, 25, 48, .90));
  box-shadow: 0 18px 48px rgba(0, 0, 0, .24);
}
.quote-head { display: flex; align-items: flex-end; justify-content: space-between; }
.price { font-size: 45px; font-weight: 950; font-variant-numeric: tabular-nums; }
.price small { color: #7d8ca6; font-size: 13px; font-weight: 700; }
.change { font-size: 23px; font-weight: 950; font-variant-numeric: tabular-nums; }
.up { color: #39dba2; }
.down { color: #fb7185; }
.flat { color: #a1aec3; }
.subline { margin-top: 6px; color: #8391a8; font-size: 12px; }
.chart-wrap { position: relative; margin-top: 18px; height: 238px; }
.chart-label { position: absolute; right: 5px; color: #6f7e96; font-size: 10px; }
.chart-label.high { top: 2px; }
.chart-label.low { bottom: 1px; }
.chart { width: 100%; height: 220px; margin-top: 9px; }
.chart .grid { stroke: rgba(144, 165, 202, .10); stroke-width: 1; }
.chart .area { opacity: .16; }
.chart .line { fill: none; stroke-width: 4; stroke-linecap: round; stroke-linejoin: round; }
.chart.up .line { stroke: #39dba2; }
.chart.up .area { fill: #39dba2; }
.chart.down .line { stroke: #fb7185; }
.chart.down .area { fill: #fb7185; }
.chart.flat .line { stroke: #9ba9bd; }
.chart.flat .area { fill: #9ba9bd; }
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 17px; }
.stat {
  padding: 13px 12px; border-radius: 14px; text-align: center;
  border: 1px solid rgba(135, 163, 211, .14); background: rgba(8, 15, 30, .32);
}
.stat-label { color: #75849d; font-size: 10px; }
.stat-value { margin-top: 6px; font-size: 15px; font-weight: 900; }
.slogan {
  margin-top: 18px; padding: 14px 17px; border-left: 3px solid #77aaff;
  color: #b7c5db; background: rgba(73, 116, 208, .08); border-radius: 0 12px 12px 0;
  font-size: 14px; font-weight: 750;
}
.footer {
  margin-top: 18px; display: flex; justify-content: space-between;
  color: #71809a; font-size: 11px;
}
.footer strong { color: #8fbaff; }
</style>
</head>
<body>
  <div class="top">
    <div>
      <div class="market">{{ market_name }} MARKET · {{ rank_text }} · {{ status_text }}</div>
      <div class="title">{{ title }}</div>
    </div>
    <div class="ticker">{{ ticker }}</div>
  </div>
  <section class="quote">
    <div class="quote-head">
      <div>
        <div class="price">{{ price }} <small>热币</small></div>
        <div class="subline">最近一轮价格变化</div>
      </div>
      <div class="change {{ change_class }}">{{ change }}</div>
    </div>
    <div class="chart-wrap">
      <div class="chart-label high">高 {{ high }}</div>
      <div class="chart-label low">低 {{ low }}</div>
      <svg class="chart {{ trend_class }}" viewBox="0 0 720 220" aria-label="近期价格走势">
        <line class="grid" x1="18" y1="18" x2="702" y2="18"></line>
        <line class="grid" x1="18" y1="110" x2="702" y2="110"></line>
        <line class="grid" x1="18" y1="202" x2="702" y2="202"></line>
        <polygon class="area" points="{{ area }}"></polygon>
        <polyline class="line" points="{{ sparkline }}"></polyline>
      </svg>
    </div>
    <div class="stats">
      <div class="stat"><div class="stat-label">当前排名</div><div class="stat-value">{{ rank_text }}</div></div>
      <div class="stat"><div class="stat-label">区间涨跌</div><div class="stat-value {{ trend_class }}">{{ range_change }}</div></div>
      <div class="stat"><div class="stat-label">区间最高</div><div class="stat-value">{{ high }}</div></div>
      <div class="stat"><div class="stat-label">区间最低</div><div class="stat-value">{{ low }}</div></div>
    </div>
  </section>
  <div class="slogan">“{{ slogan }}”</div>
  <div class="footer">
    <span><strong>快捷买入</strong> /热市 买入 {{ ticker }} 100</span>
    <span>{{ updated_at }} · 近 {{ point_count }} 轮 · 虚拟盘仅供娱乐</span>
  </div>
</body>
</html>
"""

def money(cents: int) -> str:
    return f"{cents / 100:,.2f}"


def compact_money(cents: int) -> str:
    amount = cents / 100
    if abs(amount) >= 10_000:
        value = f"{amount / 10_000:.2f}".rstrip("0").rstrip(".")
        return f"{value}万"
    return f"{amount:,.2f}"


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


def _movement_class(percentage: float) -> str:
    if percentage > 0.005:
        return "up"
    if percentage < -0.005:
        return "down"
    return "flat"


def _signed_percent(percentage: float) -> str:
    sign = "+" if percentage > 0 else ""
    return f"{sign}{percentage:.1f}%"


def prepare_stock_detail(
    stock: dict[str, Any],
    history: list[int],
) -> dict[str, Any]:
    current = int(stock["price_cents"])
    previous = int(stock["previous_price_cents"])
    prices = [int(value) for value in history] or [current]
    if prices[-1] != current:
        prices.append(current)
    latest_percentage = change_percent(current, previous)
    range_percentage = change_percent(current, prices[0])
    points = sparkline_points(prices, width=720, height=220, padding=18)
    status_text = {
        "active": "正常交易",
        "fading": "离榜观察",
        "delisted": "已退市",
    }.get(str(stock["status"]), str(stock["status"]))
    rank = stock.get("rank")
    rank_text = f"榜单 #{rank}" if rank is not None else "已离榜"
    slogans = (
        "热搜有保质期，走势记录每一次围观。",
        "排名是基本面，讨论度就是今日成交量。",
        "围观群众敲钟，话题情绪定价。",
        "看懂曲线之前，先记住它为什么上热搜。",
        "热点会换，代码要短，仓位要有趣。",
    )
    ticker = str(stock["ticker"])
    slogan = slogans[sum(ord(character) for character in ticker) % len(slogans)]
    raw_updated_at = str(stock.get("updated_at") or "")
    try:
        updated_at = datetime.fromisoformat(raw_updated_at).astimezone().strftime(
            "%m-%d %H:%M"
        )
    except ValueError:
        updated_at = raw_updated_at or "尚未更新"
    trend_class = _movement_class(range_percentage)
    return {
        "market_name": f"{MARKETS[str(stock['source'])].name}股市",
        "rank_text": rank_text,
        "status_text": html.escape(status_text),
        "title": html.escape(str(stock["title"])),
        "ticker": html.escape(ticker),
        "price": money(current),
        "change": _signed_percent(latest_percentage),
        "change_class": _movement_class(latest_percentage),
        "range_change": _signed_percent(range_percentage),
        "trend_class": trend_class,
        "high": money(max(prices)),
        "low": money(min(prices)),
        "sparkline": points,
        "area": f"18,202 {points} 702,202",
        "slogan": slogan,
        "point_count": len(prices),
        "updated_at": updated_at,
    }


def format_stock_detail_text(
    stock: dict[str, Any],
    history: list[int],
    summary_max_length: int = 360,
) -> str:
    current = int(stock["price_cents"])
    previous = int(stock["previous_price_cents"])
    percentage = change_percent(current, previous)
    rank_text = f"#{stock['rank']}" if stock.get("rank") is not None else "已离榜"
    status_text = {
        "active": "正常交易",
        "fading": "离榜观察",
        "delisted": "已退市",
    }.get(str(stock.get("status", "")), str(stock.get("status", "未知")))
    history_text = " → ".join(money(int(value)) for value in history[-8:])
    summary = str(stock.get("summary") or "").strip()
    if summary:
        limit = max(80, summary_max_length)
        if len(summary) > limit:
            summary = f"{summary[:limit - 1]}…"
    else:
        summary = "该平台榜单暂未提供摘要，请打开原文查看详情。"
    link = str(stock.get("link") or "").strip()
    link_text = link or "该平台榜单暂未提供原文链接。"
    return (
        f"📰 {stock['ticker']} · 热搜资讯\n"
        f"标题：{stock['title']}\n"
        f"市场：{MARKETS[str(stock['source'])].name}股市\n"
        f"现价：{money(current)}（{percentage:+.1f}%）\n"
        f"排名：{rank_text}｜状态：{status_text}\n"
        f"近期价格：{history_text or '暂无'}\n\n"
        f"摘要：{summary}\n"
        f"原文：{link_text}"
    )


def prepare_dashboard(
    market_rows: dict[str, list[dict[str, Any]]],
    histories: dict[int, list[int]],
    refresh_minutes: int,
    updated_at: datetime | None,
    summary_rows: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    markets: list[dict[str, Any]] = []
    if summary_rows is None:
        summary_rows = market_rows
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

        market_percentages = [
            change_percent(
                int(row["price_cents"]),
                int(row["previous_price_cents"]),
            )
            for row in summary_rows.get(source, rows)
        ]
        up_count = sum(value > 0.005 for value in market_percentages)
        down_count = sum(value < -0.005 for value in market_percentages)
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

    all_summary_rows = [row for rows in summary_rows.values() for row in rows]
    summary_data: list[dict[str, Any]] = []
    for row in all_summary_rows:
        percentage = change_percent(
            int(row["price_cents"]),
            int(row["previous_price_cents"]),
        )
        summary_data.append(
            {
                "ticker": str(row["ticker"]),
                "rank": row.get("rank"),
                "status": str(row.get("status", "active")),
                "percentage": percentage,
                "change": _signed_percent(percentage),
                "change_class": _movement_class(percentage),
            }
        )

    up_count = sum(row["change_class"] == "up" for row in summary_data)
    down_count = sum(row["change_class"] == "down" for row in summary_data)
    if up_count > down_count:
        mood = "热钱进场，红榜正在扩散"
    elif down_count > up_count:
        mood = "情绪降温，先看热搜再下单"
    else:
        mood = "多空打平，下一条热搜决定方向"

    hot_row = min(
        (row for row in summary_data if row["rank"] is not None),
        key=lambda row: int(row["rank"]),
        default=None,
    )
    mover_row = max(
        summary_data,
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
            "total": len(summary_data),
            "active": sum(row["status"] == "active" for row in summary_data),
            "fading": sum(row["status"] == "fading" for row in summary_data),
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
    all_rows = [row for rows in market_rows.values() for row in rows]
    active_total = sum(
        row.get("status", "active") == "active" for row in all_rows
    )
    fading_total = sum(
        row.get("status", "active") == "fading" for row in all_rows
    )
    lines = ["📊 热搜交易所 · 全量行情"]
    if updated_at:
        lines.append(f"行情时间：{updated_at.astimezone().strftime('%m-%d %H:%M')}")
    lines.append(
        f"共 {len(all_rows)} 只｜在榜 {active_total}｜离榜观察 {fading_total}"
    )
    for source, rows in market_rows.items():
        active_count = sum(
            row.get("status", "active") == "active" for row in rows
        )
        fading_count = sum(
            row.get("status", "active") == "fading" for row in rows
        )
        lines.append(
            f"\n【{MARKETS[source].name}股市｜"
            f"在榜 {active_count} · 观察 {fading_count}】"
        )
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
            if row.get("status") == "fading":
                position = f"离榜{int(row.get('missing_count', 1))}轮"
                trade_hint = " · 仅可卖出"
            else:
                rank = int(row["rank"])
                position = f"#{rank:02d}"
                trade_hint = ""
            lines.append(
                f"{position} {row['ticker']} "
                f"{money(int(row['price_cents']))} "
                f"{sign}{percentage:.1f}%{trade_hint}\n    {title}"
            )
    return "\n".join(lines)
