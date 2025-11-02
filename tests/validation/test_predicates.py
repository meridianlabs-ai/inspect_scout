"""Tests for validation predicates."""

import pytest
from inspect_scout._scanner.result import Result
from inspect_scout._validation import ValidationCase, ValidationPredicate, ValidationSet
from inspect_scout._validation.validate import validate
from pydantic import JsonValue

# Test numeric predicates


@pytest.mark.asyncio
async def test_gt_predicate_integers() -> None:
    """Test greater than predicate with integers."""
    validation = ValidationSet(cases=[], predicate="gt")
    assert await validate(validation, Result(value=10), 5) is True
    assert await validate(validation, Result(value=5), 10) is False
    assert await validate(validation, Result(value=5), 5) is False


@pytest.mark.asyncio
async def test_gt_predicate_floats() -> None:
    """Test greater than predicate with floats."""
    validation = ValidationSet(cases=[], predicate="gt")
    assert await validate(validation, Result(value=10.5), 5.2) is True
    assert await validate(validation, Result(value=5.2), 10.5) is False
    assert await validate(validation, Result(value=5.5), 5.5) is False


@pytest.mark.asyncio
async def test_gt_predicate_mixed_types() -> None:
    """Test greater than predicate with mixed int/float."""
    validation = ValidationSet(cases=[], predicate="gt")
    assert await validate(validation, Result(value=10), 5.5) is True
    assert await validate(validation, Result(value=5.5), 10) is False


@pytest.mark.asyncio
async def test_gt_predicate_invalid_types() -> None:
    """Test greater than predicate with invalid types."""
    validation = ValidationSet(cases=[], predicate="gt")

    with pytest.raises(TypeError, match="gt predicate requires numeric value"):
        await validate(validation, Result(value="10"), 5)

    with pytest.raises(TypeError, match="gt predicate requires numeric target"):
        await validate(validation, Result(value=10), "5")


@pytest.mark.asyncio
async def test_gte_predicate() -> None:
    """Test greater than or equal predicate."""
    validation = ValidationSet(cases=[], predicate="gte")
    assert await validate(validation, Result(value=10), 5) is True
    assert await validate(validation, Result(value=5), 5) is True
    assert await validate(validation, Result(value=5), 10) is False


@pytest.mark.asyncio
async def test_lt_predicate() -> None:
    """Test less than predicate."""
    validation = ValidationSet(cases=[], predicate="lt")
    assert await validate(validation, Result(value=5), 10) is True
    assert await validate(validation, Result(value=10), 5) is False
    assert await validate(validation, Result(value=5), 5) is False


@pytest.mark.asyncio
async def test_lte_predicate() -> None:
    """Test less than or equal predicate."""
    validation = ValidationSet(cases=[], predicate="lte")
    assert await validate(validation, Result(value=5), 10) is True
    assert await validate(validation, Result(value=5), 5) is True
    assert await validate(validation, Result(value=10), 5) is False


@pytest.mark.asyncio
async def test_eq_predicate() -> None:
    """Test equality predicate."""
    validation = ValidationSet(cases=[], predicate="eq")
    assert await validate(validation, Result(value=5), 5) is True
    assert await validate(validation, Result(value="hello"), "hello") is True
    assert await validate(validation, Result(value=True), True) is True
    assert await validate(validation, Result(value=5), 10) is False
    assert await validate(validation, Result(value="hello"), "world") is False


@pytest.mark.asyncio
async def test_ne_predicate() -> None:
    """Test not equal predicate."""
    validation = ValidationSet(cases=[], predicate="ne")
    assert await validate(validation, Result(value=5), 10) is True
    assert await validate(validation, Result(value="hello"), "world") is True
    assert await validate(validation, Result(value=5), 5) is False
    assert await validate(validation, Result(value="hello"), "hello") is False


# Test string predicates


@pytest.mark.asyncio
async def test_contains_predicate() -> None:
    """Test contains predicate."""
    validation = ValidationSet(cases=[], predicate="contains")
    assert await validate(validation, Result(value="hello world"), "world") is True
    assert await validate(validation, Result(value="hello world"), "hello") is True
    assert await validate(validation, Result(value="hello world"), "o w") is True
    assert await validate(validation, Result(value="hello world"), "xyz") is False


