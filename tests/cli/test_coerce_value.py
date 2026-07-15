"""Tests for CLI value coercion helpers in import_command."""

from datetime import datetime
from typing import Annotated, Union

import pytest
from inspect_scout._cli.import_command import (
    _coerce_value,
    _get_type_name,
    _has_datetime_annotation,
    _has_int_annotation,
    _is_str_only_annotation,
)

# --- _is_str_only_annotation table-driven tests ---


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        pytest.param(str, True, id="bare_str"),
        pytest.param(str | None, True, id="str_or_none"),
        pytest.param(Union[str, None], True, id="typing_union_str_none"),
        # Unions with non-str members are not str-only
        pytest.param(str | list[str], False, id="str_or_list"),
        pytest.param(str | list[str] | None, False, id="str_or_list_or_none"),
        pytest.param(int, False, id="bare_int"),
        pytest.param(int | None, False, id="int_or_none"),
        pytest.param(list[str], False, id="list_str"),
        # String annotations (from `from __future__ import annotations`)
        pytest.param("str", True, id="string_str"),
        pytest.param("str | None", True, id="string_str_or_none"),
        pytest.param("str | list[str]", False, id="string_str_or_list"),
        pytest.param("str | list[str] | None", False, id="string_str_or_list_or_none"),
        pytest.param("int", False, id="string_int"),
        # Annotated metadata is stripped before classifying
        pytest.param(Annotated[str, "meta"], True, id="annotated_str"),
        pytest.param(Annotated[str | None, "meta"], True, id="annotated_str_or_none"),
    ],
)
def test_is_str_only_annotation(annotation: object, expected: bool) -> None:
    assert _is_str_only_annotation(annotation) is expected


# --- _has_int_annotation / _has_datetime_annotation table-driven tests ---


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        pytest.param(int, True, id="bare_int"),
        pytest.param(int | None, True, id="pipe_union"),
        pytest.param(Union[int, None], True, id="typing_union"),
        pytest.param("int | None", True, id="string_union"),
        pytest.param(str, False, id="bare_str"),
        # Parameterized generics are not unions: list[int] must not be
        # treated as accepting a bare int.
        pytest.param(list[int], False, id="list_int"),
        pytest.param(dict[str, int], False, id="dict_str_int"),
        # Annotated metadata is stripped before classifying
        pytest.param(Annotated[int, "meta"], True, id="annotated_int"),
        pytest.param(Annotated[int | None, "meta"], True, id="annotated_int_or_none"),
        pytest.param(Annotated[list[int], "meta"], False, id="annotated_list_int"),
    ],
)
def test_has_int_annotation(annotation: object, expected: bool) -> None:
    assert _has_int_annotation(annotation) is expected


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        pytest.param(datetime, True, id="bare_datetime"),
        pytest.param(datetime | None, True, id="pipe_union"),
        pytest.param(Union[datetime, None], True, id="typing_union"),
        pytest.param("datetime | None", True, id="string_union"),
        pytest.param(str, False, id="bare_str"),
        # Parameterized generics are not unions: list[datetime] must not be
        # treated as accepting a bare datetime.
        pytest.param(list[datetime], False, id="list_datetime"),
        # Annotated metadata is stripped before classifying
        pytest.param(Annotated[datetime, "meta"], True, id="annotated_datetime"),
        pytest.param(
            Annotated[datetime | None, "meta"], True, id="annotated_datetime_or_none"
        ),
    ],
)
def test_has_datetime_annotation(annotation: object, expected: bool) -> None:
    assert _has_datetime_annotation(annotation) is expected


# --- _get_type_name union handling ---


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        pytest.param(str | None, "str", id="pipe_optional"),
        pytest.param(Union[str, None], "str", id="typing_optional"),
        pytest.param(str | int, "str | int", id="pipe_union"),
        pytest.param(Union[str, int], "str | int", id="typing_union"),
        pytest.param(list[str] | None, "list[str]", id="pipe_optional_generic"),
        pytest.param(list[str], "list[str]", id="plain_generic"),
        pytest.param(Annotated[int, "meta"], "int", id="annotated_int"),
        pytest.param(Annotated[int | None, "meta"], "int", id="annotated_optional"),
    ],
)
def test_get_type_name_unions(annotation: object, expected: str) -> None:
    assert _get_type_name(annotation) == expected


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


def test_coerce_typing_union_int() -> None:
    """typing.Union[int, None] coerces to int like int | None does."""
    assert _coerce_value("42", Union[int, None]) == 42


def test_coerce_typing_union_datetime() -> None:
    """typing.Union[datetime, None] coerces to datetime."""
    result = _coerce_value("2025-01-15T10:30:00", Union[datetime, None])
    assert isinstance(result, datetime)


def test_coerce_list_int_uses_yaml_not_int() -> None:
    """list[int] is not a union with int: value parses as YAML, not int()."""
    assert _coerce_value("[1, 2, 3]", list[int]) == [1, 2, 3]


def test_coerce_annotated_int_uses_int_not_yaml() -> None:
    """Annotated[int, ...] scalar-coerces: YAML would read "010" as octal 8."""
    assert _coerce_value("010", Annotated[int, "meta"]) == 10


def test_coerce_annotated_datetime_not_yaml_date() -> None:
    """Annotated[datetime, ...] gives datetime: YAML would give a date."""
    result = _coerce_value("2025-01-15", Annotated[datetime, "meta"])
    assert isinstance(result, datetime)


def test_coerce_annotated_str_stays_raw() -> None:
    """Annotated[str, ...] keeps value as-is (no YAML parsing)."""
    assert _coerce_value("true", Annotated[str, "meta"]) == "true"
