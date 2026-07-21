import json
from typing import Any, Literal

import pandas as pd
from inspect_ai._util._async import run_coroutine
from inspect_ai._util.json import to_json_str_safe
from inspect_ai.log import expand_events
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
    exclude_columns: list[str] | None = None,
) -> ScanResultsDF:
    """Scan results as Pandas data frames.

    Args:
        scan_location: Location of scan (e.g. directory or s3 bucket).
        scanner: Scanner name (defaults to all scanners).
        rows: Row granularity. Specify "results" to yield a row for each scanner result
            (potentially multiple per transcript); Specify "transcript" to yield a row
            for each transcript (in which case multiple results will be packed
            into the `value` field as a JSON list of `Result`).
        exclude_columns: List of column names to exclude when reading parquet files.
            Useful for reducing memory usage by skipping large unused columns.

    Returns:
         ScanResults: Results as pandas data frames.
    """
    return run_coroutine(
        scan_results_df_async(
            scan_location, scanner=scanner, rows=rows, exclude_columns=exclude_columns
        )
    )


async def scan_results_df_async(
    scan_location: str,
    *,
    scanner: str | None = None,
    rows: Literal["results", "transcripts"] = "results",
    exclude_columns: list[str] | None = None,
) -> ScanResultsDF:
    """Scan results as Pandas data frames.

    Args:
        scan_location: Location of scan (e.g. directory or s3 bucket).
        scanner: Scanner name (defaults to all scanners).
        rows: Row granularity. Specify "results" to yield a row for each scanner result
            (potentially multiple per transcript); Specify "transcript" to yield a row
            for each transcript (in which case multiple results will be packed
            into the `value` field as a JSON list of `Result`).
        exclude_columns: List of column names to exclude when reading parquet files.
            Useful for reducing memory usage by skipping large unused columns.

    Returns:
         ScanResults: Results as Pandas data frames.
    """
    recorder = scan_recorder_type_for_location(scan_location)
    results = await recorder.results_df(
        scan_location, scanner=scanner, exclude_columns=exclude_columns
    )

    # Always expand condensed event refs (storage optimization, not consumer-visible)
    if rows == "results":
        transformer = lambda df: _expand_resultset_rows(_expand_events_in_df(df))  # noqa: E731
    else:
        transformer = _expand_events_in_df

    scanners = LazyScannerMapping(
        scanner_names=list(results.scanners.keys()),
        loader=lambda name: results.scanners[name],
        transformer=transformer,
    )
    return ScanResultsDF(
        complete=results.complete,
        spec=results.spec,
        location=results.location,
        summary=results.summary,
        errors=results.errors,
        scanners=scanners,
    )


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


_RESULTSET_INDEX = "_resultset_index"
"""Temporary column tying expanded rows back to their originating resultset row."""


def _parse_json_dict(value: Any) -> dict[str, Any] | None:
    """Parse a value as a JSON object, returning None if it isn't one."""
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


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
        "validation_target" not in resultset_rows.columns
        or "validation_result" not in resultset_rows.columns
    ):
        return expanded, pd.DataFrame()

    # Propagate per-label results to rows whose own validation is label-based
    # (i.e. their validation_target is a JSON dict keyed by label). Only the
    # validation_result column is modified (a whole-row apply would let pandas
    # re-infer dtypes of untouched columns, e.g. object -> bool).
    def assign_label_validation(row: "pd.Series[Any]") -> Any:
        """Validation result for this row based on its label."""
        result = row["validation_result"]
        label = row.get("label")
        if pd.isna(label):
            return result

        if _parse_json_dict(row.get("validation_target")) is None:
            return result

        val_results_dict = _parse_json_dict(result)
        if val_results_dict is not None and label in val_results_dict:
            # Replace overall validation_result with this label's specific result
            return val_results_dict[label]

        return result

    if not expanded.empty:
        expanded["validation_result"] = expanded.apply(assign_label_validation, axis=1)

    # Labels present in each resultset row's own expansion
    present_labels: dict[Any, set[str]] = {}
    if not expanded.empty and "label" in expanded.columns:
        for resultset_index, labels in expanded.groupby(_RESULTSET_INDEX)["label"]:
            present_labels[resultset_index] = set(labels.dropna().unique())

    # Create synthetic rows for each resultset row's missing labels with
    # negative expected values
    synthetic_rows_list: list["pd.Series[Any]"] = []
    for _, resultset_row in resultset_rows.iterrows():
        parsed_target = _parse_json_dict(resultset_row.get("validation_target"))
        if parsed_target is None:
            # Not label-based validation for this row
            continue
        parsed_results = _parse_json_dict(resultset_row.get("validation_result"))
        if parsed_results is None:
            # Label validation always stores a dict result at scan time; if
            # it's absent (e.g. the scan errored), don't synthesize rows for
            # verdicts that were never computed
            continue

        present = present_labels.get(resultset_row[_RESULTSET_INDEX], set())
        missing_labels = set(parsed_target.keys()) - present

        for label in sorted(missing_labels):
            expected_value = parsed_target[label]
            # Only create synthetic row if expected value is negative
            negative_values = (False, None, "NONE", "none", 0, "")
            if expected_value not in negative_values:
                continue

            # Template the synthetic row on this row (its own transcript/case)
            template_row = resultset_row.copy()

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
            # Note: validation_target, validation_predicate, validation_split
            # are preserved from template_row (same for all results from the
            # same case)

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


