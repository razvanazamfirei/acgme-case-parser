"""Command line interface for the case parser."""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .exceptions import CaseParserError
from .io import ExcelHandler, read_excel
from .logging_config import setup_logging
from .models import ColumnMap
from .processor import CaseProcessor
from .validation import ValidationReport

console = Console()


def build_arg_parser() -> argparse.ArgumentParser:
    """Build command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Convert anesthesia Excel file to case log format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic conversion
  %(prog)s input.xlsx output.xlsx

  # With custom sheet and year
  %(prog)s input.xlsx output.xlsx --sheet "Data" --default-year 2024

  # With column overrides
  %(prog)s input.xlsx output.xlsx --col-date "Date of Service" --col-age "Patient Age"

  # With validation report
  %(prog)s input.xlsx output.xlsx --validation-report validation.txt
        """,
    )

    # Required arguments
    parser.add_argument("input_file", help="Input Excel file path (.xlsx or .xls)")
    parser.add_argument("output_file", help="Output Excel file path (.xlsx)")

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

    # Column override options
    for field_name in ColumnMap.__dataclass_fields__:
        arg_name = f"--col-{field_name.replace('_', '-')}"
        help_text = f"Override {field_name} column name"
        if field_name == "emergent":
            help_text += " (optional column)"
        parser.add_argument(arg_name, help=help_text)

    return parser


def columns_from_args(args: argparse.Namespace) -> ColumnMap:
    """Create ColumnMap from command line arguments."""
    base = ColumnMap()

    # Build kwargs for ColumnMap constructor
    kwargs = {}
    for field_name in ColumnMap.__dataclass_fields__:
        arg_name = f"col_{field_name}"
        if hasattr(args, arg_name) and getattr(args, arg_name) is not None:
            kwargs[field_name] = getattr(args, arg_name)

    # Create new ColumnMap with overrides
    return ColumnMap(**{**base.__dict__, **kwargs})


def validate_arguments(args: argparse.Namespace) -> None:
    """Validate command line arguments."""
    input_path = Path(args.input_file)
    output_path = Path(args.output_file)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if input_path.suffix.lower() not in {".xlsx", ".xls"}:
        raise ValueError(f"Unsupported input file format: {input_path.suffix}")

    if not output_path.suffix.lower() == ".xlsx":
        raise ValueError("Output file must have .xlsx extension")

    if args.default_year < 1900 or args.default_year > 2100:
        raise ValueError("Default year must be between 1900 and 2100")


def main() -> None:  # noqa: PLR0915
    """Main entry point."""
    parser = build_arg_parser()
    args = parser.parse_args()
    output_file = Path(args.output_file)
    # Set up logging
    setup_logging(level=args.log_level, verbose=args.verbose)

    try:
        # Validate arguments
        validate_arguments(args)

        # Create column mapping
        columns = columns_from_args(args)

        # Initialize handlers
        excel_handler = ExcelHandler()

        # Read input file
        df = read_excel(args.input_file, sheet_name=args.sheet or 0)

        if df.empty:
            console.print("[yellow]Warning:[/yellow] Input file is empty")
            return

        # Process data
        processor = CaseProcessor(columns, args.default_year)
        parsed_cases = processor.process_dataframe(df)
        output_df = processor.cases_to_dataframe(parsed_cases)

        # Generate validation report if requested
        if args.validation_report:
            report_path = Path(args.validation_report)
            report = ValidationReport(parsed_cases)

            # Determine format from extension
            if report_path.suffix.lower() == ".json":
                format_type = "json"
            elif report_path.suffix.lower() in {".xlsx", ".xls"}:
                format_type = "excel"
            else:
                format_type = "text"

            report.save_report(report_path, output_format=format_type)
            console.print(f"\n[green]Validation report saved to:[/green] {report_path}")

            # Print summary to console
            summary = report.get_summary()
            console.print()
            console.print(
                Panel(
                    "[bold]Validation Summary[/bold]",
                    border_style="cyan",
                )
            )

            # Create summary table
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
            console.print()

        # Write output
        excel_handler.write_excel(
            output_df, args.output_file, fixed_widths={"Original Procedure": 12}
        )

        # Print summary
        summary = excel_handler.get_data_summary(output_df)
        print_summary(output_file, summary)

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except ValueError as e:
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


def print_summary(output_file: Path, summary: dict[str, Any]):
    console.print()
    console.print(
        Panel(
            "[bold]Output Summary[/bold]",
            border_style="green",
        )
    )

    # Create summary table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="cyan", no_wrap=True)
    table.add_column(style="white")

    table.add_row("Cases:", str(summary["total_cases"]))
    table.add_row("Date range:", summary["date_range"])

    console.print(table)

    if summary["empty_cases"] > 0:
        console.print(
            f"  [yellow]Warning:[/yellow] {summary['empty_cases']} "
            "cases have empty Case IDs"
        )

    console.print()
    console.print(f"[green]Output saved to:[/green] {output_file}")
    console.print("[bold green]Done.[/bold green]")


if __name__ == "__main__":
    main()
