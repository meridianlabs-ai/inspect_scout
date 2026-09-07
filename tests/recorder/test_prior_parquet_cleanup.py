"""Temporary prior parquets downloaded by `FileRecorder.sync` never leak.

Syncing a remote scan location downloads the previously compacted parquet
so new buffer rows can be merged into it. Outside `FileRecorder.run_scope`
every sync removes its download before returning; inside one (held by the
scan driver for a whole run) the download is reused across syncs and
removed when the scope exits, whether or not the run completed.

A `memory://` location stands in for remote storage: it takes the same
code path as S3 (download, compact locally, upload) without credentials.
"""

import io
import tempfile
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import anyio
import pyarrow.parquet as pq
import pytest
from inspect_ai._util.asyncfiles import AsyncFilesystem
from inspect_ai.model import ChatMessageUser
from inspect_scout import Result, Scanner, scan, scan_resume, scanner
from inspect_scout._recorder import file as file_module
from inspect_scout._recorder.buffer import RecorderBuffer
from inspect_scout._recorder.file import (
    FileRecorder,
    _prior_parquet_cache,
    _prior_parquet_cache_key,
)
from inspect_scout._scanner.result import ResultReport
from inspect_scout._scanspec import ScannerSpec, ScanSpec
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript, TranscriptInfo
from upath import UPath

from tests.helpers import temp_active_scans_store

LOGS_DIR = Path(__file__).parent.parent.parent / "examples" / "scanner" / "logs"
SCANNER = "s"


@pytest.fixture(autouse=True)
def scout_buffer_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point SCOUT_SCANBUFFER_DIR at an isolated temp dir."""
    buf_dir = tmp_path / "buffer"
    monkeypatch.setenv("SCOUT_SCANBUFFER_DIR", str(buf_dir))
    return buf_dir


@pytest.fixture(autouse=True)
def temp_parquets(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[Path]]:
    """Every `.parquet` path handed out by `tempfile.mkstemp` during the test."""
    created: list[Path] = []
    real_mkstemp = tempfile.mkstemp

    def recording_mkstemp(*args: Any, **kwargs: Any) -> tuple[int, str]:
        fd, path = real_mkstemp(*args, **kwargs)
        if path.endswith(".parquet"):
            created.append(Path(path))
        return fd, path

    monkeypatch.setattr(tempfile, "mkstemp", recording_mkstemp)
    yield created
    _prior_parquet_cache.clear()
    for path in created:
        path.unlink(missing_ok=True)


@pytest.fixture
def memory_location() -> Iterator[str]:
    """A unique scans location on the process-global fsspec memory filesystem."""
    root = UPath(f"memory://{uuid.uuid4().hex}")
    yield root.as_posix()
    if root.exists():
        root.rmdir(recursive=True)


@pytest.fixture
def get_file_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Remote paths downloaded via `AsyncFilesystem.get_file` during the test."""
    calls: list[str] = []
    real_get_file = AsyncFilesystem.get_file

    async def counting_get_file(self: AsyncFilesystem, remote: str, local: str) -> None:
        calls.append(remote)
        await real_get_file(self, remote, local)

    monkeypatch.setattr(AsyncFilesystem, "get_file", counting_get_file)
    return calls


def _spec() -> ScanSpec:
    return ScanSpec(scan_name="leak", scanners={SCANNER: ScannerSpec(name=SCANNER)})


def _report() -> ResultReport:
    return ResultReport(
        input_type="message",
        input_ids=[],
        input=ChatMessageUser(content=""),
        result=Result(value=1),
        validation=None,
        error=None,
        events=[],
        model_usage={},
    )


async def _record(recorder: FileRecorder, transcript_id: str) -> None:
    await recorder.record(
        TranscriptInfo(
            transcript_id=transcript_id,
            source_type="test",
            source_id="src",
            source_uri=f"test://{transcript_id}",
        ),
        SCANNER,
        [_report()],
        None,
    )


async def _scan_with_prior(scans_location: str) -> str:
    """Create a scan whose dir already holds a compacted parquet; return the dir."""
    recorder = FileRecorder()
    await recorder.init(_spec(), scans_location)
    await _record(recorder, "t-prior")
    scan_dir = recorder.scan_dir.as_posix()
    await FileRecorder.sync(scan_dir, complete=True)
    return scan_dir


