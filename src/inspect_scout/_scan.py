import json
import os
import sys
import traceback
from logging import getLogger
from pathlib import Path
from typing import Any, AsyncIterator, Mapping, Sequence

import anyio
import yaml
from anyio.abc import TaskGroup
from dotenv import find_dotenv, load_dotenv
from inspect_ai._eval.context import init_model_context
from inspect_ai._util._async import run_coroutine
from inspect_ai._util.background import set_background_task_group
from inspect_ai._util.config import resolve_args
from inspect_ai._util.error import PrerequisiteError
from inspect_ai._util.path import pretty_path
from inspect_ai._util.platform import platform_init as init_platform
from inspect_ai._util.rich import rich_traceback
from inspect_ai.model._generate_config import GenerateConfig
from inspect_ai.model._model import Model, init_model_usage, model_usage, resolve_models
from inspect_ai.model._model_config import (
    model_config_to_model,
    model_roles_config_to_model_roles,
)
from inspect_ai.model._util import resolve_model_roles
from inspect_ai.util._anyio import inner_exception
from pydantic import TypeAdapter
from rich.console import RenderableType

from inspect_scout._util.attachments import resolve_event_attachments
from inspect_scout._validation.types import ValidationSet
from inspect_scout._view.notify import view_notify_scan

from ._concurrency.common import ParseFunctionResult, ParseJob, ScannerJob
from ._concurrency.multi_process import multi_process_strategy
from ._concurrency.single_process import single_process_strategy
from ._display._display import (
    DisplayType,
    display,
    display_type_initialized,
    init_display_type,
)
from ._recorder.factory import (
    scan_recorder_for_location,
    scan_recorder_type_for_location,
)
from ._recorder.recorder import ScanRecorder, Status
from ._scancontext import ScanContext, create_scan, resume_scan
from ._scanjob import ScanJob, ScanJobConfig
from ._scanner.loader import config_for_loader
from ._scanner.result import Error, Result, ResultReport
from ._scanner.scanner import Scanner, config_for_scanner
from ._scanner.types import ScannerInput
from ._scanner.util import get_input_type_and_ids
from ._scanspec import ScannerWork, ScanSpec
from ._transcript.transcripts import Transcripts
from ._transcript.types import (
    Transcript,
    TranscriptContent,
    TranscriptInfo,
)
from ._transcript.util import union_transcript_contents
from ._util.constants import DEFAULT_MAX_TRANSCRIPTS
from ._util.log import init_log
from ._util.process import default_max_processes

logger = getLogger(__name__)


