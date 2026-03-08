"""Tests for airway/anesthesia review-set generation."""

from __future__ import annotations

from datetime import date

import pandas as pd

from case_parser.domain import (
    AirwayManagement,
    AnesthesiaType,
    ParsedCase,
    ProcedureCategory,
)
from ml_training import airway_review


def _parsed_case(**overrides) -> ParsedCase:
    base = {
        "raw_date": "2025-01-01",
        "episode_id": "CASE-1",
        "raw_age": 55.0,
        "raw_asa": "3",
        "emergent": False,
        "raw_anesthesia_type": "Intubation routine",
        "services": ["THORACIC"],
        "procedure": "VATS lobectomy",
        "procedure_notes": "Left double lumen tube placed",
        "responsible_provider": "SMITH, JANE",
        "case_date": date(2025, 1, 1),
        "anesthesia_type": AnesthesiaType.GENERAL,
        "procedure_category": ProcedureCategory.INTRATHORACIC_NON_CARDIAC,
        "airway_management": [
            AirwayManagement.DOUBLE_LUMEN_ETT,
            AirwayManagement.ORAL_ETT,
        ],
        "parsing_warnings": [
            "Inferred general anesthesia from airway management findings"
        ],
    }
    base.update(overrides)
    return ParsedCase(**base)


def test_assess_case_for_review_scores_all_requested_targets():
    case = _parsed_case()

    assessment = airway_review.assess_case_for_review(case, source_file="pair.csv")

    assert assessment.scores["double_lumen"] > 0
    assert assessment.scores["tube_route"] > 0
    assert assessment.scores["ga_mac"] > 0
    assert "double_lumen" in assessment.review_targets
    assert "tube_route" in assessment.review_targets
    assert "ga_mac" in assessment.review_targets


def test_build_review_record_exposes_blank_label_columns():
    case = _parsed_case()
    assessment = airway_review.assess_case_for_review(case, source_file="pair.csv")

    record = airway_review.build_review_record(
        case,
        source_file="pair.csv",
        assessment=assessment,
    )

    assert record["predicted_has_double_lumen_tube"] == "Yes"
    assert record["predicted_tube_route"] == "Oral"
    assert record["predicted_ga_mac"] == "GA"
    assert record["label_has_double_lumen_tube"] == ""
    assert record["label_ga_mac"] == ""
    assert record["label_tube_route"] == ""


def test_assess_case_for_review_does_not_treat_ldlt_as_dlt():
    case = _parsed_case(
        procedure="Liver LDLT recipient",
        procedure_category=ProcedureCategory.OTHER,
        airway_management=[],
        procedure_notes="",
        parsing_warnings=[],
    )

    assessment = airway_review.assess_case_for_review(case, source_file="pair.csv")

    assert assessment.scores["double_lumen"] == 0
    assert "explicit_double_lumen_text" not in assessment.review_reasons


def test_assess_case_for_review_does_not_use_generic_lobectomy_as_thoracic():
    case = _parsed_case(
        procedure="Total thyroid lobectomy",
        procedure_category=ProcedureCategory.INTRATHORACIC_NON_CARDIAC,
        airway_management=[],
        procedure_notes="",
        parsing_warnings=[],
    )

    assessment = airway_review.assess_case_for_review(case, source_file="pair.csv")

    assert assessment.scores["double_lumen"] == 0
    assert "thoracic_procedure_hint" not in assessment.review_reasons


def test_build_airway_review_dataframe_from_supervised_pair(tmp_path):
    base_dir = tmp_path / "Output-Supervised"
    case_dir = base_dir / "case-list"
    proc_dir = base_dir / "procedure-list"
    case_dir.mkdir(parents=True)
    proc_dir.mkdir(parents=True)

    case_df = pd.DataFrame({
        "MPOG_Case_ID": ["CASE-1"],
        "AIMS_Scheduled_DT": ["2025-01-01 07:30:00"],
        "AIMS_Patient_Age_Years": [55],
        "ASA_Status": [3],
        "AIMS_Actual_Procedure_Text": ["VATS lobectomy"],
        "AnesAttendings": ["SMITH, JANE@2025-01-01 07:30:00"],
    })
    proc_df = pd.DataFrame({
        "MPOG_Case_ID": ["CASE-1"],
        "ProcedureName": ["Intubation routine"],
        "Comment": [pd.NA],
        "Details": ["Left double lumen tube placed"],
    })

    case_df.to_csv(case_dir / "TEST.Supervised.CaseList.csv", index=False)
    proc_df.to_csv(proc_dir / "TEST.Supervised.ProcedureList.csv", index=False)

    df = airway_review.build_airway_review_dataframe(
        base_dir=base_dir,
        max_cases=10,
    )

    assert len(df) == 1
    assert df.loc[0, "predicted_has_double_lumen_tube"] == "Yes"
    assert df.loc[0, "predicted_tube_route"] == "Oral"
    assert "double_lumen" in df.loc[0, "review_targets"]
    assert df.loc[0, "label_has_double_lumen_tube"] == ""
