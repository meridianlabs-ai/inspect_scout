"""Helpers for introspecting type hints."""

from types import UnionType
from typing import Any, Union, get_origin


def is_union_type(type_hint: Any) -> bool:
    """Check if a type hint is a union, in either spelling.

    Covers ``typing.Union[X, Y]`` and the ``X | Y`` syntax (distinct types
    before Python 3.14, unified from 3.14 on).
    """
    return get_origin(type_hint) in (Union, UnionType)
