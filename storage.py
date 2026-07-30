from __future__ import annotations

import hashlib
import math
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .market import (
    BULLISH_ADVANCE_RATIO,
    HotItem,
    bullish_drift_price_cents,
    smooth_price_cents,
)


class TradeError(RuntimeError):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_now_text() -> str:
    return utc_now().isoformat(timespec="seconds")


class MarketDatabase:
    def __init__(self, database_path: Path):
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(database_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("PRAGMA busy_timeout=5000")
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL UNIQUE,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                normalized_title TEXT NOT NULL,
                link TEXT NOT NULL DEFAULT '',
                raw_score TEXT NOT NULL DEFAULT '',
                rank INTEGER,
                list_size INTEGER NOT NULL,
                price_cents INTEGER NOT NULL,
                previous_price_cents INTEGER NOT NULL,
                status TEXT NOT NULL,
                missing_count INTEGER NOT NULL DEFAULT 0,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(source, normalized_title)
            );

            CREATE INDEX IF NOT EXISTS idx_stocks_source_status
            ON stocks(source, status, rank);

            CREATE TABLE IF NOT EXISTS ticker_aliases (
                alias TEXT COLLATE NOCASE PRIMARY KEY,
                stock_id INTEGER NOT NULL REFERENCES stocks(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_ticker_aliases_stock
            ON ticker_aliases(stock_id);

            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_id INTEGER NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
                captured_at TEXT NOT NULL,
                price_cents INTEGER NOT NULL,
                rank INTEGER,
                status TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_quotes_stock_time
            ON quotes(stock_id, captured_at DESC);

            CREATE TABLE IF NOT EXISTS source_state (
                source TEXT PRIMARY KEY,
                last_success_at TEXT,
                item_count INTEGER NOT NULL DEFAULT 0,
                last_error TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS accounts (
                group_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                user_name TEXT NOT NULL,
                cash_cents INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(group_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS positions (
                group_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                stock_id INTEGER NOT NULL REFERENCES stocks(id),
                shares INTEGER NOT NULL,
                average_cost_cents INTEGER NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(group_id, user_id, stock_id),
                FOREIGN KEY(group_id, user_id)
                    REFERENCES accounts(group_id, user_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                stock_id INTEGER NOT NULL REFERENCES stocks(id),
                side TEXT NOT NULL,
                shares INTEGER NOT NULL,
                price_cents INTEGER NOT NULL,
                fee_cents INTEGER NOT NULL,
                realized_profit_cents INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield self.connection
        except Exception:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()

    @staticmethod
    def _stock_by_ticker(
        connection: sqlite3.Connection,
        ticker: str,
    ) -> sqlite3.Row | None:
        normalized = ticker.strip()
        row = connection.execute(
            "SELECT * FROM stocks WHERE ticker = ? COLLATE NOCASE",
            (normalized,),
        ).fetchone()
        if row:
            return row
        return connection.execute(
            """
            SELECT s.*
            FROM ticker_aliases a
            JOIN stocks s ON s.id = a.stock_id
            WHERE a.alias = ? COLLATE NOCASE
            """,
            (normalized,),
        ).fetchone()

    @staticmethod
    def _ticker_is_available(
        connection: sqlite3.Connection,
        ticker: str,
        exclude_stock_id: int | None,
    ) -> bool:
        stock = connection.execute(
            "SELECT id FROM stocks WHERE ticker = ? COLLATE NOCASE",
            (ticker,),
        ).fetchone()
        if stock and int(stock["id"]) != exclude_stock_id:
            return False
        alias = connection.execute(
            "SELECT stock_id FROM ticker_aliases WHERE alias = ? COLLATE NOCASE",
            (ticker,),
        ).fetchone()
        return not alias or int(alias["stock_id"]) == exclude_stock_id

    def _unique_ticker(
        self,
        connection: sqlite3.Connection,
        desired: str,
        source: str,
        normalized_title: str,
        exclude_stock_id: int | None = None,
    ) -> str:
        base = desired.strip().upper()
        if self._ticker_is_available(connection, base, exclude_stock_id):
            return base

        digest = hashlib.sha1(
            f"{source}:{normalized_title}".encode(),
            usedforsecurity=False,
        ).hexdigest().upper()
        for suffix_length in (4, 6, 8, 12, 20, 40):
            candidate = f"{base}-{digest[:suffix_length]}"
            if self._ticker_is_available(
                connection,
                candidate,
                exclude_stock_id,
            ):
                return candidate
        raise RuntimeError("无法为热点生成唯一股票代码")

    def record_source_error(self, source: str, error: str) -> None:
        self.connection.execute(
            """
            INSERT INTO source_state(source, last_error)
            VALUES (?, ?)
            ON CONFLICT(source) DO UPDATE SET last_error = excluded.last_error
            """,
            (source, error[:500]),
        )
        self.connection.commit()

    def apply_market_snapshot(
        self,
        source: str,
        items: list[HotItem],
        delist_after_misses: int = 3,
    ) -> dict[str, int]:
        captured_at = utc_now_text()
        seen_titles = {item.normalized_title for item in items}
        listed_count = 0
        updated_count = 0
        faded_count = 0

        with self._transaction() as connection:
            existing_rows = connection.execute(
                "SELECT * FROM stocks WHERE source = ?",
                (source,),
            ).fetchall()
            existing = {row["normalized_title"]: row for row in existing_rows}
            price_plan: dict[str, int] = {}
            active_updates: list[tuple[HotItem, sqlite3.Row]] = []

            for item in items:
                row = existing.get(item.normalized_title)
                if row is None or row["status"] == "delisted":
                    price_plan[item.normalized_title] = item.target_price_cents
                    continue
                previous_price = int(row["price_cents"])
                price_cents = smooth_price_cents(
                    previous_price,
                    item.target_price_cents,
                )
                previous_rank = row["rank"]
                if previous_rank is not None and item.rank <= int(previous_rank):
                    price_cents = max(
                        price_cents,
                        bullish_drift_price_cents(
                            previous_price,
                            item.target_price_cents,
                        ),
                    )
                price_plan[item.normalized_title] = price_cents
                active_updates.append((item, row))

            desired_gainers = math.ceil(
                len(active_updates) * BULLISH_ADVANCE_RATIO
            )
            current_gainers = sum(
                price_plan[item.normalized_title] > int(row["price_cents"])
                for item, row in active_updates
            )
            bullish_candidates: list[
                tuple[int, int, HotItem, sqlite3.Row]
            ] = []
            for item, row in active_updates:
                previous_price = int(row["price_cents"])
                if price_plan[item.normalized_title] > previous_price:
                    continue
                previous_rank = row["rank"]
                rank_drop = (
                    item.rank - int(previous_rank)
                    if previous_rank is not None
                    else 99
                )
                drifted = bullish_drift_price_cents(
                    previous_price,
                    item.target_price_cents,
                )
                if rank_drop <= 1 and drifted > previous_price:
                    bullish_candidates.append(
                        (
                            max(0, rank_drop),
                            abs(item.target_price_cents - previous_price),
                            item,
                            row,
                        )
                    )
            bullish_candidates.sort(key=lambda candidate: candidate[:2])
            for _, _, item, row in bullish_candidates:
                if current_gainers >= desired_gainers:
                    break
                previous_price = int(row["price_cents"])
                price_plan[item.normalized_title] = bullish_drift_price_cents(
                    previous_price,
                    item.target_price_cents,
                )
                current_gainers += 1

            for item in items:
                row = existing.get(item.normalized_title)
                if row is None:
                    ticker = self._unique_ticker(
                        connection,
                        item.ticker,
                        source,
                        item.normalized_title,
                    )
                    cursor = connection.execute(
                        """
                        INSERT INTO stocks(
                            ticker, source, title, normalized_title, link, raw_score,
                            rank, list_size, price_cents, previous_price_cents,
                            status, missing_count, first_seen_at, last_seen_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', 0, ?, ?, ?)
                        """,
                        (
                            ticker,
                            source,
                            item.title,
                            item.normalized_title,
                            item.link,
                            item.raw_score,
                            item.rank,
                            item.list_size,
                            item.target_price_cents,
                            item.target_price_cents,
                            captured_at,
                            captured_at,
                            captured_at,
                        ),
                    )
                    stock_id = int(cursor.lastrowid)
                    price_cents = item.target_price_cents
                    listed_count += 1
                else:
                    ticker = self._unique_ticker(
                        connection,
                        item.ticker,
                        source,
                        item.normalized_title,
                        exclude_stock_id=int(row["id"]),
                    )
                    old_ticker = str(row["ticker"])
                    if ticker.casefold() != old_ticker.casefold():
                        connection.execute(
                            """
                            INSERT INTO ticker_aliases(alias, stock_id)
                            VALUES (?, ?)
                            ON CONFLICT(alias) DO NOTHING
                            """,
                            (old_ticker, row["id"]),
                        )
                    previous_price = int(row["price_cents"])
                    price_cents = price_plan[item.normalized_title]
                    stock_id = int(row["id"])
                    connection.execute(
                        """
                        UPDATE stocks
                        SET ticker = ?, title = ?, link = ?, raw_score = ?, rank = ?,
                            list_size = ?, price_cents = ?,
                            previous_price_cents = ?, status = 'active',
                            missing_count = 0, last_seen_at = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            ticker,
                            item.title,
                            item.link,
                            item.raw_score,
                            item.rank,
                            item.list_size,
                            price_cents,
                            previous_price,
                            captured_at,
                            captured_at,
                            stock_id,
                        ),
                    )
                    updated_count += 1

                connection.execute(
                    """
                    INSERT INTO quotes(stock_id, captured_at, price_cents, rank, status)
                    VALUES (?, ?, ?, ?, 'active')
                    """,
                    (stock_id, captured_at, price_cents, item.rank),
                )

            for normalized_title, row in existing.items():
                if normalized_title in seen_titles or row["status"] == "delisted":
                    continue
                previous_price = int(row["price_cents"])
                missing_count = int(row["missing_count"]) + 1
                status = (
                    "delisted"
                    if missing_count >= max(1, delist_after_misses)
                    else "fading"
                )
                price_cents = (
                    100
                    if status == "delisted"
                    else max(100, round(previous_price * 0.75))
                )
                connection.execute(
                    """
                    UPDATE stocks
                    SET rank = NULL, price_cents = ?, previous_price_cents = ?,
                        status = ?, missing_count = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        price_cents,
                        previous_price,
                        status,
                        missing_count,
                        captured_at,
                        row["id"],
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO quotes(stock_id, captured_at, price_cents, rank, status)
                    VALUES (?, ?, ?, NULL, ?)
                    """,
                    (row["id"], captured_at, price_cents, status),
                )
                faded_count += 1

            connection.execute(
                """
                INSERT INTO source_state(source, last_success_at, item_count, last_error)
                VALUES (?, ?, ?, '')
                ON CONFLICT(source) DO UPDATE SET
                    last_success_at = excluded.last_success_at,
                    item_count = excluded.item_count,
                    last_error = ''
                """,
                (source, captured_at, len(items)),
            )
            cutoff = (utc_now() - timedelta(days=7)).isoformat(timespec="seconds")
            connection.execute(
                "DELETE FROM quotes WHERE captured_at < ?",
                (cutoff,),
            )

        return {
            "listed": listed_count,
            "updated": updated_count,
            "faded": faded_count,
        }

    def market_rows(self, source: str, limit: int) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM stocks
            WHERE source = ? AND status = 'active'
            ORDER BY rank ASC
            LIMIT ?
            """,
            (source, max(1, limit)),
        ).fetchall()
        return [dict(row) for row in rows]

    def stock(self, ticker: str) -> dict[str, Any] | None:
        row = self._stock_by_ticker(self.connection, ticker)
        return dict(row) if row else None

    def quote_history(self, stock_id: int, limit: int = 16) -> list[int]:
        rows = self.connection.execute(
            """
            SELECT price_cents
            FROM quotes
            WHERE stock_id = ?
            ORDER BY captured_at DESC
            LIMIT ?
            """,
            (stock_id, max(2, limit)),
        ).fetchall()
        return [int(row["price_cents"]) for row in reversed(rows)]

    def source_states(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM source_state ORDER BY source"
        ).fetchall()
        return [dict(row) for row in rows]

    def latest_success_at(self) -> datetime | None:
        row = self.connection.execute(
            "SELECT MAX(last_success_at) AS value FROM source_state"
        ).fetchone()
        if not row or not row["value"]:
            return None
        return datetime.fromisoformat(str(row["value"]))

    def _ensure_account(
        self,
        connection: sqlite3.Connection,
        group_id: str,
        user_id: str,
        user_name: str,
        starting_cash_cents: int,
    ) -> sqlite3.Row:
        now = utc_now_text()
        connection.execute(
            """
            INSERT INTO accounts(
                group_id, user_id, user_name, cash_cents, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(group_id, user_id) DO UPDATE SET
                user_name = excluded.user_name,
                updated_at = excluded.updated_at
            """,
            (
                group_id,
                user_id,
                user_name,
                starting_cash_cents,
                now,
                now,
            ),
        )
        return connection.execute(
            """
            SELECT * FROM accounts
            WHERE group_id = ? AND user_id = ?
            """,
            (group_id, user_id),
        ).fetchone()

    def ensure_account(
        self,
        group_id: str,
        user_id: str,
        user_name: str,
        starting_cash_cents: int,
    ) -> dict[str, Any]:
        with self._transaction() as connection:
            row = self._ensure_account(
                connection,
                group_id,
                user_id,
                user_name,
                starting_cash_cents,
            )
        return dict(row)

    def _net_asset_cents(
        self,
        connection: sqlite3.Connection,
        group_id: str,
        user_id: str,
        cash_cents: int,
    ) -> int:
        row = connection.execute(
            """
            SELECT COALESCE(SUM(p.shares * s.price_cents), 0) AS market_value
            FROM positions p
            JOIN stocks s ON s.id = p.stock_id
            WHERE p.group_id = ? AND p.user_id = ?
            """,
            (group_id, user_id),
        ).fetchone()
        return cash_cents + int(row["market_value"])

    def buy(
        self,
        group_id: str,
        user_id: str,
        user_name: str,
        ticker: str,
        budget_cents: int,
        starting_cash_cents: int,
        fee_rate: float,
        max_position_ratio: float,
    ) -> dict[str, Any]:
        if budget_cents <= 0:
            raise TradeError("买入金额必须大于 0")

        with self._transaction() as connection:
            stock = self._stock_by_ticker(connection, ticker)
            if not stock:
                raise TradeError("没有找到这个股票代码")
            if stock["status"] != "active":
                raise TradeError("该热点已离榜，当前不能继续买入")

            account = self._ensure_account(
                connection,
                group_id,
                user_id,
                user_name,
                starting_cash_cents,
            )
            cash_cents = int(account["cash_cents"])
            if budget_cents > cash_cents:
                raise TradeError("账户余额不足")

            price_cents = int(stock["price_cents"])
            shares = int(budget_cents / (price_cents * (1 + fee_rate)))
            while shares > 0:
                cost_cents = shares * price_cents
                fee_cents = round(cost_cents * fee_rate)
                if cost_cents + fee_cents <= budget_cents:
                    break
                shares -= 1
            if shares < 1:
                raise TradeError("买入金额不足以购买 1 股")

            position = connection.execute(
                """
                SELECT * FROM positions
                WHERE group_id = ? AND user_id = ? AND stock_id = ?
                """,
                (group_id, user_id, stock["id"]),
            ).fetchone()
            old_shares = int(position["shares"]) if position else 0
            old_average = int(position["average_cost_cents"]) if position else 0
            net_asset = self._net_asset_cents(
                connection,
                group_id,
                user_id,
                cash_cents,
            )
            new_position_value = (old_shares + shares) * price_cents
            if new_position_value > round(net_asset * max_position_ratio):
                raise TradeError(f"单股持仓不能超过总资产的 {max_position_ratio:.0%}")

            total_cents = cost_cents + fee_cents
            new_shares = old_shares + shares
            average_cost = round((old_shares * old_average + total_cents) / new_shares)
            now = utc_now_text()
            connection.execute(
                """
                INSERT INTO positions(
                    group_id, user_id, stock_id, shares,
                    average_cost_cents, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(group_id, user_id, stock_id) DO UPDATE SET
                    shares = excluded.shares,
                    average_cost_cents = excluded.average_cost_cents,
                    updated_at = excluded.updated_at
                """,
                (
                    group_id,
                    user_id,
                    stock["id"],
                    new_shares,
                    average_cost,
                    now,
                ),
            )
            connection.execute(
                """
                UPDATE accounts
                SET cash_cents = cash_cents - ?, user_name = ?, updated_at = ?
                WHERE group_id = ? AND user_id = ?
                """,
                (total_cents, user_name, now, group_id, user_id),
            )
            connection.execute(
                """
                INSERT INTO orders(
                    group_id, user_id, stock_id, side, shares,
                    price_cents, fee_cents, created_at
                )
                VALUES (?, ?, ?, 'buy', ?, ?, ?, ?)
                """,
                (
                    group_id,
                    user_id,
                    stock["id"],
                    shares,
                    price_cents,
                    fee_cents,
                    now,
                ),
            )

        return {
            "ticker": stock["ticker"],
            "title": stock["title"],
            "shares": shares,
            "price_cents": price_cents,
            "cost_cents": cost_cents,
            "fee_cents": fee_cents,
            "cash_cents": cash_cents - total_cents,
        }

    def sell(
        self,
        group_id: str,
        user_id: str,
        user_name: str,
        ticker: str,
        shares_to_sell: int | None,
        starting_cash_cents: int,
        fee_rate: float,
    ) -> dict[str, Any]:
        with self._transaction() as connection:
            stock = self._stock_by_ticker(connection, ticker)
            if not stock:
                raise TradeError("没有找到这个股票代码")
            account = self._ensure_account(
                connection,
                group_id,
                user_id,
                user_name,
                starting_cash_cents,
            )
            position = connection.execute(
                """
                SELECT * FROM positions
                WHERE group_id = ? AND user_id = ? AND stock_id = ?
                """,
                (group_id, user_id, stock["id"]),
            ).fetchone()
            if not position:
                raise TradeError("你没有持有这只股票")

            held_shares = int(position["shares"])
            shares = held_shares if shares_to_sell is None else shares_to_sell
            if shares <= 0:
                raise TradeError("卖出股数必须大于 0")
            if shares > held_shares:
                raise TradeError(f"持仓不足，当前只有 {held_shares} 股")

            price_cents = int(stock["price_cents"])
            value_cents = shares * price_cents
            fee_cents = round(value_cents * fee_rate)
            proceeds_cents = value_cents - fee_cents
            realized_profit_cents = proceeds_cents - shares * int(
                position["average_cost_cents"]
            )
            now = utc_now_text()
            remaining_shares = held_shares - shares
            if remaining_shares == 0:
                connection.execute(
                    """
                    DELETE FROM positions
                    WHERE group_id = ? AND user_id = ? AND stock_id = ?
                    """,
                    (group_id, user_id, stock["id"]),
                )
            else:
                connection.execute(
                    """
                    UPDATE positions SET shares = ?, updated_at = ?
                    WHERE group_id = ? AND user_id = ? AND stock_id = ?
                    """,
                    (
                        remaining_shares,
                        now,
                        group_id,
                        user_id,
                        stock["id"],
                    ),
                )
            connection.execute(
                """
                UPDATE accounts
                SET cash_cents = cash_cents + ?, user_name = ?, updated_at = ?
                WHERE group_id = ? AND user_id = ?
                """,
                (proceeds_cents, user_name, now, group_id, user_id),
            )
            connection.execute(
                """
                INSERT INTO orders(
                    group_id, user_id, stock_id, side, shares,
                    price_cents, fee_cents, realized_profit_cents, created_at
                )
                VALUES (?, ?, ?, 'sell', ?, ?, ?, ?, ?)
                """,
                (
                    group_id,
                    user_id,
                    stock["id"],
                    shares,
                    price_cents,
                    fee_cents,
                    realized_profit_cents,
                    now,
                ),
            )
            cash_cents = int(account["cash_cents"]) + proceeds_cents

        return {
            "ticker": stock["ticker"],
            "title": stock["title"],
            "shares": shares,
            "price_cents": price_cents,
            "fee_cents": fee_cents,
            "proceeds_cents": proceeds_cents,
            "profit_cents": realized_profit_cents,
            "cash_cents": cash_cents,
        }

    def portfolio(
        self,
        group_id: str,
        user_id: str,
        user_name: str,
        starting_cash_cents: int,
    ) -> dict[str, Any]:
        account = self.ensure_account(
            group_id,
            user_id,
            user_name,
            starting_cash_cents,
        )
        rows = self.connection.execute(
            """
            SELECT
                p.shares, p.average_cost_cents,
                s.ticker, s.title, s.source, s.price_cents, s.status
            FROM positions p
            JOIN stocks s ON s.id = p.stock_id
            WHERE p.group_id = ? AND p.user_id = ?
            ORDER BY p.shares * s.price_cents DESC
            """,
            (group_id, user_id),
        ).fetchall()
        positions: list[dict[str, Any]] = []
        market_value_cents = 0
        unrealized_cents = 0
        for row in rows:
            item = dict(row)
            value_cents = int(row["shares"]) * int(row["price_cents"])
            profit_cents = int(row["shares"]) * (
                int(row["price_cents"]) - int(row["average_cost_cents"])
            )
            item["value_cents"] = value_cents
            item["profit_cents"] = profit_cents
            market_value_cents += value_cents
            unrealized_cents += profit_cents
            positions.append(item)
        cash_cents = int(account["cash_cents"])
        return {
            "cash_cents": cash_cents,
            "market_value_cents": market_value_cents,
            "net_asset_cents": cash_cents + market_value_cents,
            "unrealized_cents": unrealized_cents,
            "positions": positions,
        }

    def leaderboard(self, group_id: str, limit: int = 10) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT
                a.user_id,
                a.user_name,
                a.cash_cents,
                a.cash_cents + COALESCE(SUM(p.shares * s.price_cents), 0)
                    AS net_asset_cents
            FROM accounts a
            LEFT JOIN positions p
                ON p.group_id = a.group_id AND p.user_id = a.user_id
            LEFT JOIN stocks s ON s.id = p.stock_id
            WHERE a.group_id = ?
              AND EXISTS (
                  SELECT 1
                  FROM orders o
                  WHERE o.group_id = a.group_id
                    AND o.user_id = a.user_id
              )
            GROUP BY a.group_id, a.user_id
            ORDER BY net_asset_cents DESC, a.updated_at ASC
            LIMIT ?
            """,
            (group_id, max(1, limit)),
        ).fetchall()
        return [dict(row) for row in rows]

    def group_ids_with_participants(self) -> list[str]:
        rows = self.connection.execute(
            "SELECT DISTINCT group_id FROM orders ORDER BY group_id"
        ).fetchall()
        return [str(row["group_id"]) for row in rows]

    def analysis_members(
        self,
        group_id: str,
        member_limit: int = 20,
        position_limit: int = 5,
    ) -> list[dict[str, Any]]:
        members = self.leaderboard(group_id, member_limit)
        for member in members:
            rows = self.connection.execute(
                """
                SELECT
                    s.ticker, s.title, p.shares, p.average_cost_cents,
                    s.price_cents, s.status
                FROM positions p
                JOIN stocks s ON s.id = p.stock_id
                WHERE p.group_id = ? AND p.user_id = ?
                ORDER BY p.shares * s.price_cents DESC
                LIMIT ?
                """,
                (group_id, member["user_id"], max(1, position_limit)),
            ).fetchall()
            positions: list[dict[str, Any]] = []
            for row in rows:
                position = dict(row)
                position["profit_cents"] = int(row["shares"]) * (
                    int(row["price_cents"]) - int(row["average_cost_cents"])
                )
                positions.append(position)
            member["positions"] = positions
        return members

    def close(self) -> None:
        self.connection.close()
