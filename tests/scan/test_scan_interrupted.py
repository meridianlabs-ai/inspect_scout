"""Interrupted-scan teardown (issue #578).

Ctrl-C cancels the scan's task group, so `handle_scan_interrupted` runs
inside an already-cancelled scope. Its recorder sync must be shielded to
complete there; otherwise the first await re-raises the cancellation, no
status is ever produced, and the scan trips the "scan async did not return
a result" assertion instead of reporting an interrupted status.
"""

from pathlib import Path

import anyio
import pytest
from inspect_scout import Result, Scanner, Status, scanner
from inspect_scout._scan import top_level_sync_init
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript
from inspect_scout.aio import scan_async

from tests.helpers import temp_active_scans_store

LOGS_DIR = Path(__file__).parent.parent.parent / "examples" / "scanner" / "logs"

# set by the test before scanning; lets it cancel only once a scanner is
# genuinely awaiting, which is where a real Ctrl-C lands
_scanning_started: anyio.Event | None = None


@scanner(name="blocking_probe_scanner", messages="all")
def blocking_probe_scanner() -> Scanner[Transcript]:
    async def scan_transcript(transcript: Transcript) -> Result:
        assert _scanning_started is not None
        _scanning_started.set()
        await anyio.sleep_forever()
        raise RuntimeError("unreachable: the scan is expected to be cancelled")

    return scan_transcript


@pytest.mark.asyncio
async def test_cancelled_scan_returns_interrupted_status(tmp_path: Path) -> None:
    """Cancelling a running scan yields an interrupted status, not a crash."""
    global _scanning_started
    _scanning_started = anyio.Event()

    top_level_sync_init("none")

    statuses: list[Status] = []

    async def run_scan() -> None:
        statuses.append(
            await scan_async(
                scanners=[blocking_probe_scanner()],
                transcripts=transcripts_from(LOGS_DIR),
                scans=str(tmp_path),
                limit=1,
                max_processes=1,
            )
        )

    with temp_active_scans_store():
        with anyio.fail_after(60):
            async with anyio.create_task_group() as tg:
                tg.start_soon(run_scan)
                await _scanning_started.wait()
                tg.cancel_scope.cancel()

    assert statuses, "cancelled scan did not return a status"
    assert not statuses[0].complete
