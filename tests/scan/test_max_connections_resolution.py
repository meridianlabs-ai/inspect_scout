"""How `max_connections` is resolved, and when adaptive connections survive it.

`max_transcripts` is the default for `max_connections`, but supplying it disables
adaptive connections, so it is omitted only where adaptive can genuinely activate.

These assert the connection pool the model layer created rather than the resolved
config, because the pool is what the behaviour is about. The `model=` and
`model_roles=` routes carry their own configs, which never reach the scanjob's, so a
decision taken before model resolution cannot see them.
"""

import os
import tempfile
from pathlib import Path
from typing import Any, Callable
from unittest.mock import patch

import pytest
from inspect_ai.model import GenerateConfig, get_model
from inspect_ai.util._concurrency import (
    AdaptiveConcurrency,
    AdaptiveConcurrencyController,
    concurrency_semaphores,
    init_concurrency,
)
from inspect_scout import Result, Scanner, scan, scanner
from inspect_scout._scan import (
    certainly_single_process,
    resolve_connection_limit,
    scan_resume,
)
from inspect_scout._scanresults import scan_results_df
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript
from inspect_scout._util.constants import DEFAULT_MAX_TRANSCRIPTS

LOGS_DIR = Path(__file__).parent.parent.parent / "examples" / "scanner" / "logs"

MODEL = "mockllm/model"
ADAPTIVE = f"adaptive:{AdaptiveConcurrency().start}"
FIXED = f"static:{DEFAULT_MAX_TRANSCRIPTS}"

# set by the resume test so the first pass fails, leaving a scan to resume
INTERRUPT = {"active": False}


def configured(**kwargs: Any) -> Any:
    """A pre-built model carrying its own config."""
    return get_model(MODEL, config=GenerateConfig(**kwargs))


@scanner(name="pool_probe", messages="all")
def pool_probe() -> Scanner[Transcript]:
    """Report the connection pool the model layer created.

    The pool is created lazily inside the first generate, so this generates first.
    """

    async def scan_transcript(transcript: Transcript) -> Result:
        if INTERRUPT["active"]:
            raise RuntimeError("leaving this scan incomplete so it can be resumed")
        await get_model().generate("probe")
        pools = [c for c in concurrency_semaphores() if c.name == MODEL]
        if len(pools) != 1:
            return Result(value=False, explanation=f"expected 1 pool, got {len(pools)}")
        pool = pools[0]
        kind = (
            "adaptive" if isinstance(pool, AdaptiveConcurrencyController) else "static"
        )
        return Result(value=True, explanation=f"{kind}:{pool.concurrency}")

    return scan_transcript


def run_scan(tmpdir: str, **kwargs: Any) -> Any:
    """Run a single-transcript scan.

    `init_concurrency()` resets the process-global registry, which scout otherwise
    only resets on the multi-process path; without it a later scan of the same mode
    reuses an earlier scan's semaphore.
    """
    init_concurrency()
    kwargs.setdefault("limit", 1)
    kwargs.setdefault("max_processes", 1)
    return scan(
        scanners=[pool_probe()],
        transcripts=transcripts_from(LOGS_DIR),
        scans=tmpdir,
        display="none",
        **kwargs,
    )


def pool_from(location: str) -> str:
    frame = scan_results_df(location, scanner="pool_probe").scanners["pool_probe"]
    assert frame["value"].tolist() == [True], frame["explanation"].tolist()
    return str(frame["explanation"].tolist()[0])


def observed_pool(**kwargs: Any) -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        status = run_scan(tmpdir, **kwargs)
        assert status.complete
        assert status.location is not None
        return pool_from(status.location)


# --- certainly_single_process ---


def test_single_process_is_certain_when_only_one_scan_is_permitted() -> None:
    assert certainly_single_process(limit=1, max_processes=None) is True


def test_single_process_is_certain_when_only_one_process_is_permitted() -> None:
    assert certainly_single_process(limit=None, max_processes=1) is True


def test_single_process_is_certain_on_windows() -> None:
    # The strategy has always forced single process on Windows.
    with patch("inspect_scout._scan.os.name", "nt"):
        assert certainly_single_process(limit=None, max_processes=4) is True


def test_single_process_is_not_certain_for_an_ordinary_scan() -> None:
    # False means "possibly multi-process", which is the answer that keeps the fixed
    # limit. It must not be read as "definitely multi-process".
    with patch("inspect_scout._scan.os.name", "posix"):
        assert certainly_single_process(limit=None, max_processes=None) is False
        assert certainly_single_process(limit=10, max_processes=4) is False


# --- the resulting pool, by route ---


