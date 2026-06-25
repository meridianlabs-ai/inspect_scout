from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path

import importlib_metadata
from inspect_ai._util.error import PrerequisiteError
from inspect_ai._util.module import load_module
from inspect_ai._util.path import cwd_relative_path
from inspect_ai._util.registry import registry_package_name
from pydantic import JsonValue, TypeAdapter

from .predicates import PredicateFn, ValidationPredicate, resolve_predicate
from .registry import (
    create_registered_predicate,
    is_registered_predicate,
    registered_predicate_file,
    registered_predicate_name,
    registered_predicate_params,
)
from .types import (
    PredicateSpec,
    RegisteredPredicateSpec,
    UnavailablePredicateSpec,
    ValidationSet,
    ValidationSetSpec,
)

logger = logging.getLogger(__name__)
_json_args = TypeAdapter(dict[str, JsonValue])


def validation_set_to_spec(
    validation: ValidationSet,
    *,
    scanner: str | None = None,
) -> ValidationSetSpec:
    """Create the data-only artifact representation of a validation set."""
    predicate = validation.predicate
    predicate_spec: PredicateSpec
    if predicate is None or isinstance(predicate, str):
        predicate_spec = predicate
    elif is_registered_predicate(predicate):
        name = registered_predicate_name(predicate)
        file = registered_predicate_file(predicate)
        package_name = registry_package_name(name) if file is None else None
        package_version: str | None = None
        if package_name:
            try:
                package_version = importlib_metadata.version(package_name)
            except importlib_metadata.PackageNotFoundError:
                pass
        predicate_spec = RegisteredPredicateSpec(
            name=name,
            args=_json_args.validate_python(registered_predicate_params(predicate)),
            file=cwd_relative_path(file) if file else None,
            package_version=package_version,
        )
    else:
        display_name = getattr(predicate, "__name__", None)
        predicate_spec = UnavailablePredicateSpec(
            display_name=display_name,
            reason="anonymous",
        )
        scanner_context = f" for scanner '{scanner}'" if scanner else ""
        logger.warning(
            "Custom validation predicate%s is not registered and will not be "
            "available from the scan artifact during resume. Register it with "
            "@validation_predicate or supply predicate_overrides.",
            scanner_context,
        )

    return ValidationSetSpec(
        cases=validation.cases,
        predicate=predicate_spec,
        split=validation.split,
    )


def validation_sets_to_specs(
    validation: dict[str, ValidationSet] | None,
) -> dict[str, ValidationSetSpec] | None:
    """Create data-only validation specs for a scan artifact."""
    if validation is None:
        return None
    return {
        scanner: validation_set_to_spec(validation_set, scanner=scanner)
        for scanner, validation_set in validation.items()
    }


def validation_sets_from_specs(
    validation: dict[str, ValidationSetSpec] | None,
    predicate_overrides: Mapping[str, PredicateFn] | None = None,
) -> dict[str, ValidationSet] | None:
    """Create runtime validation sets at the explicit resume boundary."""
    if validation is None:
        if predicate_overrides:
            raise PrerequisiteError(
                "Predicate overrides were provided, but this scan has no validation."
            )
        return None

    overrides = dict(predicate_overrides or {})
    custom_scanners = {
        scanner
        for scanner, validation_set in validation.items()
        if isinstance(
            validation_set.predicate,
            RegisteredPredicateSpec | UnavailablePredicateSpec,
        )
    }
    unknown_overrides = set(overrides) - custom_scanners
    if unknown_overrides:
        raise PrerequisiteError(
            "Predicate overrides do not match custom validation predicates: "
            + ", ".join(sorted(unknown_overrides))
        )

    missing_overrides = {
        scanner
        for scanner, validation_set in validation.items()
        if isinstance(validation_set.predicate, UnavailablePredicateSpec)
        and scanner not in overrides
    }
    if missing_overrides:
        raise PrerequisiteError(
            "This scan contains unavailable custom validation predicates for: "
            + ", ".join(sorted(missing_overrides))
            + ". Resume from the original trusted scan configuration or supply "
            "predicate_overrides."
        )

    runtime: dict[str, ValidationSet] = {}
    loaded_files: set[str] = set()
    for scanner, validation_set in validation.items():
        predicate_spec = validation_set.predicate
        override = overrides.get(scanner)
        predicate: ValidationPredicate | None
        if override is not None:
            resolve_predicate(override)
            predicate = override
        elif isinstance(predicate_spec, RegisteredPredicateSpec):
            if predicate_spec.file and predicate_spec.file not in loaded_files:
                load_module(Path(predicate_spec.file))
                loaded_files.add(predicate_spec.file)
            predicate = create_registered_predicate(
                predicate_spec.name,
                predicate_spec.args,
            )
        elif isinstance(predicate_spec, UnavailablePredicateSpec):
            raise AssertionError("Unavailable predicates require an override.")
        else:
            predicate = predicate_spec

        runtime[scanner] = ValidationSet(
            cases=validation_set.cases,
            predicate=predicate,
            split=validation_set.split,
        )

    return runtime
