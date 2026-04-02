"""Command line interface for the case parser."""

from __future__ import annotations

import argparse
import logging
import sys
import traceback
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from pandas import DataFrame

from .domain import ParsedCase, ProcedureCategory
from .exceptions import CaseParserError
from .io import (
    CsvHandler,
    ExcelHandler,
    ExcelWriteOptions,
    discover_csv_pairs,
    read_excel,
)
from .logging_config import setup_logging
from .ml.config import DEFAULT_ML_THRESHOLD
from .models import (
    FORMAT_TYPE_CASELOG,
    FORMAT_TYPE_STANDALONE,
    OUTPUT_FORMAT_VERSION,
    STANDALONE_OUTPUT_FORMAT_VERSION,
    ColumnMap,
)
from .patterns.categorization import (
    OBGYN_SERVICE_KEYWORDS,
    _apply_rule_category,
    _categorize_obgyn_text,
    _normalize_categorization_request,
    _resolve_category_result,
    categorize_obgyn,
)
from .patterns.procedure_patterns import (
    PROCEDURE_RULES,
    PROCEDURE_TEXT_RULES,
    ProcedureRule,
)
from .processor import CaseProcessor
from .standalone_exports import (
    StandaloneOutputSpec,
    iter_standalone_case_exports,
    split_standalone_cases,
)
from .validation import ValidationReport

logger = logging.getLogger(__name__)
console = Console()
__all__ = ["split_standalone_cases"]
type _ProcessingMode = Literal["excel", "csv_v2"]


@dataclass(frozen=True)
class _ProcessingOptions:
    """Runtime options used across processing entry points."""

    default_year: int
    sheet_name: str | int | None
    use_ml: bool
    ml_threshold: float
    workers: int


@dataclass(frozen=True)
class _LoadedInput:
    """Normalized input payload ready for shared processing."""

    main_df: DataFrame
    orphan_df: DataFrame


@dataclass(frozen=True)
class _ProcessingRequest:
    """Explicit CLI processing request passed into the shared dispatcher."""

    mode: _ProcessingMode
    input_path: Path
    output_path: Path | None = None
    excel_handler: ExcelHandler | None = None


@dataclass(frozen=True)
class _ProcessingResult:
    """Processed output returned by the shared CLI dispatcher."""

    cases: list[ParsedCase]
    output_df: DataFrame
    standalone_case_count: int = 0
    standalone_cases: list[ParsedCase] = field(default_factory=list)


