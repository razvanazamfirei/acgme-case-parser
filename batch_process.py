#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pandas>=3.0.1",
#   "rich>=14.3.3",
#   "case-parser",
# ]
# ///
"""Batch process all residents from Output-Supervised into Output folders."""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sys
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from case_parser.io import (
    CsvHandler,
    ExcelHandler,
    ExcelWriteOptions,
    join_case_and_procedures,
)
from case_parser.models import (
    FORMAT_TYPE_CASELOG,
    FORMAT_TYPE_STANDALONE,
    OUTPUT_FORMAT_VERSION,
    STANDALONE_OUTPUT_FORMAT_VERSION,
    ColumnMap,
)
from case_parser.processor import CaseProcessor
from case_parser.standalone_exports import iter_standalone_case_exports

# Suppress noisy logging from the pipeline
logging.getLogger("case_parser").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
console = Console()

_WORKER_PROCESSORS: dict[tuple[int, bool, ColumnMap], CaseProcessor] = {}


@dataclass(frozen=True)
class ProcessConfig:
    output_dir: Path
    columns: ColumnMap
    excel_handler: ExcelHandler
    use_ml: bool


def _get_worker_processor(columns: ColumnMap, use_ml: bool) -> CaseProcessor:
    """Return the cached processor for this process, column map, and ML mode."""
    cache_key = (os.getpid(), use_ml, columns)
    cached = _WORKER_PROCESSORS.get(cache_key)
    if cached is None:
        cached = CaseProcessor(columns, default_year=2025, use_ml=use_ml)
        _WORKER_PROCESSORS[cache_key] = cached
    return cached


def find_resident_pairs(case_dir: Path, proc_dir: Path) -> list[tuple[str, Path, Path]]:
    """Find matching case/procedure file pairs.

    Args:
        case_dir: Directory containing ``*.CaseList.csv`` files.
        proc_dir: Directory containing ``*.ProcedureList.csv`` files.

    Returns:
        Sorted list of ``(name, case_path, proc_path)`` tuples for residents
        that have both a CaseList and a ProcedureList file.
    """
    case_files = {
        f.name.removesuffix(".CaseList.csv"): f for f in case_dir.glob("*.CaseList.csv")
    }
    proc_files = {
        f.name.removesuffix(".ProcedureList.csv"): f
        for f in proc_dir.glob("*.ProcedureList.csv")
    }
    common = sorted(set(case_files) & set(proc_files))
    return [(name, case_files[name], proc_files[name]) for name in common]


def format_name(name: str) -> str:
    """Convert resident file stems into a clean display name.

    Args:
        name: Filename stem from the CSV export pair.

    Returns:
        Best-effort title-cased resident name with any ``.Supervised`` marker
        removed.
    """
    cleaned = name.replace(".Supervised", "").strip()
    if "," in cleaned:
        last, first = (part.strip() for part in cleaned.split(",", 1))
        return f"{first.title()} {last.title()}".strip()

    parts = [part.strip() for part in cleaned.split("_", 1)]
    if len(parts) == 2:
        first, second = parts
        if first.isupper() and second.isupper():
            return f"{second.title()} {first.title()}"
        return f"{first.title()} {second.title()}"
    return cleaned.title()


def _resident_output_dir(base_output_dir: Path, resident_name: str) -> Path:
    """Return the per-resident output folder, creating it when needed."""
    resident_dir = base_output_dir / resident_name
    resident_dir.mkdir(parents=True, exist_ok=True)
    return resident_dir


def _write_standalone_exports(
    *,
    processor: CaseProcessor,
    excel_handler: ExcelHandler,
    output_dir: Path,
    resident_name: str,
    orphan_cases: list,
) -> tuple[list[str], int]:
    """Write the split standalone orphan exports for one resident."""
    written_files: list[str] = []
    written_case_count = 0
    for spec, export_cases in iter_standalone_case_exports(orphan_cases):
        if not export_cases:
            continue
        output_path = output_dir / f"{resident_name}_{spec.suffix}.xlsx"
        excel_handler.write_excel(
            processor.procedures_to_dataframe(export_cases),
            output_path,
            options=ExcelWriteOptions(
                format_type=FORMAT_TYPE_STANDALONE,
                version=STANDALONE_OUTPUT_FORMAT_VERSION,
            ),
        )
        written_files.append(output_path.name)
        written_case_count += len(export_cases)
    return written_files, written_case_count


def process_resident(
    pairs: tuple[str, Path, Path],
    config: ProcessConfig,
) -> tuple[int, tuple[str, int, list[str]] | None]:
    """Process one resident pair and write case-log and orphan outputs."""
    name, case_file, proc_file = pairs
    processor = _get_worker_processor(config.columns, config.use_ml)
    formatted_name = format_name(name)
    resident_output_dir = _resident_output_dir(config.output_dir, formatted_name)
    joined, orphans = join_case_and_procedures(
        pd.read_csv(case_file),
        pd.read_csv(proc_file),
    )

    orphan_notice: tuple[str, int, list[str]] | None = None
    if not orphans.empty:
        orphan_cases = processor.process_dataframe(
            CsvHandler(config.columns).normalize_orphan_columns(orphans)
        )
        written_files, written_case_count = _write_standalone_exports(
            processor=processor,
            excel_handler=config.excel_handler,
            output_dir=resident_output_dir,
            resident_name=formatted_name,
            orphan_cases=orphan_cases,
        )
        if written_files:
            orphan_notice = (name, written_case_count, written_files)

    if joined.empty:
        return 0, orphan_notice

    parsed_cases = processor.process_dataframe(
        CsvHandler(config.columns).normalize_columns(joined),
        workers=1,
    )
    if not parsed_cases:
        return 0, orphan_notice

    config.excel_handler.write_excel(
        processor.cases_to_dataframe(parsed_cases),
        resident_output_dir / f"{formatted_name}_all_cases.xlsx",
        options=ExcelWriteOptions(
            fixed_widths={"Original Procedure": 12},
            format_type=FORMAT_TYPE_CASELOG,
            version=OUTPUT_FORMAT_VERSION,
        ),
    )
    return len(parsed_cases), orphan_notice