@pytest.mark.asyncio
async def test_contains_predicate_case_sensitive() -> None:
    """Test contains predicate is case-sensitive."""
    validation = ValidationSet(cases=[], predicate="contains")
    assert await validate(validation, Result(value="Hello World"), "World") is True
    assert await validate(validation, Result(value="Hello World"), "world") is False


@pytest.mark.asyncio
async def test_contains_predicate_invalid_types() -> None:
    """Test contains predicate with invalid types."""
    validation = ValidationSet(cases=[], predicate="contains")

    with pytest.raises(TypeError, match="contains predicate requires string value"):
        await validate(validation, Result(value=123), "1")

    with pytest.raises(TypeError, match="contains predicate requires string target"):
        await validate(validation, Result(value="hello"), 123)


@pytest.mark.asyncio
async def test_startswith_predicate() -> None:
    """Test startswith predicate."""
    validation = ValidationSet(cases=[], predicate="startswith")
    assert await validate(validation, Result(value="hello world"), "hello") is True
    assert await validate(validation, Result(value="hello world"), "h") is True
    assert await validate(validation, Result(value="hello world"), "world") is False
    assert await validate(validation, Result(value="hello world"), "Hello") is False


@pytest.mark.asyncio
async def test_endswith_predicate() -> None:
    """Test endswith predicate."""
    validation = ValidationSet(cases=[], predicate="endswith")
    assert await validate(validation, Result(value="hello world"), "world") is True
    assert await validate(validation, Result(value="hello world"), "d") is True
    assert await validate(validation, Result(value="hello world"), "hello") is False
    assert await validate(validation, Result(value="hello world"), "World") is False


@pytest.mark.asyncio
async def test_icontains_predicate() -> None:
    """Test case-insensitive contains predicate."""
    validation = ValidationSet(cases=[], predicate="icontains")
    assert await validate(validation, Result(value="Hello World"), "world") is True
    assert await validate(validation, Result(value="Hello World"), "WORLD") is True
    assert await validate(validation, Result(value="Hello World"), "WoRlD") is True
    assert await validate(validation, Result(value="hello world"), "O W") is True
    assert await validate(validation, Result(value="Hello World"), "xyz") is False


@pytest.mark.asyncio
async def test_iequals_predicate() -> None:
    """Test case-insensitive equality predicate."""
    validation = ValidationSet(cases=[], predicate="iequals")
    assert await validate(validation, Result(value="Hello"), "hello") is True
    assert await validate(validation, Result(value="WORLD"), "world") is True
    assert await validate(validation, Result(value="Hello"), "HELLO") is True
    assert await validate(validation, Result(value="Hello"), "world") is False


# Test default predicate (None)


@pytest.mark.asyncio
async def test_default_predicate() -> None:
    """Test that None defaults to equality comparison."""
    validation = ValidationSet(cases=[], predicate=None)
    assert await validate(validation, Result(value=5), 5) is True
    assert await validate(validation, Result(value="hello"), "hello") is True
    assert await validate(validation, Result(value=5), 10) is False


# Test custom callable predicates


@pytest.mark.asyncio
async def test_custom_callable_predicate() -> None:
    """Test that custom callable predicates still work."""

    async def custom_predicate(result: Result, target: object) -> bool:
        return str(result.value) == str(target)

    validation = ValidationSet(cases=[], predicate=custom_predicate)
    assert await validate(validation, Result(value=123), "123") is True
    assert await validate(validation, Result(value="hello"), "hello") is True
    assert await validate(validation, Result(value=123), "456") is False


# Test dict target validation (string predicates applied to each key)


@pytest.mark.asyncio
async def test_dict_target_with_string_predicate() -> None:
    """Test dict target with string predicate (applied to each key)."""
    validation = ValidationSet(cases=[], predicate="gt")
    result = await validate(
        validation,
        Result(value={"score1": 10, "score2": 20, "score3": 5}),
        {"score1": 5, "score2": 15, "score3": 10},
    )
    assert result == {"score1": True, "score2": True, "score3": False}


@pytest.mark.asyncio
async def test_dict_target_with_contains() -> None:
    """Test dict target with contains predicate."""
    validation = ValidationSet(cases=[], predicate="contains")
    result = await validate(
        validation,
        Result(value={"msg1": "hello world", "msg2": "foo bar", "msg3": "test"}),
        {"msg1": "world", "msg2": "baz", "msg3": "test"},
    )
    assert result == {"msg1": True, "msg2": False, "msg3": True}


