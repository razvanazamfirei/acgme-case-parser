"""Shared routing for standalone orphan-procedure export files."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .domain import ParsedCase, ProcedureCategory
from .patterns.block_site_patterns import PERIPHERAL_BLOCK_SITE_TERMS

_OB_PROCEDURE_HINTS = ("EPIDURAL", "SPINAL", "CSE")
_OBSTETRIC_CATEGORIES = {
    ProcedureCategory.CESAREAN,
    ProcedureCategory.VAGINAL_DELIVERY,
}


@dataclass(frozen=True)
class StandaloneOutputSpec:
    """Metadata describing one standalone orphan output file."""

    suffix: str
    label: str


BLOCKS_OUTPUT_SPEC = StandaloneOutputSpec(
    suffix="blocks",
    label="Blocks",
)
NEURAXIAL_DELIVERY_OUTPUT_SPEC = StandaloneOutputSpec(
    suffix="ob",
    label="OB",
)
UNMATCHED_OUTPUT_SPEC = StandaloneOutputSpec(
    suffix="unmatched",
    label="Unmatched",
)


def _standalone_case_search_text(case: ParsedCase) -> str:
    """Build a single uppercase search string for standalone-case routing."""
    return " ".join(
        value
        for value in (
            case.raw_anesthesia_type,
            case.raw_nerve_block_type,
            case.unmatched_block_source,
            case.procedure,
            case.procedure_notes,
            case.nerve_block_type,
        )
        if value
    ).upper()


def is_block_standalone_case(case: ParsedCase) -> bool:
    """Return True when standalone procedure text indicates a block technique."""
    search_text = _standalone_case_search_text(case)
    # Use word boundaries to avoid false positives like "HEART BLOCK"
    pattern = r"\b(PERIPHERAL NERVE BLOCK|NERVE BLOCK|BLOCK)\b"
    return bool(re.search(pattern, search_text, re.IGNORECASE))


def _normalized_block_terms(case: ParsedCase) -> set[str]:
    """Split normalized standalone block-site text into canonical terms."""
    if not case.nerve_block_type:
        return set()
    return {
        term.strip()
        for term in case.nerve_block_type.split(";")
        if term and term.strip()
    }


def _has_normalized_peripheral_block(case: ParsedCase) -> bool:
    """Return True when normalized standalone block text is peripheral."""
    return bool(_normalized_block_terms(case) & set(PERIPHERAL_BLOCK_SITE_TERMS))


def is_ob_standalone_case(case: ParsedCase) -> bool:
    """Return True when a standalone procedure belongs in the OB export."""
    procedure_text = (case.procedure or "").upper()
    return (
        any(hint in procedure_text for hint in _OB_PROCEDURE_HINTS)
        or case.procedure_category in _OBSTETRIC_CATEGORIES
    )


def split_standalone_cases(
    cases: list[ParsedCase],
) -> tuple[list[ParsedCase], list[ParsedCase], list[ParsedCase]]:
    """Split standalone orphan procedures into block, OB, and unmatched lists.

    The OB export includes cases where the procedure text contains epidural,
    spinal, or CSE, plus any case already categorized as cesarean or vaginal
    delivery.
    """
    block_cases: list[ParsedCase] = []
    ob_cases: list[ParsedCase] = []
    unmatched_cases: list[ParsedCase] = []

    for case in cases:
        if _has_normalized_peripheral_block(case) or is_block_standalone_case(case):
            block_cases.append(case)
            continue
        if is_ob_standalone_case(case):
            ob_cases.append(case)
            continue
        unmatched_cases.append(case)

    return block_cases, ob_cases, unmatched_cases


def iter_standalone_case_exports(
    cases: list[ParsedCase],
) -> list[tuple[StandaloneOutputSpec, list[ParsedCase]]]:
    """Return standalone export specs paired with their routed case lists."""
    block_cases, ob_cases, unmatched_cases = split_standalone_cases(cases)
    return [
        (BLOCKS_OUTPUT_SPEC, block_cases),
        (NEURAXIAL_DELIVERY_OUTPUT_SPEC, ob_cases),
        (UNMATCHED_OUTPUT_SPEC, unmatched_cases),
    ]
