"""A scan resumed without its local buffer (a new machine) skips synced work."""

import json
from pathlib import Path

import anyio
import pytest
from inspect_ai.model import ChatMessageUser
from inspect_ai.scorer import mean, stderr
from inspect_scout import (
    Result,
    Scanner,
    Status,
    Transcript,
    scan,
    scan_results_df,
    scan_resume,
    scanner,
    transcripts_db,
    transcripts_from,
)
from inspect_scout._scan import top_level_sync_init
from inspect_scout.aio import scan_async

from tests.helpers import temp_active_scans_store

SCANNER = "resume_fresh_buffer"
TRANSCRIPT_IDS = [f"t{i}" for i in range(6)]
SLOW_ID = TRANSCRIPT_IDS[-1]
FAILING_ID = TRANSCRIPT_IDS[-2]

# set by the test; the slow transcript sets it once every other transcript is
# recorded (one of them as an error), so the test interrupts the scan with
# exactly one transcript left
_others_recorded: anyio.Event | None = None


@scanner(name=SCANNER, messages="all", metrics=[mean(), stderr()])
def resume_fresh_buffer(
    calls: str, buffer_dir: str, release: str
) -> Scanner[Transcript]:
    async def run(transcript: Transcript) -> Result:
        with open(calls, "a") as f:
            f.write(transcript.transcript_id + "\n")
        if transcript.transcript_id == SLOW_ID and not Path(release).exists():
            assert _others_recorded is not None
            while _buffered_scans(Path(buffer_dir)) < len(TRANSCRIPT_IDS) - 1:
                await anyio.sleep(0.01)
            _others_recorded.set()
            await anyio.sleep_forever()
        if transcript.transcript_id == FAILING_ID and not Path(release).exists():
            raise RuntimeError("Transient scanner failure")
        return Result(value=TRANSCRIPT_IDS.index(transcript.transcript_id))

    return run


def _buffered_scans(buffer_dir: Path) -> int:
    summaries = list(buffer_dir.glob("*/_summary.json"))
    if not summaries:
        return 0
    summary = json.loads(summaries[0].read_text())
    return int(summary["scanners"][SCANNER]["scans"])


def _read_calls(calls: Path) -> list[str]:
    return calls.read_text().split() if calls.exists() else []


def test_resume_with_fresh_buffer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_buffer = tmp_path / "buffer-first-machine"
    monkeypatch.setenv("SCOUT_SCANBUFFER_DIR", str(first_buffer))
    database = str(tmp_path / "transcripts")
    calls = tmp_path / "calls.txt"
    release = tmp_path / "release"
    scanner_instance = resume_fresh_buffer(str(calls), str(first_buffer), str(release))

    async def interrupted_scan() -> Status:
        global _others_recorded
        _others_recorded = anyio.Event()
        async with transcripts_db(database) as db:
            await db.insert(
                [
                    Transcript(
                        transcript_id=transcript_id,
                        messages=[ChatMessageUser(content=transcript_id)],
                    )
                    for transcript_id in TRANSCRIPT_IDS
                ]
            )
        statuses: list[Status] = []

        async def run() -> None:
            statuses.append(
                await scan_async(
                    scanners=[scanner_instance],
                    transcripts=transcripts_from(database),
                    scans=str(tmp_path / "scans"),
                    max_processes=1,
                )
            )

        with anyio.fail_after(60):
            async with anyio.create_task_group() as tg:
                tg.start_soon(run)
                await _others_recorded.wait()
                tg.cancel_scope.cancel()
        return statuses[0]

    top_level_sync_init("none")
    with temp_active_scans_store():
        interrupted = anyio.run(interrupted_scan)
        assert not interrupted.complete
        assert [e.transcript_id for e in interrupted.errors] == [FAILING_ID]
        synced = scan_results_df(interrupted.location).scanners[SCANNER]
        assert sorted(synced["transcript_id"]) == TRANSCRIPT_IDS[:-1]
        assert sorted(_read_calls(calls)) == TRANSCRIPT_IDS

        # resume on a "new machine": the synced scan dir is all that remains
        monkeypatch.setenv("SCOUT_SCANBUFFER_DIR", str(tmp_path / "buffer-new"))
        calls.unlink()
        release.touch()
        resumed = scan_resume(interrupted.location, display="none")
        resumed_calls = _read_calls(calls)
        clean = scan(
            scanners=[scanner_instance],
            transcripts=transcripts_from(database),
            scans=str(tmp_path / "clean"),
            max_processes=1,
            display="none",
        )

    assert sorted(resumed_calls) == [FAILING_ID, SLOW_ID]
    assert resumed.complete and not resumed.errors
    results = scan_results_df(resumed.location).scanners[SCANNER]
    assert sorted(results["transcript_id"]) == TRANSCRIPT_IDS
    # metrics cover the synced results as well as the rescanned ones
    metrics = resumed.summary.scanners[SCANNER].metrics
    assert metrics == clean.summary.scanners[SCANNER].metrics
    assert metrics is not None and metrics[SCANNER]["mean"] == 2.5
