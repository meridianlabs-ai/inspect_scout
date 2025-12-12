import json
import os
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
from inspect_ai._util.constants import DEFAULT_MAX_CONNECTIONS_BATCH
from inspect_ai._util.error import PrerequisiteError
from inspect_ai._util.json import jsonable_python
from inspect_ai._util.path import pretty_path
from inspect_ai._util.platform import platform_init as init_platform
from inspect_ai.model._generate_config import GenerateConfig
from inspect_ai.model._model import Model, init_model_usage, model_usage, resolve_models
from inspect_ai.model._model_config import (
    model_config_to_model,
    model_roles_config_to_model_roles,
)
from inspect_ai.model._util import resolve_model_roles
from inspect_ai.util import span
from inspect_ai.util._anyio import inner_exception
from pydantic import TypeAdapter

from inspect_scout._concurrency._mp_common import set_log_level
from inspect_scout._scanner.metrics import metrics_accumulators
from inspect_scout._transcript.local_files_cache import (
    cleanup_task_files_cache,
    init_task_files_cache,
)
from inspect_scout._util.attachments import resolve_event_attachments
from inspect_scout._util.refusal import RefusalError
from inspect_scout._validation.types import ValidationSet
from inspect_scout._validation.validate import validate
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
from ._scanner.result import Error, Result, ResultReport, ResultValidation, as_resultset
from ._scanner.scanner import Scanner, config_for_scanner
from ._scanner.util import get_input_type_and_ids
from ._scanspec import ScanSpec, Worklist
from ._transcript.transcripts import ScannerWork, Transcripts, TranscriptsReader
from ._transcript.types import (
    Transcript,
    TranscriptContent,
    TranscriptInfo,
)
from ._transcript.util import union_transcript_contents
from ._util.constants import DEFAULT_MAX_TRANSCRIPTS
from ._util.log import init_log

logger = getLogger(__name__)


def scan(
    scanners: (
        Sequence[Scanner[Any] | tuple[str, Scanner[Any]]]
        | dict[str, Scanner[Any]]
        | ScanJob
        | ScanJobConfig
    ),
    transcripts: Transcripts | None = None,
    results: str | None = None,
    worklist: Sequence[ScannerWork] | Sequence[Worklist] | str | Path | None = None,
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
    fail_on_error: bool = False,
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
        worklist: Transcripts too process for each scanner (defaults to processing all transcripts). Either a list of `ScannerWork` or a YAML or JSON file with same.
        validation: Validation cases to evaluate for scanners.
        model: Model to use for scanning by default (individual scanners can always
            call `get_model()` to us arbitrary models). If not specified use the value of the SCOUT_SCAN_MODEL environment variable.
        model_config: `GenerationConfig` for calls to the model.
        model_base_url: Base URL for communicating with the model API.
        model_args: Model creation args (as a dictionary or as a path to a JSON or YAML config file).
        model_roles: Named roles for use in `get_model()`.
        max_transcripts: The maximum number of transcripts to process concurrently (this also serves as the default value for `max_connections`). Defaults to 25.
        max_processes: The maximum number of concurrent processes (for multiproccesing). Defaults to 4.
        limit: Limit the number of transcripts processed.
        shuffle: Shuffle the order of transcripts (pass an `int` to set a seed for shuffling).
        tags: One or more tags for this scan.
        metadata: Metadata for this scan.
        display: Display type: "rich", "plain", "log", or "none" (defaults to "rich").
        log_level: Level for logging to the console: "debug", "http", "sandbox",
            "info", "warning", "error", "critical", or "notset" (defaults to "warning")
        fail_on_error: Re-raise exceptions instead of capturing them in results. Defaults to False.

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
            fail_on_error=fail_on_error,
        )
    )


