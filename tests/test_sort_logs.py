from __future__ import annotations

import sys
from pathlib import Path

import sort_logs


def test_main_copies_matching_resident_directories(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    input_dir = tmp_path / "Output"
    gabriel_dir = input_dir / "Gabriel Zuckerberg"
    william_dir = input_dir / "William Ryan"
    gabriel_dir.mkdir(parents=True)
    william_dir.mkdir(parents=True)
    (gabriel_dir / "Gabriel Zuckerberg_all_cases.xlsx").write_text(
        "gabriel", encoding="utf-8"
    )
    (william_dir / "William Ryan_all_cases.xlsx").write_text(
        "william", encoding="utf-8"
    )

    names_file = tmp_path / "anesthesia-residents.txt"
    names_file.write_text(
        'Gabriel (Gabe) Zuckerberg\nWilliam "Bill" Ryan\n',
        encoding="utf-8",
    )
    output_dir = tmp_path / "Output-Residents"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sort_logs.py",
            "--input-dir",
            str(input_dir),
            "--output-dir",
            str(output_dir),
            "--names-file",
            str(names_file),
        ],
    )

    sort_logs.main()

    assert (
        output_dir / "Gabriel Zuckerberg" / "Gabriel Zuckerberg_all_cases.xlsx"
    ).read_text(encoding="utf-8") == "gabriel"
    assert (output_dir / "William Ryan" / "William Ryan_all_cases.xlsx").read_text(
        encoding="utf-8"
    ) == "william"

    captured = capsys.readouterr()
    assert "Matched: 2/2" in captured.out
    assert "Copied 2 resident folder(s)" in captured.out


def test_main_falls_back_to_flat_excel_files(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    input_dir = tmp_path / "Output-Individual"
    input_dir.mkdir()
    (input_dir / "Alice Smith.xlsx").write_text("alice", encoding="utf-8")
    (input_dir / "Bob Jones.xlsx").write_text("bob", encoding="utf-8")

    names_file = tmp_path / "anesthesia-residents.txt"
    names_file.write_text("Alice Smith\n", encoding="utf-8")
    output_dir = tmp_path / "Output-Residents"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sort_logs.py",
            "--input-dir",
            str(input_dir),
            "--output-dir",
            str(output_dir),
            "--names-file",
            str(names_file),
        ],
    )

    sort_logs.main()

    assert (output_dir / "Alice Smith.xlsx").read_text(encoding="utf-8") == "alice"

    captured = capsys.readouterr()
    assert "Matched: 1/1" in captured.out
    assert "Copied 1 file(s)" in captured.out
