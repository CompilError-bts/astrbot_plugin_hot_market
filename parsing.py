from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

MAX_MONEY = Decimal("92233720368547758.07")


def parse_money_to_cents(raw: Any) -> int:
    """Parse a user-supplied money amount into integer cents."""
    normalized = str(raw).strip()
    if not normalized:
        raise ValueError("买入金额应为数字")

    try:
        amount = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError("买入金额应为数字") from exc

    if not amount.is_finite():
        raise ValueError("买入金额应为有限数字")
    if amount <= 0:
        raise ValueError("买入金额必须大于 0")
    if amount > MAX_MONEY:
        raise ValueError("买入金额过大")

    cents = int(
        (amount * 100).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    )
    if cents <= 0:
        raise ValueError("买入金额至少为 0.01 热币")
    return cents
