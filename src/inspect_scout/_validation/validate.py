from pydantic import JsonValue

from inspect_scout._scanner.result import Result

from .predicates import ValidationPredicate, resolve_predicate
from .types import ValidationSet


async def validate(
    validation: ValidationSet,
    result: Result,
    target: JsonValue | None = None,
    labels: dict[str, bool] | None = None,
    predicate_override: ValidationPredicate | None = None,
) -> bool | dict[str, bool]:
    """Validate a result against a target or labels using the validation set's predicate.

    Args:
        validation: ValidationSet containing the predicate
        result: The result to validate
        target: The expected target value (can be single value or dict) - for regular validation
        labels: Label-specific target values - for resultset validation
        predicate_override: Optional predicate to override the validation set's predicate

    Returns:
        bool if target is a single value
        dict[str, bool] if target is a dict OR labels is provided (one bool per key/label)

    Raises:
        ValueError: If target is a dict but value is not, or if both/neither target and labels are provided
        TypeError: If predicate type doesn't match target type
    """
    # Validate exactly one of target or labels is provided
    if (target is None) == (labels is None):
        raise ValueError("Exactly one of 'target' or 'labels' must be provided")

    # Determine effective predicate (override takes precedence)
    effective_predicate = (
        predicate_override if predicate_override is not None else validation.predicate
    )

    # Label-based validation for resultsets
    if labels is not None:
        return await _validate_labels(validation, result, labels, effective_predicate)
    # Regular target-based validation
    elif isinstance(target, dict):
        return await _validate_dict(validation, result, target, effective_predicate)
    else:
        return await _validate_single(result, target, effective_predicate)


async def _validate_single(
    result: Result,
    target: list[JsonValue] | str | bool | int | float | None,
    predicate: ValidationPredicate | None,
) -> bool:
    predicate_fn = resolve_predicate(predicate)
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
    predicate: ValidationPredicate | None,
) -> dict[str, bool]:
    # Validate that value is also a dict
    if not isinstance(result.value, dict):
        raise ValueError(
            f"Validation target has multiple values ({target}) but value is not a dict ({result.value})"
        )

    # resolve predicate
    predicate_fn = resolve_predicate(predicate)

    # if its a callable then we pass the entire dict
    if callable(predicate):
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


async def _validate_labels(
    validation: ValidationSet,
    result: Result,
    labels: dict[str, bool],
    predicate: ValidationPredicate | None,
) -> dict[str, bool]:
    """Validate a resultset against label presence/absence expectations.

    Args:
        validation: ValidationSet (unused, kept for API compatibility)
        result: The result to validate (must be a resultset)
        labels: Dict mapping label names to boolean expectations
               true = expect positive result, false = expect no result or negative
        predicate: Unused (kept for API compatibility)

    Returns:
        Dict mapping each label to its validation result (bool)
    """
    import json

    # Validate resultset type
    if result.type != "resultset":
        raise ValueError(
            f"Label-based validation requires a resultset, got '{result.type}'"
        )

    # Parse resultset value
    if isinstance(result.value, str):
        resultset_data = json.loads(result.value)
    elif isinstance(result.value, list):
        resultset_data = result.value
    else:
        raise ValueError("Resultset value must be JSON string or list")

    # Group results by label
    results_by_label: dict[str, list[dict[str, JsonValue]]] = {}
    for item in resultset_data:
        if isinstance(item, dict) and "label" in item:
            label = item["label"]
            results_by_label.setdefault(label, []).append(item)

    # Validate each label
    validation_results: dict[str, bool] = {}

    for label, expect_positive in labels.items():
        label_results = results_by_label.get(label, [])

        if expect_positive:
            # true: pass if ANY result has non-negative value
            validation_results[label] = any(
                is_positive_value(Result.model_validate(item).value)
                for item in label_results
            )
        else:
            # false: pass if NO results OR ALL have negative values
            validation_results[label] = all(
                not is_positive_value(Result.model_validate(item).value)
                for item in label_results
            )

    return validation_results


def is_positive_value(value: JsonValue) -> bool:
    """Check if a value is considered 'positive' (non-negative).

    Negative values: False, None, 0, "", "NONE", "none", {}, []
    Non-empty dicts, lists, non-zero numbers, non-empty strings, True = positive.
    """
    if value is None or value is False:
        return False
    if value == 0 or value == "":
        return False
    if isinstance(value, str) and value.lower() == "none":
        return False
    if isinstance(value, dict) and len(value) == 0:
        return False
    if isinstance(value, list) and len(value) == 0:
        return False
    # Non-empty dicts/lists, non-zero numbers, non-empty strings, True = positive
    return True