@pytest.mark.asyncio
async def test_dict_target_with_default_predicate() -> None:
    """Test dict target with default equality predicate."""
    validation = ValidationSet(cases=[])  # Uses default "eq"
    result = await validate(
        validation,
        Result(value={"a": 1, "b": 2, "c": 3}),
        {"a": 1, "b": 2, "c": 4},
    )
    assert result == {"a": True, "b": True, "c": False}


@pytest.mark.asyncio
async def test_dict_target_with_custom_multi_callable() -> None:
    """Test dict target with custom multi-value callable."""

    async def custom_multi(result: Result, targets: JsonValue) -> dict[str, bool]:
        assert isinstance(result.value, dict)
        assert isinstance(targets, dict)
        return {
            key: str(result.value.get(key)) == str(val) for key, val in targets.items()
        }

    validation = ValidationSet(cases=[], predicate=custom_multi)
    result_val = await validate(
        validation,
        Result(value={"a": 123, "b": "hello"}),
        {"a": "123", "b": "hello"},
    )
    assert result_val == {"a": True, "b": True}


# Test serialization


def test_predicate_serialization() -> None:
    """Test that string predicates serialize correctly."""
    validation = ValidationSet(
        cases=[ValidationCase(id="test1", target=10)], predicate="gt"
    )

    # Serialize to dict
    data = validation.model_dump()
    assert data["predicate"] == "gt"

    # Deserialize from dict
    restored = ValidationSet.model_validate(data)
    assert restored.predicate == "gt"


def test_custom_predicate_serialization() -> None:
    """Test that custom predicates serialize via dill."""

    async def custom(result: Result, target: object) -> bool:
        return result.value == target

    validation = ValidationSet(
        cases=[ValidationCase(id="test1", target=10)], predicate=custom
    )

    # Serialize to dict
    data = validation.model_dump()
    assert isinstance(data["predicate"], str)
    assert data["predicate"] != "eq"  # Should be base64-encoded dill

    # Deserialize from dict
    restored = ValidationSet.model_validate(data)
    assert callable(restored.predicate)


def test_predicate_serialization_with_dict_target() -> None:
    """Test that predicate string serializes correctly with dict targets."""
    validation = ValidationSet(
        cases=[ValidationCase(id="test1", target={"a": 1, "b": 2})],
        predicate="gte",
    )

    # Serialize to dict
    data = validation.model_dump()
    assert data["predicate"] == "gte"

    # Deserialize from dict
    restored = ValidationSet.model_validate(data)
    assert restored.predicate == "gte"


# Test unknown predicate


def test_unknown_predicate() -> None:
    """Test that unknown predicate strings raise an error during validation."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="Input should be"):
        ValidationSet(
            cases=[ValidationCase(id="test1", target=10)],
            predicate="unknown",  # type: ignore[arg-type]
        )


# Test ValidationPredicate type hints


def test_validation_predicate_type_hints() -> None:
    """Test that ValidationPredicate type works for type hints."""
    predicate: ValidationPredicate = "gt"
    assert predicate == "gt"

    predicate = "contains"
    assert predicate == "contains"


# Test error cases


@pytest.mark.asyncio
async def test_dict_target_with_non_dict_value_raises_error() -> None:
    """Test that dict target with non-dict value raises error."""
    validation = ValidationSet(cases=[], predicate="gt")

    with pytest.raises(ValueError, match="value is not a dict"):
        await validate(validation, Result(value=10), {"a": 5, "b": 10})


# Test predicate type detection


def test_predicate_type_detection() -> None:
    """Test predicate type detection."""
    # String predicates
    validation_gt = ValidationSet(cases=[], predicate="gt")
    assert validation_gt.predicate == "gt"

    validation_contains = ValidationSet(cases=[], predicate="contains")
    assert validation_contains.predicate == "contains"

    # None
    validation_none = ValidationSet(cases=[], predicate=None)
    assert validation_none.predicate is None

    # Single-value callable
    async def single(result: Result, target: JsonValue) -> bool:
        return result.value == target

    validation_single = ValidationSet(cases=[], predicate=single)
    assert callable(validation_single.predicate)

    # Multi-value callable (with type hints)
    async def multi(result: Result, target: JsonValue) -> dict[str, bool]:
        assert isinstance(result.value, dict)
        assert isinstance(target, dict)
        return {k: True for k in target}

    validation_multi = ValidationSet(cases=[], predicate=multi)
    assert callable(validation_multi.predicate)