def build_arg_parser() -> argparse.ArgumentParser:
    """Build command line argument parser.

    Returns:
        Configured ArgumentParser with all supported flags and column overrides.
    """
    parser = argparse.ArgumentParser(
        description="Convert anesthesia Excel file to case log format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic conversion
  %(prog)s input.xlsx output.xlsx

  # Process all Excel files in a directory
  %(prog)s /path/to/excel/files/ combined_output.xlsx

  # With custom sheet and year
  %(prog)s input.xlsx output.xlsx --sheet "Data" --default-year 2024

  # With column overrides
  %(prog)s input.xlsx output.xlsx --col-date "Date of Service" --col-age "Patient Age"

  # With validation report
  %(prog)s input.xlsx output.xlsx --validation-report validation.txt

  # Debug categorization with interactive bug tracking report
  %(prog)s debug-categorize "CABG" "CARDIAC" --bug-track

  # Process and review all categorizations interactively for bug tracking
  %(prog)s input.xlsx output.xlsx --bug-track
        """,
    )

    # Required arguments
    parser.add_argument(
        "input_file",
        nargs="?",
        help="Input Excel file path or directory containing Excel files",
    )
    parser.add_argument("output_file", nargs="?", help="Output Excel file path (.xlsx)")

    # Optional arguments
    parser.add_argument("--sheet", help="Sheet name to read (default: first sheet)")
    parser.add_argument(
        "--default-year",
        type=int,
        default=2025,
        help="Fallback year if a date cannot be parsed (default: 2025)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level (default: INFO)",
    )
    parser.add_argument(
        "--validation-report",
        help="Generate validation report (text, json, or excel format)",
        metavar="FILE",
    )
    parser.add_argument(
        "--v2",
        action="store_true",
        help="Use CSV v2 format (separate CaseList and ProcedureList files). "
        "Input must be a directory containing matching CSV pairs.",
    )
    parser.add_argument(
        "--no-ml",
        action="store_true",
        help="Disable ML-assisted categorization and use rules only.",
    )
    parser.add_argument(
        "--ml-threshold",
        type=float,
        default=DEFAULT_ML_THRESHOLD,
        help=(
            "Minimum ML confidence used for hybrid categorization "
            f"(default: {DEFAULT_ML_THRESHOLD:.2f})"
        ),
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help=(
            "Number of worker slots for parsing "
            "(default: 1; large ML-heavy batches may use process chunks, "
            "but higher values often do not improve smaller runs)"
        ),
    )
    parser.add_argument(
        "--bug-track",
        action="store_true",
        help=(
            "Interactively review categorization results and output a "
            "Markdown table for bug tracking."
        ),
    )

    # Column override options
    for field_name in ColumnMap.__dataclass_fields__:
        arg_name = f"--col-{field_name.replace('_', '-')}"
        help_text = f"Override {field_name} column name"
        if field_name == "emergent":
            help_text += " (optional column)"
        parser.add_argument(arg_name, help=help_text)

    return parser


def columns_from_args(args: argparse.Namespace) -> ColumnMap:
    """Create ColumnMap from command line arguments, applying any --col-* overrides.

    Args:
        args: Parsed argument namespace containing optional col_* attributes.

    Returns:
        ColumnMap with default values overridden by any provided --col-* flags.
    """
    base = ColumnMap()
    kwargs = {}
    for field_name in ColumnMap.__dataclass_fields__:
        arg_name = f"col_{field_name}"
        if hasattr(args, arg_name) and getattr(args, arg_name) is not None:
            kwargs[field_name] = getattr(args, arg_name)
    return ColumnMap(**{**base.__dict__, **kwargs})


def validate_arguments(args: argparse.Namespace) -> None:
    """Validate command line arguments, raising on any invalid combination.

    Args:
        args: Parsed argument namespace to validate.

    Raises:
        FileNotFoundError: If the input path does not exist.
        ValueError: If the input/output formats are unsupported, no Excel files
            are found in a directory, or the year is out of range.
    """
    if not args.input_file or not args.output_file:
        raise ValueError("Both input_file and output_file are required for processing.")

    input_path = Path(args.input_file)
    output_path = Path(args.output_file)

    if not input_path.exists():
        raise FileNotFoundError(f"Input path not found: {input_path}")

    if args.v2:
        if not input_path.is_dir():
            raise ValueError(
                "--v2 requires input to be a directory containing "
                "CaseList and ProcedureList CSV files"
            )
        try:
            discover_csv_pairs(input_path)
        except ValueError as e:
            raise ValueError(f"CSV v2 validation failed: {e}") from e
    elif input_path.is_file() and input_path.suffix.lower() not in {".xlsx", ".xls"}:
        raise ValueError(f"Unsupported input file format: {input_path.suffix}")
    elif input_path.is_dir():
        excel_files = list(input_path.glob("*.xlsx")) + list(input_path.glob("*.xls"))
        if not excel_files:
            raise ValueError(f"No Excel files found in directory: {input_path}")

    if output_path.suffix.lower() != ".xlsx":
        raise ValueError("Output file must have .xlsx extension")

    if args.default_year < 1900 or args.default_year > 2100:
        raise ValueError("Default year must be between 1900 and 2100")
    if not 0.0 <= args.ml_threshold <= 1.0:
        raise ValueError("ML threshold must be between 0.0 and 1.0")
    if args.workers < 1:
        raise ValueError("workers must be at least 1")


def find_excel_files(directory: Path) -> list[Path]:
    """Return all .xlsx and .xls files in directory, sorted by name.

    Args:
        directory: Directory to search for Excel files.

    Returns:
        Sorted list of matching file paths sorted alphabetically (.xlsx before .xls).
    """
    return sorted(directory.glob("*.xlsx")) + sorted(directory.glob("*.xls"))


def _load_excel_input(input_path: Path, options: _ProcessingOptions) -> _LoadedInput:
    """Read one Excel file or directory of Excel files into one processing payload."""
    if input_path.is_file():
        excel_files = [input_path]
    else:
        excel_files = find_excel_files(input_path)
        console.print(
            f"\n[bold cyan]Found {len(excel_files)} Excel file(s) "
            f"in directory[/bold cyan]\n"
        )

    frames: list[DataFrame] = []
    loaded_file_count = 0
    for excel_file in excel_files:
        console.print(f"[cyan]Reading:[/cyan] {excel_file.name}")
        df = read_excel(str(excel_file), sheet_name=options.sheet_name or 0)
        if df.empty:
            console.print(
                f"[yellow]  Warning:[/yellow] {excel_file.name} is empty, skipping"
            )
            continue
        loaded_file_count += 1
        console.print(
            f"[green]  OK[/green] Loaded {len(df)} rows from {excel_file.name}"
        )
        frames.append(df)

    if input_path.is_dir():
        console.print(
            f"\n[bold green]Loaded {loaded_file_count} non-empty file(s), "
            f"total {sum(len(frame) for frame in frames)} row(s)[/bold green]\n"
        )

    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return _LoadedInput(main_df=combined, orphan_df=pd.DataFrame())


def _load_csv_input(
    input_path: Path,
    columns: ColumnMap,
    output_path: Path,
) -> _LoadedInput:
    """Read CSV v2 input into the shared processing payload."""
    console.print(
        Panel(
            f"[cyan]Processing CSV v2 format from:[/cyan] {input_path}\n"
            f"[cyan]Output file:[/cyan] {output_path}",
            title="CSV v2 Mode",
            border_style="cyan",
        )
    )
    main_df, orphan_df = CsvHandler(columns).read(input_path)
    return _LoadedInput(main_df=main_df, orphan_df=orphan_df)


def _build_processor(columns: ColumnMap, options: _ProcessingOptions) -> CaseProcessor:
    """Create a processor instance from shared runtime options."""
    return CaseProcessor(
        columns,
        options.default_year,
        use_ml=options.use_ml,
        ml_threshold=options.ml_threshold,
    )


def _load_input(
    request: _ProcessingRequest,
    columns: ColumnMap,
    options: _ProcessingOptions,
) -> _LoadedInput:
    """Load input data for the selected CLI processing mode."""
    if request.mode == "excel":
        return _load_excel_input(request.input_path, options)
    if request.output_path is None:
        raise ValueError("output_path is required for csv_v2 processing")
    return _load_csv_input(request.input_path, columns, request.output_path)


def process_input(
    request: _ProcessingRequest,
    columns: ColumnMap,
    options: _ProcessingOptions,
) -> _ProcessingResult:
    """Dispatch CLI processing through one shared read/process/export path.

    Args:
        request: Explicit processing request including mode and I/O paths.
        columns: Column mapping configuration.
        options: Shared runtime options.

    Returns:
        Processed cases, output dataframe, and standalone output count.
    """
    processor = _build_processor(columns, options)
    loaded_input = _load_input(
        request=request,
        columns=columns,
        options=options,
    )

    all_cases = processor.process_dataframe(
        loaded_input.main_df,
        workers=options.workers,
    )
    output_df = processor.cases_to_dataframe(all_cases)

    standalone_case_count = 0
    standalone_cases: list[ParsedCase] = []
    if not loaded_input.orphan_df.empty:
        if (
            request.mode != "csv_v2"
            or request.output_path is None
            or request.excel_handler is None
        ):
            raise ValueError(
                "csv_v2 standalone outputs require output_path and excel_handler"
            )
        orphan_cases = processor.process_dataframe(
            loaded_input.orphan_df,
            workers=options.workers,
        )
        for spec, export_cases in iter_standalone_case_exports(orphan_cases):
            standalone_case_count += len(export_cases)
            standalone_cases.extend(export_cases)
            _write_standalone_output(
                processor=processor,
                excel_handler=request.excel_handler,
                output_path=request.output_path,
                cases=export_cases,
                spec=spec,
            )
        # Do not extend all_cases with orphan_cases; keep main cases separate so
        # main() can correctly gate on has_main_cases for standalone-only runs.

    return _ProcessingResult(
        cases=all_cases,
        output_df=output_df,
        standalone_case_count=standalone_case_count,
        standalone_cases=standalone_cases,
    )


def _write_standalone_output(
    *,
    processor: CaseProcessor,
    excel_handler: ExcelHandler,
    output_path: Path,
    cases: list[ParsedCase],
    spec: StandaloneOutputSpec,
) -> None:
    """Write one standalone orphan-procedure workbook when rows are present."""
    if not cases:
        return

    standalone_output = processor.procedures_to_dataframe(cases)
    standalone_path = output_path.with_stem(f"{output_path.stem}_{spec.suffix}")
    excel_handler.write_excel(
        standalone_output,
        standalone_path,
        options=ExcelWriteOptions(
            format_type=FORMAT_TYPE_STANDALONE,
            version=STANDALONE_OUTPUT_FORMAT_VERSION,
        ),
    )
    console.print(
        f"[cyan]{spec.label}:[/cyan] {standalone_path} ({len(cases)} procedure(s))"
    )


def save_validation_report(cases: list[ParsedCase], report_path: Path) -> None:
    """Generate and save a validation report, then print its summary.

    The output format is inferred from the file extension: .json produces a JSON
    report, .xlsx/.xls produces an Excel report, and anything else produces a
    plain-text report.

    Args:
        cases: List of parsed cases to validate.
        report_path: File path where the report will be written.
    """
    suffix = report_path.suffix.lower()
    if suffix == ".json":
        format_type = "json"
    elif suffix in {".xlsx", ".xls"}:
        format_type = "excel"
    else:
        format_type = "text"

    report = ValidationReport(cases)
    report.save_report(report_path, output_format=format_type)

    console.print(f"\n[green]Validation report saved to:[/green] {report_path}")
    console.print(Panel("[bold]Validation Summary[/bold]", border_style="cyan"))
    print_validation_summary(report.get_summary())


def print_validation_summary(summary: dict[str, Any]) -> None:
    """Print a validation summary as a rich table.

    Args:
        summary: Summary dict as returned by ValidationReport.get_summary().
    """
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="cyan", no_wrap=True)
    table.add_column(style="white")

    table.add_row("Total Cases:", str(summary["total_cases"]))
    table.add_row(
        "Cases with Warnings:",
        f"[yellow]{summary['cases_with_warnings']}[/yellow]"
        if summary["cases_with_warnings"] > 0
        else str(summary["cases_with_warnings"]),
    )
    table.add_row(
        "Low Confidence Cases:",
        f"[red]{summary['low_confidence_cases']}[/red]"
        if summary["low_confidence_cases"] > 0
        else str(summary["low_confidence_cases"]),
    )
    table.add_row("Average Confidence:", f"{summary['average_confidence']:.3f}")
    console.print(table)


def get_output_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Return aggregate stats for the output DataFrame for terminal display.

    Args:
        df: Output DataFrame produced by CaseProcessor.cases_to_dataframe().

    Returns:
        Dict with keys: total_cases, date_range, columns, empty_cases,
        missing_dates. Falls back to a minimal dict on any error.
    """
    try:
        dates = pd.to_datetime(df["Case Date"], format="%m/%d/%Y", errors="coerce")
        date_range = "Unavailable"
        if dates.notna().any():
            min_date = dates.min().strftime("%m/%d/%Y")
            max_date = dates.max().strftime("%m/%d/%Y")
            date_range = f"{min_date} to {max_date}"

        return {
            "total_cases": len(df),
            "date_range": date_range,
            "columns": list(df.columns),
            "empty_cases": (
                df["Case ID"].fillna("").astype(str).str.strip().eq("").sum()
            ),
            "missing_dates": df["Case Date"].isna().sum(),
        }
    except Exception as e:
        logger.warning("Could not generate output summary: %s", e)
        return {"total_cases": len(df), "date_range": "Unavailable"}


def print_summary(output_file: Path, summary: dict[str, Any]) -> None:
    """Print the final output summary panel.

    Args:
        output_file: Path to the written output file (displayed in the panel).
        summary: Summary dict as returned by get_output_summary().
    """
    console.print()
    console.print(Panel("[bold]Output Summary[/bold]", border_style="green"))

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="cyan", no_wrap=True)
    table.add_column(style="white")
    table.add_row("Cases:", str(summary["total_cases"]))
    table.add_row("Date range:", summary["date_range"])
    console.print(table)

    empty_cases = summary.get("empty_cases", 0)
    if empty_cases > 0:
        console.print(
            f"  [yellow]Warning:[/yellow] {empty_cases} cases have empty Case IDs"
        )

    console.print()
    console.print(f"[green]Output saved to:[/green] {output_file}")
    console.print("[bold green]Done.[/bold green]")


