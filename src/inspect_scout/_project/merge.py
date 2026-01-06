"""Merge project configuration."""

from typing import Any, TypeVar

from inspect_scout._scanjob_config import ScanJobConfig

# Field categories for special merge semantics.
# Simple fields (fallback behavior) are any fields not in these categories.
MODEL_FIELDS = {
    "model",
    "model_base_url",
    "model_args",
    "generate_config",
    "model_roles",
}
UNION_LIST_FIELDS = {"worklist", "tags"}
UNION_DICT_FIELDS = {"scanners", "validation", "metadata"}
SPECIAL_FIELDS = MODEL_FIELDS | UNION_LIST_FIELDS | UNION_DICT_FIELDS

# TypeVar for generic config merging (preserves subclass type)
ConfigT = TypeVar("ConfigT", bound=ScanJobConfig)


def merge_configs(base: ConfigT, override: ScanJobConfig) -> ConfigT:
    """Merge two config objects (config-level, no realization).

    Override values take precedence for simple fields when explicitly set.
    Union fields are combined (override wins on conflicts).
    Model fields are treated as atomic unit.

    Args:
        base: The base configuration providing defaults.
        override: The override configuration with higher priority values.

    Returns:
        A new config object with merged values, same type as base.
    """
    # Use exclude_unset=True to only include fields that were explicitly set,
    # not fields that just have their default values
    result = _merge_config_dicts(
        base.model_dump(exclude_unset=True),
        override.model_dump(exclude_unset=True),
    )
    # Return same type as base (supports ProjectConfig subclass)
    return type(base).model_validate(result)


def _merge_config_dicts(
    base: dict[str, Any], override: dict[str, Any]
) -> dict[str, Any]:
    """Merge two config dicts following merge semantics."""
    result = dict(base)

    # Get all possible fields from both dicts
    all_fields = set(base.keys()) | set(override.keys())

    # Simple fields: override wins if present (any field not in special categories)
    simple_fields = all_fields - SPECIAL_FIELDS
    for field in simple_fields:
        if field in override:
            result[field] = override[field]

    # Model fields: atomic - if any model field in override, use all from override
    if any(field in override for field in MODEL_FIELDS):
        for field in MODEL_FIELDS:
            result.pop(field, None)  # Remove base model fields
        for field in MODEL_FIELDS:
            if field in override:
                result[field] = override[field]

    # Union list fields: combine (base + override)
    for field in UNION_LIST_FIELDS:
        if field in override:
            base_list = base.get(field) or []
            override_list = override[field] or []
            if field == "tags":
                # Deduplicate preserving order
                seen: set[str] = set()
                merged: list[str] = []
                for item in list(base_list) + list(override_list):
                    if item not in seen:
                        seen.add(item)
                        merged.append(item)
                result[field] = merged
            else:  # worklist - simple concatenation
                result[field] = list(base_list) + list(override_list)

    # Union dict fields: combine (base | override, override wins on conflicts)
    for field in UNION_DICT_FIELDS:
        if field in override:
            base_dict = base.get(field) or {}
            override_dict = override[field] or {}
            result[field] = {**base_dict, **override_dict}

    return result