async def scan_async(
    scanners: (
        Sequence[Scanner[Any] | tuple[str, Scanner[Any]]]
        | dict[str, Scanner[Any]]
        | ScanJob
        | ScanJobConfig
    ),
    transcripts: Transcripts | None = None,
    results: str | None = None,
    worklist: Sequence[ScannerWork] | Sequence[Worklist] | str | Path | None = None,
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
    fail_on_error: bool = False,
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
        max_processes: The maximum number of concurrent processes (for multiproccesing). Defaults to 4.
        limit: Limit the number of transcripts processed.
        shuffle: Shuffle the order of transcripts (pass an `int` to set a seed for shuffling).
        tags: One or more tags for this scan.
        metadata: Metadata for this scan.
        log_level: Level for logging to the console: "debug", "http", "sandbox",
            "info", "warning", "error", "critical", or "notset" (defaults to "warning")
        fail_on_error: Re-raise exceptions instead of capturing them in results. Defaults to False.

    Returns:
        ScanStatus: Status of scan (spec, completion, summary, errors, etc.)
    """
    top_level_async_init(log_level)

    # resolve scanjob
    if isinstance(scanners, ScanJob):
        scanjob = scanners
    elif isinstance(scanners, ScanJobConfig):
        scanjob = ScanJob.from_config(scanners)
    else:
        scanjob = ScanJob(scanners=scanners, worklist=await _resolve_worklist(worklist))

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
        max_transcripts
        or scanjob._max_transcripts
        or (
            DEFAULT_MAX_TRANSCRIPTS
            if scanjob.generate_config is None or not scanjob.generate_config.batch
            else DEFAULT_MAX_CONNECTIONS_BATCH
        )
    )
    scanjob._max_processes = max_processes or scanjob._max_processes
    scanjob._limit = limit or scanjob._limit
    scanjob._shuffle = shuffle if shuffle is not None else scanjob._shuffle

    # tags and metadata
    scanjob._tags = tags or scanjob._tags
    scanjob._metadata = metadata or scanjob._metadata

    # derive max_connections if not specified
    scanjob._generate_config = (
        scanjob._generate_config.merge(model_config)
        if scanjob._generate_config and model_config
        else model_config or scanjob._generate_config or GenerateConfig()
    )
    if scanjob._generate_config.max_connections is None:
        scanjob._generate_config.max_connections = scanjob._max_transcripts

    # initialize runtime context
    resolved_model, resolved_model_args, resolved_model_roles = init_scan_model_context(
        model=model or scanjob._model,
        model_config=scanjob._generate_config,
        model_base_url=model_base_url or scanjob._model_base_url,
        model_args=model_args or scanjob._model_args,
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
    return await _scan_async(scan=scan, recorder=recorder, fail_on_error=fail_on_error)


def scan_resume(
    scan_location: str,
    display: DisplayType | None = None,
    log_level: str | None = None,
    fail_on_error: bool = False,
) -> Status:
    """Resume a previous scan.

    Args:
       scan_location: Scan location to resume from.
       display: Display type: "rich", "plain", "log", or "none" (defaults to "rich").
       log_level: Level for logging to the console: "debug", "http", "sandbox",
            "info", "warning", "error", "critical", or "notset" (defaults to "warning")
       fail_on_error: Re-raise exceptions instead of capturing them in results.

    Returns:
       ScanStatus: Status of scan (spec, completion, summary, errors, etc.)
    """
    top_level_sync_init(display)
    return run_coroutine(
        scan_resume_async(
            scan_location, log_level=log_level, fail_on_error=fail_on_error
        )
    )


async def scan_resume_async(
    scan_location: str, log_level: str | None = None, fail_on_error: bool = False
) -> Status:
    """Resume a previous scan.

    Args:
       scan_location: Scan location to resume from.
       log_level: Level for logging to the console: "debug", "http", "sandbox",
            "info", "warning", "error", "critical", or "notset" (defaults to "warning")
       fail_on_error: Re-raise exceptions instead of capturing them in results.

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
    return await _scan_async(scan=scan, recorder=recorder, fail_on_error=fail_on_error)


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
       display: Display type: "rich", "plain", "log", or "none" (defaults to "rich").
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
    status = await recorder_type.sync(scan_location, complete=True)
    display().scan_complete(status)
    return status


_scan_async_running = False


async def _scan_async(
    *, scan: ScanContext, recorder: ScanRecorder, fail_on_error: bool = False
) -> Status:
    result: Status | None = None

    async def run(tg: TaskGroup) -> None:
        try:
            nonlocal result
            result = await _scan_async_inner(
                scan=scan, recorder=recorder, tg=tg, fail_on_error=fail_on_error
            )
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
    *,
    scan: ScanContext,
    recorder: ScanRecorder,
    tg: TaskGroup,
    fail_on_error: bool = False,
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
        fail_on_error: Re-raise exceptions instead of capturing them in results. Defaults to False.

    Returns:
        ScanStatus indicating completion status, spec, and location for resumption
    """
    try:
        # set background task group for this coroutine (used by batching)
        set_background_task_group(tg)

        # initialize task local files cache
        init_task_files_cache()

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

        async with transcripts.reader() as tr:
            # get the snapshot
            snapshot = await tr.snapshot()
            scan.spec.transcripts = snapshot

            # write the snapshot
            await recorder.snapshot_transcripts(snapshot)

            # Count already-completed scans to initialize progress
            scanner_names_list = list(scan.scanners.keys())
            total_scans = 0
            skipped_scans = 0
            for transcript_id in snapshot.transcript_ids.keys():
                for name in scanner_names_list:
                    if await recorder.is_recorded(transcript_id, name):
                        skipped_scans += 1
                    total_scans += 1

            # override total scans if there is a worklist
            if scan.worklist is not None:
                total_scans = sum(len(work.transcripts) for work in scan.worklist)

            # start scan
            with display().scan_display(
                scan=scan,
                scan_location=await recorder.location(),
                summary=await recorder.summary(),
                total=total_scans,
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

                # create metrics accumulator
                metrics_accum = metrics_accumulators(scan.scanners)

                async def _transcripts_reader() -> TranscriptsReader:
                    global _process_transcripts_reader
                    if _process_transcripts_reader is None:
                        _process_transcripts_reader = await transcripts.reader(
                            snapshot
                        ).__aenter__()
                    return _process_transcripts_reader

                async def _strategy_completed() -> None:
                    global _process_transcripts_reader
                    if _process_transcripts_reader is not None:
                        await _process_transcripts_reader.__aexit__(None, None, None)
                        _process_transcripts_reader = None

                async def _parse_function(job: ParseJob) -> ParseFunctionResult:
                    try:
                        reader = await _transcripts_reader()
                        union_transcript = await reader.read(
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
                    validation: ResultValidation | None = None

                    scanner_config = config_for_scanner(job.scanner)
                    loader = scanner_config.loader

                    async for loader_result in loader(job.union_transcript):
                        result: Result | list[Result] | None = None
                        final_result: Result | None = None
                        error: Error | None = None
                        try:
                            type_and_ids = get_input_type_and_ids(loader_result)
                            if type_and_ids is None:
                                continue

                            # do scan
                            async with span("scan"):
                                result = await job.scanner(loader_result)

                            # handle lists
                            final_result = (
                                as_resultset(result)
                                if isinstance(result, list)
                                else result
                            )

                            # do validation if we have one for this scanner/id
                            if scan.validation and job.scanner_name in scan.validation:
                                validation = await _validate_scan(
                                    scan.validation[job.scanner_name],
                                    type_and_ids[1],
                                    final_result,
                                )

                        # Special case for errors that should bring down the scan
                        except PrerequisiteError:
                            raise

                        except Exception as ex:  # pylint: disable=W0718
                            if fail_on_error:
                                raise
                            error = Error(
                                transcript_id=job.union_transcript.transcript_id,
                                scanner=job.scanner_name,
                                error=str(ex),
                                traceback=traceback.format_exc(),
                                refusal=isinstance(ex, RefusalError),
                            )

                        # Always append a result (success or error) if we have type_and_ids
                        if type_and_ids is not None:
                            results.append(
                                # All of this data needs to be pickeable (i.e. no
                                # async functions that catpure the task group)
                                ResultReport(
                                    input_type=type_and_ids[0],
                                    input_ids=type_and_ids[1],
                                    input=loader_result,
                                    result=final_result,
                                    validation=validation,
                                    error=error,
                                    events=jsonable_python(
                                        resolve_event_attachments(inspect_transcript)
                                    ),
                                    model_usage=model_usage(),
                                )
                            )

                    return results

                prefetch_multiple = 1.0
                max_tasks = min(
                    total_scans, scan.spec.options.max_transcripts * len(scan.scanners)
                )

                diagnostics = os.getenv("SCOUT_DIAGNOSTICS", "false").lower() in (
                    "1",
                    "true",
                    "yes",
                )
                # are we running single process?
                single_process = (
                    total_scans == 1
                    or scan.spec.options.limit == 1
                    or scan.spec.options.max_processes == 1
                    or os.name == "nt"
                )

                # set strategy accordingly
                strategy = (
                    single_process_strategy(
                        task_count=max_tasks,
                        prefetch_multiple=prefetch_multiple,
                        diagnostics=diagnostics,
                    )
                    if single_process
                    else multi_process_strategy(
                        total_scans=total_scans,
                        max_processes=scan.spec.options.max_processes,
                        task_count=max_tasks,
                        prefetch_multiple=prefetch_multiple,
                        diagnostics=diagnostics,
                    )
                )

                # if we are single process then re-use the tr we are holding
                # (otherwise this will be initialized on demand in children)
                if single_process:
                    global _process_transcripts_reader
                    _process_transcripts_reader = tr

                def accumulate_metrics(
                    scanner: str, results: Sequence[ResultReport]
                ) -> dict[str, dict[str, float]] | None:
                    if scanner in metrics_accum:
                        for result in results:
                            if result.result is not None:
                                metrics_accum[scanner].add_result(result.result.value)
                        return metrics_accum[scanner].compute_metrics_throttled()
                    else:
                        return None

                async def record_results(
                    transcript: TranscriptInfo,
                    scanner: str,
                    results: Sequence[ResultReport],
                ) -> None:
                    metrics = accumulate_metrics(scanner, results)
                    await recorder.record(transcript, scanner, results, metrics)
                    scan_display.results(transcript, scanner, results, metrics)

                await strategy(
                    parse_jobs=_parse_jobs(scan, recorder, tr),
                    parse_function=_parse_function,
                    scan_function=_scan_function,
                    record_results=record_results,
                    update_metrics=scan_display.metrics,
                    completed=_strategy_completed,
                )

                # we've been throttle metrics calculation, now report it all
                for scanner in metrics_accum:
                    await recorder.record_metrics(
                        scanner, metrics_accum[scanner].compute_metrics()
                    )

                # report status
                errors = await recorder.errors()
                scan_status = await recorder.sync(
                    await recorder.location(), complete=len(errors) == 0
                )

        # report scan complete
        display().scan_complete(scan_status)

        # notify view
        view_notify_scan(scan_status.location)

        # return status
        return scan_status

    except Exception as ex:
        return await handle_scan_interrupted(ex, scan.spec, recorder)

    except anyio.get_cancelled_exc_class():
        return await handle_scan_interrupted("Aborted!", scan.spec, recorder)

    finally:
        cleanup_task_files_cache()


def top_level_sync_init(display: DisplayType | None) -> None:
    init_environment()
    init_display_type(display)


def top_level_async_init(log_level: str | None, *, main_process: bool = True) -> None:
    init_platform(hooks=False)
    init_environment()
    if not display_type_initialized():
        init_display_type("plain")
    init_log(log_level)
    if main_process:
        set_log_level(log_level)


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
    if not model_config:
        model_config = GenerateConfig()

    init_model_context(
        model=model,
        model_roles=resolved_model_roles,
        config=model_config,
    )

    return model, resolved_model_args, resolved_model_roles


async def handle_scan_interrupted(
    message_or_exc: str | Exception, spec: ScanSpec, recorder: ScanRecorder
) -> Status:
    scan_status = await recorder.sync(await recorder.location(), complete=False)
    display().scan_interrupted(message_or_exc, scan_status)
    return scan_status


async def _parse_jobs(
    context: ScanContext,
    recorder: ScanRecorder,
    tr: TranscriptsReader,
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
    if context.worklist:
        scanner_to_transcript_ids: dict[str, list[str]] | None = {
            work.scanner: work.transcripts for work in context.worklist
        }
    else:
        scanner_to_transcript_ids = None

    async for transcript_info in tr.index():
        scanner_indices_for_transcript: list[int] = []
        for name in scanner_names:
            # if its not in the worklist then move on
            if (
                scanner_to_transcript_ids is not None
                and transcript_info.transcript_id
                not in scanner_to_transcript_ids.get(name, [])
            ):
                continue
            # if its already recorded then move on
            if await recorder.is_recorded(transcript_info.transcript_id, name):
                continue
            scanner_indices_for_transcript.append(name_to_index[name])
        if not scanner_indices_for_transcript:
            continue
        yield ParseJob(
            transcript_info=transcript_info,
            scanner_indices=set(scanner_indices_for_transcript),
        )


def _content_for_scanner(scanner: Scanner[Any]) -> TranscriptContent:
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
        transcript_id=job.transcript_info.transcript_id,
        source_type=job.transcript_info.source_type,
        source_id=job.transcript_info.source_id,
        source_uri=job.transcript_info.source_uri,
        metadata=job.transcript_info.metadata,
        messages=[],
        events=[],
    )
    return [
        ResultReport(
            input_type="transcript",
            input_ids=[job.transcript_info.transcript_id],
            input=placeholder_transcript,
            result=None,
            validation=None,
            error=Error(
                transcript_id=job.transcript_info.transcript_id,
                scanner=scanner_names[idx],
                error=str(exception),
                traceback=traceback.format_exc(),
                refusal=False,
            ),
            events=[],
            model_usage={},
        )
        for idx in job.scanner_indices
    ]


async def _resolve_worklist(
    worklist: Sequence[ScannerWork] | Sequence[Worklist] | str | Path | None,
) -> list[Worklist] | None:
    if worklist is None:
        return None
    elif isinstance(worklist, str | Path):
        with open(worklist, "r") as f:
            contents = f.read().strip()

        if contents.startswith("["):
            data = json.loads(contents)
        else:
            data = yaml.safe_load(contents)

        if not isinstance(data, list):
            raise PrerequisiteError(
                f"Worklist data from JSON or YAML file must be a list (found type {type(data)})"
            )

        # validate with pydantic and return
        adapter = TypeAdapter[list[Worklist]](list[Worklist])
        return adapter.validate_python(data)
    else:
        # resolve transcript queries
        resolved: list[Worklist] = []
        for work in worklist:
            if isinstance(work.transcripts, Transcripts):
                async with work.transcripts.reader() as tr:
                    snapshot = await tr.snapshot()
                    resolved.append(
                        Worklist(
                            scanner=work.scanner,
                            transcripts=list(snapshot.transcript_ids.keys()),
                        )
                    )
            else:
                resolved.append(
                    Worklist(scanner=work.scanner, transcripts=work.transcripts)
                )

        return resolved


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


async def _validate_scan(
    validation_set: ValidationSet,
    scan_ids: str | list[str],
    scan_result: Result,
) -> ResultValidation | None:
    # normalize scan_ids to str for single-element lists
    scan_ids = scan_ids[0] if len(scan_ids) == 1 else scan_ids

    # is there a validation case for the scan_ids?
    v_case = next(
        (c for c in validation_set.cases if c.id == scan_ids),
        None,
    )

    # if so then perform the validation and return it
    if v_case:
        async with span("validation"):
            # Handle label-based validation for resultsets
            if v_case.labels is not None:
                valid = await validate(
                    validation_set,
                    scan_result,
                    labels=v_case.labels,
                )
                return ResultValidation(target=v_case.labels, valid=valid)
            # Handle regular target-based validation
            else:
                valid = await validate(
                    validation_set,
                    scan_result,
                    target=v_case.target,
                )
                return ResultValidation(target=v_case.target, valid=valid)
    else:
        return None


# initialized on demand in child processes
_process_transcripts_reader: TranscriptsReader | None = None
