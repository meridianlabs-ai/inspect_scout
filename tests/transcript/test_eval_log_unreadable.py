"""An unreadable eval log is skipped when indexing instead of aborting."""

import shutil
from pathlib import Path

import pytest
from inspect_scout import Result, Scanner, scan, scanner
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript

from tests.helpers import temp_active_scans_store

LOGS_DIR = Path(__file__).parent.parent / "recorder" / "logs"
GOOD_LOG = LOGS_DIR / "2025-09-23T08-09-58-04-00_popularity_DN2wbX2ZvACsBpjwptzBRo.eval"
BAD_LOG = (
    LOGS_DIR / "2025-09-23T08-09-58-04-00_security-guide_LuxZJVwvymC3S3SyoJczxB.eval"
)


@pytest.fixture
def logs_dir(tmp_path: Path) -> Path:
    """A readable log next to one whose zip end-of-central-directory is cut off."""
    logs = tmp_path / "logs"
    logs.mkdir()
    shutil.copy(GOOD_LOG, logs / GOOD_LOG.name)
    truncated = logs / BAD_LOG.name
    truncated.write_bytes(BAD_LOG.read_bytes()[:-200])
    return logs


@scanner(name="noop", messages="all")
def noop_scanner() -> Scanner[Transcript]:
    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(value=True)

    return scan_transcript


@pytest.mark.asyncio
async def test_index_skips_unreadable_log(logs_dir: Path) -> None:
    async with transcripts_from(logs_dir).reader() as reader:
        infos = [info async for info in reader.index()]
        unreadable = reader.unreadable()

    assert infos
    assert {info.source_uri for info in infos} == {
        (logs_dir / GOOD_LOG.name).as_posix()
    }
    assert [source.uri for source in unreadable] == [
        (logs_dir / BAD_LOG.name).as_posix()
    ]


def test_scan_records_unreadable_log_as_error(logs_dir: Path, tmp_path: Path) -> None:
    with temp_active_scans_store():
        status = scan(
            scanners=[noop_scanner()],
            transcripts=transcripts_from(logs_dir),
            scans=(tmp_path / "scans").as_posix(),
            max_processes=1,
            display="none",
        )

    assert status.summary.scanners["noop"].results > 0
    assert len(status.errors) == 1
    assert status.errors[0].scanner == "noop"
    assert (logs_dir / BAD_LOG.name).as_posix() in status.errors[0].error
    assert status.summary.scanners["noop"].errors == 1
