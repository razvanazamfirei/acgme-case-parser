"""Shared type aliases for case-parser."""

from __future__ import annotations

from collections.abc import Sequence

# Scalar values from pandas DataFrames, Excel cells, or dict lookups.
# pd.NA/pd.NaT are handled via pd.isna() at runtime.
type Scalar = str | int | float | bool | None

# Raw services field: single string, sequence of strings, or null.
type ServicesInput = str | Sequence[str] | None
