"""Export case data to JSON format for ACGME web form integration."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from pandas import DataFrame

from .acgme_mappings import field_mapper

logger = logging.getLogger(__name__)


class WebExporter:
    """Export processed case data to ACGME-compatible JSON format."""

    def __init__(self):
        """Initialize the web exporter."""
        self.mapper = field_mapper

    def export_to_json(
        self,
        df: DataFrame,
        output_file: str | Path,
        resident_id: str | None = None,
        program_info: dict[str, Any] | None = None,
    ) -> None:
        """
        Export DataFrame to JSON format for ACGME web form.

        Args:
            df: Processed case DataFrame
            output_file: Path to output JSON file
            resident_id: ACGME resident ID (optional)
            program_info: Program-specific information (optional)
        """
        output_file = Path(output_file)

        logger.info("Exporting %d cases to JSON: %s", len(df), output_file)

        cases = self._convert_dataframe_to_cases(df, resident_id, program_info)

        json_data = {
            "metadata": {
                "export_date": datetime.now(UTC).isoformat(),
                "total_cases": len(cases),
                "tool_version": "1.0.0",
                "format_version": "1.0",
            },
            "program_info": program_info or {},
            "cases": cases,
        }

        with Path(output_file).open("w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)

        logger.info("Successfully exported %d cases to %s", len(cases), output_file)

    def _convert_dataframe_to_cases(
        self,
        df: DataFrame,
        resident_id: str | None = None,
        program_info: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Convert DataFrame rows to case dictionaries."""
        cases: list[dict[str, Any]] = []

        for idx, row in df.iterrows():
            # Convert idx to int for row numbering
            row_num = int(idx) if isinstance(idx, (int, float)) else len(cases)
            case = self._convert_row_to_case(row, row_num, resident_id, program_info)
            if case:
                cases.append(case)

        return cases

    def _convert_row_to_case(  # noqa: PLR0914
        self,
        row: pd.Series,
        row_idx: int,
        resident_id: str | None = None,
        program_info: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Convert a single DataFrame row to a case dictionary."""
        try:
            # Extract basic fields
            case_id = self._get_value(row, "Case ID")
            case_date = self._get_value(row, "Case Date")
            case_year = self._get_value(row, "Case Year")

            # Get institution/site
            institution = self._get_value(row, "Site")
            institution_code = self.mapper.fuzzy_match_institution(institution)

            # Get patient age category
            age_category = self._get_value(row, "Age Category")
            age_code = self.mapper.get_patient_age_code(age_category)

            # Get ASA status
            asa_status = self._get_value(row, "ASA Status")
            asa_code = self.mapper.parse_asa_status(asa_status)

            # Parse procedure codes
            procedure_codes = []

            # Add ASA code
            if asa_code:
                procedure_codes.append(asa_code)

            # Parse other procedures
            anesthesia_type = self._get_value(row, "Anesthesia Type")
            if anesthesia_type:
                anesthesia_codes = self.mapper.get_procedure_codes(anesthesia_type)
                procedure_codes.extend(anesthesia_codes)

            airway = self._get_value(row, "Airway Management")
            if airway:
                airway_codes = self.mapper.get_procedure_codes(airway)
                procedure_codes.extend(airway_codes)

            procedure_category = self._get_value(row, "Procedure Category")
            if procedure_category:
                proc_codes = self.mapper.get_procedure_codes(procedure_category)
                procedure_codes.extend(proc_codes)

            vascular = self._get_value(row, "Vascular Access")
            if vascular:
                vascular_codes = self.mapper.get_procedure_codes(vascular)
                procedure_codes.extend(vascular_codes)

            monitoring = self._get_value(row, "Monitoring")
            if monitoring:
                monitoring_codes = self.mapper.get_procedure_codes(monitoring)
                procedure_codes.extend(monitoring_codes)

            # Build case dictionary
            case = {
                "row_number": int(row_idx) + 1,
                "case_id": str(case_id) if case_id else "",
                "case_date": self._format_date(case_date),
                "case_year": int(case_year) if case_year else None,
                "resident_id": resident_id,
                # Site/Institution
                "institution": {
                    "name": institution,
                    "code": institution_code,
                },
                # Supervisor - will need to be filled manually or from lookup
                "supervisor": {
                    "name": "",  # Not in current output
                    "code": "",  # Would need supervisor mapping
                },
                # Patient info
                "patient": {
                    "age_category": age_category,
                    "age_code": age_code,
                },
                # ASA Status
                "asa_status": {
                    "text": asa_status,
                    "code": asa_code,
                },
                # Procedures
                "procedures": {
                    "anesthesia_type": anesthesia_type,
                    "airway_management": airway,
                    "procedure_category": procedure_category,
                    "vascular_access": vascular,
                    "monitoring": monitoring,
                },
                # Procedure codes for ACGME form
                "procedure_codes": list(set(procedure_codes)),  # Remove duplicates
                # Optional fields
                "comments": self._get_value(row, "Comments", ""),
                "case_types": [],  # Life-threatening, difficult airway, etc.
                # Raw data for reference
                "raw_data": row.to_dict(),
            }

            # Add program info if provided
            if program_info:
                case["program_info"] = program_info

            return case

        except Exception as e:
            logger.error("Error converting row %s to case: %s", row_idx, e)
            return None

    def _get_value(self, row: pd.Series, column: str, default: Any = None) -> Any:  # noqa: PLR6301
        """Safely get value from row, handling missing columns."""
        if column not in row:
            return default

        value = row[column]

        # Handle NaN/None
        if pd.isna(value):
            return default

        return value

    def _format_date(self, date_value: Any) -> str:  # noqa: PLR6301
        """Format date for ACGME form (MM/DD/YYYY)."""
        if not date_value or pd.isna(date_value):
            return ""

        try:
            # If already a string in correct format
            if isinstance(date_value, str):
                # Try to parse and reformat to ensure consistency
                try:
                    dt = pd.to_datetime(date_value)
                    return dt.strftime("%m/%d/%Y")
                except Exception:
                    return date_value

            # If datetime object
            if isinstance(date_value, (datetime, pd.Timestamp)):
                return date_value.strftime("%m/%d/%Y")

            return str(date_value)

        except Exception as e:
            logger.warning("Error formatting date '%s': %s", date_value, e)
            return str(date_value)

    def export_to_csv(self, df: DataFrame, output_file: str | Path) -> None:  # noqa: PLR6301
        """
        Export DataFrame to CSV format (alternative to JSON).

        Args:
            df: Processed case DataFrame
            output_file: Path to output CSV file
        """
        output_file = Path(output_file)

        logger.info("Exporting %d cases to CSV: %s", len(df), output_file)

        df.to_csv(output_file, index=False, encoding="utf-8")

        logger.info("Successfully exported to %s", output_file)

    def generate_import_template(self, output_file: str | Path) -> None:  # noqa: PLR6301
        """
        Generate a template JSON file showing the expected format.

        Args:
            output_file: Path to output template file
        """
        output_file = Path(output_file)

        template = {
            "metadata": {
                "export_date": "2025-01-15T12:00:00",
                "total_cases": 1,
                "tool_version": "1.0.0",
                "format_version": "1.0",
            },
            "program_info": {
                "program_id": "0404121134",
                "program_name": "University of Pennsylvania Health System Program",
                "specialty": "Anesthesiology",
                "specialty_code": "040",
            },
            "cases": [
                {
                    "row_number": 1,
                    "case_id": "CASE001",
                    "case_date": "11/15/2025",
                    "case_year": 2,
                    "resident_id": "1325527",
                    "institution": {
                        "name": "University of Pennsylvania Health System",
                        "code": "12748",
                    },
                    "supervisor": {"name": "FACULTY, FACULTY", "code": "255593"},
                    "patient": {
                        "age_category": "d. >= 12 yr. and < 65 yr.",
                        "age_code": "33",
                    },
                    "asa_status": {"text": "ASA 2", "code": "156632"},
                    "procedures": {
                        "anesthesia_type": "General Maintenance",
                        "airway_management": "Oral ETT; Laryngoscope - Direct",
                        "procedure_category": "Intrathoracic non-cardiac",
                        "vascular_access": "Arterial Catheter",
                        "monitoring": "",
                    },
                    "procedure_codes": [
                        "156632",
                        "1256330",
                        "156654",
                        "1256334",
                        "156683",
                        "1256338",
                    ],
                    "comments": "",
                    "case_types": [],
                }
            ],
        }

        with Path(output_file).open("w", encoding="utf-8") as f:
            json.dump(template, f, indent=2, ensure_ascii=False)

        logger.info("Generated template file: %s", output_file)


def export_cases_to_json(
    df: DataFrame,
    output_file: str | Path,
    resident_id: str | None = None,
    program_info: dict[str, Any] | None = None,
) -> None:
    """
    Convenience function to export cases to JSON.

    Args:
        df: Processed case DataFrame
        output_file: Path to output JSON file
        resident_id: ACGME resident ID (optional)
        program_info: Program-specific information (optional)
    """
    exporter = WebExporter()
    exporter.export_to_json(df, output_file, resident_id, program_info)
