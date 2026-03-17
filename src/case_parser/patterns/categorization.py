"""
Procedure Categorization Logic.

This module contains all the logic for categorizing procedures based on
services and procedure text. Each surgery type has its own categorization
function that encapsulates the specific rules for that type.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from functools import lru_cache
from itertools import starmap
from numbers import Real

import pandas as pd

from ..domain import ProcedureCategory
from .approach_patterns import detect_approach, detect_intracerebral_pathology
from .procedure_patterns import (
    DEFAULT_PROCEDURE_CATEGORY,
    OBGYN_SERVICE_KEYWORDS,
    PROCEDURE_RULES,
    PROCEDURE_TEXT_RULES,
    ProcedureRule,
)

_SERVICE_SENTINELS = {"", "<NA>", "NAN", "NONE"}
_CESAREAN_KEYWORDS = ("CESAREAN", "C-SECTION", "C SECTION")
_OB_DELIVERY_KEYWORDS = ("VAGINAL", "DELIVERY", "LABOR")
_OB_GENERIC_NEURAXIAL_KEYWORDS = ("EPIDURAL", "CSE")


def categorize_cardiac(procedure_text: str) -> ProcedureCategory:
    """
    Categorize cardiac procedures based on CPB usage.

    Cardiac procedures are split into:
    - Cardiac with CPB: Traditional open-heart surgery with cardiopulmonary bypass
    - Cardiac without CPB: Percutaneous/transcatheter procedures, VAD removal, etc.

    Args:
        procedure_text: Uppercase procedure description

    Returns:
        ProcedureCategory for cardiac subtype
    """
    no_cpb_keywords = (
        "TAVR",
        "TAVI",
        "TRANSCATHETER AORTIC VALVE REPLACEMENT",
        "OFF-PUMP",
        "OFF PUMP",
        "OPCAB",
        "BEATING HEART",
        "REMOVAL VENTRICULAR ASSIST DEVICE",
        "REMOVAL IMPLANT",
    )

    strong_cpb_keywords = (
        "CPB",
        "CARDIOPULMONARY BYPASS",
        "CABG",
        "CORONARY ARTERY BYPASS",
        "ASCENDING AORTA GRAFT",
        "HEART TRANSPLANT",
        "LUNG TRANSPLANT",
    )
    cpb_keywords = (
        "BYPASS",
        "PUMP",
        "ON-PUMP",
        "ON PUMP",
    )

    has_no_cpb = any(kw in procedure_text for kw in no_cpb_keywords)
    has_strong_cpb = any(kw in procedure_text for kw in strong_cpb_keywords)
    has_cpb = any(kw in procedure_text for kw in cpb_keywords)

    if any(
        kw in procedure_text
        for kw in ("OFF-PUMP", "OFF PUMP", "OPCAB", "BEATING HEART")
    ):
        return ProcedureCategory.CARDIAC_WITHOUT_CPB

    if has_strong_cpb:
        return ProcedureCategory.CARDIAC_WITH_CPB

    if has_no_cpb:
        return ProcedureCategory.CARDIAC_WITHOUT_CPB
    if has_cpb:
        return ProcedureCategory.CARDIAC_WITH_CPB

    if "TRANSCATHETER" in procedure_text and any(
        term in procedure_text for term in ("VALVE", "VALVULOPLASTY", "AORTIC")
    ):
        return ProcedureCategory.CARDIAC_WITHOUT_CPB

    # Default to with CPB for unspecified cardiac procedures
    return ProcedureCategory.CARDIAC_WITH_CPB


def categorize_vascular(procedure_text: str) -> ProcedureCategory:
    """
    Categorize major vessel procedures based on surgical approach.

    Major vessel procedures are split into:
    - Endovascular: Percutaneous, catheter-based interventions
    - Open: Traditional open surgical repair

    Args:
        procedure_text: Procedure description

    Returns:
        ProcedureCategory for vascular subtype
    """
    approach = detect_approach(procedure_text)
    if approach == "endovascular":
        return ProcedureCategory.MAJOR_VESSELS_ENDOVASCULAR
    return ProcedureCategory.MAJOR_VESSELS_OPEN


def categorize_intracerebral(procedure_text: str) -> ProcedureCategory:
    """
    Categorize intracerebral procedures based on approach and pathology.

    Intracerebral procedures are split by:
    1. Approach: endovascular vs open
    2. Pathology (for open): vascular vs nonvascular

    Args:
        procedure_text: Procedure description

    Returns:
        ProcedureCategory for intracerebral subtype
    """
    approach = detect_approach(procedure_text)

    if approach == "endovascular":
        return ProcedureCategory.INTRACEREBRAL_ENDOVASCULAR

    if approach == "open":
        pathology = detect_intracerebral_pathology(procedure_text)
        if pathology == "vascular":
            return ProcedureCategory.INTRACEREBRAL_VASCULAR_OPEN
        if pathology == "nonvascular":
            return ProcedureCategory.INTRACEREBRAL_NONVASCULAR_OPEN
        # Default to vascular if unknown
        return ProcedureCategory.INTRACEREBRAL_VASCULAR_OPEN

    return ProcedureCategory.INTRACEREBRAL_NONVASCULAR_OPEN


def _categorize_obgyn_text(
    procedure_text: str,
    *,
    allow_generic_neuraxial: bool = False,
) -> ProcedureCategory:
    """Return the OB/GYN category for normalized procedure text."""
    if any(keyword in procedure_text for keyword in _CESAREAN_KEYWORDS):
        return ProcedureCategory.CESAREAN

    if any(keyword in procedure_text for keyword in _OB_DELIVERY_KEYWORDS):
        return ProcedureCategory.VAGINAL_DELIVERY

    if allow_generic_neuraxial and any(
        keyword in procedure_text for keyword in _OB_GENERIC_NEURAXIAL_KEYWORDS
    ):
        return ProcedureCategory.VAGINAL_DELIVERY

    return ProcedureCategory.OTHER


def categorize_obgyn(procedure_text: str) -> ProcedureCategory:
    """
    Categorize OB/GYN procedures based on delivery type.

    OB/GYN procedures are split into:
    - Cesarean delivery
    - Vaginal delivery (including labor epidurals)
    - Other GYN procedures

    Args:
        procedure_text: Uppercase procedure description

    Returns:
        ProcedureCategory for OB/GYN subtype
    """
    return _categorize_obgyn_text(procedure_text)


def _match_rules(
    values: list[str],
    procedure_text: str,
    rules: list[ProcedureRule],
    *,
    exclude_in_values: bool,
) -> list[ProcedureCategory]:
    """Return ordered unique categories matched by a set of ProcedureRule values."""
    categories: list[ProcedureCategory] = []
    for value in values:
        for rule in rules:
            if not any(keyword in value for keyword in rule.keywords):
                continue
            if rule.exclude_keywords and any(
                excl in procedure_text or (exclude_in_values and excl in value)
                for excl in rule.exclude_keywords
            ):
                continue
            category = _apply_rule_category(rule.category, procedure_text)
            _append_unique_category(categories, category)
            break
    return categories


def _append_unique_category(
    categories: list[ProcedureCategory],
    category: ProcedureCategory,
) -> None:
    """Append one category while preserving encounter order and uniqueness."""
    if category not in categories:
        categories.append(category)


def _match_services_to_categories(
    services: list[str], procedure_text: str
) -> list[ProcedureCategory]:
    """Match services against procedure rules and return matched categories."""
    categories = _match_rules(
        services,
        procedure_text,
        PROCEDURE_RULES,
        exclude_in_values=True,
    )

    has_obstetric_service = any(
        any(keyword in service for keyword in OBGYN_SERVICE_KEYWORDS)
        for service in services
    )
    if has_obstetric_service:
        obgyn_category = _categorize_obgyn_text(
            procedure_text,
            allow_generic_neuraxial=True,
        )
        if obgyn_category != ProcedureCategory.OTHER:
            _append_unique_category(categories, obgyn_category)

    return categories


def _fallback_categories_from_text(procedure_text: str) -> list[ProcedureCategory]:
    """Infer categories directly from procedure text when services are empty.

    Scans PROCEDURE_RULES keywords against the uppercase procedure text and
    returns the first matching category. If no rule matches, falls back to
    categorize_obgyn; returns an empty list if that also yields OTHER.

    Args:
        procedure_text: Uppercase procedure description.

    Returns:
        List containing at most one ProcedureCategory, or an empty list when
        no rule or OB/GYN keyword matches.
    """
    categories = _match_rules(
        [procedure_text],
        procedure_text,
        PROCEDURE_TEXT_RULES,
        exclude_in_values=False,
    )
    if categories:
        return [categories[0]]

    obgyn_category = categorize_obgyn(procedure_text)
    return [] if obgyn_category == ProcedureCategory.OTHER else [obgyn_category]


def _collect_candidate_categories(
    procedure_text: str,
    services: tuple[str, ...],
) -> list[ProcedureCategory]:
    """Collect ordered category candidates from services, then text fallback."""
    categories = _match_services_to_categories(list(services), procedure_text)
    if categories or not procedure_text:
        return categories
    return _fallback_categories_from_text(procedure_text)


def _resolve_category_result(
    categories: list[ProcedureCategory],
    services: tuple[str, ...],
) -> tuple[ProcedureCategory, tuple[str, ...]]:
    """Resolve candidate categories to the final category and warnings."""
    if not categories:
        return ProcedureCategory(DEFAULT_PROCEDURE_CATEGORY), ()

    if len(categories) == 1:
        return categories[0], ()

    warning = (
        f"Multiple procedure categories detected for services {list(services)}: "
        f"{[category.value for category in categories]}. "
        f"Using first: {categories[0].value}"
    )
    return categories[0], (warning,)


def _normalize_categorization_request(
    procedure: str | None,
    services: object,
) -> tuple[str, tuple[str, ...]]:
    """Normalize one categorization request for cached lookup."""
    return _normalize_procedure_text(procedure), _normalize_services(services)


def _categorize_normalized_requests(
    normalized_requests: Sequence[tuple[str, tuple[str, ...]]],
) -> list[tuple[ProcedureCategory, list[str]]]:
    """Categorize normalized requests through the shared cached path."""
    results: list[tuple[ProcedureCategory, list[str]]] = []
    for procedure_text, normalized_services in normalized_requests:
        category, warnings = _categorize_procedure_cached(
            procedure_text,
            normalized_services,
        )
        results.append((category, list(warnings)))
    return results


def categorize_procedure(
    procedure: str | None,
    services: object,
) -> tuple[ProcedureCategory, list[str]]:
    """
    Categorize a procedure based on services and procedure text.

    This is the main entry point for procedure categorization. It:
    1. Checks services against PROCEDURE_RULES
    2. Applies surgery-specific categorization logic
    3. Handles special cases such as OB/GYN delivery categorization
    4. Returns the category and any warnings

    Args:
        procedure: Procedure description text
        services: Sequence of raw service values, a single raw service
            string, or a scalar missing sentinel. Missing/null sentinels are
            ignored during normalization.

    Returns:
        Tuple of (ProcedureCategory, warnings_list)
    """
    return _categorize_normalized_requests(
        [_normalize_categorization_request(procedure, services)]
    )[0]


def categorize_procedures(
    procedures: Sequence[str | None],
    services_list: Sequence[object],
) -> list[tuple[ProcedureCategory, list[str]]]:
    """Categorize multiple procedures while reusing cached normalization."""
    if len(procedures) != len(services_list):
        raise ValueError("services_list must match procedures length")

    normalized_requests = list(
        starmap(
            _normalize_categorization_request,
            zip(procedures, services_list, strict=True),
        )
    )
    return _categorize_normalized_requests(normalized_requests)


def _normalize_procedure_text(procedure: str | None) -> str:
    """Normalize optional procedure text to uppercase for caching."""
    if pd.isna(procedure):
        return ""
    return str(procedure).upper()


def _is_missing_service_scalar(service: object) -> bool:
    """Return True when a raw services input is a scalar null sentinel."""
    if service is None or service is pd.NA or service is pd.NaT:
        return True
    if isinstance(service, Real):
        return math.isnan(float(service))
    return False


def _normalize_services(services: object) -> tuple[str, ...]:
    """Normalize raw service values to uppercase immutable tuples for caching."""
    if _is_missing_service_scalar(services):
        return ()

    raw_services: Sequence[object] | tuple[object, ...]
    if isinstance(services, str):
        raw_services = (services,)
    elif isinstance(services, Sequence):
        raw_services = services
    else:
        raw_services = (services,)

    normalized: list[str] = []
    for service in raw_services:
        if _is_missing_service_scalar(service):
            continue

        service_text = str(service).strip().upper()
        if service_text and service_text not in _SERVICE_SENTINELS:
            normalized.append(service_text)
    return tuple(normalized)


@lru_cache(maxsize=32768)
def _categorize_procedure_cached(
    procedure_text: str,
    services: tuple[str, ...],
) -> tuple[ProcedureCategory, tuple[str, ...]]:
    """Cached implementation of categorize_procedure()."""
    categories = _collect_candidate_categories(procedure_text, services)
    return _resolve_category_result(categories, services)


def _apply_rule_category(rule_category: str, procedure_text: str) -> ProcedureCategory:
    """
    Apply surgery-specific categorization based on rule category.

    This maps rule categories to their specific categorization functions.

    Args:
        rule_category: Category from PROCEDURE_RULES
        procedure_text: Uppercase procedure description

    Returns:
        Specific ProcedureCategory
    """
    if rule_category == "Cardiac":
        return categorize_cardiac(procedure_text)

    if rule_category == "Procedures Major Vessels":
        return categorize_vascular(procedure_text)

    if rule_category == "Intracerebral":
        return categorize_intracerebral(procedure_text)

    # Standard category mapping
    category_map = {
        "Intrathoracic non-cardiac": ProcedureCategory.INTRATHORACIC_NON_CARDIAC,
        "Other (procedure cat)": ProcedureCategory.OTHER,
    }
    return category_map.get(rule_category, ProcedureCategory.OTHER)
