"""Tests for validation_from function."""

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from inspect_scout._validation import ValidationCase, ValidationSet
from inspect_scout._validation import validation_set as validation_from

# CSV Tests


def test_csv_with_headers_single_target(tmp_path: Path) -> None:
    """Test CSV with headers and single target column."""
    csv_content = """id,target
ef453da45,true
fffffffff,false
123456789,42"""

    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    validation = validation_from(csv_file)

    assert len(validation.cases) == 3
    assert validation.cases[0].id == "ef453da45"
    assert validation.cases[0].target is True
    assert validation.cases[1].id == "fffffffff"
    assert validation.cases[1].target is False
    assert validation.cases[2].id == "123456789"
    assert validation.cases[2].target == 42


def test_csv_without_headers_single_target(tmp_path: Path) -> None:
    """Test CSV without headers (2-column format)."""
    csv_content = """ef453da45,true
fffffffff,false
123456789,42"""

    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    validation = validation_from(csv_file)

    assert len(validation.cases) == 3
    assert validation.cases[0].id == "ef453da45"
    assert validation.cases[0].target is True
    assert validation.cases[1].id == "fffffffff"
    assert validation.cases[1].target is False


def test_csv_with_dict_target(tmp_path: Path) -> None:
    """Test CSV with multiple target_* columns."""
    csv_content = """id,target_foo,target_bar
ef453da45,true,33
ef4533345,false,33
ef4533346,true,44"""

    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    validation = validation_from(csv_file)

    assert len(validation.cases) == 3
    assert validation.cases[0].id == "ef453da45"
    assert validation.cases[0].target == {"foo": True, "bar": 33}
    assert validation.cases[1].id == "ef4533345"
    assert validation.cases[1].target == {"foo": False, "bar": 33}
    assert validation.cases[2].id == "ef4533346"
    assert validation.cases[2].target == {"foo": True, "bar": 44}


def test_csv_with_comma_separated_ids(tmp_path: Path) -> None:
    """Test CSV with comma-separated IDs."""
    csv_content = """id,target
"id1,id2",true
"id3, id4",false"""

    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    validation = validation_from(csv_file)

    assert len(validation.cases) == 2
    assert validation.cases[0].id == ["id1", "id2"]
    assert validation.cases[0].target is True
    assert validation.cases[1].id == ["id3", "id4"]
    assert validation.cases[1].target is False


def test_csv_with_json_array_ids(tmp_path: Path) -> None:
    """Test CSV with JSON-style array IDs."""
    csv_content = """id,target
"[""ef453da45"",""ddddddd""]",true
"[""abc"",""def""]",false"""

    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    validation = validation_from(csv_file)

    assert len(validation.cases) == 2
    assert validation.cases[0].id == ["ef453da45", "ddddddd"]
    assert validation.cases[0].target is True
    assert validation.cases[1].id == ["abc", "def"]
    assert validation.cases[1].target is False


# YAML Tests


def test_yaml_single_target(tmp_path: Path) -> None:
    """Test YAML with single target values."""
    yaml_content = """- id: ef453da45
  target: true
- id: fffffffff
  target: false
- id: 123456789
  target: 42"""

    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(yaml_content)

    validation = validation_from(yaml_file)

    assert len(validation.cases) == 3
    assert validation.cases[0].id == "ef453da45"
    assert validation.cases[0].target is True
    assert validation.cases[1].id == "fffffffff"
    assert validation.cases[1].target is False
    assert validation.cases[2].id == "123456789"
    assert validation.cases[2].target == 42


def test_yaml_with_dict_target(tmp_path: Path) -> None:
    """Test YAML with dict targets."""
    yaml_content = """- id: ef453da45
  target:
    foo: true
    bar: 33
- id: fffffffff
  target:
    foo: false
    bar: 44"""

    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(yaml_content)

    validation = validation_from(yaml_file)

    assert len(validation.cases) == 2
    assert validation.cases[0].id == "ef453da45"
    assert validation.cases[0].target == {"foo": True, "bar": 33}
    assert validation.cases[1].id == "fffffffff"
    assert validation.cases[1].target == {"foo": False, "bar": 44}