def scan(
    scanners: Sequence[Scanner[ScannerInput] | tuple[str, Scanner[ScannerInput]]]
    | dict[str, Scanner[ScannerInput]]
    | ScanJob
    | ScanJobConfig,
    transcripts: Transcripts | None = None,
    results: str | None = None,
    worklist: Sequence[ScannerWork] | str | Path | None = None,
    validation: ValidationSet | dict[str, ValidationSet] | None = None,
    model: str | Model | None = None,
    model_config: GenerateConfig | None = None,
    model_base_url: str | None = None,
    model_args: dict[str, Any] | str | None = None,
    model_roles: dict[str, str | Model] | None = None,
    max_transcripts: int | None = None,
    max_processes: int | None = None,
    limit: int | None = None,
    shuffle: bool | int | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    display: DisplayType | None = None,
    log_level: str | None = None,
) -> Status:
    """Scan transcripts.

    Scan transcripts using one or more scanners. Note that scanners must each
    have a unique name. If you have more than one instance of a scanner
    with the same name, numbered prefixes will be automatically assigned.
    Alternatively, you can pass tuples of (name,scanner) or a dict with
    explicit names for each scanner.

    Args:
        scanners: Scanners to execute (list, dict with explicit names, or ScanJob). If a `ScanJob` or `ScanJobConfig` is specified, then its options are used as the default options for the scan.
        transcripts: Transcripts to scan.
        results: Location to write results (filesystem or S3 bucket). Defaults to "./scans".
        worklist: Transcript ids to process for each scanner (defaults to processing all transcripts). Either a list of `ScannerWork` or a YAML or JSON file contianing the same.
        validation: Validation cases to evaluate for scanners.
        model: Model to use for scanning by default (individual scanners can always
            call `get_model()` to us arbitrary models). If not specified use the value of the SCOUT_SCAN_MODEL environment variable.
        model_config: `GenerationConfig` for calls to the model.
        model_base_url: Base URL for communicating with the model API.
        model_args: Model creation args (as a dictionary or as a path to a JSON or YAML config file).
        model_roles: Named roles for use in `get_model()`.
        max_transcripts: The maximum number of transcripts to process concurrently (this also serves as the default value for `max_connections`). Defaults to 25.
        max_processes: The maximum number of concurrent processes (for multiproccesing). Defaults to `multiprocessing.cpu_count()`.
        limit: Limit the number of transcripts processed.
        shuffle: Shuffle the order of transcripts (pass an `int` to set a seed for shuffling).
        tags: One or more tags for this scan.
        metadata: Metadata for this scan.
        display: Display type: "rich", "plain", or "none" (defaults to "rich").
        log_level: Level for logging to the console: "debug", "http", "sandbox",
            "info", "warning", "error", "critical", or "notset" (defaults to "warning")

    Returns:
        ScanStatus: Status of scan (spec, completion, summary, errors, etc.)
    """
    top_level_sync_init(display)

    return run_coroutine(
        scan_async(
            scanners=scanners,
            transcripts=transcripts,
            results=results,
            worklist=worklist,
            validation=validation,
            model=model,
            model_config=model_config,
            model_base_url=model_base_url,
            model_args=model_args,
            model_roles=model_roles,
            max_transcripts=max_transcripts,
            max_processes=max_processes,
            limit=limit,
            shuffle=shuffle,
            tags=tags,
            metadata=metadata,
            log_level=log_level,
        )
    )


