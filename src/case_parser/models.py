"""Data models and configuration for the case parser.

NOTE: Business rules (age ranges, anesthesia mappings, procedure rules) have been
moved to the patterns/ directory for easier modification. Import them from there:
- patterns.age_patterns.AGE_RANGES
- patterns.anesthesia_patterns.ANESTHESIA_MAPPING
- patterns.procedure_patterns.PROCEDURE_RULES
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ColumnMap:
    """Column mapping configuration for input Excel files."""

    date: str = "Date"
    episode_id: str = "Episode ID"
    anesthesiologist: str = "Responsible Provider"
    age: str = "Age At Encounter"
    emergent: str = "Emergent"  # optional; used to append E to ASA if present
    asa: str = "ASA"
    final_anesthesia_type: str = "Final Anesthesia Type"
    procedure_notes: str = "Procedure Notes"
    procedure: str = "Procedure"
    services: str = "Services"


# Output column order
OUTPUT_COLUMNS = [
    "Case ID",
    "Case Date",
    "Supervisor",
    "Age",
    "Original Procedure",
    "ASA Physical Status",
    "Anesthesia Type",
    "Airway Management",
    "Procedure Category",
    "Specialized Vascular Access",
    "Specialized Monitoring Techniques",
]