def test_yaml_with_array_ids(tmp_path: Path) -> None:
    """Test YAML with array IDs."""
    yaml_content = """- id: [ef453da45, ddddddd]
  target: true
- id: [abc, def]
  target: false"""

    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(yaml_content)

    validation = validation_from(yaml_file)

    assert len(validation.cases) == 2
    assert validation.cases[0].id == ["ef453da45", "ddddddd"]
    assert validation.cases[0].target is True
    assert validation.cases[1].id == ["abc", "def"]
    assert validation.cases[1].target is False


def test_yml_extension(tmp_path: Path) -> None:
    """Test .yml extension works."""
    yaml_content = """- id: test
  target: true"""

    yaml_file = tmp_path / "test.yml"
    yaml_file.write_text(yaml_content)

    validation = validation_from(yaml_file)

    assert len(validation.cases) == 1
    assert validation.cases[0].id == "test"
    assert validation.cases[0].target is True


# JSON Tests


def test_json_array_format(tmp_path: Path) -> None:
    """Test JSON array format."""
    json_content = [
        {"id": "ef453da45", "target": True},
        {"id": "fffffffff", "target": False},
        {"id": "123456789", "target": 42},
    ]

    json_file = tmp_path / "test.json"
    json_file.write_text(json.dumps(json_content))

    validation = validation_from(json_file)

    assert len(validation.cases) == 3
    assert validation.cases[0].id == "ef453da45"
    assert validation.cases[0].target is True
    assert validation.cases[1].id == "fffffffff"
    assert validation.cases[1].target is False
    assert validation.cases[2].id == "123456789"
    assert validation.cases[2].target == 42


def test_json_with_dict_target(tmp_path: Path) -> None:
    """Test JSON with dict targets."""
    json_content = [
        {"id": "ef453da45", "target": {"foo": True, "bar": 33}},
        {"id": "fffffffff", "target": {"foo": False, "bar": 44}},
    ]

    json_file = tmp_path / "test.json"
    json_file.write_text(json.dumps(json_content))

    validation = validation_from(json_file)

    assert len(validation.cases) == 2
    assert validation.cases[0].id == "ef453da45"
    assert validation.cases[0].target == {"foo": True, "bar": 33}


def test_json_with_array_ids(tmp_path: Path) -> None:
    """Test JSON with array IDs."""
    json_content = [
        {"id": ["ef453da45", "ddddddd"], "target": True},
        {"id": ["abc", "def"], "target": False},
    ]

    json_file = tmp_path / "test.json"
    json_file.write_text(json.dumps(json_content))

    validation = validation_from(json_file)

    assert len(validation.cases) == 2
    assert validation.cases[0].id == ["ef453da45", "ddddddd"]
    assert validation.cases[0].target is True


# JSONL Tests


def test_jsonl_format(tmp_path: Path) -> None:
    """Test JSONL (newline-delimited JSON) format."""
    jsonl_content = """{"id": "ef453da45", "target": true}
{"id": "fffffffff", "target": false}
{"id": "123456789", "target": 42}"""

    jsonl_file = tmp_path / "test.jsonl"
    jsonl_file.write_text(jsonl_content)

    validation = validation_from(jsonl_file)

    assert len(validation.cases) == 3
    assert validation.cases[0].id == "ef453da45"
    assert validation.cases[0].target is True
    assert validation.cases[1].id == "fffffffff"
    assert validation.cases[1].target is False
    assert validation.cases[2].id == "123456789"
    assert validation.cases[2].target == 42


def test_jsonl_with_dict_target(tmp_path: Path) -> None:
    """Test JSONL with dict targets."""
    jsonl_content = """{"id": "ef453da45", "target": {"foo": true, "bar": 33}}
{"id": "fffffffff", "target": {"foo": false, "bar": 44}}"""

    jsonl_file = tmp_path / "test.jsonl"
    jsonl_file.write_text(jsonl_content)

    validation = validation_from(jsonl_file)

    assert len(validation.cases) == 2
    assert validation.cases[0].id == "ef453da45"
    assert validation.cases[0].target == {"foo": True, "bar": 33}


