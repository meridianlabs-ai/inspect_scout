"""Case-insensitive predicates handle Unicode caseless comparisons."""

import pytest
from inspect_scout import Result, ValidationSet
from inspect_scout._validation.predicates import PredicateType
from inspect_scout._validation.validate import validate


@pytest.mark.asyncio
@pytest.mark.parametrize("predicate", ["iequals", "icontains"])
@pytest.mark.parametrize(
    ("value", "target", "expected"),
    [
        ("Σ", "ς", True),
        ("ς", "Σ", True),
        ("Straße", "STRASSE", True),
        ("STRASSE", "Straße", True),
        ("HELLO", "hello", True),
        ("雪", "雪", True),
        ("", "", True),
        ("no", "yes", False),
        ("I", "ı", False),
        ("café", "cafe", False),
        ("é", "e\u0301", False),
    ],
)
async def test_unicode_caseless_comparison(
    predicate: PredicateType, value: str, target: str, expected: bool
) -> None:
    validation = ValidationSet(cases=[], predicate=predicate)
    assert await validate(validation, Result(value=value), target) is expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("value", "target", "expected"),
    [("Die Straße ist lang", "STRASSE", True), ("ΑΣΩ", "ς", True), ("a", "aa", False)],
)
async def test_unicode_caseless_substring(
    value: str, target: str, expected: bool
) -> None:
    validation = ValidationSet(cases=[], predicate="icontains")
    assert await validate(validation, Result(value=value), target) is expected


@pytest.mark.asyncio
@pytest.mark.parametrize("predicate", ["eq", "contains"])
@pytest.mark.parametrize(("value", "target"), [("Σ", "ς"), ("Straße", "STRASSE")])
async def test_case_sensitive_predicates_remain_distinct(
    predicate: PredicateType, value: str, target: str
) -> None:
    validation = ValidationSet(cases=[], predicate=predicate)
    assert await validate(validation, Result(value=value), target) is False