def _parse_args() -> argparse.Namespace:
    """Parse and validate command-line options for batch processing."""
    parser = argparse.ArgumentParser(description="Batch process resident case files")
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("Output-Supervised"),
        help="Base directory containing case-list and procedure-list subdirectories "
        "(default: Output-Supervised)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("Output"),
        help=(
            "Directory to write one folder per resident with individual Excel files "
            "(default: Output)"
        ),
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers for resident processing (default: 4)",
    )
    parser.set_defaults(use_ml=True)
    parser.add_argument(
        "--use-ml",
        dest="use_ml",
        action="store_true",
        help="Enable ML-enhanced procedure categorization (default)",
    )
    parser.add_argument(
        "--no-ml",
        dest="use_ml",
        action="store_false",
        help="Disable ML-enhanced procedure categorization and use rules only",
    )
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")
    return args


def _validate_input_dirs(base_dir: Path) -> tuple[Path, Path]:
    """Validate expected input folder structure and return subdirectories."""
    case_dir = base_dir / "case-list"
    proc_dir = base_dir / "procedure-list"

    if not base_dir.exists():
        console.print(f"[red]Error:[/red] Base directory not found: {base_dir}")
        sys.exit(1)

    if not case_dir.exists() or not proc_dir.exists():
        console.print(
            f"[red]Error:[/red] Expected subdirectories not found in {base_dir}.\n"
            "  Looking for: case-list/ and procedure-list/"
        )
        sys.exit(1)

    return case_dir, proc_dir


def _sanitize_resident_id(resident_id: str) -> str:
    """Return a non-sensitive resident identifier for logs and error output."""
    return hashlib.sha256(resident_id.encode("utf-8")).hexdigest()[:8]


def _process_in_parallel(
    pairs: list[tuple[str, Path, Path]],
    config: ProcessConfig,
    workers: int,
) -> tuple[int, list[tuple[str, str]], list[tuple[str, int, list[str]]]]:
    """Process resident file pairs in parallel and collect summary results."""
    total_cases = 0
    errors: list[tuple[str, str]] = []
    orphan_notices: list[tuple[str, int, list[str]]] = []
    executor_cls = ProcessPoolExecutor if config.use_ml else ThreadPoolExecutor

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Processing residents", total=len(pairs))

        with executor_cls(max_workers=workers) as executor:
            futures = {
                executor.submit(process_resident, pair, config): pair[0]
                for pair in pairs
            }
            for future in as_completed(futures):
                resident_id = futures[future]
                try:
                    cases_written, orphan_notice = future.result()
                    total_cases += cases_written
                    if orphan_notice is not None:
                        orphan_notices.append(orphan_notice)
                except Exception:
                    sanitized_id = _sanitize_resident_id(resident_id)
                    logger.error("Failed processing resident %s", sanitized_id)
                    errors.append((sanitized_id, "processing_failed"))
                progress.advance(task)
    return total_cases, errors, orphan_notices


def main() -> None:
    """Run the batch resident-processing CLI."""
    args = _parse_args()
    output_dir: Path = args.output_dir
    case_dir, proc_dir = _validate_input_dirs(args.base_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pairs = find_resident_pairs(case_dir, proc_dir)
    if not pairs:
        console.print("[yellow]Warning:[/yellow] No matching resident file pairs found")
        sys.exit(0)

    console.print(
        f"Found [cyan]{len(pairs)}[/cyan] residents with both case and procedure files"
    )

    config = ProcessConfig(
        output_dir=output_dir,
        columns=ColumnMap(),
        excel_handler=ExcelHandler(),
        use_ml=args.use_ml,
    )
    total_cases, errors, orphan_notices = _process_in_parallel(
        pairs, config, args.workers
    )

    for resident_id, orphan_count, standalone_names in orphan_notices:
        console.print(
            f"  [yellow]Note:[/yellow] {resident_id}: {orphan_count} orphan "
            f"procedure(s) → {', '.join(standalone_names)}"
        )

    console.print(
        f"\n[green]Done.[/green] Processed [cyan]{len(pairs) - len(errors)}[/cyan] "
        f"residents, [cyan]{total_cases}[/cyan] total cases\n",
        f"Output saved to: [cyan]{output_dir}/[/cyan]",
    )

    if errors:
        console.print(f"\n[yellow]{len(errors)} errors:[/yellow]")
        for name, err in errors[:10]:
            console.print(f"  {name}: {err}")
        if len(errors) > 10:
            console.print(f"  ... and {len(errors) - 10} more")
        sys.exit(1)


if __name__ == "__main__":
    main()
