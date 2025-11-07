import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from .predicates import ValidationPredicate
from .types import ValidationCase, ValidationSet


def validation_set(
    cases: str | Path | pd.DataFrame,
    predicate: ValidationPredicate | None = "eq",
) -> ValidationSet:
    """Create a validation set by reading cases from a file or data frame.

    Args:
        cases: Path to a CSV, YAML, JSON, or JSONL file with validation cases, or data frame with validation cases.
        predicate: Predicate for comparing scanner results to validation targets (defaults to equality comparison).
            For single-value targets, compares value to target directly.
            For dict targets, string/single-value predicates are applied to each key,
            while multi-value predicates receive the full dicts.
    """
    # Load data into DataFrame if not already one
    if isinstance(cases, pd.DataFrame):
        df = cases
    else:
        df = _load_file(cases)

    # Validate required columns
    if "id" not in df.columns:
        raise ValueError("Validation data must contain an 'id' column")

    # Parse id column to handle arrays
    df["id"] = df["id"].apply(_parse_id)

    # Detect and process target/label columns
    target_cols = [col for col in df.columns if col.startswith("target_")]
    label_cols = [col for col in df.columns if col.startswith("label_")]

    if label_cols:
        # Multiple label_* columns - create label-based validation for resultsets
        validate_cases = _create_cases_with_labels(df, label_cols)
    elif target_cols:
        # Multiple target_* columns - create dict targets
        validate_cases = _create_cases_with_dict_target(df, target_cols)
    elif "target" in df.columns:
        # Single target column
        validate_cases = _create_cases_with_single_target(df)
    else:
        raise ValueError(
            "Validation data must contain either a 'target' column, 'target_*' columns, or 'label_*' columns"
        )

    return ValidationSet(cases=validate_cases, predicate=predicate)


def _load_file(file: str | Path) -> pd.DataFrame:
    """Load a file into a DataFrame based on its extension."""
    path = Path(file) if isinstance(file, str) else file
    suffix = str(path.suffix).lower()

    if suffix == ".csv":
        # Use automatic type detection (pandas default)
        df = pd.read_csv(path)

        # Auto-detect headerless 2-column CSV
        # If we have exactly 2 columns and no "id" column, check if first row looks like data
        if len(df.columns) == 2 and "id" not in df.columns:
            # Check if the column names look like header names or data
            col_names = df.columns.tolist()
            # If columns are like ['name', 'target'] or other meaningful names, keep headers
            # If they look like data values, treat as headerless
            if not any(
                name.lower() in ["id", "target", "name", "value", "key"]
                or name.startswith("target_")
                or name.startswith("label_")
                for name in col_names
            ):
                df = pd.read_csv(path, header=None, names=["id", "target"])

        # Convert string booleans and fix integer types
        df = _convert_csv_types(df)

        return df
    elif suffix == ".json":
        # Try to read as JSON array first
        try:
            with open(path, "r") as f:
                data = json.load(f)
            # Preprocess to flatten labels: {...} into label_* columns
            data = _flatten_labels_in_data(data)
            return pd.DataFrame(data)
        except Exception:
            # Fall back to pandas JSON reader
            return pd.read_json(path)
    elif suffix == ".jsonl":
        # Read JSONL manually to preserve types better
        with open(path, "r") as f:
            data = [json.loads(line) for line in f if line.strip()]
        # Preprocess to flatten labels: {...} into label_* columns
        data = _flatten_labels_in_data(data)
        return pd.DataFrame(data)
    elif suffix in [".yaml", ".yml"]:
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        # Preprocess to flatten labels: {...} into label_* columns
        data = _flatten_labels_in_data(data)
        return pd.DataFrame(data)
    else:
        raise ValueError(
            f"Unsupported file format: {suffix}. Supported formats: .csv, .json, .jsonl, .yaml, .yml"
        )