async def _attach_and_record(scan_dir: str, transcript_id: str) -> FileRecorder:
    """Mirror inspect_ai's eval-time scanning: attach, then record a new row."""
    recorder = FileRecorder()
    await recorder.attach(scan_dir)
    await _record(recorder, transcript_id)
    return recorder


def _cache_key(scan_dir: str) -> str:
    return _prior_parquet_cache_key(RecorderBuffer.buffer_dir(scan_dir))


def _row_count(scan_dir: str) -> int:
    data = (UPath(scan_dir) / f"{SCANNER}.parquet").read_bytes()
    return pq.ParquetFile(io.BytesIO(data)).metadata.num_rows


def _live(temp_parquets: list[Path]) -> list[Path]:
    return [p for p in temp_parquets if p.exists()]


def _assert_no_temp_parquets(temp_parquets: list[Path]) -> None:
    assert temp_parquets, "expected the sync to go through temp parquet files"
    assert _live(temp_parquets) == []


@pytest.mark.asyncio
async def test_repeated_non_final_syncs_leave_no_temp_files(
    memory_location: str, temp_parquets: list[Path], get_file_calls: list[str]
) -> None:
    """Each sync outside a run scope downloads the prior and removes it again."""
    scan_dir = await _scan_with_prior(memory_location)
    await _attach_and_record(scan_dir, "t-1")
    assert _cache_key(scan_dir) not in _prior_parquet_cache

    for _ in range(3):
        await FileRecorder.sync(scan_dir, complete=False)

    assert len(get_file_calls) == 3
    _assert_no_temp_parquets(temp_parquets)
    assert _cache_key(scan_dir) not in _prior_parquet_cache


