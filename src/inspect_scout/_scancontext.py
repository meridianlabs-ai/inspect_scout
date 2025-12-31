from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence, Set, cast

import importlib_metadata
from inspect_ai._util.constants import PKG_NAME as INSPECT_PKG_NAME
from inspect_ai._util.error import PrerequisiteError
from inspect_ai._util.module import load_module
from inspect_ai._util.path import cwd_relative_path
from inspect_ai._util.registry import (
    is_registry_object,
    registry_info,
    registry_log_name,
    registry_package_name,
    registry_params,
)
from inspect_ai.model._model import ModelName
from inspect_ai.model._model_config import (
    ModelConfig,
    model_args_for_log,
    model_roles_to_model_roles_config,
)

from inspect_scout._transcript.factory import transcripts_from_snapshot
from inspect_scout._util.constants import (
    DEFAULT_MAX_TRANSCRIPTS,
    PKG_NAME,
)
from inspect_scout._util.revision import scan_revision
from inspect_scout._validation.types import ValidationSet

from ._recorder.factory import scan_recorder_type_for_location
from ._scanjob import SCANJOB_FILE_ATTR, ScanJob
from ._scanner.scanner import (
    SCANNER_FILE_ATTR,
    Scanner,
    scanner_create,
    scanner_version,
)
from ._scanspec import (
    ScannerSpec,
    ScanOptions,
    ScanSpec,
    Worklist,
)
from ._transcript.transcripts import Transcripts


@dataclass
class ScanContext:
    spec: ScanSpec
    """Scan specification."""

    transcripts: Transcripts
    """Corpus of transcripts to scan."""

    scanners: dict[str, Scanner[Any]]
    """Scanners to apply to transcripts."""

    worklist: Sequence[Worklist] | None
    """Transcript ids to process for each scanner."""

    validation: dict[str, ValidationSet] | None
    """Validation cases to apply for scanners."""


async def create_scan(scanjob: ScanJob) -> ScanContext:
    if scanjob.transcripts is None:
        raise PrerequisiteError("No transcripts specified for scan.")

    if scanjob.worklist and scanjob.limit is not None:
        raise PrerequisiteError("You cannot specify both a worklist and a limit")

    # get revision and package version
    revision = scan_revision()
    packages = {
        INSPECT_PKG_NAME: importlib_metadata.version(INSPECT_PKG_NAME),
        PKG_NAME: importlib_metadata.version(PKG_NAME),
    }

    # create options
    options = ScanOptions(
        max_transcripts=scanjob.max_transcripts or DEFAULT_MAX_TRANSCRIPTS,
        max_processes=scanjob.max_processes,
        limit=scanjob.limit,
        shuffle=scanjob.shuffle,
    )

    # resolve model
    model = scanjob.model or None

    # create scan spec
    spec = ScanSpec(
        scan_file=job_file(scanjob),
        scan_name=scanjob.name,
        scan_args=job_args(scanjob),
        options=options or ScanOptions(),
        scanners=_spec_scanners(scanjob.scanners),
        worklist=list(scanjob.worklist) if scanjob.worklist else None,
        validation=scanjob.validation,
        tags=scanjob.tags,
        metadata=scanjob.metadata,
        model=ModelConfig(
            model=str(ModelName(model)),
            config=model.config,
            base_url=model.api.base_url,
            args=model_args_for_log(scanjob.model_args or {}),
        )
        if model is not None
        else None,
        model_roles=model_roles_to_model_roles_config(scanjob.model_roles),
        revision=revision,
        packages=packages,
    )

    return ScanContext(
        spec=spec,
        transcripts=scanjob.transcripts,
        scanners=scanjob.scanners,
        worklist=scanjob.worklist,
        validation=scanjob.validation,
    )


async def resume_scan(scan_location: str) -> ScanContext:
    # load the spec
    recorder_type = scan_recorder_type_for_location(scan_location)
    status = await recorder_type.status(scan_location)
    if status.complete:
        raise PrerequisiteError(f"Scan at '{scan_location}' is already complete.")

    spec = status.spec
    if spec.transcripts is None:
        raise RuntimeError("Cannot resume scan because it has no transcripts snapshot.")
    transcripts = await transcripts_from_snapshot(spec.transcripts)
    scanners = scanners_from_spec_dict(spec.scanners)
    return ScanContext(
        spec=spec,
        transcripts=transcripts,
        scanners=scanners,
        worklist=spec.worklist,
        validation=spec.validation,
    )


def _spec_scanners(
    scanners: dict[str, Scanner[Any]],
) -> dict[str, ScannerSpec]:
    return {
        k: ScannerSpec(
            name=registry_log_name(v),
            version=scanner_version(v),
            package_version=_scanner_package_version(v),
            file=scanner_file(v),
            params=registry_params(v),
        )
        for k, v in scanners.items()
    }


def _scanner_package_version(scanner: Scanner[Any]) -> str | None:
    package_name = registry_package_name(registry_info(scanner).name)
    if package_name is not None:
        return importlib_metadata.version(package_name)
    else:
        return None


def scanners_from_spec_dict(
    scanner_specs: dict[str, ScannerSpec],
) -> dict[str, Scanner[Any]]:
    scanners = scanners_from_spec_list(scanner_specs.values())
    return dict(zip(scanner_specs.keys(), scanners, strict=True))


def scanners_from_spec_list(
    scanner_specs: Iterable[ScannerSpec],
) -> list[Scanner[Any]]:
    loaded: Set[str] = set()
    scanners: list[Scanner[Any]] = []
    for scanner in scanner_specs:
        # we need to ensure that any files scanners were defined in have been loaded/parsed
        if scanner.file is not None and scanner.file not in loaded:
            load_scanner_file(Path(scanner.file))
            loaded.add(scanner.file)

        # create the scanner
        scanners.append(scanner_create(scanner.name, scanner.params))

    return scanners


def scanner_file(scanner: Scanner[Any]) -> str | None:
    file = cast(str | None, getattr(scanner, SCANNER_FILE_ATTR, None))
    if file:
        return cwd_relative_path(file)
    else:
        return None


def job_file(scanjob: ScanJob) -> str | None:
    file = cast(str | None, getattr(scanjob, SCANJOB_FILE_ATTR, None))
    if file:
        return cwd_relative_path(file)
    else:
        return None


def job_args(scanjob: ScanJob) -> dict[str, Any] | None:
    if is_registry_object(scanjob):
        return dict(registry_params(scanjob))
    else:
        return None


def load_scanner_file(file: Path) -> None:
    load_module(file)