def _trace_match_rules(
    values: list[str],
    procedure_text: str,
    rules: list[ProcedureRule],
    *,
    exclude_in_values: bool,
) -> list[dict]:
    """Trace the matching process for a set of rules."""
    matches = []
    seen_categories = set()

    for value in values:
        for rule in rules:
            # Check for inclusion
            matching_keyword = next((kw for kw in rule.keywords if kw in value), None)
            if matching_keyword is None:
                continue

            # Check for exclusion
            excluding_keyword = None
            if rule.exclude_keywords:
                excluding_keyword = next(
                    (
                        excl
                        for excl in rule.exclude_keywords
                        if excl in procedure_text
                        or (exclude_in_values and excl in value)
                    ),
                    None,
                )

            if excluding_keyword:
                continue

            # If we reach here, it's a match
            category = _apply_rule_category(rule.category, procedure_text)

            if category not in seen_categories:
                seen_categories.add(category)
                matches.append({
                    "category": category,
                    "rule_category": rule.category,
                    "matched_value": value,
                    "matched_keyword": matching_keyword,
                    "source": "Service" if exclude_in_values else "Text",
                })
            # First matching rule wins for this value
            break

    return matches


def print_bug_tracking_table(cases: list[ParsedCase]) -> None:
    """Print a Markdown table for bug tracking of categorization.

    This generates a table that is more concise and includes matched rules.
    It prompts the user interactively to select the correct category for each case.
    """
    if not cases:
        return

    # List of all categories to show as options, sorted for consistency
    categories = sorted([c.value for c in ProcedureCategory])

    final_rows = []
    print("\n[bold]Starting Interactive Bug Tracking Review...[/bold]")
    print("For each case, confirm the predicted category or select the correct one.")

    for i, case in enumerate(cases):
        procedure = case.procedure or "N/A"
        services = ", ".join(case.services) or "N/A"
        predicted = case.procedure_category.value
        rules = ", ".join(case.matched_rules) or "None"

        print(f"\n[bold cyan]Case {i + 1}/{len(cases)}[/bold cyan]")
        print(f"  [bold]Procedure:[/bold] {procedure}")
        print(f"  [bold]Services:[/bold]  {services}")
        print(f"  [bold]Predicted:[/bold] [green]{predicted}[/green]")
        print(f"  [bold]Rules Matched:[/bold] {rules}")

        print("\nSelect the correct category:")
        print("  0. [Use Predicted]")
        for idx, cat in enumerate(categories, 1):
            print(f"  {idx}. {cat}")

        choice = input(f"\nYour choice (0-{len(categories)}) [0]: ").strip()

        if not choice or choice == "0":
            correct_cat = predicted
        else:
            try:
                choice_idx = int(choice)
                if 1 <= choice_idx <= len(categories):
                    correct_cat = categories[choice_idx - 1]
                else:
                    print(f"[red]Invalid choice. Using predicted: {predicted}[/red]")
                    correct_cat = predicted
            except ValueError:
                print(f"[red]Invalid input. Using predicted: {predicted}[/red]")
                correct_cat = predicted

        # Normalize and escape values for Markdown table
        procedure_esc = procedure.replace("|", "\\|").replace("\n", " ")
        services_esc = services.replace("|", "\\|")
        rules_esc = rules.replace("|", "\\|")

        row = (
            f"| {procedure_esc} | {services_esc} | "
            f"**{predicted}** | {correct_cat} | {rules_esc} | [ ] |"
        )
        final_rows.append(row)

    # Output the final Markdown table
    print("\n### Categorization Bug Tracking\n")
    print(
        "| Original Procedure | Services | Predicted Category | "
        "Correct Category | Matched Rules | Done |"
    )
    print("| :--- | :--- | :--- | :--- | :--- | :---: |")
    for row in final_rows:
        print(row)
    print()


