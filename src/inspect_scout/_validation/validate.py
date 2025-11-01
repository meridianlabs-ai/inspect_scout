from pydantic import JsonValue

from .types import ValidationSet


def validate(
    validation: ValidationSet,
    value: JsonValue,
    target: JsonValue,
) -> bool:
    predicate = validation.predicate or _equals
    return predicate(value, target)


def validate_dict(
    validation: ValidationSet,
    value: JsonValue,
    target: dict[str, JsonValue],
) -> dict[str, bool]:
    # validate value
    if not isinstance(value, dict):
        raise ValueError(
            f"Validation case has multiple values ({target}) but value does not ({value})"
        )
    predicate = validation.multi_predicate or _dict_equals
    return predicate(value, target)


def _equals(value: JsonValue, target: JsonValue) -> bool:
    return value == target


def _dict_equals(
    values: dict[str, JsonValue], targets: dict[str, JsonValue]
) -> dict[str, bool]:
    return {key: value == values.get(key, None) for key, value in targets.items()}
