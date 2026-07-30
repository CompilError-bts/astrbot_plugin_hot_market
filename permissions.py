from __future__ import annotations

from typing import Any


def normalize_allowed_umos(raw: Any) -> frozenset[str]:
    """Normalize the configured group-session UMO allowlist."""
    if not isinstance(raw, list):
        return frozenset()
    return frozenset(
        umo
        for item in raw
        if (umo := str(item).strip())
    )


def is_group_umo_allowed(
    umo: str,
    *,
    is_private_chat: bool,
    allowed_umos: frozenset[str],
) -> bool:
    """Return whether a group-session UMO may use the plugin."""
    normalized_umo = str(umo or "").strip()
    if is_private_chat or not normalized_umo:
        return False
    return "*" in allowed_umos or normalized_umo in allowed_umos
