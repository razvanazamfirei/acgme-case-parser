"""Shared type aliases for case-parser."""

from __future__ import annotations

from collections.abc import Sequence
from math import isnan
from numbers import Real

import pandas as pd

# Scalar values from pandas DataFrames, Excel cells, or dict lookups.
# pd.NA/pd.NaT are handled via pd.isna() at runtime.
type Scalar = str | int | float | bool | None

# Raw services field: single string, sequence of strings, or null.
type ServicesInput = str | Sequence[str] | None


def is_missing_scalar(value: Scalar | object) -> bool:
    """Return True for scalar missing-value sentinels.

    Args:
        value: Any value to check.

    Returns:
        True if value is None, pd.NA, pd.NaT, or a real NaN float.
    """
    if value is None or value is pd.NA or value is pd.NaT:
        return True
    if isinstance(value, Real):
        return isnan(float(value))
    return False
