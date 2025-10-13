import os
import sys
import traceback
from logging import getLogger
from typing import Any, AsyncIterator, Mapping, Sequence

import anyio
from anyio.abc import TaskGroup
from dotenv import find_dotenv, load_dotenv
from inspect_ai._display.core.rich import rich_theme
from inspect_ai._eval.context import init_model_context
from inspect_ai._eval.task.task import resolve_model_roles
from inspect_ai._util._async import run_coroutine
from inspect_ai._util.background import set_background_task_group
from inspect_ai._util.config import resolve_args
from inspect_ai._util.path import pretty_path
from inspect_ai._util.platform import platform_init as init_platform
from inspect_ai._util.rich import rich_traceback
from inspect_ai.model._generate_config import GenerateConfig
from inspect_ai.model._model import Model, init_model_usage, model_usage, resolve_models
from inspect_ai.model._model_config import (
    model_config_to_model,
    model_roles_config_to_model_roles,
)
from inspect_ai.util._anyio import inner_exception
from rich import print
from rich.console import RenderableType
from rich.progress import (
    BarColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
)

from inspect_scout._util.display import DisplayType
from inspect_scout._util.log import init_log

from ._concurrency.common import ParseJob, ScanMetrics, ScannerJob
from ._concurrency.multi_process import multi_process_strategy
from ._concurrency.single_process import single_process_strategy
from ._progress_utils import UtilizationColumn
from ._recorder.factory import scan_recorder_for_location
from ._recorder.recorder import ScanRecorder, ScanStatus
from ._scancontext import ScanContext, create_scan, resume_scan
from ._scanjob import ScanJob
from ._scanner.result import Error, Result, ResultReport
from ._scanner.scanner import Scanner, config_for_scanner
from ._scanner.types import ScannerInput
from ._scanspec import ScanOptions, ScanSpec
from ._transcript.transcripts import Transcripts
from ._transcript.util import filter_transcript, union_transcript_contents
from ._util.constants import DEFAULT_MAX_PROCESSES, DEFAULT_MAX_TRANSCRIPTS
from ._util.display import display_type_initialized, init_display_type

logger = getLogger(__name__)


