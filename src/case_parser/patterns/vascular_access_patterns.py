"""
Vascular Access Extraction Patterns.

This file contains all regex patterns used to extract specialized vascular access
from procedure notes.

FIELDS EXTRACTED:
- Arterial Catheter (A-line, radial, femoral arterial lines)
- Central Venous Catheter (CVC, IJ, subclavian, femoral)
- Pulmonary Artery Catheter (Swan-Ganz, PAC)

MODIFICATION GUIDE:
To add a new pattern, simply append it to the relevant list below.
Patterns are case-insensitive and use standard Python regex syntax.

EXAMPLES OF MATCHED TEXT:
- "arterial line placed" → Arterial Catheter
- "right radial A-line" → Arterial Catheter
- "CVC via right IJ" → Central Venous Catheter
- "Swan-Ganz catheter" → Pulmonary Artery Catheter
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..domain import ExtractionFinding, VascularAccess
from .airway_patterns import NEGATION_PATTERNS
from .extraction_utils import (
    calculate_pattern_confidence,
    extract_with_context,
    remove_duplicates_preserve_order,
)

# ============================================================================
# ARTERIAL CATHETERS
# ============================================================================
# Arterial lines for continuous blood pressure monitoring
ARTERIAL_LINE_PATTERNS = [
    r"\barterial\s+line\b",
    r"\bA-?line\b",
    r"\bart[- ]line\b",
    r"\barterial\s+catheter\b",
    r"\b[Aa]\s+line\b",
    r"\bradial\s+(artery|arterial|line)\b",
    r"\bfemoral\s+(artery|arterial|line)\b",
]

# ============================================================================
# CENTRAL VENOUS CATHETERS
# ============================================================================
# Central lines for medication administration, CVP monitoring, etc.
CENTRAL_LINE_PATTERNS = [
    r"\bcentral\s+(venous|line)\b",
    r"\bCVC\b",
    r"\binternal\s+jugular\b",
    r"\bIJ\b.*\b(line|catheter)\b",
    r"\bsubclavian\b.*\b(line|catheter)\b",
    r"\bfemoral\s+(venous\s+)?(line|catheter)\b",
    r"\bcentral\s+access\b",
]

# ============================================================================
# PULMONARY ARTERY CATHETERS
# ============================================================================
# Swan-Ganz catheters for hemodynamic monitoring
PA_CATHETER_PATTERNS = [
    r"\bpulmonary\s+artery\s+catheter\b",
    r"\bPA\s+catheter\b",
    r"\bSwan[- ]?Ganz\b",
    r"\bPAC\b",
]


# ============================================================================
# EXTRACTION FUNCTION
# ============================================================================


def extract_vascular_access(
    notes: Any, source_field: str = "procedure_notes"
) -> tuple[list[VascularAccess], list[ExtractionFinding]]:
    """
    Extract vascular access with pattern matching and confidence scoring.

    This function analyzes procedure notes to identify:
    - Arterial lines (radial, femoral, etc.)
    - Central venous catheters (IJ, subclavian, femoral)
    - Pulmonary artery catheters (Swan-Ganz)

    Args:
        notes: Procedure notes text (can be None, NaN, or string)
        source_field: Name of the field being analyzed (for tracking)

    Returns:
        Tuple of (vascular_access_list, extraction_findings)
        - vascular_access_list: List of VascularAccess enums found
        - extraction_findings: List of ExtractionFinding objects with confidence scores

    Example:
        notes = "Arterial line placed in right radial artery, CVC via right IJ"
        access, findings = extract_vascular_access(notes)
        # access: [VascularAccess.ARTERIAL_CATHETER,
        VascularAccess.CENTRAL_VENOUS_CATHETER]
    """
    if notes is None or (isinstance(notes, float) and pd.isna(notes)):
        return [], []

    text = str(notes)
    vascular = []
    findings = []

    # Arterial line
    art_matches = extract_with_context(text, ARTERIAL_LINE_PATTERNS)
    if art_matches:
        vascular.append(VascularAccess.ARTERIAL_CATHETER)
        confidence = calculate_pattern_confidence(
            text, ARTERIAL_LINE_PATTERNS, None, NEGATION_PATTERNS
        )
        findings.append(
            ExtractionFinding(
                value=VascularAccess.ARTERIAL_CATHETER.value,
                confidence=confidence,
                context=art_matches[0][1],
                source_field=source_field,
            )
        )

    # Central venous catheter
    cvc_matches = extract_with_context(text, CENTRAL_LINE_PATTERNS)
    if cvc_matches:
        vascular.append(VascularAccess.CENTRAL_VENOUS_CATHETER)
        confidence = calculate_pattern_confidence(
            text, CENTRAL_LINE_PATTERNS, None, NEGATION_PATTERNS
        )
        findings.append(
            ExtractionFinding(
                value=VascularAccess.CENTRAL_VENOUS_CATHETER.value,
                confidence=confidence,
                context=cvc_matches[0][1],
                source_field=source_field,
            )
        )

    # PA catheter
    pa_matches = extract_with_context(text, PA_CATHETER_PATTERNS)
    if pa_matches:
        vascular.append(VascularAccess.PULMONARY_ARTERY_CATHETER)
        confidence = calculate_pattern_confidence(
            text, PA_CATHETER_PATTERNS, CENTRAL_LINE_PATTERNS
        )
        findings.append(
            ExtractionFinding(
                value=VascularAccess.PULMONARY_ARTERY_CATHETER.value,
                confidence=confidence,
                context=pa_matches[0][1],
                source_field=source_field,
            )
        )

    return remove_duplicates_preserve_order(vascular), findings
