"""CSV v2 format I/O operations for case and procedure matching."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from pandas import DataFrame

from .models import ColumnMap

logger = logging.getLogger(__name__)


def discover_csv_pairs(directory: Path) -> list[tuple[Path, Path]]:
    """
    Discover matching CaseList and ProcedureList CSV file pairs.

    Args:
        directory: Directory to search for CSV files

    Returns:
        List of (case_file, procedure_file) path tuples

    Raises:
        ValueError: If no matching pairs found
    """
    directory = Path(directory)

    # Find all CaseList and ProcedureList files
    case_files = {
        f.name.replace(".CaseList.csv", ""): f for f in directory.glob("*.CaseList.csv")
    }
    proc_files = {
        f.name.replace(".ProcedureList.csv", ""): f
        for f in directory.glob("*.ProcedureList.csv")
    }

    # Find matching pairs
    common_prefixes = set(case_files.keys()) & set(proc_files.keys())

    # Warn about unpaired files
    unpaired_case = set(case_files.keys()) - common_prefixes
    unpaired_proc = set(proc_files.keys()) - common_prefixes

    if unpaired_case or unpaired_proc:
        logger.warning(
            "Found unpaired files - CaseList: %s, ProcedureList: %s",
            list(unpaired_case),
            list(unpaired_proc),
        )

    if not common_prefixes:
        raise ValueError(
            f"No matching CSV pairs found in {directory}. "
            "Expected files matching pattern: "
            "<PREFIX>.CaseList.csv and <PREFIX>.ProcedureList.csv"
        )

    # Create sorted list of pairs
    pairs = [
        (case_files[prefix], proc_files[prefix]) for prefix in sorted(common_prefixes)
    ]

    logger.info("Discovered %d CSV pair(s)", len(pairs))
    return pairs


# Invasiveness ranking for MPOG ProcedureName values (higher = more invasive/complex).
# Used to select the primary anesthesia technique when a case has multiple procedures.
TECHNIQUE_RANK = {
    "Intubation complex": 6,
    "Intubation routine": 5,
    "Spinal": 4,
    "Epidural": 3,
    "LMA": 2,
    "Peripheral nerve block": 1,
}


def _select_primary_technique(proc_group: pd.DataFrame) -> pd.Series:
    """
    Select the primary (most invasive) anesthesia technique for one case.

    Args:
        proc_group: DataFrame of procedures for one MPOG_Case_ID

    Returns:
        Series with the highest-ranked technique as Airway_Type
    """
    techniques = proc_group["ProcedureName"].dropna()

    if techniques.empty:
        return pd.Series({"Airway_Type": None})

    ranked = [(TECHNIQUE_RANK.get(t, 0), t) for t in techniques]
    primary = max(ranked)[1]

    return pd.Series({"Airway_Type": primary})


def join_case_and_procedures(
    case_df: DataFrame, proc_df: DataFrame
) -> tuple[DataFrame, DataFrame]:
    """
    Join case and procedure DataFrames, aggregating multiple procedures per case.

    Args:
        case_df: CaseList DataFrame with MPOG_Case_ID
        proc_df: ProcedureList DataFrame with MPOG_Case_ID

    Returns:
        Tuple of (joined_df, orphan_procs_df) where orphan_procs_df contains
        procedures whose MPOG_Case_ID has no matching entry in case_df (e.g.,
        standalone labor epidurals, peripheral nerve catheters).
    """
    # Identify orphan procedures before aggregation
    orphan_procs = pd.DataFrame(columns=proc_df.columns if not proc_df.empty else [])
    if not proc_df.empty:
        case_ids = set(case_df["MPOG_Case_ID"])
        orphan_mask = ~proc_df["MPOG_Case_ID"].isin(case_ids)
        orphan_procs = proc_df[orphan_mask].copy().reset_index(drop=True)
        if not orphan_procs.empty:
            logger.info(
                "Found %d orphan procedure(s) with no matching case", len(orphan_procs)
            )

    # Group procedures by case ID and aggregate
    if not proc_df.empty:
        proc_agg = (
            proc_df.groupby("MPOG_Case_ID")
            .apply(_select_primary_technique)
            .reset_index()
        )
    else:
        proc_agg = pd.DataFrame(columns=["MPOG_Case_ID", "Airway_Type"])

    # Left join cases to aggregated procedures
    result = case_df.merge(proc_agg, on="MPOG_Case_ID", how="left")

    logger.info(
        "Joined %d cases with procedures (%d cases without procedures)",
        len(result),
        result["Airway_Type"].isna().sum(),
    )

    return result, orphan_procs


def _clean_attending_names(value: str) -> str:
    """
    Clean attending names by removing timestamps.

    Args:
        value: Raw attending string like "DOE, JOHN@2023-01-01 08:00:00"

    Returns:
        Cleaned string with timestamps removed
    """
    if pd.isna(value):
        return ""

    # Split on semicolon for multiple attendings, take only the first
    first_part = str(value).split(";")[0]

    # Remove timestamp portion (everything after @)
    return first_part.split("@")[0].strip()


def map_csv_to_standard_columns(csv_df: DataFrame, column_map: ColumnMap) -> DataFrame:
    """
    Map CSV v2 columns to standard ColumnMap field names.

    Args:
        csv_df: DataFrame from CSV v2 with joined case/procedure data
        column_map: Target column mapping

    Returns:
        DataFrame with renamed columns matching ColumnMap
    """
    result = csv_df.copy()

    # Create mapping from CSV columns to standard columns
    rename_map = {
        "MPOG_Case_ID": column_map.episode_id,
        "AIMS_Scheduled_DT": column_map.date,
        "AIMS_Patient_Age_Years": column_map.age,
        "ASA_Status": column_map.asa,
        "AIMS_Actual_Procedure_Text": column_map.procedure,
        "Airway_Type": column_map.final_anesthesia_type,
    }

    # Rename columns
    result = result.rename(columns=rename_map)

    # Clean and map attending names
    if "AnesAttendings" in csv_df.columns:
        result[column_map.anesthesiologist] = csv_df["AnesAttendings"].apply(
            _clean_attending_names
        )

    # CSV v2 airway values carry both anesthesia signal and airway technique hints.
    # Populate procedure notes so airway extraction can run through the normal flow.
    if "Airway_Type" in csv_df.columns:
        result[column_map.procedure_notes] = csv_df["Airway_Type"]

    # CSV v2 doesn't have Services column - will derive from procedure text
    # Add empty services column for compatibility
    result[column_map.services] = ""

    logger.info("Mapped CSV columns to standard format")

    return result


def map_orphan_procedures(orphan_df: DataFrame, column_map: ColumnMap) -> DataFrame:
    """
    Map orphan procedure rows to standard column format.

    Orphan procedures are ProcedureList entries whose MPOG_Case_ID has no
    matching case in the CaseList (e.g., standalone labor epidurals, peripheral
    nerve catheters). They carry only MPOG_Case_ID and ProcedureName.

    Args:
        orphan_df: DataFrame of orphan procedure rows
        column_map: Target column mapping

    Returns:
        DataFrame with standard column names, suitable for CaseProcessor.
    """
    result = pd.DataFrame(index=orphan_df.index)
    result[column_map.episode_id] = orphan_df.get("MPOG_Case_ID")
    result[column_map.procedure] = orphan_df.get("ProcedureName")
    # Use ProcedureName as anesthesia type hint (e.g. "Epidural", "Labor Epidural")
    result[column_map.final_anesthesia_type] = orphan_df.get("ProcedureName")
    # Also as procedure notes so airway/vascular extraction can inspect it
    result[column_map.procedure_notes] = orphan_df.get("ProcedureName")
    # Fill remaining required columns with NA
    for col in [
        column_map.date,
        column_map.age,
        column_map.asa,
        column_map.anesthesiologist,
        column_map.services,
        column_map.emergent,
    ]:
        result[col] = pd.NA
    return result.reset_index(drop=True)


def read_csv_v2(
    directory: Path, add_source: bool = False, column_map: ColumnMap | None = None
) -> tuple[DataFrame, DataFrame]:
    """
    Read and join CSV v2 format files.

    Args:
        directory: Directory containing CaseList and ProcedureList CSV files
        add_source: If True, add 'Source File' column with file prefix
        column_map: Target column mapping (default: standard ColumnMap)

    Returns:
        Tuple of (main_df, orphan_df) where orphan_df contains standalone
        procedures (e.g., labor epidurals, peripheral nerve catheters) that
        have no matching case in the CaseList. orphan_df is empty if none found.
    """
    directory = Path(directory)
    column_map = column_map or ColumnMap()

    # Discover CSV pairs
    pairs = discover_csv_pairs(directory)

    # Read and join each pair
    all_dfs = []
    all_orphan_dfs = []
    for case_file, proc_file in pairs:
        logger.info("Reading pair: %s, %s", case_file.name, proc_file.name)

        # Read CSVs
        case_df = pd.read_csv(case_file)
        proc_df = pd.read_csv(proc_file)

        # Join
        joined, orphan_procs = join_case_and_procedures(case_df, proc_df)

        prefix = case_file.name.replace(".CaseList.csv", "")

        # Add source column if requested (before mapping)
        if add_source:
            joined["Source File"] = prefix
            if not orphan_procs.empty:
                orphan_procs = orphan_procs.copy()
                orphan_procs["Source File"] = prefix

        all_dfs.append(joined)
        if not orphan_procs.empty:
            all_orphan_dfs.append(orphan_procs)

    # Combine all pairs
    combined = pd.concat(all_dfs, ignore_index=True)

    # Map to standard columns
    result = map_csv_to_standard_columns(combined, column_map)

    # Preserve source column if added
    if add_source and "Source File" in combined.columns:
        result["Source File"] = combined["Source File"]

    logger.info("Read total of %d cases from %d file pair(s)", len(result), len(pairs))

    # Combine and map orphan procedures
    if all_orphan_dfs:
        orphan_combined = pd.concat(all_orphan_dfs, ignore_index=True)
        orphan_result = map_orphan_procedures(orphan_combined, column_map)
        if add_source and "Source File" in orphan_combined.columns:
            orphan_result["Source File"] = orphan_combined["Source File"].values
        logger.info("Found %d total orphan procedure(s)", len(orphan_result))
    else:
        orphan_result = pd.DataFrame()

    return result, orphan_result
