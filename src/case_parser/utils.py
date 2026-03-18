from __future__ import annotations

"""Shared utility helpers for case-parser scripts and tools."""


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
