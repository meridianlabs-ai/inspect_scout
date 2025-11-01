from pydantic import JsonValue

from .predicates import get_predicate_type, resolve_predicate
from .types import ValidationSet


def validate(
    validation: ValidationSet,
    value: JsonValue,
    target: JsonValue,
) -> bool | dict[str, bool]:
    """Validate a value against a target using the validation set's predicate.

    Args:
        validation: ValidationSet containing the predicate
        value: The actual value to validate
        target: The expected target value (can be single value or dict)

    Returns:
        bool if target is a single value
        dict[str, bool] if target is a dict (one bool per key)

    Raises:
        ValueError: If target is a dict but value is not
        TypeError: If predicate type doesn't match target type
    """
    # Detect if target is a dict (multi-value validation)
    if isinstance(target, dict):
        return _validate_dict(validation, value, target)
    else:
        return _validate_single(validation, value, target)


def _validate_single(
    validation: ValidationSet,
    value: JsonValue,
    target: JsonValue,
) -> bool:
    """Validate a single value against a single target."""
    predicate_type = get_predicate_type(validation.predicate)

    if predicate_type == "multi":
        raise TypeError(
            "Cannot use multi-value predicate for single-value validation. "
            "Target is a single value but predicate expects dict inputs."
        )

    # Resolve and apply predicate
    predicate_fn = resolve_predicate(validation.predicate)
    return predicate_fn(value, target)  # type: ignore[arg-type,return-value]


def _validate_dict(
    validation: ValidationSet,
    value: JsonValue,
    target: dict[str, JsonValue],
) -> dict[str, bool]:
    """Validate a dict value against a dict target."""
    # Validate that value is also a dict
    if not isinstance(value, dict):
        raise ValueError(
            f"Validation target has multiple values ({target}) but value is not a dict ({value})"
        )

    predicate_type = get_predicate_type(validation.predicate)

    if predicate_type in ("string", "single", "none"):
        # String or single-value predicate: apply to each key individually
        predicate_fn = resolve_predicate(validation.predicate)
        return {
            key: predicate_fn(value.get(key), target_val)  # type: ignore[arg-type,misc]
            for key, target_val in target.items()
        }
    else:  # multi
        # Multi-value predicate: pass full dicts
        predicate_fn = resolve_predicate(validation.predicate)
        return predicate_fn(value, target)  # type: ignore[return-value]
