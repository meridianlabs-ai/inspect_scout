"""Merge project configuration into scan jobs."""

from typing import Any

from inspect_ai._util.config import resolve_args
from inspect_ai.model import GenerateConfig, get_model

from inspect_scout._scanjob import ScanJob
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._validation.types import ValidationSet

from .types import ProjectConfig


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
    if scanjob._results is None and proj.results is not None:
        scanjob._results = proj.results

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
