"""
Specialized Monitoring Extraction Patterns.

This file contains all regex patterns used to extract specialized monitoring
techniques from procedure notes.

FIELDS EXTRACTED:
- TEE (Transesophageal Echocardiography)
- Electrophysiologic Monitoring (SSEP, MEP, EMG, EEG)
- CSF Drain (Cerebrospinal Fluid Drainage)
- Invasive Neurological Monitoring (ICP, ventriculostomy)

MODIFICATION GUIDE:
To add a new pattern, simply append it to the relevant list below.
Patterns are case-insensitive and use standard Python regex syntax.

EXAMPLES OF MATCHED TEXT:
- "TEE performed" → TEE
- "neuromonitoring with SSEPs" → Electrophysiologic mon
- "lumbar drain placed" → CSF Drain
- "ICP monitor" → Invasive neuro mon
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..domain import ExtractionFinding, MonitoringTechnique
from .extraction_utils import (
    calculate_pattern_confidence,
    extract_with_context,
    remove_duplicates_preserve_order,
)

# ============================================================================
# TRANSESOPHAGEAL ECHOCARDIOGRAPHY
# ============================================================================
# TEE for cardiac visualization and monitoring
TEE_PATTERNS = [
    r"\bTEE\b",
    r"\btransesophageal\s+echo(cardiograph(y|ic))?\b",
    r"\btrans[- ]?esophageal\b",
]

# ============================================================================
# ELECTROPHYSIOLOGIC MONITORING
# ============================================================================
# Neuromonitoring including SSEPs, MEPs, EMG, EEG
ELECTROPHYSIOLOGIC_PATTERNS = [
    r"\belectrophysiolog(ic|y)\b",
    r"\bEP\s+stud(y|ies)\b",
    r"\bSSCP\b",  # Somatosensory Cortical Potentials
    r"\bSSEP\b",  # Somatosensory Evoked Potentials
    r"\bneuro(physiologic)?\s+monitor",
    r"\bevoked\s+potential",
]

# ============================================================================
# CSF DRAINAGE
# ============================================================================
# Cerebrospinal fluid drains (lumbar drains, etc.)
CSF_DRAIN_PATTERNS = [
    r"\bCSF\s+(drain(age)?|catheter)\b",
    r"\blumbar\s+drain\b",
    r"\bcerebrospinal\s+fluid\s+drain",
    r"\bspinal\s+drain\b",
]

# ============================================================================
# INVASIVE NEUROLOGICAL MONITORING
# ============================================================================
# ICP monitoring, ventriculostomy, EVD
INVASIVE_NEURO_PATTERNS = [
    r"\bICP\s+(monitor|catheter)\b",
    r"\bintracranial\s+pressure\b",
    r"\bventriculostomy\b",
    r"\bEVD\b",  # External Ventricular Drain
]


# ============================================================================
# EXTRACTION FUNCTION
# ============================================================================


def extract_monitoring(
    notes: Any, source_field: str = "procedure_notes"
) -> tuple[list[MonitoringTechnique], list[ExtractionFinding]]:
    """
    Extract monitoring techniques with pattern matching and confidence scoring.

    This function analyzes procedure notes to identify:
    - TEE (transesophageal echocardiography)
    - Electrophysiologic monitoring (SSEP, MEP, EMG, etc.)
    - CSF drains (lumbar drains, etc.)
    - Invasive neurological monitoring (ICP, ventriculostomy)

    Args:
        notes: Procedure notes text (can be None, NaN, or string)
        source_field: Name of the field being analyzed (for tracking)

    Returns:
        Tuple of (monitoring_list, extraction_findings)
        - monitoring_list: List of MonitoringTechnique enums found
        - extraction_findings: List of ExtractionFinding objects with confidence scores

    Example:
        notes = "TEE performed, neuromonitoring with SSEPs"
        monitoring, findings = extract_monitoring(notes)
        # monitoring: [MonitoringTechnique.TEE,
        MonitoringTechnique.ELECTROPHYSIOLOGIC_MON]
    """
    if notes is None or (isinstance(notes, float) and pd.isna(notes)):
        return [], []

    text = str(notes)
    monitoring = []
    findings = []

    # TEE
    tee_matches = extract_with_context(text, TEE_PATTERNS)
    if tee_matches:
        monitoring.append(MonitoringTechnique.TEE)
        confidence = calculate_pattern_confidence(text, TEE_PATTERNS)
        findings.append(
            ExtractionFinding(
                value=MonitoringTechnique.TEE.value,
                confidence=confidence,
                context=tee_matches[0][1],
                source_field=source_field,
            )
        )

    # Electrophysiologic monitoring
    ep_matches = extract_with_context(text, ELECTROPHYSIOLOGIC_PATTERNS)
    if ep_matches:
        monitoring.append(MonitoringTechnique.ELECTROPHYSIOLOGIC_MON)
        confidence = calculate_pattern_confidence(text, ELECTROPHYSIOLOGIC_PATTERNS)
        findings.append(
            ExtractionFinding(
                value=MonitoringTechnique.ELECTROPHYSIOLOGIC_MON.value,
                confidence=confidence,
                context=ep_matches[0][1],
                source_field=source_field,
            )
        )

    # CSF drain
    csf_matches = extract_with_context(text, CSF_DRAIN_PATTERNS)
    if csf_matches:
        monitoring.append(MonitoringTechnique.CSF_DRAIN)
        confidence = calculate_pattern_confidence(text, CSF_DRAIN_PATTERNS)
        findings.append(
            ExtractionFinding(
                value=MonitoringTechnique.CSF_DRAIN.value,
                confidence=confidence,
                context=csf_matches[0][1],
                source_field=source_field,
            )
        )

    # Invasive neuro monitoring
    neuro_matches = extract_with_context(text, INVASIVE_NEURO_PATTERNS)
    if neuro_matches:
        monitoring.append(MonitoringTechnique.INVASIVE_NEURO_MON)
        confidence = calculate_pattern_confidence(text, INVASIVE_NEURO_PATTERNS)
        findings.append(
            ExtractionFinding(
                value=MonitoringTechnique.INVASIVE_NEURO_MON.value,
                confidence=confidence,
                context=neuro_matches[0][1],
                source_field=source_field,
            )
        )

    return remove_duplicates_preserve_order(monitoring), findings