# DataFrame Tests


def test_dataframe_input_single_target() -> None:
    """Test direct DataFrame input with single target."""
    df = pd.DataFrame(
        {
            "id": ["ef453da45", "fffffffff", "123456789"],
            "target": [True, False, 42],
        }
    )

    validation = validation_from(df)

    assert len(validation.cases) == 3
    assert validation.cases[0].id == "ef453da45"
    assert validation.cases[0].target is True


def test_dataframe_input_dict_target() -> None:
    """Test direct DataFrame input with dict target."""
    df = pd.DataFrame(
        {
            "id": ["ef453da45", "fffffffff"],
            "target_foo": [True, False],
            "target_bar": [33, 44],
        }
    )

    validation = validation_from(df)

    assert len(validation.cases) == 2
    assert validation.cases[0].id == "ef453da45"
    assert validation.cases[0].target == {"foo": True, "bar": 33}


def test_dataframe_with_list_ids() -> None:
    """Test DataFrame with list IDs."""
    df = pd.DataFrame(
        {
            "id": [["id1", "id2"], ["id3", "id4"]],
            "target": [True, False],
        }
    )

    validation = validation_from(df)

    assert len(validation.cases) == 2
    assert validation.cases[0].id == ["id1", "id2"]
    assert validation.cases[0].target is True


# Error Handling Tests


def test_missing_id_column_error(tmp_path: Path) -> None:
    """Test error when id column is missing."""
    csv_content = """name,target
test,true"""

    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    with pytest.raises(ValueError, match="must contain an 'id' column"):
        validation_from(csv_file)


def test_missing_target_columns_error(tmp_path: Path) -> None:
    """Test error when both target and target_* columns are missing."""
    csv_content = """id,value
test,123"""

    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    with pytest.raises(ValueError, match="must contain target columns"):
        validation_from(csv_file)


def test_unsupported_file_format_error(tmp_path: Path) -> None:
    """Test error for unsupported file formats."""
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("some content")

    with pytest.raises(ValueError, match="Unsupported file format"):
        validation_from(txt_file)


def test_missing_id_column_shows_actual_columns(tmp_path: Path) -> None:
    """Test that missing id column error shows actual columns and expected format."""
    # Use column names that are in the whitelist (so auto-detection won't trigger)
    # but don't include 'id' so the error is raised
    csv_content = """name,target
abc123,true
def456,false"""

    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    with pytest.raises(ValueError) as exc_info:
        validation_from(csv_file)

    error_msg = str(exc_info.value)
    # Should show actual columns found
    assert "name" in error_msg
    assert "target" in error_msg
    # Should show expected format
    assert "id,target" in error_msg


def test_missing_target_shows_actual_columns(tmp_path: Path) -> None:
    """Test that missing target column error shows actual columns."""
    csv_content = """id,score
abc123,100
def456,200"""

    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    with pytest.raises(ValueError) as exc_info:
        validation_from(csv_file)

    error_msg = str(exc_info.value)
    # Should show actual non-id columns found
    assert "score" in error_msg
    # Should mention expected patterns
    assert "target" in error_msg.lower()


def test_csv_headerless_logs_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that auto-detection of headerless CSV logs a warning."""
    csv_content = """abc123def456,true
ghi789jkl012,false"""

    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    # Capture warning calls
    warnings_logged: list[str] = []
    import inspect_scout._validation.validation as validation_module

    monkeypatch.setattr(
        validation_module.logger,
        "warning",
        lambda msg: warnings_logged.append(msg),
    )

    validation = validation_from(csv_file)

    # Should still work (backwards compatibility)
    assert len(validation.cases) == 2
    assert validation.cases[0].target is True

    # Should have logged a warning
    assert len(warnings_logged) == 1
    assert "no recognized headers" in warnings_logged[0]
    assert "id,target" in warnings_logged[0]


def test_csv_explicit_headers_no_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that proper headers don't trigger warnings."""
    csv_content = """id,target
abc123,true
def456,false"""

    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    # Capture warning calls
    warnings_logged: list[str] = []
    import inspect_scout._validation.validation as validation_module

    monkeypatch.setattr(
        validation_module.logger,
        "warning",
        lambda msg: warnings_logged.append(msg),
    )

    validation = validation_from(csv_file)

    assert len(validation.cases) == 2

    # Should NOT have logged any warnings about headers
    assert len(warnings_logged) == 0


