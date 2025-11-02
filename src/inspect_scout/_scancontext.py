from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence, Set, cast

import importlib_metadata
from inspect_ai._util.constants import PKG_NAME as INSPECT_PKG_NAME
from inspect_ai._util.error import PrerequisiteError
from inspect_ai._util.git import git_context
from inspect_ai._util.module import load_module
from inspect_ai._util.path import cwd_relative_path
from inspect_ai._util.registry import (
    is_registry_object,
    registry_log_name,
    registry_params,
)
from inspect_ai.model._model import ModelName
from inspect_ai.model._model_config import (
    ModelConfig,
    model_args_for_log,
    model_roles_to_model_roles_config,
)

from inspect_scout._util.constants import DEFAULT_MAX_TRANSCRIPTS, PKG_NAME
from inspect_scout._util.process import default_max_processes
from inspect_scout._validation.types import ValidationSet

from ._recorder.factory import scan_recorder_type_for_location
from ._scanjob import SCANJOB_FILE_ATTR, ScanJob
from ._scanner.scanner import SCANNER_FILE_ATTR, Scanner, scanner_create
from ._scanner.types import ScannerInput
from ._scanspec import (
    ScannerSpec,
    ScannerWork,
    ScanOptions,
    ScanRevision,
    ScanSpec,
)
from ._transcript.database import transcripts_from_snapshot
from ._transcript.transcripts import Transcripts


@dataclass
class ScanContext:
    spec: ScanSpec
    """Scan specification."""

    transcripts: Transcripts
    """Corpus of transcripts to scan."""

    scanners: dict[str, Scanner[Any]]
    """Scanners to apply to transcripts."""

    worklist: Sequence[ScannerWork]
    """Transcript ids to process for each scanner."""

    validation: dict[str, ValidationSet] | None
    """Validation cases to apply for scanners."""


async def create_scan(scanjob: ScanJob) -> ScanContext:
    if scanjob.transcripts is None:
        raise PrerequisiteError("No transcripts specified for scan.")

    # get revision and package version
    git = git_context()
    revision = (
        ScanRevision(type="git", origin=git.origin, commit=git.commit) if git else None
    )
    packages = {
        INSPECT_PKG_NAME: importlib_metadata.version(INSPECT_PKG_NAME),
        PKG_NAME: importlib_metadata.version(PKG_NAME),
    }

    # create options
    options = ScanOptions(
        max_transcripts=scanjob.max_transcripts or DEFAULT_MAX_TRANSCRIPTS,
        max_processes=scanjob.max_processes or default_max_processes(),
        limit=scanjob.limit,
        shuffle=scanjob.shuffle,
    )

    # resolve model
    model = scanjob.model or None

    # create scan spec
    async with scanjob.transcripts:
        spec = ScanSpec(
            scan_file=job_file(scanjob),
            scan_name=scanjob.name,
            scan_args=job_args(scanjob),
            options=options or ScanOptions(),
            transcripts=await scanjob.transcripts.snapshot(),
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
        worklist=scanjob.worklist
        if scanjob.worklist is not None
        else await _default_worklist(
            scanjob.transcripts, list(scanjob.scanners.keys())
        ),
        validation=scanjob.validation,
    )


async def resume_scan(scan_location: str) -> ScanContext:
    # load the spec
    recorder_type = scan_recorder_type_for_location(scan_location)
    status = await recorder_type.status(scan_location)
    if status.complete:
        raise PrerequisiteError(f"Scan at '{scan_location}' is already complete.")

    spec = status.spec
    transcripts = await transcripts_from_snapshot(spec.transcripts)
    scanners = _scanners_from_spec(spec.scanners)
    worklist = (
        spec.worklist
        if spec.worklist is not None
        else await _default_worklist(transcripts, list(scanners.keys()))
    )
    return ScanContext(
        spec=spec,
        transcripts=transcripts,
        scanners=scanners,
        worklist=worklist,
        validation=spec.validation,
    )


async def _default_worklist(
    transcripts: Transcripts, scanners: Sequence[str]
) -> Sequence[ScannerWork]:
    async with transcripts:
        transcript_ids = [tr.id for tr in await transcripts.index()]
        return [
            ScannerWork(scanner=scanner, transcripts=transcript_ids)
            for scanner in scanners
        ]


def _spec_scanners(
    scanners: dict[str, Scanner[Any]],
) -> dict[str, ScannerSpec]:
    return {
        k: ScannerSpec(
            name=registry_log_name(v), file=scanner_file(v), params=registry_params(v)
        )
        for k, v in scanners.items()
    }


def _scanners_from_spec(
    scanner_specs: dict[str, ScannerSpec],
) -> dict[str, Scanner[Any]]:
    loaded: Set[str] = set()
    scanners: dict[str, Scanner[Any]] = {}
    for name, scanner in scanner_specs.items():
        # we need to ensure that any files scanners were defined in have been loaded/parsed
        if scanner.file is not None and scanner.file not in loaded:
            load_module(Path(scanner.file))
            loaded.add(scanner.file)

        # create the scanner
        scanners[name] = scanner_create(scanner.name, scanner.params)

    return scanners


def scanner_from_spec(scanner: ScannerSpec) -> Scanner[Any]:
    if scanner.file is not None:
        load_module(Path(scanner.file))
    return scanner_create(scanner.name, scanner.params)


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