def scan(
    scanners: Sequence[Scanner[ScannerInput] | tuple[str, Scanner[ScannerInput]]]
    | dict[str, Scanner[ScannerInput]]
    | ScanJob,
    transcripts: Transcripts | None = None,
    results: str | None = None,
    model: str | Model | None = None,
    model_config: GenerateConfig | None = None,
    model_base_url: str | None = None,
    model_args: dict[str, Any] | str | None = None,
    model_roles: dict[str, str | Model] | None = None,
    max_transcripts: int | None = None,
    max_processes: int | float | None = None,
    limit: int | None = None,
    shuffle: bool | int | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    display: DisplayType | None = None,
    log_level: str | None = None,
) -> ScanStatus:
    top_level_sync_init(display)

    return run_coroutine(
        scan_async(
            scanners=scanners,
            transcripts=transcripts,
            results=results,
            model=model,
            model_config=model_config,
            model_base_url=model_base_url,
            model_args=model_args,
            model_roles=model_roles,
            max_transcripts=max_transcripts,
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
    | ScanJob,
    transcripts: Transcripts | None = None,
    results: str | None = None,
    model: str | Model | None = None,
    model_config: GenerateConfig | None = None,
    model_base_url: str | None = None,
    model_args: dict[str, Any] | str | None = None,
    model_roles: dict[str, str | Model] | None = None,
    max_transcripts: int | None = None,
    max_processes: int | float | None = None,
    limit: int | None = None,
    shuffle: bool | int | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    log_level: str | None = None,
) -> ScanStatus:
    top_level_async_init(log_level)

    # resolve scanjob
    if isinstance(scanners, ScanJob):
        scanjob = scanners
    else:
        scanjob = ScanJob(scanners=scanners)

    # resolve transcripts
    transcripts = transcripts or scanjob.transcripts
    if transcripts is None:
        raise ValueError("No 'transcripts' specified for scan.")

    # resolve results
    results = results or str(os.getenv("SCOUT_SCAN_RESULTS", "./scans"))

    # initialize scan config
    scan_config = ScanOptions(
        max_transcripts=max_transcripts or DEFAULT_MAX_TRANSCRIPTS,
        max_processes=max_processes or DEFAULT_MAX_PROCESSES,
        limit=limit,
        shuffle=shuffle,
    )

    # derive max_connections if not specified
    model_config = model_config or GenerateConfig()
    if model_config.max_connections is None:
        model_config.max_connections = scan_config.max_transcripts

    # initialize runtime context
    resolved_model, resolved_model_args, resolved_model_roles = init_scan_model_context(
        model=model,
        model_config=model_config,
        model_base_url=model_base_url,
        model_args=model_args,
        model_roles=model_roles,
    )

    # create job and recorder
    scan = await create_scan(
        scanjob=scanjob,
        transcripts=transcripts,
        model=resolved_model,
        model_args=resolved_model_args,
        model_roles=resolved_model_roles,
        config=scan_config,
        tags=tags,
        metadata=metadata,
    )
    recorder = scan_recorder_for_location(results)
    await recorder.init(scan.spec, results)

    # run the scan
    return await _scan_async(scan=scan, recorder=recorder)


def scan_resume(
    scan_dir: str,
    display: DisplayType | None = None,
    log_level: str | None = None,
) -> ScanStatus:
    top_level_sync_init(display)
    return run_coroutine(scan_resume_async(scan_dir, log_level=log_level))


async def scan_resume_async(scan_dir: str, log_level: str | None = None) -> ScanStatus:
    top_level_async_init(log_level)

    # resume job
    scan = await resume_scan(scan_dir)

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
    recorder = scan_recorder_for_location(scan_dir)
    await recorder.resume(scan_dir)
    return await _scan_async(scan=scan, recorder=recorder)


def scan_complete(
    scan_dir: str,
    display: DisplayType | None = None,
    log_level: str | None = None,
) -> ScanStatus:
    top_level_sync_init(display)

    return run_coroutine(scan_complete_async(scan_dir, log_level=log_level))


async def scan_complete_async(
    scan_dir: str, log_level: str | None = None
) -> ScanStatus:
    top_level_async_init(log_level)

    # resume job (will validate that the scan isn't already complete)
    await resume_scan(scan_dir)

    # create recorder, resume it, then complete it
    recorder = scan_recorder_for_location(scan_dir)
    await recorder.resume(scan_dir)
    status = await recorder.complete()
    print_scan_complete(status.location)
    return status


async def _scan_async(*, scan: ScanContext, recorder: ScanRecorder) -> ScanStatus:
    result: ScanStatus | None = None

    async def run(tg: TaskGroup) -> None:
        try:
            nonlocal result
            result = await _scan_async_inner(scan=scan, recorder=recorder, tg=tg)
        finally:
            tg.cancel_scope.cancel()

    try:
        async with anyio.create_task_group() as tg:
            tg.start_soon(run, tg)
    except Exception as ex:
        raise inner_exception(ex) from None
    except anyio.get_cancelled_exc_class():
        # Cancelled exceptions are expected and handled by _scan_async_inner
        pass

    assert result is not None, "scan async did not return a result."

    return result


async def _scan_async_inner(
    *, scan: ScanContext, recorder: ScanRecorder, tg: TaskGroup
) -> ScanStatus:
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

        # establish max_transcripts
        max_transcripts = scan.spec.options.max_transcripts or DEFAULT_MAX_TRANSCRIPTS
        max_processes = scan.spec.options.max_processes or DEFAULT_MAX_PROCESSES

        transcripts = scan.transcripts
        # apply limits/shuffle
        if scan.spec.options.limit is not None:
            transcripts = transcripts.limit(scan.spec.options.limit)
        if scan.spec.options.shuffle is not None:
            transcripts = transcripts.shuffle(
                scan.spec.options.shuffle
                if isinstance(scan.spec.options.shuffle, int)
                else None
            )

        async with transcripts:
            with Progress(
                TextColumn("Scanning"),
                BarColumn(),
                TextColumn("{task.completed}/{task.total}"),
                TextColumn("(processes/parsing/scanning/waiting) (buffered scan jobs)"),
                UtilizationColumn(),
                TimeElapsedColumn(),
                transient=True,
            ) as progress:
                scans_per_transcript = len(scan.scanners)
                total_ticks = (await transcripts.count()) * scans_per_transcript
                task_id = progress.add_task("Scan", total=total_ticks)

                # Build scanner list and union content for index resolution
                scanner_names_list = list(scan.scanners.keys())
                scanners_list = list(scan.scanners.values())
                union_content = union_transcript_contents(
                    [
                        config_for_scanner(scanner).content
                        for scanner in scan.scanners.values()
                    ]
                )

                async def _parse_function(job: ParseJob) -> list[ScannerJob]:
                    union_transcript = await transcripts.read(
                        job.transcript_info, union_content
                    )
                    return [
                        ScannerJob(
                            union_transcript=union_transcript,
                            scanner=scanners_list[idx],
                            scanner_name=scanner_names_list[idx],
                        )
                        for idx in job.scanner_indices
                    ]

                async def _scan_function(job: ScannerJob) -> list[ResultReport]:
                    from inspect_ai.log._transcript import Transcript, init_transcript

                    # initialize model_usage tracking for this coroutine
                    init_model_usage()

                    transcript = Transcript()
                    init_transcript(transcript)

                    result: Result | None = None
                    error: Error | None = None

                    try:
                        result = await job.scanner(
                            filter_transcript(
                                job.union_transcript,
                                config_for_scanner(job.scanner).content,
                            )
                        )
                    except Exception as ex:
                        logger.error(f"Error in '{job.scanner_name}': {ex}")
                        error = Error(error=str(ex), traceback=traceback.format_exc())

                    return [
                        ResultReport(
                            input_type="transcript",
                            input_id=job.union_transcript.id,
                            result=result,
                            error=error,
                            events=transcript.events,
                            model_usage=model_usage(),
                        )
                    ]

                # transform knobs
                # For now, let's say that:
                # - max_transcripts is limit of how many parsed transcripts we'll keep in memory
                # - we want a buffer multiple of 1.0 so that we could feed all active tasks at once if they all finished at the same time.

                prefetch_multiple = 1.0
                max_tasks = int(
                    (max_transcripts * scans_per_transcript) / (1 + prefetch_multiple)
                )

                # TODO: Plumb this
                disable_multi_process = True
                diagnostics = False
                strategy = (
                    multi_process_strategy(
                        task_count=max_tasks,
                        processes=max_processes,
                        prefetch_multiple=prefetch_multiple,
                        diagnostics=diagnostics,
                    )
                    if not disable_multi_process
                    and (isinstance(max_processes, float) or max_processes != 1)
                    else single_process_strategy(
                        task_count=max_tasks,
                        prefetch_multiple=prefetch_multiple,
                        diagnostics=diagnostics,
                    )
                )

                # For multi-process strategy, set context (scanners + union_content)
                # TODO: Follow up with JJ on this stuff. I'm missing something.
                if hasattr(strategy, "set_context"):
                    strategy.set_context(scanners_list, union_content)

                # Count already-completed scans to advance progress bar
                skipped_scans = 0
                for transcript_info in await transcripts.index():
                    for name in scanner_names_list:
                        if await recorder.is_recorded(transcript_info, name):
                            skipped_scans += 1
                if skipped_scans > 0:
                    progress.update(task_id, completed=skipped_scans)

                def update_metrics(metrics: ScanMetrics) -> None:
                    progress.update(
                        task_id,
                        metrics=metrics,
                        completed=skipped_scans + metrics.completed_scans,
                    )

                await strategy(
                    parse_jobs=_parse_jobs(scan, recorder, transcripts),
                    parse_function=_parse_function,
                    scan_function=_scan_function,
                    record_results=recorder.record,
                    update_metrics=update_metrics,
                )

                # report status
                errors = await recorder.errors()
                if len(errors) > 0:
                    print_scan_errors(errors, await recorder.location())
                    return ScanStatus(
                        complete=False,
                        spec=scan.spec,
                        location=await recorder.location(),
                    )
                else:
                    scan_info = await recorder.complete()
                    print_scan_complete(scan_info.location)

        # return scan_info
        return scan_info

    except Exception as ex:
        type, value, tb = sys.exc_info()
        type = type if type else BaseException
        value = value if value else ex
        rich_tb = rich_traceback(type, value, tb)
        return await handle_scan_interruped(
            rich_tb, scan.spec, await recorder.location()
        )

    except anyio.get_cancelled_exc_class():
        return await handle_scan_interruped(
            "Cancelled!", scan.spec, await recorder.location()
        )


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


async def handle_scan_interruped(
    message: RenderableType, spec: ScanSpec, location: str
) -> ScanStatus:
    theme = rich_theme()

    print(message)

    resume_message = (
        f"\n[bold][{theme.error}]Scan interrupted. Resume scan with:[/{theme.error}]\n\n"
        + f'[bold][{theme.light}]scout scan-resume "{pretty_path(location)}"[/{theme.light}][/bold]\n'
    )
    print(resume_message)

    return ScanStatus(
        complete=False,
        spec=spec,
        location=location,
    )


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

    for transcript_info in await transcripts.index():
        scanner_indices_for_transcript: list[int] = []
        for name in scanner_names:
            if await recorder.is_recorded(transcript_info, name):
                continue
            scanner_indices_for_transcript.append(name_to_index[name])
        if not scanner_indices_for_transcript:
            continue
        yield ParseJob(
            transcript_info=transcript_info,
            scanner_indices=set(scanner_indices_for_transcript),
        )


def print_scan_complete(scan_dir: str) -> None:
    print(f'\n[bold]Scan complete:[/bold] "{pretty_path(scan_dir)}"\n')


def print_scan_errors(errors: list[Error], scan_dir: str) -> None:
    theme = rich_theme()
    print(f"\n[bold]{len(errors)} scan errors occurred![/bold]\n")
    print(
        f'Resume (retrying errors):   [bold][{theme.light}]scout scan resume "{pretty_path(scan_dir)}"[/{theme.light}][/bold]\n'
    )
    print(
        f'Complete (ignoring errors): [bold][{theme.light}]scout scan complete "{pretty_path(scan_dir)}"[/{theme.light}][/bold]\n'
    )
