"""Tests for CLI value coercion helpers in import_command."""

from datetime import datetime

import pytest
from inspect_scout._cli.import_command import _coerce_value, _is_str_only_annotation

# --- _is_str_only_annotation table-driven tests ---

_STR_ONLY_CASES: list[tuple[object, bool]] = [
    # Bare str → True
    (str, True),
    # str | None → True
    (str | None, True),
    # str | list[str] → False (union with non-str type)
    (str | list[str], False),
    # str | list[str] | None → False
    (str | list[str] | None, False),
    # int → False
    (int, False),
    # int | None → False
    (int | None, False),
    # list[str] → False
    (list[str], False),
    # String annotation "str" → True
    ("str", True),
    # String annotation "str | None" → True
    ("str | None", True),
    # String annotation "str | list[str]" → False
    ("str | list[str]", False),
    # String annotation "str | list[str] | None" → False
    ("str | list[str] | None", False),
    # String annotation "int" → False
    ("int", False),
]


@pytest.mark.parametrize(
    ("annotation", "expected"),
    _STR_ONLY_CASES,
    ids=[
        "bare_str",
        "str_or_none",
        "str_or_list",
        "str_or_list_or_none",
        "bare_int",
        "int_or_none",
        "list_str",
        "string_str",
        "string_str_or_none",
        "string_str_or_list",
        "string_str_or_list_or_none",
        "string_int",
    ],
)
def test_is_str_only_annotation(annotation: object, expected: bool) -> None:
    assert _is_str_only_annotation(annotation) is expected


# --- _coerce_value integration tests ---


def test_coerce_str_stays_raw() -> None:
    """Plain str annotation keeps value as-is (no YAML parsing)."""
    assert _coerce_value("true", str) == "true"
    assert _coerce_value("123", str) == "123"


def test_coerce_str_or_none_stays_raw() -> None:
    """Str | None annotation keeps value as-is."""
    assert _coerce_value("true", str | None) == "true"
    assert _coerce_value("[a, b]", str | None) == "[a, b]"


def test_coerce_str_or_list_parses_yaml_list() -> None:
    """Str | list[str] | None annotation YAML-parses lists."""
    result = _coerce_value("[a, b, c]", str | list[str] | None)
    assert result == ["a", "b", "c"]


def test_coerce_str_or_list_parses_yaml_scalar() -> None:
    """Str | list[str] | None passes through plain strings via YAML."""
    result = _coerce_value("hello", str | list[str] | None)
    assert result == "hello"


def test_coerce_int_annotation() -> None:
    """Int annotation coerces to int."""
    assert _coerce_value("42", int) == 42


def test_coerce_datetime_annotation() -> None:
    """Datetime annotation coerces to datetime."""
    result = _coerce_value("2025-01-15T10:30:00", datetime)
    assert isinstance(result, datetime)
    assert result.year == 2025
