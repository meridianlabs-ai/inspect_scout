from pydantic import JsonValue

from inspect_scout._scanner.result import Result

from .predicates import resolve_predicate
from .types import ValidationSet


async def validate(
    validation: ValidationSet,
    result: Result,
    target: JsonValue | None = None,
    labels: dict[str, JsonValue] | None = None,
) -> bool | dict[str, bool]:
    """Validate a result against a target or labels using the validation set's predicate.

    Args:
        validation: ValidationSet containing the predicate
        result: The result to validate
        target: The expected target value (can be single value or dict) - for regular validation
        labels: Label-specific target values - for resultset validation

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

    # Label-based validation for resultsets
    if labels is not None:
        return await _validate_labels(validation, result, labels)
    # Regular target-based validation
    elif isinstance(target, dict):
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


async def _validate_labels(
    validation: ValidationSet,
    result: Result,
    labels: dict[str, JsonValue],
) -> dict[str, bool]:
    """Validate a resultset against label-specific expected values.

    Uses "at least one" logic: if any result with a given label matches the
    expected value, validation passes for that label. Missing labels are treated
    as negative values (False, None, "NONE", 0, etc).

    Args:
        validation: ValidationSet containing the predicate
        result: The result to validate (should be a resultset)
        labels: Dict mapping label names to expected values

    Returns:
        Dict mapping each label to its validation result (bool)
    """
    import json

    # Validate that this is a resultset
    if result.type != "resultset":
        raise ValueError(
            f"Label-based validation requires a resultset, but got result of type '{result.type}'"
        )

    # Parse the resultset value (JSON array of Result objects)
    if isinstance(result.value, str):
        resultset_data = json.loads(result.value)
    elif isinstance(result.value, list):
        resultset_data = result.value
    else:
        raise ValueError(
            f"Resultset value must be a JSON string or list, got {type(result.value)}"
        )

    # Build a dict of label -> list of Result objects
    results_by_label: dict[str, list[dict[str, JsonValue]]] = {}
    for item in resultset_data:
        if isinstance(item, dict) and "label" in item:
            label = item["label"]
            if label not in results_by_label:
                results_by_label[label] = []
            results_by_label[label].append(item)

    # Validate each label
    predicate_fn = resolve_predicate(validation.predicate)
    validation_results: dict[str, bool] = {}

    for label, expected_value in labels.items():
        # Get all results with this label
        label_results = results_by_label.get(label, [])

        if label_results:
            # At least one result exists - check if any matches expected value
            # Use "at least one" logic
            any_match = False
            for item_data in label_results:
                item_result = Result.model_validate(item_data)
                is_match = await predicate_fn(item_result, expected_value)
                if is_match:
                    any_match = True
                    break
            validation_results[label] = any_match
        else:
            # No results with this label - treat as negative/absent
            # Passes if expected value is a "negative" value
            negative_values = (False, None, "NONE", "none", 0, "")
            validation_results[label] = expected_value in negative_values

    return validation_results
