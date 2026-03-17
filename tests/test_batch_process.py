"""Tests for batch_process CLI defaults."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import pandas as pd

import batch_process


def test_parse_args_defaults_to_ml(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["batch_process.py"])

    args = batch_process._parse_args()

    assert args.use_ml is True
    assert args.output_dir == Path("Output")


def test_parse_args_no_ml_disables_ml(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["batch_process.py", "--no-ml"])

    args = batch_process._parse_args()

    assert args.use_ml is False


def test_get_worker_processor_caches_per_column_map(monkeypatch):
    created_columns: list[batch_process.ColumnMap] = []

    @dataclass
    class _DummyProcessor:
        columns: batch_process.ColumnMap
        default_year: int
        use_ml: bool

        def __init__(
            self,
            columns: batch_process.ColumnMap,
            default_year: int,
            use_ml: bool,
        ) -> None:
            """
            Initialize the dummy processor and record the provided ColumnMap.

            Parameters:
                columns (batch_process.ColumnMap): Column mapping for this processor; appended to the module-level created_columns list.
                default_year (int): Default year used by the processor.
                use_ml (bool): Whether to enable ML-based processing for this processor.
            """
            self.columns = columns
            self.default_year = default_year
            self.use_ml = use_ml
            created_columns.append(columns)

    batch_process._WORKER_PROCESSORS.clear()
    monkeypatch.setattr(batch_process, "CaseProcessor", _DummyProcessor)
    monkeypatch.setattr(batch_process.os, "getpid", lambda: 4242)

    first_columns = batch_process.ColumnMap(procedure="Procedure A")
    second_columns = batch_process.ColumnMap(procedure="Procedure B")

    first = batch_process._get_worker_processor(first_columns, use_ml=True)
    first_again = batch_process._get_worker_processor(first_columns, use_ml=True)
    second = batch_process._get_worker_processor(second_columns, use_ml=True)

    assert first is first_again
    assert second is not first
    assert created_columns == [first_columns, second_columns]
    batch_process._WORKER_PROCESSORS.clear()


def test_find_resident_pairs_matches_non_supervised_suffixes(tmp_path):
    case_dir = tmp_path / "case-list"
    proc_dir = tmp_path / "procedure-list"
    case_dir.mkdir()
    proc_dir.mkdir()

    case_file = case_dir / "DOE_JANE.CaseList.csv"
    proc_file = proc_dir / "DOE_JANE.ProcedureList.csv"
    case_file.write_text("case")
    proc_file.write_text("proc")

    assert batch_process.find_resident_pairs(case_dir, proc_dir) == [
        ("DOE_JANE", case_file, proc_file)
    ]


def test_format_name_handles_supervised_last_comma_first():
    assert (
        batch_process.format_name("ZUCKERBERG, GABRIEL.Supervised")
        == "Gabriel Zuckerberg"
    )


def test_format_name_handles_supervised_first_last_with_underscore():
    assert (
        batch_process.format_name("Gabriel.Supervised_Zuckerberg")
        == "Gabriel Zuckerberg"
    )


def test_process_resident_writes_person_folder_and_split_standalone_outputs(tmp_path):
    processor = Mock()
    config = batch_process.ProcessConfig(
        output_dir=tmp_path / "Output",
        columns=batch_process.ColumnMap(),
        excel_handler=Mock(),
        use_ml=False,
    )
    config.output_dir.mkdir()

    processor.process_dataframe.side_effect = [
        [SimpleNamespace(case_id="B1"), SimpleNamespace(case_id="N1")],
        [SimpleNamespace(case_id="MAIN1")],
    ]
    processor.procedures_to_dataframe.return_value = pd.DataFrame([{"Case ID": "S1"}])
    processor.cases_to_dataframe.return_value = pd.DataFrame([{"Case ID": "M1"}])

    with (
        patch.object(batch_process, "_get_worker_processor", return_value=processor),
        patch.object(
            batch_process,
            "join_case_and_procedures",
            return_value=(
                pd.DataFrame([{"joined": True}]),
                pd.DataFrame([{"orphan": True}]),
            ),
        ),
        patch.object(
            batch_process.CsvHandler,
            "normalize_orphan_columns",
            return_value=pd.DataFrame([{"normalized": "orphan"}]),
        ),
        patch.object(
            batch_process.CsvHandler,
            "normalize_columns",
            return_value=pd.DataFrame([{"normalized": "main"}]),
        ),
        patch.object(
            batch_process.pd,
            "read_csv",
            side_effect=[pd.DataFrame([{"case": 1}]), pd.DataFrame([{"proc": 1}])],
        ),
        patch.object(
            batch_process,
            "iter_standalone_case_exports",
            return_value=(
                (SimpleNamespace(suffix="blocks", label="Blocks"), [object()]),
                (
                    SimpleNamespace(
                        suffix="ob",
                        label="OB",
                    ),
                    [object()],
                ),
            ),
        ),
    ):
        case_count, orphan_notice = batch_process.process_resident(
            ("DOE_JANE", Path("case.csv"), Path("proc.csv")),
            config,
        )

    resident_dir = config.output_dir / "Jane Doe"
    assert case_count == 1
    assert orphan_notice == (
        "DOE_JANE",
        2,
        ["Jane Doe_blocks.xlsx", "Jane Doe_ob.xlsx"],
    )
    assert resident_dir.is_dir()
    assert config.excel_handler.write_excel.call_args_list == [
        call(
            processor.procedures_to_dataframe.return_value,
            resident_dir / "Jane Doe_blocks.xlsx",
            options=batch_process.ExcelWriteOptions(
                format_type=batch_process.FORMAT_TYPE_STANDALONE,
                version=batch_process.STANDALONE_OUTPUT_FORMAT_VERSION,
            ),
        ),
        call(
            processor.procedures_to_dataframe.return_value,
            resident_dir / "Jane Doe_ob.xlsx",
            options=batch_process.ExcelWriteOptions(
                format_type=batch_process.FORMAT_TYPE_STANDALONE,
                version=batch_process.STANDALONE_OUTPUT_FORMAT_VERSION,
            ),
        ),
        call(
            processor.cases_to_dataframe.return_value,
            resident_dir / "Jane Doe_all_cases.xlsx",
            options=batch_process.ExcelWriteOptions(
                fixed_widths={"Original Procedure": 12},
                format_type=batch_process.FORMAT_TYPE_CASELOG,
                version=batch_process.OUTPUT_FORMAT_VERSION,
            ),
        ),
    ]