async def scan_async(
    scanners: Sequence[Scanner[ScannerInput] | tuple[str, Scanner[ScannerInput]]]
    | dict[str, Scanner[ScannerInput]]
    | ScanJob
    | ScanJobConfig,
    transcripts: Transcripts | None = None,
    results: str | None = None,
    worklist: Sequence[ScannerWork] | str | Path | None = None,
    validation: ValidationSet | dict[str, ValidationSet] | None = None,
    model: str | Model | None = None,
    model_config: GenerateConfig | None = None,
    model_base_url: str | None = None,
    model_args: dict[str, Any] | str | None = None,
    model_roles: dict[str, str | Model] | None = None,
    max_transcripts: int | None = None,
    max_processes: int | None = None,
    limit: int | None = None,
    shuffle: bool | int | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    log_level: str | None = None,
) -> Status:
    """Scan transcripts.

    Scan transcripts using one or more scanners. Note that scanners must each
    have a unique name. If you have more than one instance of a scanner
    with the same name, numbered prefixes will be automatically assigned.
    Alternatively, you can pass tuples of (name,scanner) or a dict with
    explicit names for each scanner.

    Args:
        scanners: Scanners to execute (list, dict with explicit names, or ScanJob). If a `ScanJob` or `ScanJobConfig` is specified, then its options are used as the default options for the scan.
        transcripts: Transcripts to scan.
        results: Location to write results (filesystem or S3 bucket). Defaults to "./scans".
        worklist: Transcript ids to process for each scanner (defaults to processing all transcripts). Either a list of `ScannerWork` or a YAML or JSON file contianing the same.
        validation: Validation cases to apply for scanners.
        model: Model to use for scanning by default (individual scanners can always
            call `get_model()` to us arbitrary models). If not specified use the value of the SCOUT_SCAN_MODEL environment variable.
        model_config: `GenerationConfig` for calls to the model.
        model_base_url: Base URL for communicating with the model API.
        model_args: Model creation args (as a dictionary or as a path to a JSON or YAML config file).
        model_roles: Named roles for use in `get_model()`.
        max_transcripts: The maximum number of transcripts to process concurrently (this also serves as the default value for `max_connections`). Defaults to 25.
        max_processes: The maximum number of concurrent processes (for multiproccesing). Defaults to `multiprocessing.cpu_count()`.
        limit: Limit the number of transcripts processed.
        shuffle: Shuffle the order of transcripts (pass an `int` to set a seed for shuffling).
        tags: One or more tags for this scan.
        metadata: Metadata for this scan.
        log_level: Level for logging to the console: "debug", "http", "sandbox",
            "info", "warning", "error", "critical", or "notset" (defaults to "warning")

    Returns:
        ScanStatus: Status of scan (spec, completion, summary, errors, etc.)
    """
    top_level_async_init(log_level)

    # resolve worklist
    if isinstance(worklist, str | Path):
        worklist = _worklist_from(worklist)

    # resolve scanjob
    if isinstance(scanners, ScanJob):
        scanjob = scanners
    elif isinstance(scanners, ScanJobConfig):
        scanjob = ScanJob.from_config(scanners)
    else:
        scanjob = ScanJob(scanners=scanners, worklist=worklist)

    # see if we are overriding the scanjob with additional args
    scanjob._transcripts = transcripts or scanjob.transcripts
    if scanjob._transcripts is None:
        raise ValueError("No 'transcripts' specified for scan.")

    # resolve results
    scanjob._results = (
        results or scanjob._results or str(os.getenv("SCOUT_SCAN_RESULTS", "./scans"))
    )

    # resolve validation
    if validation is not None:
        scanjob._validation = _resolve_validation(validation, scanjob)

    # initialize scan config
    scanjob._max_transcripts = (
        max_transcripts or scanjob._max_transcripts or DEFAULT_MAX_TRANSCRIPTS
    )
    scanjob._max_processes = (
        max_processes or scanjob._max_processes or default_max_processes()
    )
    scanjob._limit = limit or scanjob._limit
    scanjob._shuffle = shuffle if shuffle is not None else scanjob._shuffle

    # tags and metadata
    scanjob._tags = tags
    scanjob._metadata = metadata

    # derive max_connections if not specified
    scanjob._generate_config = (
        model_config or scanjob._generate_config or GenerateConfig()
    )
    if scanjob._generate_config.max_connections is None:
        scanjob._generate_config.max_connections = scanjob._max_transcripts

    # initialize runtime context
    resolved_model, resolved_model_args, resolved_model_roles = init_scan_model_context(
        model=model or scanjob._model,
        model_config=model_config or scanjob._generate_config,
        model_base_url=model_base_url or scanjob._model_base_url,
        model_args=model_args or scanjob._model_base_url,
        model_roles=model_roles or scanjob._model_roles,
    )
    scanjob._model = resolved_model
    scanjob._model_args = resolved_model_args
    scanjob._model_roles = resolved_model_roles

    # create job and recorder
    scan = await create_scan(scanjob)
    recorder = scan_recorder_for_location(scanjob._results)
    await recorder.init(scan.spec, scanjob._results)

    # run the scan
    return await _scan_async(scan=scan, recorder=recorder)


def scan_resume(
    scan_location: str,
    display: DisplayType | None = None,
    log_level: str | None = None,
) -> Status:
    """Resume a previous scan.

    Args:
       scan_location: Scan location to resume from.
       display: Display type: "rich", "plain", or "none" (defaults to "rich").
       log_level: Level for logging to the console: "debug", "http", "sandbox",
            "info", "warning", "error", "critical", or "notset" (defaults to "warning")

    Returns:
       ScanStatus: Status of scan (spec, completion, summary, errors, etc.)
    """
    top_level_sync_init(display)
    return run_coroutine(scan_resume_async(scan_location, log_level=log_level))