def _expand_events_in_df(df: pd.DataFrame) -> pd.DataFrame:
    """Expand condensed event refs in the input column, then drop input_data."""
    if (
        "input" not in df.columns
        or "input_data" not in df.columns
        or df["input_data"].isna().all()
    ):
        return df.drop(columns=["input_data"], errors="ignore")

    df = df.copy()
    mask = df["input_data"].notna()

    for idx in df.index[mask]:
        input_json = str(df.at[idx, "input"])
        input_data_json = str(df.at[idx, "input_data"])
        input_type = str(df.at[idx, "input_type"])

        if input_type == "transcript":
            transcript = json.loads(input_json)
            events_json = json.dumps(transcript.get("events", []))
            expanded = expand_events(events_json, input_data_json)
            transcript["events"] = [e.model_dump() for e in expanded]
            df.at[idx, "input"] = json.dumps(transcript)
        elif input_type == "events":
            expanded = expand_events(input_json, input_data_json)
            df.at[idx, "input"] = json.dumps([e.model_dump() for e in expanded])

    return df.drop(columns=["input_data"])


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

    # Tag each resultset row so expanded rows can be tied back to it (label
    # validation is scoped per resultset row)
    resultset_rows[_RESULTSET_INDEX] = range(len(resultset_rows))

    # Parse JSON strings in value column to lists
    resultset_rows["value"] = resultset_rows["value"].apply(
        lambda x: json.loads(x) if isinstance(x, str) and x else []
    )

    # Explode the value column to create one row per Result
    expanded = resultset_rows.explode("value", ignore_index=True)

    # Filter out any empty results (from empty resultsets)
    expanded = expanded[expanded["value"].notna()]

    if expanded.empty:
        # No actual results to expand, but synthetic missing-label rows may
        # still apply (e.g. empty resultsets with negative label expectations)
        _, synthetic_rows = _handle_label_validation(expanded, resultset_rows)
        if synthetic_rows.empty:
            return other_rows.reset_index(drop=True)
        synthetic_rows = synthetic_rows.drop(columns=[_RESULTSET_INDEX])
        return _concat_aligned([other_rows, synthetic_rows])

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
        lambda x: (
            json.dumps(x)
            if isinstance(x, dict)
            else (json.dumps({}) if pd.isna(x) else x)
        )
    )

    # Handle references: split by type into message_references and event_references
    if "references" in expanded.columns:
        # Filter references by type (matching ResultReport.to_df_columns logic)
        expanded["message_references"] = expanded["references"].apply(
            lambda refs: (
                to_json_str_safe(
                    [
                        r
                        for r in refs
                        if isinstance(r, dict) and r.get("type") == "message"
                    ]
                )
                if isinstance(refs, list)
                else "[]"
            )
        )
        expanded["event_references"] = expanded["references"].apply(
            lambda refs: (
                to_json_str_safe(
                    [
                        r
                        for r in refs
                        if isinstance(r, dict) and r.get("type") == "event"
                    ]
                )
                if isinstance(refs, list)
                else "[]"
            )
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

    # Drop the resultset index now that label validation is done
    expanded = expanded.drop(columns=[_RESULTSET_INDEX])
    if not synthetic_rows.empty:
        synthetic_rows = synthetic_rows.drop(columns=[_RESULTSET_INDEX])

    # Combine with other rows (including synthetic rows)
    return _concat_aligned([other_rows, expanded, synthetic_rows])


def _concat_aligned(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Concatenate DataFrames after aligning columns and dtypes."""
    # Filter out empty DataFrames
    all_rows = [df for df in frames if not df.empty]

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
                # All-NA pyarrow column → non-nullable numpy numeric fails on
                # int(pd.NA); fall back to object so concat can handle it.
                try:
                    df_aligned[col] = df_aligned[col].astype(column_dtypes[col])
                except (TypeError, ValueError):
                    df_aligned[col] = df_aligned[col].astype(object)

        aligned_rows.append(df_aligned)

    result_df = pd.concat(aligned_rows, ignore_index=True)

    return result_df