def _collect_trace_matches(
    procedure_text: str | None,
    normalized_services: list[str],
) -> list[dict[str, Any]]:
    """Internal helper to gather rule matches for debugging."""
    trace_matches = []

    # 1. Match Services
    service_matches = _trace_match_rules(
        list(normalized_services),
        procedure_text,
        PROCEDURE_RULES,
        exclude_in_values=True,
    )
    trace_matches.extend(service_matches)

    # 2. Check OB/GYN promotion
    has_obstetric_service = any(
        any(keyword in service for keyword in OBGYN_SERVICE_KEYWORDS)
        for service in normalized_services
    )
    if has_obstetric_service:
        obgyn_category = _categorize_obgyn_text(
            procedure_text,
            allow_generic_neuraxial=True,
        )
        if obgyn_category != ProcedureCategory.OTHER:
            trace_matches.append({
                "category": obgyn_category,
                "rule_category": "OB/GYN Promotion",
                "matched_value": "OB/GYN Service Context",
                "matched_keyword": "Multiple",
                "source": "Service Context",
            })

    # 3. Fallback to text matching
    if not trace_matches and procedure_text:
        text_matches = _trace_match_rules(
            [procedure_text],
            procedure_text,
            PROCEDURE_TEXT_RULES,
            exclude_in_values=False,
        )
        trace_matches.extend(text_matches)

        if not trace_matches:
            obgyn_category = categorize_obgyn(procedure_text)
            if obgyn_category != ProcedureCategory.OTHER:
                trace_matches.append({
                    "category": obgyn_category,
                    "rule_category": "OB/GYN Detection",
                    "matched_value": procedure_text,
                    "matched_keyword": "OB Keywords",
                    "source": "Text Fallback",
                })
    return trace_matches


