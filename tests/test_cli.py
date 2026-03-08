"""Tests for standalone orphan splitting logic in CLI flow."""

from __future__ import annotations

from datetime import date

from case_parser.cli import split_standalone_cases
from case_parser.domain import ParsedCase


def _standalone_case(
    *,
    case_id: str,
    procedure_name: str | None,
    procedure: str | None = None,
    notes: str | None = None,
    block: str | None = None,
) -> ParsedCase:
    return ParsedCase(
        raw_date="2025-01-01",
        episode_id=case_id,
        raw_age=30.0,
        raw_asa="2",
        emergent=False,
        raw_anesthesia_type=procedure_name,
        services=[],
        procedure=procedure,
        procedure_notes=notes,
        responsible_provider="SMITH, JANE",
        nerve_block_type=block,
        case_date=date(2025, 1, 1),
    )


def test_split_standalone_cases_routes_blocks_and_neuraxial():
    cases = [
        _standalone_case(case_id="B1", procedure_name="Peripheral nerve block"),
        _standalone_case(case_id="N1", procedure_name="Labor Epidural"),
        _standalone_case(case_id="N2", procedure_name="CSE"),
    ]

    block_cases, neuraxial_cases = split_standalone_cases(cases)

    assert [c.episode_id for c in block_cases] == ["B1"]
    assert [c.episode_id for c in neuraxial_cases] == ["N1", "N2"]


def test_split_standalone_cases_treats_block_site_only_as_block():
    cases = [
        _standalone_case(
            case_id="B2",
            procedure_name="Unknown Procedure",
            block="Femoral",
        ),
    ]

    block_cases, neuraxial_cases = split_standalone_cases(cases)

    assert [c.episode_id for c in block_cases] == ["B2"]
    assert neuraxial_cases == []


def test_split_standalone_cases_defaults_unknown_to_neuraxial_bucket():
    cases = [
        _standalone_case(case_id="X1", procedure_name="Unknown Procedure"),
    ]

    block_cases, neuraxial_cases = split_standalone_cases(cases)

    assert block_cases == []
    assert [c.episode_id for c in neuraxial_cases] == ["X1"]


def test_split_standalone_cases_routes_canonical_neuraxial_sites_correctly():
    cases = [
        _standalone_case(
            case_id="N3",
            procedure_name="Unknown Procedure",
            block="Lumbar",
        ),
    ]

    block_cases, neuraxial_cases = split_standalone_cases(cases)

    assert block_cases == []
    assert [c.episode_id for c in neuraxial_cases] == ["N3"]