# Type Conversion Tests


def test_csv_type_inference_numbers(tmp_path: Path) -> None:
    """Test automatic type inference for numbers in CSV."""
    csv_content = """id,target
test1,42
test2,3.14
test3,0"""

    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    validation = validation_from(csv_file)

    # Pandas reads numeric CSV columns as floats, so accept both int and float
    assert validation.cases[0].target == 42
    assert isinstance(validation.cases[0].target, (int, float))
    assert validation.cases[1].target == 3.14
    assert isinstance(validation.cases[1].target, float)
    assert validation.cases[2].target == 0
    assert isinstance(validation.cases[2].target, (int, float))


def test_csv_type_inference_booleans(tmp_path: Path) -> None:
    """Test automatic type inference for booleans in CSV."""
    csv_content = """id,target
test1,true
test2,false
test3,True
test4,False"""

    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    validation = validation_from(csv_file)

    assert validation.cases[0].target is True
    assert validation.cases[1].target is False
    assert validation.cases[2].target is True
    assert validation.cases[3].target is False


def test_csv_type_inference_strings(tmp_path: Path) -> None:
    """Test that strings remain strings in CSV."""
    csv_content = """id,target
test1,hello
test2,world"""

    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    validation = validation_from(csv_file)

    assert validation.cases[0].target == "hello"
    assert isinstance(validation.cases[0].target, str)


# Complex Scenarios


def test_mixed_id_formats(tmp_path: Path) -> None:
    """Test file with both single and array IDs."""
    yaml_content = """- id: single_id
  target: true
- id: [array_id1, array_id2]
  target: false"""

    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(yaml_content)

    validation = validation_from(yaml_file)

    assert len(validation.cases) == 2
    assert validation.cases[0].id == "single_id"
    assert validation.cases[1].id == ["array_id1", "array_id2"]


def test_validation_object_structure() -> None:
    """Test that Validation object has correct structure."""
    df = pd.DataFrame(
        {
            "id": ["test1"],
            "target": [True],
        }
    )

    validation = validation_from(df)

    assert isinstance(validation, ValidationSet)
    assert isinstance(validation.cases, list)
    assert isinstance(validation.cases[0], ValidationCase)
    assert validation.predicate == "eq"


def test_empty_dataframe() -> None:
    """Test handling of empty DataFrame."""
    df = pd.DataFrame({"id": [], "target": []})

    validation = validation_from(df)

    assert len(validation.cases) == 0
    assert validation.cases == []


# Parametrized Tests


@pytest.mark.parametrize(
    "file_ext,content_builder",
    [
        (
            ".csv",
            lambda: "id,target\ntest1,true\ntest2,false",
        ),
        (
            ".yaml",
            lambda: "- id: test1\n  target: true\n- id: test2\n  target: false",
        ),
        (
            ".json",
            lambda: json.dumps(
                [{"id": "test1", "target": True}, {"id": "test2", "target": False}]
            ),
        ),
        (
            ".jsonl",
            lambda: '{"id": "test1", "target": true}\n{"id": "test2", "target": false}',
        ),
    ],
)
def test_all_formats_produce_same_output(
    tmp_path: Path, file_ext: str, content_builder: Any
) -> None:
    """Test that all formats produce consistent output."""
    test_file = tmp_path / f"test{file_ext}"
    test_file.write_text(content_builder())

    validation = validation_from(test_file)

    assert len(validation.cases) == 2
    assert validation.cases[0].id == "test1"
    assert validation.cases[0].target is True
    assert validation.cases[1].id == "test2"
    assert validation.cases[1].target is False