async def scan_resume_async(scan_location: str, log_level: str | None = None) -> Status:
    """Resume a previous scan.

    Args:
       scan_location: Scan location to resume from.
       log_level: Level for logging to the console: "debug", "http", "sandbox",
            "info", "warning", "error", "critical", or "notset" (defaults to "warning")

    Returns:
       ScanStatus: Status of scan (spec, completion, summary, errors, etc.)
    """
    top_level_async_init(log_level)

    # resume job
    scan = await resume_scan(scan_location)

    # can't resume a job with non-deterministic shuffling
    if scan.spec.options.shuffle is True:
        raise RuntimeError(
            "Cannot resume scans with transcripts shuffled without a seed."
        )

    # create model
    if scan.spec.model is not None:
        model = model_config_to_model(scan.spec.model)
    else:
        model = None

    # create/initialize models then call init runtime context
    init_scan_model_context(
        model=model,
        model_roles=model_roles_config_to_model_roles(scan.spec.model_roles),
    )

    # create recorder and scan
    recorder = scan_recorder_for_location(scan_location)
    await recorder.resume(scan_location)
    return await _scan_async(scan=scan, recorder=recorder)


def scan_complete(
    scan_location: str,
    display: DisplayType | None = None,
    log_level: str | None = None,
) -> Status:
    """Complete a scan.

    This function is used to indicate that a scan with errors in some
    transcripts should be completed in spite of the errors.

    Args:
       scan_location: Scan location to complete.
       display: Display type: "rich", "plain", or "none" (defaults to "rich").
       log_level: Level for logging to the console: "debug", "http", "sandbox",
            "info", "warning", "error", "critical", or "notset" (defaults to "warning")

    Returns:
       ScanStatus: Status of scan (spec, summary, errors, etc.)
    """
    top_level_sync_init(display)

    return run_coroutine(scan_complete_async(scan_location, log_level=log_level))


async def scan_complete_async(
    scan_location: str, log_level: str | None = None
) -> Status:
    """Complete a scan.

    This function is used to indicate that a scan with errors in some
    transcripts should be completed in spite of the errors.

    Args:
       scan_location: Scan location to complete.
       log_level: Level for logging to the console: "debug", "http", "sandbox",
            "info", "warning", "error", "critical", or "notset" (defaults to "warning")

    Returns:
       ScanStatus: Status of scan (spec, summary, errors, etc.)
    """
    top_level_async_init(log_level)

    # check if the scan is already complete
    recorder_type = scan_recorder_type_for_location(scan_location)
    status = await recorder_type.status(scan_location)
    if status.complete:
        raise PrerequisiteError(
            f"Scan at '{pretty_path(scan_location)}' is already complete."
        )

    # complete the scan
    status = await recorder_type.complete(scan_location)
    display().scan_complete(status)
    return status


_scan_async_running = False


async def _scan_async(*, scan: ScanContext, recorder: ScanRecorder) -> Status:
    result: Status | None = None

    async def run(tg: TaskGroup) -> None:
        try:
            nonlocal result
            result = await _scan_async_inner(scan=scan, recorder=recorder, tg=tg)
        finally:
            tg.cancel_scope.cancel()

    global _scan_async_running
    if _scan_async_running:
        raise RuntimeError(
            "You can only have a single scan running at once in a process."
        )
    _scan_async_running = True

    try:
        async with anyio.create_task_group() as tg:
            tg.start_soon(run, tg)
    except Exception as ex:
        raise inner_exception(ex) from None
    except anyio.get_cancelled_exc_class():
        # Cancelled exceptions are expected and handled by _scan_async_inner
        pass
    finally:
        _scan_async_running = False

    assert result is not None, "scan async did not return a result."

    return result