@pytest.mark.asyncio
async def test_final_sync_leaves_no_temp_files(
    memory_location: str, temp_parquets: list[Path], get_file_calls: list[str]
) -> None:
    scan_dir = await _scan_with_prior(memory_location)
    await _attach_and_record(scan_dir, "t-1")

    await FileRecorder.sync(scan_dir, complete=True)

    assert len(get_file_calls) == 1
    _assert_no_temp_parquets(temp_parquets)
    assert _cache_key(scan_dir) not in _prior_parquet_cache


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["compaction", "upload"])
async def test_failed_sync_leaves_no_temp_files(
    memory_location: str,
    temp_parquets: list[Path],
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    scan_dir = await _scan_with_prior(memory_location)
    await _attach_and_record(scan_dir, "t-1")

    def failing_compaction(*args: Any, **kwargs: Any) -> bool:
        raise RuntimeError("boom")

    async def failing_upload(*args: Any, **kwargs: Any) -> str | None:
        raise RuntimeError("boom")

    if failure == "compaction":
        monkeypatch.setattr(file_module, "scanner_table", failing_compaction)
    else:
        monkeypatch.setattr(AsyncFilesystem, "write_file_streaming", failing_upload)

    with pytest.raises(RuntimeError, match="boom"):
        await FileRecorder.sync(scan_dir, complete=False)

    _assert_no_temp_parquets(temp_parquets)


@pytest.mark.asyncio
async def test_cancelled_download_leaves_no_temp_files(
    memory_location: str, temp_parquets: list[Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    scan_dir = await _scan_with_prior(memory_location)
    await _attach_and_record(scan_dir, "t-1")
    downloading = anyio.Event()

    async def hanging_get_file(self: AsyncFilesystem, remote: str, local: str) -> None:
        downloading.set()
        await anyio.sleep_forever()

    monkeypatch.setattr(AsyncFilesystem, "get_file", hanging_get_file)

    async def run_sync() -> None:
        await FileRecorder.sync(scan_dir, complete=False)

    with anyio.fail_after(30):
        async with anyio.create_task_group() as tg:
            tg.start_soon(run_sync)
            await downloading.wait()
            tg.cancel_scope.cancel()

    _assert_no_temp_parquets(temp_parquets)


@pytest.mark.asyncio
async def test_run_scope_reuses_download_and_removes_it_on_exit(
    memory_location: str, temp_parquets: list[Path], get_file_calls: list[str]
) -> None:
    """Inside a run scope the prior is downloaded once and kept until exit."""
    scan_dir = await _scan_with_prior(memory_location)
    recorder = await _attach_and_record(scan_dir, "t-1")

    with recorder.run_scope():
        await FileRecorder.sync(scan_dir, complete=False)
        await FileRecorder.sync(scan_dir, complete=False)
        assert len(get_file_calls) == 1
        live = _live(temp_parquets)
        assert len(live) == 1
        assert _prior_parquet_cache[_cache_key(scan_dir)] == {SCANNER: str(live[0])}

    _assert_no_temp_parquets(temp_parquets)
    assert _cache_key(scan_dir) not in _prior_parquet_cache


@pytest.mark.asyncio
async def test_complete_sync_inside_run_scope_drops_cached_prior(
    memory_location: str, temp_parquets: list[Path], get_file_calls: list[str]
) -> None:
    """Wiping the buffer invalidates the cached prior, so it is dropped at once.

    The buffer rows that prior was paired with are gone, so reusing it would
    overwrite the completed results with pre-run rows. The scope stays open:
    a later sync downloads the completed output afresh and caches that.
    """
    scan_dir = await _scan_with_prior(memory_location)
    recorder = await _attach_and_record(scan_dir, "t-1")

    with recorder.run_scope():
        await FileRecorder.sync(scan_dir, complete=False)
        await FileRecorder.sync(scan_dir, complete=True)
        assert len(get_file_calls) == 1
        _assert_no_temp_parquets(temp_parquets)
        assert _prior_parquet_cache[_cache_key(scan_dir)] == {}

        await FileRecorder.sync(scan_dir, complete=False)
        assert len(get_file_calls) == 2
        assert len(_live(temp_parquets)) == 1

    _assert_no_temp_parquets(temp_parquets)
    assert _cache_key(scan_dir) not in _prior_parquet_cache
    assert _row_count(scan_dir) == 2


@pytest.mark.asyncio
async def test_failed_download_inside_run_scope_is_retried(
    memory_location: str, temp_parquets: list[Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed download leaves nothing behind and is not remembered as a prior."""
    scan_dir = await _scan_with_prior(memory_location)
    recorder = await _attach_and_record(scan_dir, "t-1")
    calls: list[str] = []
    real_get_file = AsyncFilesystem.get_file

    async def flaky_get_file(self: AsyncFilesystem, remote: str, local: str) -> None:
        calls.append(remote)
        if len(calls) == 1:
            raise OSError("transient")
        await real_get_file(self, remote, local)

    monkeypatch.setattr(AsyncFilesystem, "get_file", flaky_get_file)

    with recorder.run_scope():
        with pytest.raises(OSError, match="transient"):
            await FileRecorder.sync(scan_dir, complete=False)
        assert _live(temp_parquets) == []
        assert _prior_parquet_cache[_cache_key(scan_dir)] == {}

        await FileRecorder.sync(scan_dir, complete=False)
        assert len(calls) == 2
        assert len(_live(temp_parquets)) == 1

    _assert_no_temp_parquets(temp_parquets)


@pytest.mark.asyncio
async def test_local_prior_is_never_deleted(
    tmp_path: Path, temp_parquets: list[Path]
) -> None:
    """A local scan dir's compacted parquet is the prior; it must survive syncs."""
    recorder = FileRecorder()
    await recorder.init(_spec(), (tmp_path / "scans").as_posix())
    await _record(recorder, "t-1")
    scan_dir = recorder.scan_dir.as_posix()

    await FileRecorder.sync(scan_dir, complete=False)
    await FileRecorder.sync(scan_dir, complete=False)

    assert (recorder.scan_dir / f"{SCANNER}.parquet").exists()
    assert temp_parquets == []


@scanner(name="prior_leak_always_failing", messages="all")
def always_failing_scanner() -> Scanner[Transcript]:
    """Fails on every transcript, so a scan and its resume both end with errors."""

    async def scan_transcript(transcript: Transcript) -> Result:
        raise RuntimeError("always fails")

    return scan_transcript


def test_scan_and_resume_on_remote_location_leave_no_temp_files(
    memory_location: str, temp_parquets: list[Path], get_file_calls: list[str]
) -> None:
    """A run that ends with errors (a non-final sync) still cleans up."""
    with temp_active_scans_store():
        first = scan(
            scanners=[always_failing_scanner()],
            transcripts=transcripts_from(LOGS_DIR),
            scans=memory_location,
            limit=2,
            max_processes=1,
            display="none",
        )
        assert first.complete is False
        assert get_file_calls == []

        resumed = scan_resume(first.location, display="none")

    assert resumed.complete is False
    assert len(get_file_calls) == 1, "resume should download the prior parquet"
    _assert_no_temp_parquets(temp_parquets)
    assert _cache_key(first.location) not in _prior_parquet_cache
