import os
import pathlib
from typing import Any

import pytest
from inspect_ai.model import GenerateConfig, get_model
from inspect_ai.util import AdaptiveConcurrency
from inspect_ai.util._concurrency import (
    AdaptiveConcurrencyController,
    concurrency_semaphores,
    init_concurrency,
)
from inspect_scout import Result, Scanner, scan, scanner
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript

LOGS_DIR = pathlib.Path(__file__).resolve().parent.parent / "recorder" / "logs"
MODEL = "mockllm/model"
FIXED = "static:7"
ADAPTIVE = f"adaptive:{AdaptiveConcurrency().start}"
may_fork = pytest.mark.skipif(
    os.name == "nt", reason="Windows scans are always single-process"
)


@scanner(name="generate_once", messages="all")
def generate_once() -> Scanner[Transcript]:
    async def scan_transcript(transcript: Transcript) -> Result:
        await get_model().generate("probe")
        return Result(value=True)

    return scan_transcript


def model_pool(scans: pathlib.Path, **kwargs: Any) -> str:
    """Scan one transcript and report the connection pool its model generated under."""
    # single-process scans don't reset the process-global registry
    init_concurrency()
    status = scan(
        scanners=[generate_once()],
        # one transcript, so max_processes > 1 is possible but never forks
        transcripts=transcripts_from(LOGS_DIR).limit(1),
        scans=str(scans),
        max_transcripts=7,
        display="none",
        fail_on_error=True,
        **{"model": MODEL, "max_processes": 1, **kwargs},
    )
    assert status.complete
    (pool,) = [c for c in concurrency_semaphores() if c.name == MODEL]
    kind = "adaptive" if isinstance(pool, AdaptiveConcurrencyController) else "static"
    return f"{kind}:{pool.concurrency}"


def opt_in() -> GenerateConfig:
    return GenerateConfig(adaptive_connections=True)


def batched() -> Any:
    return get_model(MODEL, config=GenerateConfig(batch=True))


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        pytest.param({}, FIXED, id="default"),
        pytest.param({"model_config": opt_in()}, ADAPTIVE, id="opt-in"),
        pytest.param(
            {
                "model_config": GenerateConfig(
                    adaptive_connections=AdaptiveConcurrency(min=2, start=4, max=8)
                )
            },
            "adaptive:4",
            id="opt-in-bounds",
        ),
        pytest.param(
            {"model_config": opt_in(), "max_processes": 4},
            FIXED,
            id="opt-in-may-fork",
            marks=may_fork,
        ),
        pytest.param(
            {"model_config": GenerateConfig(adaptive_connections=True, batch=True)},
            FIXED,
            id="opt-in-batch",
        ),
        pytest.param(
            {"model_config": GenerateConfig(adaptive_connections=False)},
            FIXED,
            id="opt-out",
        ),
        pytest.param(
            {
                "model_config": GenerateConfig(
                    adaptive_connections=True, max_connections=3
                )
            },
            "static:3",
            id="opt-in-explicit-max_connections",
        ),
        pytest.param(
            {"model_config": opt_in(), "model": batched()},
            FIXED,
            id="opt-in-batch-model",
        ),
        pytest.param(
            {"model_config": opt_in(), "model_roles": {"grader": batched()}},
            FIXED,
            id="opt-in-batch-role",
        ),
        pytest.param(
            {
                "model_config": opt_in(),
                "model_roles": {"graders": [get_model(MODEL), batched()]},
            },
            FIXED,
            id="opt-in-batch-role-list",
        ),
        pytest.param(
            {"model_config": opt_in(), "model_roles": {"grader": MODEL}},
            ADAPTIVE,
            id="opt-in-plain-role",
        ),
    ],
)
def test_model_pool(
    tmp_path: pathlib.Path, kwargs: dict[str, Any], expected: str
) -> None:
    assert model_pool(tmp_path, **kwargs) == expected


@may_fork
def test_reused_config_rederives_the_limit(tmp_path: pathlib.Path) -> None:
    config = opt_in()
    assert model_pool(tmp_path / "1", model_config=config, max_processes=4) == FIXED
    assert model_pool(tmp_path / "2", model_config=config) == ADAPTIVE
