"""Merge project configuration into scan jobs."""

from typing import Any, TypeVar

from inspect_ai._util.config import resolve_args
from inspect_ai.model import GenerateConfig, get_model

from inspect_scout._scanjob import ScanJob, ScanJobConfig
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._validation.types import ValidationSet

from .types import ProjectConfig

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


def merge_project_into_scanjob(proj: ProjectConfig, scanjob: ScanJob) -> None:
    """Merge project defaults into a ScanJob (mutates scanjob in place).

    - Simple fields: project value used as fallback when scanjob value is None
    - Union fields: worklist, validation, scanners, tags, metadata combined
    - generate_config: Uses GenerateConfig.merge()

    Args:
        proj: The project configuration providing defaults.
        scanjob: The ScanJob to merge into (modified in place).
    """
    _apply_simple_fallbacks(proj, scanjob)
    _merge_worklist(proj, scanjob)
    _merge_scanners(proj, scanjob)
    _merge_validation(proj, scanjob)
    _merge_model(proj, scanjob)
    _merge_tags(proj, scanjob)
    _merge_metadata(proj, scanjob)


def _merge_model(proj: ProjectConfig, scanjob: ScanJob) -> None:
    if scanjob._model is None and proj.model is not None:
        scanjob._model_base_url = proj.model_base_url
        scanjob._model_args = (
            resolve_args(proj.model_args)
            if isinstance(proj.model_args, str)
            else proj.model_args
        )
        scanjob._generate_config = proj.generate_config

        scanjob._model = get_model(
            proj.model,
            config=scanjob._generate_config or GenerateConfig(),
            base_url=scanjob._model_base_url,
            **(scanjob._model_args or {}),
        )


def _apply_simple_fallbacks(proj: ProjectConfig, scanjob: ScanJob) -> None:
    """Apply project values as fallbacks for simple fields."""
    # Transcripts - convert string to Transcripts object
    if scanjob._transcripts is None and proj.transcripts is not None:
        scanjob._transcripts = transcripts_from(proj.transcripts)

    # Results
    if scanjob._scans is None and proj.scans is not None:
        scanjob._scans = proj.scans

    # Note: Model fields are handled by _merge_model() which treats the model
    # configuration as an atomic unit (model + base_url + args + generate_config)

    # Numeric/bool fields
    if scanjob._max_transcripts is None and proj.max_transcripts is not None:
        scanjob._max_transcripts = proj.max_transcripts

    if scanjob._max_processes is None and proj.max_processes is not None:
        scanjob._max_processes = proj.max_processes

    if scanjob._limit is None and proj.limit is not None:
        scanjob._limit = proj.limit

    if scanjob._shuffle is None and proj.shuffle is not None:
        scanjob._shuffle = proj.shuffle

    if scanjob._log_level is None and proj.log_level is not None:
        scanjob._log_level = proj.log_level


def _merge_worklist(proj: ProjectConfig, scanjob: ScanJob) -> None:
    """Merge worklists - union of both lists."""
    if proj.worklist is None:
        return

    if scanjob._worklist is None:
        scanjob._worklist = list(proj.worklist)
    else:
        # Union: project worklist items come first, then scanjob items
        scanjob._worklist = list(proj.worklist) + list(scanjob._worklist)


def _merge_scanners(proj: ProjectConfig, scanjob: ScanJob) -> None:
    """Merge scanners - union of dicts, scanjob wins on key conflicts."""
    if proj.scanners is None:
        return

    # Import here to avoid circular imports
    from inspect_scout._scancontext import (
        scanners_from_spec_dict,
        scanners_from_spec_list,
    )

    # Resolve project ScannerSpecs to Scanner objects
    proj_scanners_dict: dict[str, Any] = {}
    if isinstance(proj.scanners, list):
        # Convert list to dict using scanner names from specs
        scanner_list = scanners_from_spec_list(proj.scanners)
        for spec, scanner in zip(proj.scanners, scanner_list, strict=True):
            proj_scanners_dict[spec.name] = scanner
    else:
        proj_scanners_dict = scanners_from_spec_dict(proj.scanners)

    # Merge: project scanners first, then scanjob scanners (scanjob wins on conflicts)
    scanjob._scanners = {**proj_scanners_dict, **scanjob._scanners}


def _merge_validation(proj: ProjectConfig, scanjob: ScanJob) -> None:
    """Merge validation - union of dicts, scanjob wins on key conflicts."""
    if proj.validation is None:
        return

    # Resolve project validation config (may be str paths or ValidationSet objects)
    resolved_proj_validation = _resolve_validation_config(proj.validation)

    if scanjob._validation is None:
        scanjob._validation = resolved_proj_validation
    else:
        # Union: project first, scanjob wins on conflicts
        scanjob._validation = {**resolved_proj_validation, **scanjob._validation}


def _resolve_validation_config(
    validation: dict[str, str | ValidationSet],
) -> dict[str, ValidationSet]:
    """Resolve validation config (str paths to ValidationSet objects)."""
    from inspect_scout._validation import validation_set

    result: dict[str, ValidationSet] = {}
    for key, value in validation.items():
        if isinstance(value, str):
            result[key] = validation_set(value)
        else:
            result[key] = value
    return result


def _merge_tags(proj: ProjectConfig, scanjob: ScanJob) -> None:
    """Merge tags - union with deduplication, preserving order."""
    if proj.tags is None:
        return

    if scanjob._tags is None:
        scanjob._tags = list(proj.tags)
    else:
        # Union and deduplicate while preserving order
        seen: set[str] = set()
        merged_tags: list[str] = []
        for tag in list(proj.tags) + list(scanjob._tags):
            if tag not in seen:
                seen.add(tag)
                merged_tags.append(tag)
        scanjob._tags = merged_tags


def _merge_metadata(proj: ProjectConfig, scanjob: ScanJob) -> None:
    """Merge metadata - union of dicts, scanjob wins on key conflicts."""
    if proj.metadata is None:
        return

    if scanjob._metadata is None:
        scanjob._metadata = dict(proj.metadata)
    else:
        # Union: project first, scanjob wins on conflicts
        scanjob._metadata = {**proj.metadata, **scanjob._metadata}
