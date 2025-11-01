"""Tests for validation predicates."""

import pytest
from inspect_scout._validation import ValidationCase, ValidationPredicate, ValidationSet
from inspect_scout._validation.validate import validate
from pydantic import JsonValue

# Test numeric predicates


def test_gt_predicate_integers() -> None:
    """Test greater than predicate with integers."""
    validation = ValidationSet(cases=[], predicate="gt")
    assert validate(validation, 10, 5) is True
    assert validate(validation, 5, 10) is False
    assert validate(validation, 5, 5) is False


def test_gt_predicate_floats() -> None:
    """Test greater than predicate with floats."""
    validation = ValidationSet(cases=[], predicate="gt")
    assert validate(validation, 10.5, 5.2) is True
    assert validate(validation, 5.2, 10.5) is False
    assert validate(validation, 5.5, 5.5) is False


def test_gt_predicate_mixed_types() -> None:
    """Test greater than predicate with mixed int/float."""
    validation = ValidationSet(cases=[], predicate="gt")
    assert validate(validation, 10, 5.5) is True
    assert validate(validation, 5.5, 10) is False


def test_gt_predicate_invalid_types() -> None:
    """Test greater than predicate with invalid types."""
    validation = ValidationSet(cases=[], predicate="gt")

    with pytest.raises(TypeError, match="gt predicate requires numeric value"):
        validate(validation, "10", 5)

    with pytest.raises(TypeError, match="gt predicate requires numeric target"):
        validate(validation, 10, "5")


def test_gte_predicate() -> None:
    """Test greater than or equal predicate."""
    validation = ValidationSet(cases=[], predicate="gte")
    assert validate(validation, 10, 5) is True
    assert validate(validation, 5, 5) is True
    assert validate(validation, 5, 10) is False


def test_lt_predicate() -> None:
    """Test less than predicate."""
    validation = ValidationSet(cases=[], predicate="lt")
    assert validate(validation, 5, 10) is True
    assert validate(validation, 10, 5) is False
    assert validate(validation, 5, 5) is False


def test_lte_predicate() -> None:
    """Test less than or equal predicate."""
    validation = ValidationSet(cases=[], predicate="lte")
    assert validate(validation, 5, 10) is True
    assert validate(validation, 5, 5) is True
    assert validate(validation, 10, 5) is False


def test_eq_predicate() -> None:
    """Test equality predicate."""
    validation = ValidationSet(cases=[], predicate="eq")
    assert validate(validation, 5, 5) is True
    assert validate(validation, "hello", "hello") is True
    assert validate(validation, True, True) is True
    assert validate(validation, 5, 10) is False
    assert validate(validation, "hello", "world") is False


def test_ne_predicate() -> None:
    """Test not equal predicate."""
    validation = ValidationSet(cases=[], predicate="ne")
    assert validate(validation, 5, 10) is True
    assert validate(validation, "hello", "world") is True
    assert validate(validation, 5, 5) is False
    assert validate(validation, "hello", "hello") is False


# Test string predicates


def test_contains_predicate() -> None:
    """Test contains predicate."""
    validation = ValidationSet(cases=[], predicate="contains")
    assert validate(validation, "hello world", "world") is True
    assert validate(validation, "hello world", "hello") is True
    assert validate(validation, "hello world", "o w") is True
    assert validate(validation, "hello world", "xyz") is False


def test_contains_predicate_case_sensitive() -> None:
    """Test contains predicate is case-sensitive."""
    validation = ValidationSet(cases=[], predicate="contains")
    assert validate(validation, "Hello World", "World") is True
    assert validate(validation, "Hello World", "world") is False


def test_contains_predicate_invalid_types() -> None:
    """Test contains predicate with invalid types."""
    validation = ValidationSet(cases=[], predicate="contains")

    with pytest.raises(TypeError, match="contains predicate requires string value"):
        validate(validation, 123, "1")

    with pytest.raises(TypeError, match="contains predicate requires string target"):
        validate(validation, "hello", 123)


def test_startswith_predicate() -> None:
    """Test startswith predicate."""
    validation = ValidationSet(cases=[], predicate="startswith")
    assert validate(validation, "hello world", "hello") is True
    assert validate(validation, "hello world", "h") is True
    assert validate(validation, "hello world", "world") is False
    assert validate(validation, "hello world", "Hello") is False


def test_endswith_predicate() -> None:
    """Test endswith predicate."""
    validation = ValidationSet(cases=[], predicate="endswith")
    assert validate(validation, "hello world", "world") is True
    assert validate(validation, "hello world", "d") is True
    assert validate(validation, "hello world", "hello") is False
    assert validate(validation, "hello world", "World") is False