def _convert_csv_types(df: pd.DataFrame) -> pd.DataFrame:
    """Convert CSV string types to appropriate Python types."""

    def convert_value(val: Any) -> Any:
        """Convert a single value to the appropriate type."""
        # Handle NaN/None
        if pd.isna(val):
            return val

        # Convert boolean strings
        if isinstance(val, str):
            if val in ["true", "True"]:
                return True
            elif val in ["false", "False"]:
                return False

            # Try to convert numeric strings
            try:
                # Try integer first
                if "." not in val:
                    return int(val)
                else:
                    # It's a float
                    float_val = float(val)
                    # Convert to int if it's a whole number
                    if float_val.is_integer():
                        return int(float_val)
                    return float_val
            except (ValueError, AttributeError):
                # Not a numeric string, return as is
                pass

        # Convert floats that are actually integers
        if isinstance(val, float) and val.is_integer():
            return int(val)

        return val

    # Apply conversion to all columns except 'id'
    # Convert values and change dtype to object to preserve mixed types
    for col in df.columns:
        if col == "id":
            continue
        converted_values = [convert_value(val) for val in df[col]]
        # Change dtype to object first to prevent type coercion during assignment
        df[col] = df[col].astype(object)
        df[col] = converted_values

    return df


def _parse_id(id_value: str | list[str]) -> str | list[str]:
    """Parse id value to handle comma-separated and JSON-style arrays."""
    # Already a list
    if isinstance(id_value, list):
        return id_value

    # Convert to string if not already
    id_str = str(id_value)

    # Try to parse as JSON array first (e.g., "[id1,id2]")
    if id_str.strip().startswith("[") and id_str.strip().endswith("]"):
        try:
            parsed = json.loads(id_str)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    # Check for comma-separated values (e.g., "id1,id2")
    if "," in id_str:
        # Split and strip whitespace
        return [x.strip() for x in id_str.split(",")]

    # Single id value
    return id_str


def _flatten_labels_in_data(data: Any) -> Any:
    """Flatten labels: {...} into label_* columns for DataFrame processing.

    Transforms:
        {"id": "123", "labels": {"deception": true, "jailbreak": false}}
    Into:
        {"id": "123", "label_deception": true, "label_jailbreak": false}
    """
    if not isinstance(data, list):
        return data

    flattened = []
    for item in data:
        if not isinstance(item, dict):
            flattened.append(item)
            continue

        # Check if this item has a "labels" field
        if "labels" in item and isinstance(item["labels"], dict):
            # Flatten labels dict into label_* keys
            new_item = {k: v for k, v in item.items() if k != "labels"}
            for label_key, label_value in item["labels"].items():
                new_item[f"label_{label_key}"] = label_value
            flattened.append(new_item)
        else:
            flattened.append(item)

    return flattened


def _create_cases_with_single_target(df: pd.DataFrame) -> list[ValidationCase]:
    """Create ValidationCase objects with a single target column."""
    cases = []
    for _, row in df.iterrows():
        case = ValidationCase(
            id=row["id"],
            target=row["target"],
        )
        cases.append(case)
    return cases


def _create_cases_with_dict_target(
    df: pd.DataFrame, target_cols: list[str]
) -> list[ValidationCase]:
    """Create ValidationCase objects with multiple target_* columns."""
    cases = []
    for _, row in df.iterrows():
        # Build dict from target_* columns, stripping the "target_" prefix
        target_dict = {}
        for col in target_cols:
            key = col[7:]  # Remove "target_" prefix
            target_dict[key] = row[col]

        case = ValidationCase(
            id=row["id"],
            target=target_dict,
        )
        cases.append(case)
    return cases


def _create_cases_with_labels(
    df: pd.DataFrame, label_cols: list[str]
) -> list[ValidationCase]:
    """Create ValidationCase objects with multiple label_* columns for resultset validation."""
    cases = []
    for _, row in df.iterrows():
        # Build dict from label_* columns, stripping the "label_" prefix
        labels_dict = {}
        for col in label_cols:
            key = col[6:]  # Remove "label_" prefix
            labels_dict[key] = row[col]

        case = ValidationCase(
            id=row["id"],
            labels=labels_dict,
        )
        cases.append(case)
    return cases