def _display_trace_matches(trace_matches: list[dict[str, Any]]) -> None:
    """Internal helper to display trace matches in a Rich table."""
    if trace_matches:
        table = Table(
            title="Match Trace", show_header=True, header_style="bold magenta"
        )
        table.add_column("Source", style="dim")
        table.add_column("Rule Category")
        table.add_column("Matched Value")
        table.add_column("Keyword", style="green")
        table.add_column("Result Category", style="bold")

        for m in trace_matches:
            table.add_row(
                m["source"],
                m["rule_category"],
                m["matched_value"],
                m["matched_keyword"],
                m["category"].value,
            )
        console.print(table)
    else:
        console.print("[yellow]No rules matched.[/yellow]")


def handle_debug_categorize(
    procedure: str | None,
    services_input: str | list[str] | None,
    bug_track: bool = False,
) -> None:
    """Run categorization with detailed tracing and display results."""
    # Normalize inputs
    procedure_text, normalized_services = _normalize_categorization_request(
        procedure, services_input
    )

    if not bug_track:
        console.print(
            Panel(
                f"[bold]Procedure:[/bold] {procedure_text or '(None)'}\n"
                f"[bold]Services:[/bold] {list(normalized_services) or '(None)'}",
                title="Categorization Debugger",
                border_style="cyan",
            )
        )

    # Gather Match Trace
    trace_matches = _collect_trace_matches(procedure_text, list(normalized_services))

    # Display Trace Table
    if not bug_track:
        _display_trace_matches(trace_matches)

    # Final Result
    categories = [m["category"] for m in trace_matches]
    final_category, warnings = _resolve_category_result(categories, normalized_services)

    if not bug_track:
        result_style = (
            "bold green" if final_category != ProcedureCategory.OTHER else "bold yellow"
        )
        console.print(
            Panel(
                f"[bold]Final Category:[/bold] [{result_style}]"
                f"{final_category.value}[/]\n"
                f"[bold]Warnings:[/bold] {warnings or 'None'}",
                title="Result",
                border_style="green",
            )
        )

        if warnings:
            for w in warnings:
                console.print(f"[bold yellow]WARNING:[/bold yellow] {w}")
    else:
        # Output as Markdown row

        # Format matched rules for the table
        matched_rules_summary = [
            f"{m['source']}:{m['rule_category']}({m['matched_keyword']})"
            for m in trace_matches
        ]

        # Create a dummy ParsedCase for the table formatter
        dummy_case = ParsedCase(
            case_date=datetime.now(UTC).date(),
            episode_id="DEBUG",
            procedure=procedure_text,
            services=list(normalized_services),
            procedure_category=final_category,
            matched_rules=matched_rules_summary,
            raw_date=None,
            raw_age=None,
            raw_asa=None,
            raw_anesthesia_type=None,
            procedure_notes=None,
            responsible_provider=None,
        )
        print_bug_tracking_table([dummy_case])


