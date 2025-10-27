# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Case Parser is a Python tool that processes anesthesia case data from Excel files and converts it to standardized case log format. The tool extracts and categorizes medical procedures, patient demographics, airway management techniques, vascular access, and specialized monitoring from unstructured medical data.

## Commands

### Development Setup
```bash
# Install dependencies (recommended)
uv sync

# Install in development mode
uv pip install -e .

# Install with dev dependencies
uv sync --extra dev
```

### Running the Application
```bash
# Direct invocation
python main.py input.xlsx output.xlsx

# Using installed command
case-parser input.xlsx output.xlsx

# With options
case-parser input.xlsx output.xlsx --sheet "Data" --default-year 2024 --verbose
```

### Code Quality
```bash
# Format and lint code
ruff check --fix .
ruff format .
```

## Architecture

### Core Processing Pipeline

The application follows a pipeline architecture with clear separation of concerns:

1. **CLI Layer** (`cli.py`) - Argument parsing, validation, orchestration
2. **I/O Layer** (`io.py`) - Excel file reading/writing with openpyxl
3. **Processing Layer** (`processors.py`) - Core data transformation logic
4. **Extraction Layer** (`extractors.py`) - Text parsing using regex patterns
5. **Configuration Layer** (`models.py`) - Data models and business rules

### Data Flow

```
Excel Input → read_excel() → DataFrame → CaseProcessor.process_dataframe() →
process_row() for each row → extract_*() functions → Transformed DataFrame →
ExcelHandler.write_excel() → Formatted Excel Output
```

### Key Design Patterns

**Immutable Configuration**: `ColumnMap`, `AgeRange`, and `ProcedureRule` use frozen dataclasses to ensure configuration cannot be mutated during processing.

**Rule-Based Processing**: Procedure categorization and anesthesia type mapping use ordered rule lists (`PROCEDURE_RULES`, `ANESTHESIA_MAPPING`) that are evaluated sequentially. Order matters - more specific rules should come before general ones.

**Text Extraction Pattern**: All text extraction functions (`extract_airway_management`, `extract_vascular_access`, `extract_monitoring`) follow the same pattern:
- Accept `Any` type and handle None/NaN
- Use case-insensitive regex patterns via `_regex_any()` helper
- Return semicolon-separated findings with duplicates removed
- Return empty string for missing data

**Error Resilience**: `process_row()` catches all exceptions and returns empty-valued rows to maintain dataframe structure. Individual row failures don't stop processing.

### Important Business Logic

**Age Categorization** (`processors.py:60-79`): Uses ordered list of `AgeRange` objects with upper bounds. Returns first matching category where age < upper_bound. Categories are labeled a-e for residency requirement tracking.

**ASA Emergency Flag** (`processors.py:142-146`): If a separate "Emergent" column indicates emergency status but the ASA value doesn't contain "E", the function automatically appends "E" to the ASA status.

**OB/GYN Special Case** (`processors.py:116-122`): OB/GYN procedures have special logic - cesarean deliveries are detected by searching for "CESAREAN", "C-SECTION", or "C SECTION" in the procedure text and categorized separately from other OB/GYN procedures.

**Column Overrides**: All column mappings can be overridden via CLI arguments (`--col-*` flags). The `columns_from_args()` function merges overrides with defaults dynamically.

### Module Responsibilities

**models.py**: Contains all business rules as data. Modifications to categorization logic, anesthesia types, or procedure rules should be made here, not in processing code.

**extractors.py**: Pure text parsing functions with no business logic beyond regex patterns. Adding new extraction capabilities requires adding new functions following the established pattern.

**processors.py**: Contains only transformation logic. Each processing method should be stateless except for the ColumnMap and default_year configuration.

**io.py**: Handles all file system operations. The `ExcelHandler` class manages column auto-sizing and provides data summaries. Fixed column widths can be specified for columns that need specific formatting.

## Configuration Files

**ruff.toml**: Comprehensive linting rules enabled. Notably, `PLR2004` (magic value comparison) is ignored to allow inline threshold checking. Python 3.13 target version set but requires-python is 3.11+ for broader compatibility.

**pyproject.toml**: Uses hatchling as build backend. The package lives in `src/case_parser/` following src-layout pattern. Entry point is `case_parser.cli:main`.
