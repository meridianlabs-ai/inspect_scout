from pydantic import JsonValue

from inspect_scout._scanner.result import Result

from .predicates import resolve_predicate
from .types import ValidationSet


async def validate(
    validation: ValidationSet,
    result: Result,
    target: JsonValue,
) -> bool | dict[str, bool]:
    """Validate a value against a target using the validation set's predicate.

    Args:
        validation: ValidationSet containing the predicate
        result: The result to validate
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
        return await _validate_dict(validation, result, target)
    else:
        return await _validate_single(validation, result, target)


async def _validate_single(
    validation: ValidationSet,
    result: Result,
    target: list[JsonValue] | str | bool | int | float | None,
) -> bool:
    predicate_fn = resolve_predicate(validation.predicate)
    valid = await predicate_fn(result, target)
    if not isinstance(valid, bool):
        raise RuntimeError(
            f"Validation function must return bool for target of type '{type(target)}' (returned '{type(valid)}')"
        )
    return valid


async def _validate_dict(
    validation: ValidationSet,
    result: Result,
    target: dict[str, JsonValue],
) -> dict[str, bool]:
    # Validate that value is also a dict
    if not isinstance(result.value, dict):
        raise ValueError(
            f"Validation target has multiple values ({target}) but value is not a dict ({result.value})"
        )

    # resolve predicate
    predicate_fn = resolve_predicate(validation.predicate)

    # if its a callable then we pass the entire dict
    if callable(validation.predicate):
        valid = await predicate_fn(result, target)
        if not isinstance(valid, dict):
            raise RuntimeError(
                f"Validation function must return dict for target of type dict (returned '{type(valid)}')"
            )
        return valid
    else:
        return {
            key: bool(
                await predicate_fn(Result(value=result.value.get(key)), target_val)
            )
            for key, target_val in target.items()
        }
