"""Read and write validation files preserving format."""

import json
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import yaml

from .types import ValidationCase
from .validation import (
    _convert_csv_types,
    _flatten_labels_in_data,
    _flatten_splits_in_data,
)

FileFormat = Literal["csv", "yaml", "json", "jsonl"]


def _has_nested_split_format(data: list[Any]) -> bool:
    """Check if data uses nested split format ({split: name, cases: [...]})."""
    if not data or not isinstance(data[0], dict):
        return False
    first_item = data[0]
    return "split" in first_item and "cases" in first_item and "id" not in first_item


def _has_valid_columns(columns: list[str]) -> bool:
    """Check if columns contain required validation file structure."""
    if "id" not in columns:
        return False
    has_target = "target" in columns
    has_target_cols = any(c.startswith("target_") for c in columns)
    has_label_cols = any(c.startswith("label_") for c in columns)
    return has_target or has_target_cols or has_label_cols


def _load_raw_data(
    file_path: Path,
) -> tuple[list[dict[str, Any]], bool, bool]:
    """Load raw data from a validation file.

    Returns:
        Tuple of (flattened cases, has_nested_splits, is_valid).
        is_valid is True if the file has valid validation columns,
        or if the file is empty (for JSON/YAML/JSONL formats).
    """
    suffix = file_path.suffix.lower()

    if suffix == ".csv":
        df = pd.read_csv(file_path)
        df = _convert_csv_types(df)
        columns = list(df.columns)
        # Convert DataFrame to list of dicts, handling NaN
        cases: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            case: dict[str, Any] = {}
            for col in df.columns:
                val = row[col]
                if pd.isna(val):
                    continue
                case[col] = val
            cases.append(case)
        is_valid = _has_valid_columns(columns)
        return cases, False, is_valid

    elif suffix in {".yaml", ".yml"}:
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, list):
            raise ValueError(f"Expected list in {file_path}")
        has_nested = _has_nested_split_format(data)
        data = _flatten_splits_in_data(data)
        data = _flatten_labels_in_data(data)
        if not data:
            return data, has_nested, True
        columns = list(data[0].keys()) if isinstance(data[0], dict) else []
        return data, has_nested, _has_valid_columns(columns)

    elif suffix == ".json":
        with open(file_path, "r") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError(f"Expected list in {file_path}")
        has_nested = _has_nested_split_format(data)
        data = _flatten_splits_in_data(data)
        data = _flatten_labels_in_data(data)
        if not data:
            return data, has_nested, True
        columns = list(data[0].keys()) if isinstance(data[0], dict) else []
        return data, has_nested, _has_valid_columns(columns)

    elif suffix == ".jsonl":
        with open(file_path, "r") as f:
            data = [json.loads(line) for line in f if line.strip()]
        data = _flatten_labels_in_data(data)
        if not data:
            return data, False, True
        columns = list(data[0].keys()) if isinstance(data[0], dict) else []
        return data, False, _has_valid_columns(columns)

    else:
        raise ValueError(f"Unsupported file format: {suffix}")