def test_icontains_predicate() -> None:
    """Test case-insensitive contains predicate."""
    validation = ValidationSet(cases=[], predicate="icontains")
    assert validate(validation, "Hello World", "world") is True
    assert validate(validation, "Hello World", "WORLD") is True
    assert validate(validation, "Hello World", "WoRlD") is True
    assert validate(validation, "hello world", "O W") is True
    assert validate(validation, "Hello World", "xyz") is False


def test_iequals_predicate() -> None:
    """Test case-insensitive equality predicate."""
    validation = ValidationSet(cases=[], predicate="iequals")
    assert validate(validation, "Hello", "hello") is True
    assert validate(validation, "WORLD", "world") is True
    assert validate(validation, "Hello", "HELLO") is True
    assert validate(validation, "Hello", "world") is False


# Test default predicate (None)


def test_default_predicate() -> None:
    """Test that None defaults to equality comparison."""
    validation = ValidationSet(cases=[], predicate=None)
    assert validate(validation, 5, 5) is True
    assert validate(validation, "hello", "hello") is True
    assert validate(validation, 5, 10) is False


# Test custom callable predicates


def test_custom_callable_predicate() -> None:
    """Test that custom callable predicates still work."""

    def custom_predicate(value: object, target: object) -> bool:
        return str(value) == str(target)

    validation = ValidationSet(cases=[], predicate=custom_predicate)
    assert validate(validation, 123, "123") is True
    assert validate(validation, "hello", "hello") is True
    assert validate(validation, 123, "456") is False


# Test dict target validation (string predicates applied to each key)


def test_dict_target_with_string_predicate() -> None:
    """Test dict target with string predicate (applied to each key)."""
    validation = ValidationSet(cases=[], predicate="gt")
    result = validate(
        validation,
        {"score1": 10, "score2": 20, "score3": 5},
        {"score1": 5, "score2": 15, "score3": 10},
    )
    assert result == {"score1": True, "score2": True, "score3": False}


def test_dict_target_with_contains() -> None:
    """Test dict target with contains predicate."""
    validation = ValidationSet(cases=[], predicate="contains")
    result = validate(
        validation,
        {"msg1": "hello world", "msg2": "foo bar", "msg3": "test"},
        {"msg1": "world", "msg2": "baz", "msg3": "test"},
    )
    assert result == {"msg1": True, "msg2": False, "msg3": True}


def test_dict_target_with_default_predicate() -> None:
    """Test dict target with default equality predicate."""
    validation = ValidationSet(cases=[])  # Uses default "eq"
    result = validate(
        validation,
        {"a": 1, "b": 2, "c": 3},
        {"a": 1, "b": 2, "c": 4},
    )
    assert result == {"a": True, "b": True, "c": False}


def test_dict_target_with_custom_multi_callable() -> None:
    """Test dict target with custom multi-value callable."""

    def custom_multi(
        values: dict[str, JsonValue], targets: dict[str, JsonValue]
    ) -> dict[str, bool]:
        return {key: str(values.get(key)) == str(val) for key, val in targets.items()}

    validation = ValidationSet(cases=[], predicate=custom_multi)
    result = validate(
        validation,
        {"a": 123, "b": "hello"},
        {"a": "123", "b": "hello"},
    )
    assert result == {"a": True, "b": True}


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

    def custom(value: object, target: object) -> bool:
        return value == target

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


def test_multi_predicate_with_single_target_raises_error() -> None:
    """Test that using a multi-value predicate with single target raises error."""

    def multi_pred(
        values: dict[str, JsonValue], targets: dict[str, JsonValue]
    ) -> dict[str, bool]:
        return {k: True for k in targets}

    validation = ValidationSet(cases=[], predicate=multi_pred)

    with pytest.raises(
        TypeError, match="Cannot use multi-value predicate for single-value validation"
    ):
        validate(validation, 10, 5)


def test_dict_target_with_non_dict_value_raises_error() -> None:
    """Test that dict target with non-dict value raises error."""
    validation = ValidationSet(cases=[], predicate="gt")

    with pytest.raises(ValueError, match="value is not a dict"):
        validate(validation, 10, {"a": 5, "b": 10})


# Test predicate type detection


def test_get_predicate_type() -> None:
    """Test predicate type detection."""
    from inspect_scout._validation.predicates import get_predicate_type

    # String predicates
    assert get_predicate_type("gt") == "string"
    assert get_predicate_type("contains") == "string"

    # None
    assert get_predicate_type(None) == "none"

    # Single-value callable
    def single(val: JsonValue, target: JsonValue) -> bool:
        return val == target

    assert get_predicate_type(single) == "single"

    # Multi-value callable (with type hints)
    def multi(
        vals: dict[str, JsonValue], targets: dict[str, JsonValue]
    ) -> dict[str, bool]:
        return {k: True for k in targets}

    assert get_predicate_type(multi) == "multi"