@pytest.mark.parametrize(
    "id_input,expected_output",
    [
        ("single_id", "single_id"),
        ("id1,id2", ["id1", "id2"]),
        ("id1, id2, id3", ["id1", "id2", "id3"]),
        ('["id1","id2"]', ["id1", "id2"]),
        (["already", "list"], ["already", "list"]),
    ],
)
def test_id_parsing_variations(id_input: Any, expected_output: Any) -> None:
    """Test various ID parsing scenarios."""
    from inspect_scout._validation.validation import _parse_id

    result = _parse_id(id_input)
    assert result == expected_output


# Split Tests


def test_csv_with_split_column(tmp_path: Path) -> None:
    """Test CSV with split column."""
    csv_content = """id,target,split
test1,true,dev
test2,false,test
test3,true,dev"""

    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    validation = validation_from(csv_file)

    assert len(validation.cases) == 3
    assert validation.cases[0].id == "test1"
    assert validation.cases[0].split == "dev"
    assert validation.cases[1].id == "test2"
    assert validation.cases[1].split == "test"
    assert validation.cases[2].id == "test3"
    assert validation.cases[2].split == "dev"


def test_csv_with_split_filter_single(tmp_path: Path) -> None:
    """Test filtering by single split."""
    csv_content = """id,target,split
test1,true,dev
test2,false,test
test3,true,dev"""

    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    validation = validation_from(csv_file, split="dev")

    assert len(validation.cases) == 2
    assert validation.cases[0].id == "test1"
    assert validation.cases[1].id == "test3"
    assert validation.split == "dev"


def test_csv_with_split_filter_multiple(tmp_path: Path) -> None:
    """Test filtering by multiple splits."""
    csv_content = """id,target,split
test1,true,dev
test2,false,test
test3,true,train
test4,false,dev"""

    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    validation = validation_from(csv_file, split=["dev", "test"])

    assert len(validation.cases) == 3
    assert {c.id for c in validation.cases} == {"test1", "test2", "test4"}
    assert validation.split == ["dev", "test"]


def test_yaml_nested_split_format(tmp_path: Path) -> None:
    """Test nested YAML format with splits."""
    yaml_content = """- split: dev
  cases:
    - id: test1
      target: true
    - id: test2
      target: false
- split: test
  cases:
    - id: test3
      target: true"""

    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(yaml_content)

    validation = validation_from(yaml_file)

    assert len(validation.cases) == 3
    assert validation.cases[0].id == "test1"
    assert validation.cases[0].split == "dev"
    assert validation.cases[1].id == "test2"
    assert validation.cases[1].split == "dev"
    assert validation.cases[2].id == "test3"
    assert validation.cases[2].split == "test"


def test_yaml_nested_split_with_filter(tmp_path: Path) -> None:
    """Test nested YAML format with split filtering."""
    yaml_content = """- split: dev
  cases:
    - id: test1
      target: true
    - id: test2
      target: false
- split: test
  cases:
    - id: test3
      target: true"""

    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(yaml_content)

    validation = validation_from(yaml_file, split="dev")

    assert len(validation.cases) == 2
    assert validation.cases[0].id == "test1"
    assert validation.cases[1].id == "test2"


def test_yaml_flat_split_field(tmp_path: Path) -> None:
    """Test flat YAML format with split field."""
    yaml_content = """- id: test1
  target: true
  split: dev
- id: test2
  target: false
  split: test"""

    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(yaml_content)

    validation = validation_from(yaml_file)

    assert len(validation.cases) == 2
    assert validation.cases[0].split == "dev"
    assert validation.cases[1].split == "test"


def test_json_with_split_field(tmp_path: Path) -> None:
    """Test JSON with split field."""
    json_content = [
        {"id": "test1", "target": True, "split": "dev"},
        {"id": "test2", "target": False, "split": "test"},
    ]

    json_file = tmp_path / "test.json"
    json_file.write_text(json.dumps(json_content))

    validation = validation_from(json_file)

    assert len(validation.cases) == 2
    assert validation.cases[0].split == "dev"
    assert validation.cases[1].split == "test"