async def _scan_async_inner(
    *, scan: ScanContext, recorder: ScanRecorder, tg: TaskGroup
) -> Status:
    """Execute a scan by orchestrating concurrent scanner execution across transcripts.

    This function is the orchestration layer that coordinates scanner execution
    with a focus on maximizing LLM call throughput. Since scanners often make LLM
    calls, which are orders of magnitude slower than local computation, the primary
    optimization goal is to keep `max_transcripts` concurrent LLM calls in flight
    at all times.

    Args:
        scan: The scan context containing scanners, transcripts, and configuration
        recorder: The scan recorder for tracking completed work and persisting results
        tg: Task group we are running within

    Returns:
        ScanStatus indicating completion status, spec, and location for resumption
    """
    try:
        # set background task group for this coroutine (used by batching)
        set_background_task_group(tg)

        # apply limits/shuffle
        transcripts = scan.transcripts
        if scan.spec.options.limit is not None:
            transcripts = transcripts.limit(scan.spec.options.limit)
        if scan.spec.options.shuffle is not None:
            transcripts = transcripts.shuffle(
                scan.spec.options.shuffle
                if isinstance(scan.spec.options.shuffle, int)
                else None
            )

        async with transcripts:
            # Count already-completed scans to initialize progress
            scanner_names_list = list(scan.scanners.keys())
            skipped_scans = 0
            for transcript_info in await transcripts.index():
                for name in scanner_names_list:
                    if await recorder.is_recorded(transcript_info, name):
                        skipped_scans += 1

            # start scan
            with display().scan_display(
                scan=scan,
                scan_location=await recorder.location(),
                summary=await recorder.summary(),
                transcripts=await transcripts.count(),
                skipped=skipped_scans,
            ) as scan_display:
                # Build scanner list and union content for index resolution
                scanners_list = list(scan.scanners.values())
                union_content = union_transcript_contents(
                    [
                        _content_for_scanner(scanner)
                        for scanner in scan.scanners.values()
                    ]
                )

                async def _parse_function(job: ParseJob) -> ParseFunctionResult:
                    try:
                        union_transcript = await transcripts._read(  # pylint: disable=protected-access
                            job.transcript_info, union_content
                        )
                        return (
                            True,
                            [
                                ScannerJob(
                                    union_transcript=union_transcript,
                                    scanner=scanners_list[idx],
                                    scanner_name=scanner_names_list[idx],
                                )
                                for idx in job.scanner_indices
                            ],
                        )
                    except Exception as ex:  # pylint: disable=W0718
                        # Create error ResultReport for each affected scanner
                        return (
                            False,
                            _reports_for_parse_error(job, ex, scanner_names_list),
                        )

                async def _scan_function(job: ScannerJob) -> list[ResultReport]:
                    from inspect_ai.log._transcript import (
                        Transcript as InspectTranscript,
                    )
                    from inspect_ai.log._transcript import init_transcript

                    # the code below might get called many times (e.g. if the scanner
                    # task message or event or list[message], list[event] or if it has
                    # a custom loader:
                    # 1) Is there a loader? If so it's a generator that will yield
                    #    scanner inputs.
                    # 2) We need to reflect the signature of the scanner fn -- either
                    #    by introspecting or by synthesizing a loader

                    # initialize model_usage tracking for this coroutine
                    init_model_usage()

                    inspect_transcript = InspectTranscript()
                    init_transcript(inspect_transcript)

                    results: list[ResultReport] = []

                    scanner_config = config_for_scanner(job.scanner)
                    loader = scanner_config.loader

                    async for loader_result in loader(job.union_transcript):
                        try:
                            result: Result | None = None
                            error: Error | None = None

                            type_and_ids = get_input_type_and_ids(loader_result)
                            if type_and_ids is None:
                                continue

                            result = await job.scanner(loader_result)

                        # Special case for errors that should bring down the scan
                        except PrerequisiteError:
                            raise

                        except Exception as ex:  # pylint: disable=W0718
                            error = Error(
                                transcript_id=job.union_transcript.id,
                                scanner=job.scanner_name,
                                error=str(ex),
                                traceback=traceback.format_exc(),
                            )

                        # Always append a result (success or error) if we have type_and_ids
                        if type_and_ids is not None:
                            results.append(
                                ResultReport(
                                    input_type=type_and_ids[0],
                                    input_ids=type_and_ids[1],
                                    input=loader_result,
                                    result=result,
                                    error=error,
                                    events=resolve_event_attachments(
                                        inspect_transcript
                                    ),
                                    model_usage=model_usage(),
                                )
                            )

                    return results

                prefetch_multiple = 1.0
                max_tasks = (scan.spec.options.max_transcripts or 25) * len(
                    scan.scanners
                )

                diagnostics = os.getenv("SCOUT_DIAGNOSTICS", "false").lower() in (
                    "1",
                    "true",
                    "yes",
                )
                strategy = (
                    single_process_strategy(
                        task_count=max_tasks,
                        prefetch_multiple=prefetch_multiple,
                        diagnostics=diagnostics,
                    )
                    if scan.spec.options.max_processes == 1 or os.name == "nt"
                    else multi_process_strategy(
                        process_count=scan.spec.options.max_processes,
                        task_count=max_tasks,
                        prefetch_multiple=prefetch_multiple,
                        diagnostics=diagnostics,
                    )
                )

                async def record_results(
                    transcript: TranscriptInfo,
                    scanner: str,
                    results: Sequence[ResultReport],
                ) -> None:
                    await recorder.record(transcript, scanner, results)
                    scan_display.results(transcript, scanner, results)

                await strategy(
                    parse_jobs=_parse_jobs(scan, recorder, transcripts),
                    parse_function=_parse_function,
                    scan_function=_scan_function,
                    record_results=record_results,
                    update_metrics=scan_display.metrics,
                )

                # report status
                errors = await recorder.errors()
                if len(errors) > 0:
                    scan_status = Status(
                        complete=False,
                        spec=scan.spec,
                        location=await recorder.location(),
                        summary=await recorder.summary(),
                        errors=errors,
                    )
                else:
                    scan_status = await recorder.complete(await recorder.location())

        # report scan complete
        display().scan_complete(scan_status)

        # notify view
        view_notify_scan(scan_status.location)

        # return status
        return scan_status

    except Exception as ex:
        type, value, tb = sys.exc_info()
        type = type if type else BaseException
        value = value if value else ex
        rich_tb = rich_traceback(type, value, tb)
        return await handle_scan_interrupted(rich_tb, scan.spec, recorder)

    except anyio.get_cancelled_exc_class():
        return await handle_scan_interrupted("Aborted!", scan.spec, recorder)


