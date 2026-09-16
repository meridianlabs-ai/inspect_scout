"""How `max_connections` is resolved, and when adaptive connections survive it.

Scout used to stamp `max_connections` unconditionally during config resolution. That
silently disabled adaptive connections, because `adaptive_active()` in inspect_ai
requires `max_connections` to be None. Adaptive is not supported across processes (the
cross-process semaphore registry warns and degrades to a fixed limit), so the stamp is
still correct whenever the scan might be multi-process, and is only skipped when the
scan is certainly single-process.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from inspect_ai.model import GenerateConfig
from inspect_ai.model._generate_config import active_generate_config
from inspect_scout import Result, Scanner, scan, scanner
from inspect_scout._scan import certainly_single_process
from inspect_scout._scanresults import scan_results_df
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript

LOGS_DIR = Path(__file__).parent.parent.parent / "examples" / "scanner" / "logs"


@scanner(name="max_connections_probe", messages="all")
def max_connections_probe() -> Scanner[Transcript]:
    """Record what the model layer actually sees, from inside the scan."""

    async def scan_transcript(transcript: Transcript) -> Result:
        observed = active_generate_config().max_connections
        return Result(value=observed is None, explanation=str(observed))

    return scan_transcript


def test_single_process_is_certain_when_only_one_scan_is_permitted() -> None:
    assert certainly_single_process(limit=1, max_processes=None) is True


def test_single_process_is_certain_when_only_one_process_is_permitted() -> None:
    assert certainly_single_process(limit=None, max_processes=1) is True


def test_single_process_is_certain_on_windows() -> None:
    # The strategy has always forced single process on Windows.
    with patch("inspect_scout._scan.os.name", "nt"):
        assert certainly_single_process(limit=None, max_processes=4) is True


def test_single_process_is_not_certain_for_an_ordinary_scan() -> None:
    # False means "possibly multi-process", which is the answer that keeps the
    # fixed limit in place. It must not be read as "definitely multi-process".
    with patch("inspect_scout._scan.os.name", "posix"):
        assert certainly_single_process(limit=None, max_processes=None) is False
        assert certainly_single_process(limit=10, max_processes=4) is False


def test_adaptive_survives_when_the_scan_is_certainly_single_process() -> None:
    # max_processes=1 is knowable before the transcripts are read, so the stamp is
    # skipped and max_connections reaches the model layer as None, which is what
    # adaptive_active() requires.
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[max_connections_probe()],
            transcripts=transcripts_from(LOGS_DIR),
            scans=tmpdir,
            limit=1,
            max_processes=1,
            model="mockllm/model",
        )
        assert status.complete
        assert status.location is not None

        results = scan_results_df(status.location, scanner="max_connections_probe")
        observed = results.scanners["max_connections_probe"]["value"].tolist()
        assert observed == [True]


def test_explicit_max_connections_is_never_overridden() -> None:
    # The resolution only ever fills in an unset value, so a caller who asks for a
    # specific cap keeps it whichever process mode the scan turns out to use.
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[max_connections_probe()],
            transcripts=transcripts_from(LOGS_DIR),
            scans=tmpdir,
            limit=1,
            max_processes=1,
            model="mockllm/model",
            model_config=GenerateConfig(max_connections=7),
        )
        assert status.complete
        assert status.location is not None

        results = scan_results_df(status.location, scanner="max_connections_probe")
        frame = results.scanners["max_connections_probe"]
        assert frame["value"].tolist() == [False]
        assert frame["explanation"].tolist() == ["7"]


@pytest.mark.skipif(
    os.name == "nt",
    reason="Windows always takes the single-process path, so the stamp cannot be "
    "exercised here; this asserts the no-regression case on the platforms that can "
    "run multi-process scans.",
)
def test_fixed_limit_is_still_applied_when_multi_process_is_possible() -> None:
    # The regression this guards against: dropping the stamp altogether would leave
    # multi-process scans on AdaptiveConcurrency().start, which is below the default
    # max_transcripts the stamp supplies today.
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[max_connections_probe()],
            transcripts=transcripts_from(LOGS_DIR),
            scans=tmpdir,
            limit=2,
            max_processes=2,
            model="mockllm/model",
        )
        assert status.complete
        assert status.location is not None

        results = scan_results_df(status.location, scanner="max_connections_probe")
        frame = results.scanners["max_connections_probe"]
        assert all(value is False for value in frame["value"].tolist())
