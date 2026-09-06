"""
Text extraction functions.

This module provides extraction functions for medical case data. The actual
extraction logic lives in the patterns/ directory, organized by field category.

For implementation details and pattern definitions, see:
- patterns/airway_patterns.py
- patterns/vascular_access_patterns.py
- patterns/monitoring_patterns.py
"""

from __future__ import annotations

import re

from .patterns import (
    extract_airway_management,
    extract_monitoring,
    extract_vascular_access,
)
from .types import Scalar, is_missing_scalar

__all__ = [
    "clean_names",
    "extract_airway_management",
    "extract_attending",
    "extract_monitoring",
    "extract_vascular_access",
]


def clean_names(name: Scalar | None) -> str:
    """
    Clean and standardize provider names.

    Removes titles, trailing commas, and normalizes whitespace.

    Args:
        name: Raw provider name or missing scalar.

    Returns:
        Cleaned name string, or an empty string for missing values.

    Example:
        clean_names("Smith, John MD")
        # Returns: "Smith, John"
    """
    if is_missing_scalar(name):
        return ""
    # Take only the first attending if multiple are listed
    name = str(name).split(";")[0].strip()
    name = re.sub(r",\s*$", "", name).strip()
    # Strip trailing credentials only. A leading "DO," is a surname, not a title.
    credential_match = re.search(
        r"[\s,]+(\b(?:MD|DO|PhD|CRNA|RN)\b)\.?\s*$",
        name,
        flags=re.IGNORECASE,
    )
    if credential_match:
        before = name[: credential_match.start()].rstrip(" ,")
        prior_parts = [part for part in re.split(r"[\s,]+", before) if part]
        # Keep "NGUYEN, DO" where DO is the only given name.
        if not (len(prior_parts) == 1 and credential_match.group(1).casefold() == "do"):
            name = before
    name = re.sub(r",\s*$", "", name).strip()
    return re.sub(r"\s+", " ", name)


def extract_attending(value: Scalar) -> str:
    """Clean an attending name by removing timestamps and extra entries.

    Input format: "DOE, JOHN@2023-01-01 08:00:00" or semicolon-separated list.
    Returns the first name with the timestamp stripped.

    Args:
        value: Raw attending name value from the MPOG AnesAttendings field.
            May be NaN or contain multiple semicolon-separated entries, each
            optionally followed by an "@timestamp" suffix.

    Returns:
        First attending name with the timestamp removed, or an empty string
        if value is NaN.
    """
    if is_missing_scalar(value):
        return ""
    first_part = str(value).split(";")[0]
    return first_part.split("@")[0].strip()