def top_level_sync_init(display: DisplayType | None) -> None:
    init_environment()
    init_display_type(display)


def top_level_async_init(log_level: str | None) -> None:
    init_platform(hooks=False)
    init_environment()
    if not display_type_initialized():
        init_display_type("plain")
    init_log(log_level)


def init_environment() -> None:
    global _initialized_environment
    if not _initialized_environment:
        dotenv_file = find_dotenv(usecwd=True)
        load_dotenv(dotenv_file)
        _initialized_environment = True


_initialized_environment: bool = False


def init_scan_model_context(
    model: str | Model | None = None,
    model_config: GenerateConfig | None = None,
    model_base_url: str | None = None,
    model_args: dict[str, Any] | str | None = None,
    model_roles: Mapping[str, str | Model] | None = None,
) -> tuple[Model, dict[str, Any], dict[str, Model] | None]:
    # resolve from inspect eval model env var if rquired
    if model is None:
        model = os.getenv("SCOUT_SCAN_MODEL", None)

    # init model context
    resolved_model_args = resolve_args(model_args or {})
    model = resolve_models(
        model, model_base_url, resolved_model_args, model_config or GenerateConfig()
    )[0]
    resolved_model_roles = resolve_model_roles(model_roles)
    init_model_context(
        model=model,
        model_roles=resolved_model_roles,
        config=model_config or GenerateConfig(),
    )

    return model, resolved_model_args, resolved_model_roles


