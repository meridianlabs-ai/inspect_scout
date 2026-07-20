"""Tests for type hint introspection helpers."""

from types import UnionType
from typing import Annotated, Any, Literal, Optional, Union

import pytest
from inspect_scout._util.type_hints import is_union_type


@pytest.mark.parametrize(
    ("type_hint", "expected"),
    [
        # typing.Union spelling
        pytest.param(Union[int, None], True, id="typing_union"),
        pytest.param(Union[int, str], True, id="typing_union_two_types"),
        pytest.param(Optional[str], True, id="typing_optional"),
        # X | Y spelling (types.UnionType before 3.14, unified from 3.14 on)
        pytest.param(int | None, True, id="pipe_optional"),
        pytest.param(int | str, True, id="pipe_union"),
        pytest.param(list[int] | None, True, id="pipe_optional_generic"),
        # Single-member Union collapses to the bare type
        pytest.param(Union[int], False, id="single_member_union"),
        # Unsubscripted union forms are not unions
        pytest.param(Union, False, id="bare_union"),
        pytest.param(UnionType, False, id="bare_union_type"),
        # Annotated wrapping a union is not itself a union
        pytest.param(Annotated[int | None, "meta"], False, id="annotated_union"),
        # Bare and parameterized types
        pytest.param(int, False, id="bare_int"),
        pytest.param(type(None), False, id="none_type"),
        pytest.param(list[int], False, id="list_int"),
        pytest.param(dict[str, int], False, id="dict_str_int"),
        pytest.param(Literal["a", "b"], False, id="literal"),
        # String annotations are not introspected here
        pytest.param("str | None", False, id="string_annotation"),
    ],
)
def test_is_union_type(type_hint: Any, expected: bool) -> None:
    assert is_union_type(type_hint) is expected
