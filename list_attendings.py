#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# ///

"""Export anesthesia attending case counts from case-list CSV exports."""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from collections import Counter
from numbers import Real
from pathlib import Path
from typing import TextIO

from case_parser.utils import format_name

_CASE_LIST_DIR = "case-list"
_ATTENDING_COLUMN = "AnesAttendings"
_RESIDENT_LIST_PATH = Path("anesthesia-residents.txt")
_TITLE_PATTERN = re.compile(r"\b(MD|DO|PhD|CRNA|RN)\b", flags=re.IGNORECASE)
_TRAILING_COMMA_PATTERN = re.compile(r",\s*$")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def _is_missing_scalar(value: object) -> bool:
    """Return True for the scalar missing-value sentinels handled here."""
    return value is None or (
        isinstance(value, Real)
        and not isinstance(value, bool)
        and math.isnan(float(value))
    )


def clean_attending_name(value: object) -> str:
    """Normalize one attending name after timestamp and list splitting."""
    if _is_missing_scalar(value):
        return ""

    name = _TITLE_PATTERN.sub("", str(value)).strip()
    name = _TRAILING_COMMA_PATTERN.sub("", name).strip()
    return _WHITESPACE_PATTERN.sub(" ", name)


def _iter_attending_names(raw_value: object) -> list[str]:
    """Split a raw attending field into normalized individual names."""
    if _is_missing_scalar(raw_value):
        return []

    names: list[str] = []
    for part in str(raw_value).split(";"):
        cleaned = clean_attending_name(part.split("@")[0])
        if cleaned:
            names.append(cleaned)
    return names


def _normalize_resident_name(raw: str) -> list[str]:
    """Return candidate display names for a resident list entry."""
    no_parens = re.sub(r"\s*\([^)]+\)", "", raw).strip()
    no_quotes = re.sub(r'\s*"[^"]+"\s*', " ", no_parens).strip()
    words = no_quotes.split()
    candidates = [no_quotes]
    if len(words) >= 3:
        candidates.append(f"{words[0]} {words[-1]}")
    alternative = re.search(r"\(([^)]+)\)", raw)
    if alternative and words:
        candidates.append(f"{alternative.group(1)} {words[-1]}")
    return candidates


def _load_resident_keys(names_file: Path) -> set[str]:
    """Load normalized resident display names from the resident list."""
    names = [
        line.strip()
        for line in names_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return {
        candidate.lower()
        for name in names
        for candidate in _normalize_resident_name(name)
    }


def collect_attending_counts(
    input_dir: Path,
    *,
    names_file: Path,
    minimum_cases: int = 0,
) -> list[tuple[str, int]]:
    """Collect sorted attending case counts from resident-supervised case-list CSVs."""
    counts: Counter[str] = Counter()
    resident_keys = _load_resident_keys(names_file)

    directory = input_dir / _CASE_LIST_DIR
    if not directory.exists():
        return []

    for csv_path in sorted(directory.glob("*.csv")):
        resident_name = format_name(csv_path.name.removesuffix(".CaseList.csv"))
        if resident_name.lower() not in resident_keys:
            continue
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                counts.update(
                    set(_iter_attending_names(row.get(_ATTENDING_COLUMN, "")))
                )

    return sorted(
        ((name, count) for name, count in counts.items() if count >= minimum_cases),
        key=lambda item: (-item[1], item[0]),
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export anesthesia attending case counts from case-list CSVs"
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("Output-Supervised"),
        help="Directory containing case-list/ (default: Output-Supervised)",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        help="Optional CSV path to write instead of printing to stdout",
    )
    parser.add_argument(
        "--resident-list",
        type=Path,
        default=_RESIDENT_LIST_PATH,
        help="Resident names file used to filter case-list files",
    )
    parser.add_argument(
        "--filter",
        type=int,
        default=0,
        help="Only include attendings with at least this many cases",
    )
    return parser


def _write_csv(rows: list[tuple[str, int]], handle: TextIO) -> None:
    writer = csv.writer(handle)
    writer.writerow(["attending", "count"])
    writer.writerows(rows)


def main() -> None:
    args = build_arg_parser().parse_args()
    input_dir: Path = args.input_dir
    output_file: Path | None = args.output_file
    names_file: Path = args.resident_list
    minimum_cases: int = args.filter

    if not input_dir.exists():
        print(f"Error: input directory not found: {input_dir}", file=sys.stderr)
        sys.exit(1)
    if not names_file.exists():
        print(f"Error: resident list not found: {names_file}", file=sys.stderr)
        sys.exit(1)
    if minimum_cases < 0:
        print("Error: --filter must be non-negative", file=sys.stderr)
        sys.exit(1)

    rows = collect_attending_counts(
        input_dir,
        names_file=names_file,
        minimum_cases=minimum_cases,
    )
    if not rows:
        print(f"Error: no attending counts found under {input_dir}", file=sys.stderr)
        sys.exit(1)

    if output_file is not None:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open("w", encoding="utf-8", newline="") as handle:
            _write_csv(rows, handle)
        print(f"Wrote {len(rows)} attending rows to {output_file}")
        return

    _write_csv(rows, sys.stdout)


if __name__ == "__main__":
    main()
