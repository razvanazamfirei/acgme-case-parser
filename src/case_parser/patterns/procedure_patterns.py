"""
Procedure Categorization Rules.

This file contains rules for categorizing procedures based on service keywords
found in the case data.

FIELDS EXTRACTED:
- Procedure Category (Cardiac, Intracerebral, Intrathoracic, Major Vessels, etc.)

MODIFICATION GUIDE:
Rules are evaluated in order from top to bottom. The first matching rule wins.
To modify categorization:
1. Edit keywords in existing ProcedureRule entries
2. Add new ProcedureRule entries in the desired priority position
3. Use exclude_keywords to prevent false matches

SPECIAL CASES:
- OB/GYN procedures are handled separately in processors.py with cesarean detection
- More specific rules should come before general ones
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProcedureRule:
    """Rule for categorizing procedures based on service keywords."""

    keywords: tuple[str, ...]
    category: str
    exclude_keywords: tuple[str, ...] = ()


# ============================================================================
# PROCEDURE CATEGORIZATION RULES
# ============================================================================
# Rules are evaluated in priority order (first match wins)
PROCEDURE_RULES = [
    # Cardiac procedures
    ProcedureRule(
        keywords=(
            "CARDIAC",
            "CARDSURG",
            "CARDIOTHORACIC",
            "CARDVASC",
            "CABG",
            "CORONARY ARTERY BYPASS",
            "VALVE REPLACEMENT",
            "VALVE REPAIR",
            "AORTIC VALVE",
            "MITRAL VALVE",
            "TRICUSPID VALVE",
            "PULMONARY VALVE",
            "AVR",
            "MVR",
            "TVR",
            "MAZE PROCEDURE",
            "ATRIAL SEPTAL DEFECT",
            "ASD REPAIR",
            "VSD REPAIR",
            "VENTRICULAR SEPTAL DEFECT",
            "HEART TRANSPLANT",
            "CARDIAC TRANSPLANT",
            "LUNG TRANSPLANT",
            "TAVR",
            "TAVI",
            "LVAD",
            "ECMO",
            "INTRACARDIAC",
            "VENTRICULAR ASSIST DEVICE",
        ),
        category="Cardiac",
    ),
    # Intracerebral/neurosurgery procedures (exclude spine procedures)
    ProcedureRule(
        keywords=("NEURO",),
        category="Intracerebral",
        exclude_keywords=(
            "SPINE",
            "SPINAL",
            "VERTEBR",
            "INTERBODY",
            "ARTHRODESIS",
            "LAMINECTOMY",
            "LAMINOTOMY",
            "DISCECTOMY",
            "FUSION",
        ),
    ),
    # Intrathoracic non-cardiac (exclude cardiac thoracic cases)
    ProcedureRule(
        keywords=("THOR",),
        category="Intrathoracic non-cardiac",
        exclude_keywords=("CARD",),
    ),
    # Major vascular procedures
    ProcedureRule(
        keywords=(
            "VASC",
            "VASCSURG",
            "ANGIOGRAPHY",
            "ANGIOGRAM",
        ),
        category="Procedures Major Vessels",
    ),
    # Transplant procedures
    ProcedureRule(
        keywords=("TRANSPLANT",),
        category="Other (procedure cat)",
    ),
    # OB/GYN - Special handling in processors.py
    # Cesarean deliveries are detected by searching procedure text for:
    # "CESAREAN", "C-SECTION", or "C SECTION"
    # and categorized separately as "Cesarean del"
    # Other OB/GYN procedures fall into "Other (procedure cat)"
]

# Default category when no rules match
DEFAULT_PROCEDURE_CATEGORY = "Other (procedure cat)"
