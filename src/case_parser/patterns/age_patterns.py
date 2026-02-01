"""
Age Categorization Rules.

This file contains rules for categorizing patient ages into standardized
age ranges for residency requirement tracking.

FIELDS EXTRACTED:
- Age Category (a through e, corresponding to ACGME age ranges)

MODIFICATION GUIDE:
Age ranges use upper bound matching. The age is compared against each range
in order, and the first range where age < upper_bound is selected.

To modify age ranges:
1. Edit the upper_bound values (in years)
2. Edit the category labels
3. Keep ranges in ascending order by upper_bound

CATEGORIES:
- a. < 3 months (neonatal)
- b. >= 3 mos. and < 3 yr. (infant/toddler)
- c. >= 3 yr. and < 12 yr. (child)
- d. >= 12 yr. and < 65 yr. (adult)
- e. >= 65 year (geriatric)

NOTE: Ages are expected in years. Months are converted to fractional years:
- 3 months = 0.25 years
- 3 years = 3 years
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgeRange:
    """Age range with upper bound and category label."""

    upper_bound: float  # Age in years
    category: str  # Display label for this age range


# ============================================================================
# AGE CATEGORIZATION RANGES
# ============================================================================
# Ranges are evaluated in order. First match where age < upper_bound wins.
AGE_RANGES = [
    # Neonatal: Under 3 months (0.25 years)
    AgeRange(
        upper_bound=0.25,
        category="a. < 3 months",
    ),
    # Infant/Toddler: 3 months to 3 years
    AgeRange(
        upper_bound=3,
        category="b. >= 3 mos. and < 3 yr.",
    ),
    # Child: 3 years to 12 years
    AgeRange(
        upper_bound=12,
        category="c. >= 3 yr. and < 12 yr.",
    ),
    # Adult: 12 years to 65 years
    AgeRange(
        upper_bound=65,
        category="d. >= 12 yr. and < 65 yr.",
    ),
    # Geriatric: 65 years and older
    AgeRange(
        upper_bound=float("inf"),
        category="e. >= 65 year",
    ),
]
