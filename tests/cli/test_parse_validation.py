"""Tests for CLI validation parsing (_parse_validation function)."""

from pathlib import Path

import click
import pytest
from inspect_scout._cli.scan import _parse_validation
from inspect_scout._validation import ValidationSet


# Test data directory setup
@pytest.fixture
def validation_files(tmp_path: Path) -> dict[str, Path]:
    """Create temporary validation CSV files for testing."""
    # Simple validation file
    simple_csv = tmp_path / "simple.csv"
    simple_csv.write_text("id,target\nid1,true\nid2,false\n")

    # Another validation file
    other_csv = tmp_path / "other.csv"
    other_csv.write_text("id,target\nid3,1\nid4,2\n")

    # Validation file with dict targets
    dict_csv = tmp_path / "dict.csv"
    dict_csv.write_text("id,target_a,target_b\nid5,10,20\nid6,30,40\n")

    return {
        "simple": simple_csv,
        "other": other_csv,
        "dict": dict_csv,
    }


# Basic parsing tests


def test_parse_validation_empty() -> None:
    """Empty tuple should return None."""
    result = _parse_validation(())
    assert result is None


def test_parse_validation_single_file(validation_files: dict[str, Path]) -> None:
    """Single file without scanner name should return ValidationSet."""
    result = _parse_validation((str(validation_files["simple"]),))

    assert isinstance(result, ValidationSet)
    assert len(result.cases) == 2
    assert result.cases[0].id == "id1"
    assert result.cases[0].target is True
    assert result.predicate == "eq"


def test_parse_validation_file_with_predicate(
    validation_files: dict[str, Path],
) -> None:
    """File with predicate should return ValidationSet with that predicate."""
    result = _parse_validation((f"{validation_files['other']}:gt",))

    assert isinstance(result, ValidationSet)
    assert len(result.cases) == 2
    assert result.predicate == "gt"


def test_parse_validation_scanner_file(validation_files: dict[str, Path]) -> None:
    """Scanner:file format should return dict with scanner name."""
    result = _parse_validation((f"my_scanner:{validation_files['simple']}",))

    assert isinstance(result, dict)
    assert "my_scanner" in result
    assert isinstance(result["my_scanner"], ValidationSet)
    assert len(result["my_scanner"].cases) == 2
    assert result["my_scanner"].predicate == "eq"


def test_parse_validation_scanner_file_predicate(
    validation_files: dict[str, Path],
) -> None:
    """Scanner:file:predicate format should work correctly."""
    result = _parse_validation((f"my_scanner:{validation_files['other']}:lt",))

    assert isinstance(result, dict)
    assert "my_scanner" in result
    assert result["my_scanner"].predicate == "lt"


# Multiple validations


def test_parse_validation_multiple_scanners(
    validation_files: dict[str, Path],
) -> None:
    """Multiple scanner:file specs should create dict with all scanners."""
    result = _parse_validation(
        (
            f"scanner1:{validation_files['simple']}",
            f"scanner2:{validation_files['other']}",
        )
    )

    assert isinstance(result, dict)
    assert len(result) == 2
    assert "scanner1" in result
    assert "scanner2" in result
    assert len(result["scanner1"].cases) == 2
    assert len(result["scanner2"].cases) == 2


def test_parse_validation_multiple_scanners_with_predicates(
    validation_files: dict[str, Path],
) -> None:
    """Multiple scanner:file:predicate specs should work."""
    result = _parse_validation(
        (
            f"scanner1:{validation_files['simple']}:eq",
            f"scanner2:{validation_files['other']}:gte",
        )
    )

    assert isinstance(result, dict)
    assert result["scanner1"].predicate == "eq"
    assert result["scanner2"].predicate == "gte"


# Error cases


def test_parse_validation_invalid_predicate(validation_files: dict[str, Path]) -> None:
    """Invalid predicate name gets treated as filename and fails to load."""
    # When format is file.csv:invalid_pred, and invalid_pred is not a known predicate,
    # it gets interpreted as scanner:file (scanner=file.csv, file=invalid_pred)
    # This will fail when trying to load "invalid_pred" as a file
    with pytest.raises(click.UsageError, match="Error loading validation file"):
        _parse_validation((f"{validation_files['simple']}:invalid_pred",))


def test_parse_validation_invalid_predicate_three_parts(
    validation_files: dict[str, Path],
) -> None:
    """Invalid predicate in scanner:file:predicate should raise UsageError."""
    with pytest.raises(
        click.UsageError, match="Unknown validation predicate 'bad_predicate'"
    ):
        _parse_validation((f"scanner:{validation_files['simple']}:bad_predicate",))


def test_parse_validation_too_many_colons(validation_files: dict[str, Path]) -> None:
    """Too many colons should raise UsageError."""
    with pytest.raises(click.UsageError, match="Invalid validation format"):
        _parse_validation(
            (f"scanner:{validation_files['simple']}:gt:extra",)  # 4 parts
        )


def test_parse_validation_nonexistent_file() -> None:
    """Nonexistent file should raise UsageError."""
    with pytest.raises(click.UsageError, match="Error loading validation file"):
        _parse_validation(("nonexistent_file.csv",))