def _unflatten_labels(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert label_* keys back to nested labels dict."""
    unflattened = []
    for case in cases:
        if not isinstance(case, dict):
            unflattened.append(case)
            continue

        label_cols = {k: v for k, v in case.items() if k.startswith("label_")}
        if label_cols:
            new_case = {k: v for k, v in case.items() if not k.startswith("label_")}
            labels = {k[6:]: v for k, v in label_cols.items()}  # Remove "label_" prefix
            new_case["labels"] = labels
            unflattened.append(new_case)
        else:
            unflattened.append(case)
    return unflattened


def _nest_by_splits(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group cases by split into nested format."""
    splits: dict[str | None, list[dict[str, Any]]] = {}

    for case in cases:
        split = case.get("split")
        case_without_split = {k: v for k, v in case.items() if k != "split"}
        if split not in splits:
            splits[split] = []
        splits[split].append(case_without_split)

    result: list[dict[str, Any]] = []
    for split_name, split_cases in splits.items():
        if split_name is not None:
            result.append({"split": split_name, "cases": split_cases})
        else:
            result.extend(split_cases)

    return result


class ValidationFileWriter:
    """Read and write validation files preserving their format.

    Supports CSV, YAML, JSON, and JSONL formats. For YAML/JSON files, detects
    and preserves the nested split format when present.
    """

    def __init__(self, file_path: Path) -> None:
        """Initialize the writer for an existing file.

        Args:
            file_path: Path to the validation file.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        self.file_path = file_path.resolve()
        if not self.file_path.exists():
            raise FileNotFoundError(f"Validation file not found: {file_path}")

        self._format = self._detect_format()
        self._has_nested_splits = False

    def _detect_format(self) -> FileFormat:
        """Detect the file format from the extension."""
        suffix = self.file_path.suffix.lower()
        if suffix == ".csv":
            return "csv"
        elif suffix in {".yaml", ".yml"}:
            return "yaml"
        elif suffix == ".json":
            return "json"
        elif suffix == ".jsonl":
            return "jsonl"
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

    @property
    def format(self) -> FileFormat:
        """Return the file format."""
        return self._format

    def read_cases(self) -> list[dict[str, Any]]:
        """Read all cases from the validation file.

        Returns:
            List of case dictionaries with flattened structure.
        """
        cases, self._has_nested_splits, _ = _load_raw_data(self.file_path)
        return cases

    def write_cases(
        self, cases: list[dict[str, Any]], nested_splits: bool | None = None
    ) -> None:
        """Write cases to the validation file.

        Args:
            cases: List of case dictionaries to write.
            nested_splits: Whether to use nested split format for YAML/JSON.
                          If None, preserves the original format detected on read.
        """
        use_nested = (
            nested_splits if nested_splits is not None else self._has_nested_splits
        )

        if self._format == "csv":
            self._write_csv(cases)
        elif self._format == "yaml":
            self._write_structured(cases, use_nested, "yaml")
        elif self._format == "json":
            self._write_structured(cases, use_nested, "json")
        elif self._format == "jsonl":
            self._write_jsonl(cases)

    def _write_csv(self, cases: list[dict[str, Any]]) -> None:
        """Write cases to CSV format."""
        if not cases:
            df = pd.DataFrame(columns=["id", "target"])
        else:
            df = pd.DataFrame(cases)

        # Ensure id is the first column
        cols = list(df.columns)
        if "id" in cols:
            cols.remove("id")
            cols = ["id"] + cols
            df = df[cols]

        df.to_csv(self.file_path, index=False)

    def _write_structured(
        self,
        cases: list[dict[str, Any]],
        nested_splits: bool,
        fmt: Literal["yaml", "json"],
    ) -> None:
        """Write cases to YAML or JSON format."""
        data = _unflatten_labels(cases)
        if nested_splits:
            data = _nest_by_splits(data)

        with open(self.file_path, "w") as f:
            if fmt == "yaml":
                yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
            else:
                json.dump(data, f, indent=2)

    def _write_jsonl(self, cases: list[dict[str, Any]]) -> None:
        """Write cases to JSONL format."""
        data = _unflatten_labels(cases)
        with open(self.file_path, "w") as f:
            for case in data:
                f.write(json.dumps(case) + "\n")

    def find_case_index(
        self, cases: list[dict[str, Any]], case_id: str | list[str]
    ) -> int | None:
        """Find the index of a case by its ID.

        Args:
            cases: List of case dictionaries.
            case_id: The ID to search for (string or list of strings).

        Returns:
            Index of the matching case, or None if not found.
        """
        search_id = case_id if isinstance(case_id, list) else [case_id]
        search_id_set = set(search_id) if len(search_id) > 1 else None
        search_id_single = search_id[0] if len(search_id) == 1 else None

        for i, case in enumerate(cases):
            case_id_value = case.get("id")
            if case_id_value is None:
                continue

            if isinstance(case_id_value, list):
                if search_id_set is not None:
                    if set(case_id_value) == search_id_set:
                        return i
                elif len(case_id_value) == 1 and case_id_value[0] == search_id_single:
                    return i
            else:
                if search_id_single is not None:
                    if str(case_id_value) == search_id_single:
                        return i
                elif len(search_id) == 1 and str(case_id_value) == search_id[0]:
                    return i

        return None

    def upsert_case(self, case: ValidationCase) -> None:
        """Create or update a case in the validation file."""
        cases = self.read_cases()
        case_dict = case.model_dump(exclude_none=True)
        index = self.find_case_index(cases, case.id)

        if index is not None:
            cases[index] = case_dict
        else:
            cases.append(case_dict)

        self.write_cases(cases)

    def delete_case(self, case_id: str | list[str]) -> bool:
        """Delete a case from the validation file.

        Returns:
            True if a case was deleted, False if not found.
        """
        cases = self.read_cases()
        index = self.find_case_index(cases, case_id)

        if index is None:
            return False

        del cases[index]
        self.write_cases(cases)
        return True

    @classmethod
    def create_new(
        cls,
        file_path: Path,
        cases: list[ValidationCase],
        nested_splits: bool = False,
    ) -> "ValidationFileWriter":
        """Create a new validation file with the given cases.

        Args:
            file_path: Path for the new file.
            cases: Initial list of validation cases.
            nested_splits: Whether to use nested split format for YAML/JSON.

        Returns:
            A new ValidationFileWriter instance.

        Raises:
            FileExistsError: If the file already exists.
        """
        file_path = file_path.resolve()
        if file_path.exists():
            raise FileExistsError(f"File already exists: {file_path}")

        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Detect format and create file
        suffix = file_path.suffix.lower()
        case_dicts = [c.model_dump(exclude_none=True) for c in cases]

        if suffix == ".csv":
            if not case_dicts:
                df = pd.DataFrame(columns=["id", "target"])
            else:
                df = pd.DataFrame(case_dicts)
                cols = list(df.columns)
                if "id" in cols:
                    cols.remove("id")
                    cols = ["id"] + cols
                    df = df[cols]
            df.to_csv(file_path, index=False)

        elif suffix in {".yaml", ".yml", ".json"}:
            data = _unflatten_labels(case_dicts)
            if nested_splits and data:
                data = _nest_by_splits(data)

            with open(file_path, "w") as f:
                if suffix in {".yaml", ".yml"}:
                    yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
                else:
                    json.dump(data, f, indent=2)

        elif suffix == ".jsonl":
            data = _unflatten_labels(case_dicts)
            with open(file_path, "w") as f:
                for case_dict in data:
                    f.write(json.dumps(case_dict) + "\n")
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

        return cls(file_path)
