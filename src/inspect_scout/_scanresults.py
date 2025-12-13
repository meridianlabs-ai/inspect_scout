import json
from typing import Any, Literal

import pandas as pd
from inspect_ai._util._async import run_coroutine
from inspect_ai._util.json import to_json_str_safe
from upath import UPath

from ._recorder.factory import scan_recorder_type_for_location
from ._recorder.file import LazyScannerMapping, _cast_value_column
from ._recorder.recorder import (
    ScanResultsArrow,
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


def scan_results_arrow(
    scan_location: str,
) -> ScanResultsArrow:
    """Scan results as Arrow.

    Args:
        scan_location: Location of scan (e.g. directory or s3 bucket).

    Returns:
        ScanResultsArrow: Results as Arrow record batches.
    """
    return run_coroutine(scan_results_arrow_async(scan_location))


async def scan_results_arrow_async(scan_location: str) -> ScanResultsArrow:
    """Scan results as Arrow.

    Args:
        scan_location: Location of scan (e.g. directory or s3 bucket).

    Returns:
        ScanResultsArrow: Results as Arrow record batches.
    """
    recorder = scan_recorder_type_for_location(scan_location)
    return await recorder.results_arrow(scan_location)


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
    results = await recorder.results_df(scan_location, scanner=scanner)

    # Apply expansion lazily when in "results" mode
    if rows == "results":
        scanners = LazyScannerMapping(
            scanner_names=list(results.scanners.keys()),
            loader=lambda name: results.scanners[name],
            transformer=_expand_resultset_rows,
        )
        return ScanResultsDF(
            status=results.complete,
            spec=results.spec,
            location=results.location,
            summary=results.summary,
            errors=results.errors,
            scanners=scanners,
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


def _handle_label_validation(
    expanded: pd.DataFrame, resultset_rows: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Handle label-based validation for expanded resultset rows.

    This function:
    1. Propagates per-label validation results to individual expanded rows
    2. Creates synthetic rows for missing labels (where expected value is negative)

    Args:
        expanded: DataFrame of expanded result rows
        resultset_rows: Original resultset rows before expansion

    Returns:
        Tuple of (expanded DataFrame with validation, synthetic rows DataFrame)
    """
    # Check if we have validation columns
    if (
        "validation_target" not in expanded.columns
        or "validation_result" not in expanded.columns
    ):
        return expanded, pd.DataFrame()

    # Check if validation is label-based (both target and result should be JSON dicts)
    # Get a sample validation_target to check
    sample_target = (
        expanded["validation_target"].iloc[0] if not expanded.empty else None
    )
    if sample_target is None or not isinstance(sample_target, str):
        return expanded, pd.DataFrame()

    # Try to parse as JSON dict
    try:
        parsed_target = json.loads(sample_target)
        if not isinstance(parsed_target, dict):
            # Not label-based validation
            return expanded, pd.DataFrame()
    except (json.JSONDecodeError, TypeError):
        return expanded, pd.DataFrame()

    # Parse validation results (should also be a dict)
    sample_result = (
        expanded["validation_result"].iloc[0] if not expanded.empty else None
    )
    try:
        parsed_results = (
            json.loads(sample_result)
            if isinstance(sample_result, str)
            else sample_result
        )
        if not isinstance(parsed_results, dict):
            return expanded, pd.DataFrame()
    except (json.JSONDecodeError, TypeError):
        return expanded, pd.DataFrame()

    # This is label-based validation! Propagate per-label results
    def assign_label_validation(row: pd.Series) -> pd.Series:
        """Assign validation result based on the row's label."""
        label = row.get("label")
        if pd.isna(label):
            return row

        # Parse validation results for this row
        val_result_str = row.get("validation_result")
        if pd.isna(val_result_str):
            return row

        try:
            val_results_dict = (
                json.loads(val_result_str)
                if isinstance(val_result_str, str)
                else val_result_str
            )
            if isinstance(val_results_dict, dict) and label in val_results_dict:
                # Replace overall validation_result with this label's specific result
                row["validation_result"] = val_results_dict[label]
        except (json.JSONDecodeError, TypeError, KeyError):
            pass

        return row

    expanded = expanded.apply(assign_label_validation, axis=1)

    # Create synthetic rows for missing labels
    # Get all labels present in expanded rows
    present_labels = set(expanded["label"].dropna().unique())

    # Get expected labels from validation_target
    expected_labels = set(parsed_target.keys())

    # Missing labels = expected but not present
    missing_labels = expected_labels - present_labels

    # Create synthetic rows for missing labels with negative expected values
    synthetic_rows_list = []
    for label in missing_labels:
        expected_value = parsed_target[label]
        # Only create synthetic row if expected value is negative
        negative_values = (False, None, "NONE", "none", 0, "")
        if expected_value not in negative_values:
            continue

        # Get a template row from the first resultset row
        if resultset_rows.empty:
            continue
        template_row = resultset_rows.iloc[0].copy()

        # Set result-specific fields for the synthetic row
        template_row["label"] = label
        template_row["value"] = expected_value
        template_row["value_type"] = (
            "boolean" if isinstance(expected_value, bool) else "null"
        )
        template_row["answer"] = None
        template_row["explanation"] = None
        template_row["metadata"] = json.dumps({})
        template_row["message_references"] = "[]"
        template_row["event_references"] = "[]"
        template_row["uuid"] = None  # Will be assigned by system if needed

        # Set validation result for this synthetic row
        template_row["validation_result"] = parsed_results.get(label, None)

        template_row["scan_error"] = None
        template_row["scan_error_traceback"] = None
        template_row["scan_error_type"] = None

        # NULL out scan execution fields
        template_row["scan_total_tokens"] = None
        template_row["scan_model_usage"] = None

        synthetic_rows_list.append(template_row)

    synthetic_rows = (
        pd.DataFrame(synthetic_rows_list) if synthetic_rows_list else pd.DataFrame()
    )

    return expanded, synthetic_rows


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
    # Use max_level=1 to prevent deep flattening of nested structures within value
    result_fields = pd.json_normalize(expanded["value"].tolist(), max_level=1)

    # Handle case where value field is an object/dict that got flattened
    # Even with max_level=1, pd.json_normalize flattens first-level dicts,
    # creating columns like value.confidence, value.message_numbers
    # We need to reconstruct the value column from these flattened columns
    value_cols = [col for col in result_fields.columns if col.startswith("value.")]
    if value_cols and "value" not in result_fields.columns:
        # Reconstruct value column as a dict from the flattened columns
        def reconstruct_value(row: pd.Series) -> dict[str, Any]:
            """Reconstruct the value dict from flattened value.* columns."""
            value_dict = {}
            for col in value_cols:
                # Remove 'value.' prefix to get the field name
                field_name = col.replace("value.", "")
                val = row[col]
                # Only include non-NA values (handles mixed schemas)
                if not (isinstance(val, float) and pd.isna(val)):
                    value_dict[field_name] = val
            return value_dict

        result_fields["value"] = result_fields.apply(reconstruct_value, axis=1)
        # Drop the flattened columns now that we've reconstructed value
        result_fields = result_fields.drop(columns=value_cols)

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

    # Handle label-based validation: propagate per-label results and add synthetic rows
    expanded, synthetic_rows = _handle_label_validation(expanded, resultset_rows)

    # Combine with other rows (including synthetic rows)
    # Filter out empty DataFrames
    all_rows = [df for df in [other_rows, expanded, synthetic_rows] if not df.empty]

    if not all_rows:
        # All dataframes are empty, return an empty dataframe with the right structure
        return pd.DataFrame()

    if len(all_rows) == 1:
        # Only one dataframe, no concatenation needed
        return all_rows[0].reset_index(drop=True)

    # To avoid FutureWarning about all-NA columns affecting dtype inference:
    # The warning occurs when some DataFrames have all-NA values in a column while
    # others have actual values. We need to ensure dtype consistency by inferring
    # the dtype from DataFrames that have values, then explicitly setting that dtype
    # in DataFrames where the column is all-NA.

    # Get union of all columns
    all_columns = list(set().union(*[set(df.columns) for df in all_rows]))

    # For each column, determine the appropriate dtype from non-NA values
    column_dtypes: dict[str, Any] = {}
    for col in all_columns:
        # Find a DataFrame where this column has non-NA values
        for df in all_rows:
            if col in df.columns and df[col].notna().any():
                column_dtypes[col] = df[col].dtype
                break
        # If column is all-NA everywhere, use object dtype
        if col not in column_dtypes:
            column_dtypes[col] = pd.Series(dtype="object").dtype

    # Align all DataFrames to have the same columns with consistent dtypes
    aligned_rows = []
    for df in all_rows:
        df_aligned = df.copy()
        # Add missing columns with the appropriate dtype
        for col in all_columns:
            if col not in df_aligned.columns:
                # Add column with correct dtype
                df_aligned[col] = pd.Series(dtype=column_dtypes[col])
            elif df_aligned[col].isna().all() and col in column_dtypes:
                # Column exists but is all-NA - ensure it has the right dtype
                df_aligned[col] = df_aligned[col].astype(column_dtypes[col])

        aligned_rows.append(df_aligned)

    result_df = pd.concat(aligned_rows, ignore_index=True)

    return result_df