def test_parse_validation_duplicate_scanner(
    validation_files: dict[str, Path],
) -> None:
    """Duplicate scanner names should raise UsageError."""
    with pytest.raises(
        click.UsageError,
        match="Multiple validation sets specified for scanner 'scanner1'",
    ):
        _parse_validation(
            (
                f"scanner1:{validation_files['simple']}",
                f"scanner1:{validation_files['other']}",
            )
        )


def test_parse_validation_multiple_without_scanner_names(
    validation_files: dict[str, Path],
) -> None:
    """Multiple validations without scanner names should raise UsageError."""
    with pytest.raises(
        click.UsageError, match="Multiple validation sets without scanner names"
    ):
        _parse_validation(
            (
                str(validation_files["simple"]),
                str(validation_files["other"]),
            )
        )


def test_parse_validation_mixed_with_and_without_scanner(
    validation_files: dict[str, Path],
) -> None:
    """Mixing validations with and without scanner names should raise UsageError."""
    with pytest.raises(
        click.UsageError,
        match="Cannot mix validation sets with and without scanner names",
    ):
        _parse_validation(
            (
                str(validation_files["simple"]),
                f"scanner1:{validation_files['other']}",
            )
        )


# Edge cases


def test_parse_validation_all_predicates(validation_files: dict[str, Path]) -> None:
    """Test all valid predicate names."""
    predicates = [
        "eq",
        "ne",
        "gt",
        "gte",
        "lt",
        "lte",
        "contains",
        "startswith",
        "endswith",
        "icontains",
        "iequals",
    ]

    for pred in predicates:
        result = _parse_validation((f"{validation_files['simple']}:{pred}",))
        assert isinstance(result, ValidationSet)
        assert result.predicate == pred


def test_parse_validation_scanner_name_with_underscores(
    validation_files: dict[str, Path],
) -> None:
    """Scanner names with underscores should work."""
    result = _parse_validation((f"my_long_scanner_name:{validation_files['simple']}",))

    assert isinstance(result, dict)
    assert "my_long_scanner_name" in result


def test_parse_validation_file_path_with_directories(tmp_path: Path) -> None:
    """File paths with directories should work."""
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    csv_file = subdir / "validation.csv"
    csv_file.write_text("id,target\nid1,true\n")

    result = _parse_validation((str(csv_file),))

    assert isinstance(result, ValidationSet)
    assert len(result.cases) == 1


def test_parse_validation_relative_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:  # noqa: E501
    """Relative file paths should work."""
    csv_file = tmp_path / "validation.csv"
    csv_file.write_text("id,target\nid1,true\n")

    # Change to temp directory so relative path works
    monkeypatch.chdir(tmp_path)

    result = _parse_validation(("validation.csv",))

    assert isinstance(result, ValidationSet)
    assert len(result.cases) == 1


def test_parse_validation_file_formats(tmp_path: Path) -> None:
    """Test different file formats (CSV, JSON, JSONL, YAML)."""
    # CSV
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("id,target\nid1,true\n")

    # JSON
    json_file = tmp_path / "test.json"
    json_file.write_text('[{"id": "id2", "target": false}]')

    # JSONL
    jsonl_file = tmp_path / "test.jsonl"
    jsonl_file.write_text('{"id": "id3", "target": true}\n')

    # YAML
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("- id: id4\n  target: false\n")

    for file in [csv_file, json_file, jsonl_file, yaml_file]:
        result = _parse_validation((str(file),))
        assert isinstance(result, ValidationSet)
        assert len(result.cases) == 1


def test_parse_validation_complex_scenario(validation_files: dict[str, Path]) -> None:
    """Complex scenario with multiple scanners and different predicates."""
    result = _parse_validation(
        (
            f"deception_scanner:{validation_files['simple']}:eq",
            f"thrift_scanner:{validation_files['other']}:gt",
            f"dict_scanner:{validation_files['dict']}:gte",
        )
    )

    assert isinstance(result, dict)
    assert len(result) == 3
    assert "deception_scanner" in result
    assert "thrift_scanner" in result
    assert "dict_scanner" in result
    assert result["deception_scanner"].predicate == "eq"
    assert result["thrift_scanner"].predicate == "gt"
    assert result["dict_scanner"].predicate == "gte"


def test_parse_validation_preserves_case_data(
    validation_files: dict[str, Path],
) -> None:  # noqa: E501
    """Ensure case IDs and targets are preserved correctly."""
    result = _parse_validation((str(validation_files["simple"]),))

    assert isinstance(result, ValidationSet)
    assert result.cases[0].id == "id1"
    assert result.cases[0].target is True
    assert result.cases[1].id == "id2"
    assert result.cases[1].target is False


def test_parse_validation_dict_targets(validation_files: dict[str, Path]) -> None:
    """Test that dict targets work correctly."""
    result = _parse_validation((str(validation_files["dict"]),))

    assert isinstance(result, ValidationSet)
    assert len(result.cases) == 2
    assert isinstance(result.cases[0].target, dict)
    assert result.cases[0].target == {"a": 10, "b": 20}
    assert result.cases[1].target == {"a": 30, "b": 40}
