"""Shared utility helpers for case-parser scripts and tools."""

from __future__ import annotations

from .types import Scalar

LRU_CACHE_SIZE = 32768
_MISSING_TEXT_SENTINELS = {"", "<NA>", "nan", "NaN", "None", "NaT"}
_NORMALIZED_SENTINELS = {s.strip("<>").casefold() for s in _MISSING_TEXT_SENTINELS}


def normalize_stem(name: str) -> str:
    """Normalize a resident file stem into a stable, uppercase key."""
    return name.replace(".Supervised", "").replace(",", "_").strip().upper()


def format_name(name: str) -> str:
    """Convert resident file stems into a clean display name.

    Args:
        name: Filename stem from the CSV export pair.

    Returns:
        Best-effort title-cased resident name with any ``.Supervised`` marker
        removed.
    """
    cleaned = name.replace(".Supervised", "").strip()
    if "," in cleaned:
        last, first = (part.strip() for part in cleaned.split(",", 1))
        return f"{first.title()} {last.title()}".strip()

    parts = [part.strip() for part in cleaned.split("_", 1)]
    if len(parts) == 2:
        first, second = parts
        if first.isupper() and second.isupper():
            return f"{second.title()} {first.title()}"
        return f"{first.title()} {second.title()}"
    return cleaned.title()


def clean_text(value: Scalar | None) -> str:
    """Normalize text values to a plain string or empty string.

    Args:
        value: Any scalar value or None.

    Returns:
        Stripped string with missing-value sentinels normalized to empty string.
    """
    if value is None:
        return ""
    text = str(value).strip()
    if text.strip("<>").casefold() in _NORMALIZED_SENTINELS:
        return ""
    return text