def test_jsonl_with_split_field(tmp_path: Path) -> None:
    """Test JSONL with split field."""
    jsonl_content = """{"id": "test1", "target": true, "split": "dev"}
{"id": "test2", "target": false, "split": "test"}"""

    jsonl_file = tmp_path / "test.jsonl"
    jsonl_file.write_text(jsonl_content)

    validation = validation_from(jsonl_file)

    assert len(validation.cases) == 2
    assert validation.cases[0].split == "dev"
    assert validation.cases[1].split == "test"


def test_cases_without_split_excluded_when_filtering(tmp_path: Path) -> None:
    """Test that cases without split are excluded when filtering."""
    csv_content = """id,target,split
test1,true,dev
test2,false,
test3,true,dev"""

    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    validation = validation_from(csv_file, split="dev")

    # Only cases with split="dev" should be included
    assert len(validation.cases) == 2
    assert {c.id for c in validation.cases} == {"test1", "test3"}


def test_unknown_split_warns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test warning when filtering by unknown split name."""
    csv_content = """id,target,split
test1,true,dev
test2,false,test"""

    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    warnings_logged: list[str] = []
    import inspect_scout._validation.validation as validation_module

    monkeypatch.setattr(
        validation_module.logger,
        "warning",
        lambda msg: warnings_logged.append(msg),
    )

    validation = validation_from(csv_file, split="nonexistent")

    assert len(validation.cases) == 0
    assert len(warnings_logged) == 1
    assert "nonexistent" in warnings_logged[0]
    assert "dev" in warnings_logged[0]
    assert "test" in warnings_logged[0]


def test_validation_set_stores_active_split() -> None:
    """Test that ValidationSet stores the active split filter."""
    df = pd.DataFrame(
        {
            "id": ["test1", "test2"],
            "target": [True, False],
            "split": ["dev", "test"],
        }
    )

    validation = validation_from(df, split="dev")

    assert validation.split == "dev"


def test_validation_set_stores_multiple_splits() -> None:
    """Test that ValidationSet stores multiple split filters."""
    df = pd.DataFrame(
        {
            "id": ["test1", "test2", "test3"],
            "target": [True, False, True],
            "split": ["dev", "test", "train"],
        }
    )

    validation = validation_from(df, split=["dev", "test"])

    assert validation.split == ["dev", "test"]


def test_no_split_filter_returns_all() -> None:
    """Test that no split filter returns all cases."""
    df = pd.DataFrame(
        {
            "id": ["test1", "test2", "test3"],
            "target": [True, False, True],
            "split": ["dev", "test", None],
        }
    )

    validation = validation_from(df)

    assert len(validation.cases) == 3
    assert validation.split is None


def test_dataframe_with_split_column() -> None:
    """Test DataFrame input with split column."""
    df = pd.DataFrame(
        {
            "id": ["test1", "test2", "test3"],
            "target": [True, False, True],
            "split": ["dev", "test", "dev"],
        }
    )

    validation = validation_from(df, split="test")

    assert len(validation.cases) == 1
    assert validation.cases[0].id == "test2"
    assert validation.cases[0].split == "test"


def test_json_nested_split_format(tmp_path: Path) -> None:
    """Test nested JSON format with splits."""
    json_content = [
        {
            "split": "dev",
            "cases": [
                {"id": "test1", "target": True},
                {"id": "test2", "target": False},
            ],
        },
        {
            "split": "test",
            "cases": [{"id": "test3", "target": True}],
        },
    ]

    json_file = tmp_path / "test.json"
    json_file.write_text(json.dumps(json_content))

    validation = validation_from(json_file)

    assert len(validation.cases) == 3
    assert validation.cases[0].split == "dev"
    assert validation.cases[1].split == "dev"
    assert validation.cases[2].split == "test"


def test_warn_no_splits_defined(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test warning when filtering but no cases have splits defined."""
    csv_content = """id,target
test1,true
test2,false"""

    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    warnings_logged: list[str] = []
    import inspect_scout._validation.validation as validation_module

    monkeypatch.setattr(
        validation_module.logger,
        "warning",
        lambda msg: warnings_logged.append(msg),
    )

    validation = validation_from(csv_file, split="dev")

    assert len(validation.cases) == 0
    assert len(warnings_logged) == 1
    assert "No cases have split values defined" in warnings_logged[0]
