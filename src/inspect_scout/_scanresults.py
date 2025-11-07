import json
from typing import Literal

import pandas as pd
from inspect_ai._util._async import run_coroutine
from inspect_ai._util.json import to_json_str_safe
from upath import UPath

from ._recorder.factory import scan_recorder_type_for_location
from ._recorder.file import _cast_value_column
from ._recorder.recorder import (
    ScanResultsDB,
    ScanResultsDF,
    Status,
)


def scan_status(scan_location: str) -> Status:
    """Status of scan.

    Args:
        scan_location: Location to get status for (e.g. directory or s3 bucket)

    Returns:
        ScanStatus: Status of scan (spec, summary, errors, etc.)
    """
    return run_coroutine(scan_status_async(scan_location))


async def scan_status_async(scan_location: str) -> Status:
    """Status of scan.

    Args:
        scan_location: Location to get status for (e.g. directory or s3 bucket)

    Returns:
        ScanStatus: Status of scan (spec, summary, errors, etc.)
    """
    recorder = scan_recorder_type_for_location(scan_location)
    return await recorder.status(scan_location)


def scan_results_df(
    scan_location: str,
    *,
    scanner: str | None = None,
    rows: Literal["results", "transcripts"] = "results",
) -> ScanResultsDF:
    """Scan results as Pandas data frames.

    Args:
        scan_location: Location of scan (e.g. directory or s3 bucket).
        scanner: Scanner name (defaults to all scanners).
        rows: Row granularity. Specify "results" to yield a row for each scanner result
            (potentially multiple per transcript); Specify "transcript" to yield a row
            for each transcript (in which case multiple results will be packed
            into the `value` field as a JSON list of `Result`).

    Returns:
         ScanResults: Results as pandas data frames.
    """
    return run_coroutine(
        scan_results_df_async(scan_location, scanner=scanner, rows=rows)
    )


async def scan_results_df_async(
    scan_location: str,
    *,
    scanner: str | None = None,
    rows: Literal["results", "transcripts"] = "results",
) -> ScanResultsDF:
    """Scan results as Pandas data frames.

    Args:
        scan_location: Location of scan (e.g. directory or s3 bucket).
        scanner: Scanner name (defaults to all scanners).
        rows: Row granularity. Specify "results" to yield a row for each scanner result
            (potentially multiple per transcript); Specify "transcript" to yield a row
            for each transcript (in which case multiple results will be packed
            into the `value` field as a JSON list of `Result`).

    Returns:
         ScanResults: Results as Pandas data frames.
    """
    recorder = scan_recorder_type_for_location(scan_location)
    results = await recorder.results(scan_location, scanner=scanner)

    # Expand resultset rows when in "results" mode
    if rows == "results":
        for scanner_name in results.scanners:
            results.scanners[scanner_name] = _expand_resultset_rows(
                results.scanners[scanner_name]
            )

    return results


def scan_results_db(
    scan_location: str,
    *,
    rows: Literal["results", "transcripts"] = "results",
) -> ScanResultsDB:
    """Scan results as DuckDB database.

    Args:
        scan_location: Location of scan (e.g. directory or s3 bucket).
        rows: Row granularity. Specify "results" to yield a row for each scanner result
            (potentially multiple per transcript); Specify "transcript" to yield a row
            for each transcript (in which case multiple results (if any) will be packed
            into the `value` field as a JSON list of `Result`).

    Returns:
        ScanResultsDB: Results as DuckDB database.
    """
    return run_coroutine(scan_results_db_async(scan_location, rows=rows))


async def scan_results_db_async(
    scan_location: str,
    *,
    rows: Literal["results", "transcripts"] = "results",
) -> ScanResultsDB:
    """Scan results as DuckDB database.

    Args:
        scan_location: Location of scan (e.g. directory or s3 bucket).
        rows: Row granularity. Specify "results" to yield a row for each scanner result
            (potentially multiple per transcript); Specify "transcript" to yield a row
            for each transcript (in which case multiple results (if any) will be packed
            into the `value` field as a JSON list of `Result`).

    Returns:
        ScanResultsDB: Results as DuckDB database.
    """
    recorder = scan_recorder_type_for_location(scan_location)
    return await recorder.results_db(scan_location, rows=rows)


def remove_scan_results(scan_location: str) -> None:
    scan_path = UPath(scan_location)
    if scan_path.exists():
        scan_path.rmdir(recursive=True)