def main() -> None:
    """Main entry point for the case-parser CLI.

    Parses arguments, validates inputs, dispatches to the appropriate processing
    path (Excel workbook input or CSV v2 directory input), optionally writes a
    validation report, writes the primary output workbook, and prints a
    summary. In CSV v2 mode, standalone orphan procedures may also be written
    to separate block and combined neuraxial/delivery workbooks. Exits with a
    non-zero status code on any error.
    """
    if len(sys.argv) > 1 and sys.argv[1] == "debug-categorize":
        bug_track = "--bug-track" in sys.argv
        # Basic manual parsing for debug-categorize
        args_without_flag = [a for a in sys.argv if a != "--bug-track"]
        proc = args_without_flag[2] if len(args_without_flag) > 2 else None
        serv = args_without_flag[3].split(",") if len(args_without_flag) > 3 else []
        handle_debug_categorize(proc, serv, bug_track=bug_track)
        return

    parser = build_arg_parser()
    args = parser.parse_args()
    setup_logging(level=args.log_level, verbose=args.verbose)

    try:
        validate_arguments(args)
        columns = columns_from_args(args)
        input_path = Path(args.input_file)
        output_path = Path(args.output_file)
        excel_handler = ExcelHandler()
        options = _ProcessingOptions(
            default_year=args.default_year,
            sheet_name=args.sheet,
            use_ml=not args.no_ml,
            ml_threshold=args.ml_threshold,
            workers=args.workers,
        )

        processing_result = process_input(
            request=_ProcessingRequest(
                mode="csv_v2" if args.v2 else "excel",
                input_path=input_path,
                output_path=output_path if args.v2 else None,
                excel_handler=excel_handler if args.v2 else None,
            ),
            columns=columns,
            options=options,
        )
        main_cases = processing_result.cases
        output_df = processing_result.output_df
        standalone_case_count = processing_result.standalone_case_count

        if not main_cases:
            if standalone_case_count:
                console.print(
                    "[yellow]Warning:[/yellow] "
                    "No main cases to process; standalone orphan outputs were "
                    f"written for {standalone_case_count} procedure(s)"
                )
            else:
                console.print("[yellow]Warning:[/yellow] No cases to process")
            return

        if args.bug_track:
            print_bug_tracking_table(main_cases)

        if args.validation_report:
            save_validation_report(
                main_cases + processing_result.standalone_cases,
                Path(args.validation_report),
            )

        excel_handler.write_excel(
            output_df,
            output_path,
            options=ExcelWriteOptions(
                fixed_widths={"Original Procedure": 12},
                format_type=FORMAT_TYPE_CASELOG,
                version=OUTPUT_FORMAT_VERSION,
            ),
        )
        print_summary(output_path, get_output_summary(output_df))

    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except PermissionError as e:
        console.print(f"[red]Permission error:[/red] {e}")
        sys.exit(1)
    except CaseParserError as e:
        console.print(f"[red]Processing error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