@pytest.mark.parametrize(
    "make_kwargs, expected",
    [
        pytest.param(lambda: {"model": MODEL}, ADAPTIVE, id="default"),
        pytest.param(
            lambda: {"model": MODEL, "model_config": GenerateConfig(max_connections=7)},
            "static:7",
            id="explicit-limit",
        ),
        pytest.param(
            lambda: {
                "model": MODEL,
                "model_config": GenerateConfig(adaptive_connections=False),
            },
            FIXED,
            id="opt-out",
        ),
        pytest.param(
            lambda: {"model": MODEL, "model_config": GenerateConfig(batch=True)},
            FIXED,
            id="batch",
        ),
        pytest.param(
            lambda: {"model": configured(adaptive_connections=False)},
            FIXED,
            id="model-instance-opt-out",
        ),
        pytest.param(
            lambda: {"model": configured(batch=True)},
            FIXED,
            id="model-instance-batch",
        ),
        # A cap on a pre-built model is overridden, because Model._resolve_config
        # gives the active config precedence. Unchanged from main; pinned so that if
        # it ever changes, it changes deliberately.
        pytest.param(
            lambda: {"model": configured(max_connections=7)},
            FIXED,
            id="model-instance-explicit-limit",
        ),
        pytest.param(
            lambda: {
                "model": MODEL,
                "model_roles": {"grader": configured(adaptive_connections=False)},
            },
            FIXED,
            id="role-opt-out",
        ),
        pytest.param(
            lambda: {"model": MODEL, "model_roles": {"grader": configured(batch=True)}},
            FIXED,
            id="role-batch",
        ),
        # resolve_model_roles() collapses a single-element list, so a role only stays
        # a list at length two or more. The blocking model is second, so judging the
        # list by its first member alone would miss it.
        pytest.param(
            lambda: {
                "model": MODEL,
                "model_roles": {"graders": [get_model(MODEL), configured(batch=True)]},
            },
            FIXED,
            id="role-list",
        ),
        pytest.param(
            lambda: {"model": MODEL, "model_roles": {"grader": MODEL}},
            ADAPTIVE,
            id="role-plain",
        ),
    ],
)
def test_connection_pool(
    make_kwargs: Callable[[], dict[str, Any]], expected: str
) -> None:
    assert observed_pool(**make_kwargs()) == expected


# --- resume ---


def test_a_resumed_scan_re_derives_the_limit() -> None:
    # The spec records the model's own config, which carries no max_connections, so a
    # resumed scan has to re-derive the limit rather than inherit its absence and
    # fall through to the batch ceiling.
    with tempfile.TemporaryDirectory() as tmpdir:
        INTERRUPT["active"] = True
        try:
            first = run_scan(
                tmpdir, model=MODEL, model_config=GenerateConfig(batch=True)
            )
        finally:
            INTERRUPT["active"] = False
        assert not first.complete
        assert first.location is not None

        init_concurrency()
        resumed = scan_resume(first.location, display="none")
        assert resumed.location is not None
        assert pool_from(resumed.location) == FIXED


# --- the no-mutation contract ---


def test_resolving_the_limit_does_not_mutate_the_config_it_was_given() -> None:
    # Keeps the stamp out of get_model()'s memo cache, which keys on the config it was
    # handed and then stores that object as Model.config. The end-to-end sequence
    # needs a multi-process-capable first scan, which Windows cannot take.
    config = GenerateConfig()
    with patch("inspect_scout._scan.os.name", "posix"):
        resolved = resolve_connection_limit(
            config,
            model=get_model(MODEL),
            model_roles=None,
            limit=None,
            max_processes=4,
            max_transcripts=DEFAULT_MAX_TRANSCRIPTS,
        )
    assert resolved.max_connections == DEFAULT_MAX_TRANSCRIPTS
    assert config.max_connections is None


# --- multi-process ---


@pytest.mark.skipif(
    os.name == "nt",
    reason="Windows always takes the single-process path, so the stamp cannot be "
    "exercised here; this asserts the no-regression case on the platforms that can "
    "run multi-process scans.",
)
def test_fixed_limit_is_still_applied_when_multi_process_is_possible() -> None:
    # Dropping the stamp altogether would leave multi-process scans on
    # AdaptiveConcurrency().start, below the max_transcripts they get today.
    with tempfile.TemporaryDirectory() as tmpdir:
        status = run_scan(tmpdir, limit=2, max_processes=2, model=MODEL)
        assert status.complete
        assert status.location is not None
        frame = scan_results_df(status.location, scanner="pool_probe").scanners[
            "pool_probe"
        ]
        # exact, not a "static:" prefix, which would pass on the pools this change
        # exists to prevent
        assert all(
            explanation == FIXED for explanation in frame["explanation"].tolist()
        ), frame["explanation"].tolist()