async def handle_scan_interrupted(
    message: RenderableType, spec: ScanSpec, recorder: ScanRecorder
) -> Status:
    status = Status(
        complete=False,
        spec=spec,
        location=await recorder.location(),
        summary=await recorder.summary(),
        errors=await recorder.errors(),
    )

    display().scan_interrupted(message, status)

    return status


async def _parse_jobs(
    context: ScanContext,
    recorder: ScanRecorder,
    transcripts: Transcripts,
) -> AsyncIterator[ParseJob]:
    """Yield `ParseJob` objects for transcripts needing scanning.

    This encapsulates the logic for:
    - Determining union content once
    - Skipping already recorded (per-scanner) work
    - Grouping scanners per transcript
    """
    # Build name->index mapping for scanners
    scanner_names = list(context.scanners.keys())
    name_to_index = {name: idx for idx, name in enumerate(scanner_names)}

    # build scanner->transcript_ids map from worklist
    scanner_to_transcript_ids = {
        work.scanner: work.transcripts for work in context.worklist
    }

    for transcript_info in await transcripts.index():
        scanner_indices_for_transcript: list[int] = []
        for name in scanner_names:
            # if its not in the worklist then move on
            if transcript_info.id not in scanner_to_transcript_ids.get(name, []):
                continue
            # if its already recorded then move on
            if await recorder.is_recorded(transcript_info, name):
                continue
            scanner_indices_for_transcript.append(name_to_index[name])
        if not scanner_indices_for_transcript:
            continue
        yield ParseJob(
            transcript_info=transcript_info,
            scanner_indices=set(scanner_indices_for_transcript),
        )


def _content_for_scanner(scanner: Scanner[ScannerInput]) -> TranscriptContent:
    """
    Grab the TranscriptContent for the passed scanner

    This logic relies on the fact that the loader used alongside this scanner has
    adopted the filter from the scanner as appropriate.
    """
    return config_for_loader(config_for_scanner(scanner).loader).content


def _reports_for_parse_error(
    job: ParseJob, exception: Exception, scanner_names: list[str]
) -> list[ResultReport]:
    # Create placeholder transcript since parse failed
    placeholder_transcript = Transcript(
        id=job.transcript_info.id,
        source_id=job.transcript_info.source_id,
        source_uri=job.transcript_info.source_uri,
        metadata=job.transcript_info.metadata,
        messages=[],
        events=[],
    )
    return [
        ResultReport(
            input_type="transcript",
            input_ids=[job.transcript_info.id],
            input=placeholder_transcript,
            result=None,
            error=Error(
                transcript_id=job.transcript_info.id,
                scanner=scanner_names[idx],
                error=str(exception),
                traceback=traceback.format_exc(),
            ),
            events=[],
            model_usage={},
        )
        for idx in job.scanner_indices
    ]


def _worklist_from(file: str | Path) -> list[ScannerWork]:
    with open(file, "r") as f:
        contents = f.read().strip()

    if contents.startswith("["):
        data = json.loads(contents)
    else:
        data = yaml.safe_load(contents)

    if not isinstance(data, list):
        raise PrerequisiteError(
            f"Worklist data from JSON or YAML file must be a list (found type {type(data)})"
        )

    # validate with pydantic
    adapter = TypeAdapter[list[ScannerWork]](list[ScannerWork])
    return adapter.validate_python(data)


def _resolve_validation(
    validation: ValidationSet | dict[str, ValidationSet],
    scanjob: ScanJob,
) -> dict[str, ValidationSet]:
    if isinstance(validation, dict):
        # confirm all keys correspond to scanners
        for s in validation.keys():
            if s not in scanjob.scanners:
                raise ValueError(
                    f"Validation referended scanner '{s}' however there is no scanner of that name passed to the scan."
                )

        return validation
    else:
        # if a  single validation set was passed then confirm
        # that there is only a single scanner
        if len(scanjob.scanners) > 1:
            raise ValueError(
                "Validation sets must be specified as a dict of scanner:validation when there is more than one scanner."
            )
        return {next(iter(scanjob.scanners)): validation}