def _expand_resultset_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Expand rows where value_type == "resultset" into multiple rows.

    For rows with value_type == "resultset", the value field contains a JSON-encoded
    list of Result objects. This function:
    1. Parses the JSON value into a list
    2. Explodes each list element into its own row
    3. Normalizes the Result fields into columns (uuid, label, value, etc.)
    4. Applies type casting to the expanded value column

    Args:
        df: DataFrame potentially containing resultset rows

    Returns:
        DataFrame with resultset rows expanded
    """
    # Check if we have any resultset rows
    if "value_type" not in df.columns or df.empty:
        return df

    has_resultsets = (df["value_type"] == "resultset").any()
    if not has_resultsets:
        return df

    # Split into resultset and non-resultset rows
    resultset_mask = df["value_type"] == "resultset"
    resultset_rows = df[resultset_mask].copy()
    other_rows = df[~resultset_mask].copy()

    # Parse JSON strings in value column to lists
    resultset_rows["value"] = resultset_rows["value"].apply(
        lambda x: json.loads(x) if isinstance(x, str) and x else []
    )

    # Explode the value column to create one row per Result
    expanded = resultset_rows.explode("value", ignore_index=True)

    # Filter out any empty results (from empty resultsets)
    expanded = expanded[expanded["value"].notna()]

    if expanded.empty:
        # No actual results to expand, just return other rows
        return other_rows.reset_index(drop=True)

    # Normalize the Result objects into columns
    # Each Result has: uuid, label, value, type, answer, explanation, metadata
    result_fields = pd.json_normalize(expanded["value"].tolist())

    # Drop the old result-related columns from expanded dataframe
    columns_to_drop = [
        "uuid",
        "label",
        "value",
        "value_type",
        "answer",
        "explanation",
        "metadata",
    ]
    for col in columns_to_drop:
        if col in expanded.columns:
            expanded = expanded.drop(columns=[col])

    # Combine the preserved columns with the normalized result fields
    expanded = pd.concat([expanded.reset_index(drop=True), result_fields], axis=1)

    # Rename 'type' column from Result to 'value_type' and handle missing types
    if "type" in expanded.columns:
        expanded = expanded.rename(columns={"type": "value_type"})

    # Ensure value_type column exists and infer types for missing values
    if "value_type" not in expanded.columns:
        expanded["value_type"] = None

    # Infer value_type from value when not specified
    def infer_value_type(row: pd.Series) -> str:
        vtype = row.get("value_type")
        if pd.notna(vtype):
            return str(vtype)
        value = row.get("value")
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, (int, float)):
            return "number"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        else:
            return "null"

    expanded["value_type"] = expanded.apply(infer_value_type, axis=1)

    # Handle metadata: convert to JSON string and handle None values
    if "metadata" not in expanded.columns:
        expanded["metadata"] = None

    expanded["metadata"] = expanded["metadata"].apply(
        lambda x: json.dumps(x)
        if isinstance(x, dict)
        else (json.dumps({}) if pd.isna(x) else x)
    )

    # Handle references: split by type into message_references and event_references
    if "references" in expanded.columns:
        # Filter references by type (matching ResultReport.to_df_columns logic)
        expanded["message_references"] = expanded["references"].apply(
            lambda refs: to_json_str_safe(
                [r for r in refs if isinstance(r, dict) and r.get("type") == "message"]
            )
            if isinstance(refs, list)
            else "[]"
        )
        expanded["event_references"] = expanded["references"].apply(
            lambda refs: to_json_str_safe(
                [r for r in refs if isinstance(r, dict) and r.get("type") == "event"]
            )
            if isinstance(refs, list)
            else "[]"
        )
        # Drop the references column as it's been split
        expanded = expanded.drop(columns=["references"])
    else:
        # No references field, set both to empty arrays
        expanded["message_references"] = "[]"
        expanded["event_references"] = "[]"

    # Apply type casting to the value column based on value_type
    expanded = _cast_value_column(expanded)

    # NULL out scan execution fields to avoid incorrect aggregation
    # (these represent the scan execution, not individual results)
    if "scan_total_tokens" in expanded.columns:
        expanded["scan_total_tokens"] = None
    if "scan_model_usage" in expanded.columns:
        expanded["scan_model_usage"] = None

    # Combine with other rows
    result_df = pd.concat([other_rows, expanded], ignore_index=True)

    return result_df
