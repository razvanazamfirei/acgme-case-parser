from __future__ import annotations

import sys
from pathlib import Path

import list_attendings


def test_collect_attending_counts_splits_deduplicates_and_counts(
    tmp_path: Path,
) -> None:
    case_dir = tmp_path / "case-list"
    procedure_dir = tmp_path / "procedure-list"
    case_dir.mkdir()
    procedure_dir.mkdir()
    resident_list = tmp_path / "anesthesia-residents.txt"
    resident_list.write_text("Jane Doe\n", encoding="utf-8")

    (case_dir / "DOE_JANE.Supervised.CaseList.csv").write_text(
        (
            "AnesAttendings,Other\n"
            '"DOE, JANE@2025-01-01 08:00:00; SMITH, JOHN@2025-01-01 10:00:00",x\n'
            '"DOE, JANE@2025-01-02 08:00:00",y\n'
            '"SMITH, JOHN MD@2025-01-03 08:00:00",z\n'
        ),
        encoding="utf-8",
    )
    (case_dir / "SMITH_ALEX.Supervised.CaseList.csv").write_text(
        ('AnesAttendings,Other\n"IGNORED, PERSON@2025-01-01 08:00:00",x\n'),
        encoding="utf-8",
    )
    (procedure_dir / "procedure.csv").write_text(
        ('AnesAttendingNames,Other\n"ADAMS, ALEX DO",x\n'),
        encoding="utf-8",
    )

    counts = list_attendings.collect_attending_counts(
        tmp_path,
        names_file=resident_list,
    )

    assert counts == [("DOE, JANE", 2), ("SMITH, JOHN", 2)]


def test_collect_attending_counts_applies_minimum_filter(tmp_path: Path) -> None:
    case_dir = tmp_path / "case-list"
    case_dir.mkdir()
    resident_list = tmp_path / "anesthesia-residents.txt"
    resident_list.write_text("Jane Doe\n", encoding="utf-8")

    (case_dir / "DOE_JANE.Supervised.CaseList.csv").write_text(
        (
            "AnesAttendings\n"
            '"DOE, JANE@2025-01-01 08:00:00; SMITH, JOHN@2025-01-01 10:00:00"\n'
            '"DOE, JANE@2025-01-02 08:00:00"\n'
        ),
        encoding="utf-8",
    )

    counts = list_attendings.collect_attending_counts(
        tmp_path,
        names_file=resident_list,
        minimum_cases=2,
    )

    assert counts == [("DOE, JANE", 2)]


def test_collect_attending_counts_matches_parenthetical_resident_names(
    tmp_path: Path,
) -> None:
    case_dir = tmp_path / "case-list"
    case_dir.mkdir()
    resident_list = tmp_path / "anesthesia-residents.txt"
    resident_list.write_text("Gabriel (Gabe) Zuckerberg\n", encoding="utf-8")

    (case_dir / "ZUCKERBERG_GABRIEL.Supervised.CaseList.csv").write_text(
        ('AnesAttendings\n"DOE, JANE@2025-01-01 08:00:00"\n'),
        encoding="utf-8",
    )

    counts = list_attendings.collect_attending_counts(
        tmp_path,
        names_file=resident_list,
    )

    assert counts == [("DOE, JANE", 1)]


def test_main_writes_csv_output_file(tmp_path: Path, monkeypatch, capsys) -> None:
    case_dir = tmp_path / "Output-Supervised" / "case-list"
    case_dir.mkdir(parents=True)
    resident_list = tmp_path / "anesthesia-residents.txt"
    resident_list.write_text("Jane Doe\n", encoding="utf-8")

    (case_dir / "DOE_JANE.Supervised.CaseList.csv").write_text(
        (
            "AnesAttendings\n"
            '"DOE, JANE@2025-01-01 08:00:00; SMITH, JOHN@2025-01-01 10:00:00"\n'
            '"DOE, JANE@2025-01-02 08:00:00"\n'
        ),
        encoding="utf-8",
    )

    output_file = tmp_path / "attendings.csv"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "list_attendings.py",
            "--input-dir",
            str(tmp_path / "Output-Supervised"),
            "--output-file",
            str(output_file),
            "--resident-list",
            str(resident_list),
            "--filter",
            "2",
        ],
    )

    list_attendings.main()

    assert output_file.read_text(encoding="utf-8").splitlines() == [
        "attending,count",
        '"DOE, JANE",2',
    ]
    assert "Wrote 1 attending rows" in capsys.readouterr().out
