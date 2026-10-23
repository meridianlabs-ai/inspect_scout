"""Tests for the local cache of remote transcript files.

A `memory://` location stands in for remote storage.
"""

import asyncio
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from inspect_ai._util.asyncfiles import AsyncFilesystem
from inspect_scout._transcript.local_files_cache import LocalFilesCache
from upath import UPath


@pytest.fixture
def remote_dir() -> Iterator[UPath]:
    """A unique directory on the process-global fsspec memory filesystem."""
    root = UPath(f"memory://{uuid.uuid4().hex}")
    yield root
    if root.exists():
        root.rmdir(recursive=True)


@pytest.mark.asyncio
async def test_cancelled_download_lets_a_waiting_reader_download(
    tmp_path: Path,
) -> None:
    cache = LocalFilesCache(tmp_path / "cache")
    started = asyncio.Event()

    class BlockingFs(AsyncFilesystem):
        async def get_file(self, remote: str, local: str) -> None:
            Path(local).write_bytes(b"partial")
            started.set()
            await asyncio.Event().wait()

    class WorkingFs(AsyncFilesystem):
        async def get_file(self, remote: str, local: str) -> None:
            Path(local).write_bytes(b"log")

    uri = "memory://bucket/log.eval"
    first = asyncio.create_task(cache.resolve_remote_uri_to_local(BlockingFs(), uri))
    await started.wait()
    second = asyncio.create_task(cache.resolve_remote_uri_to_local(WorkingFs(), uri))
    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first
    path = await asyncio.wait_for(second, timeout=5)
    assert Path(path).read_bytes() == b"log"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("setting", "cached"), [(None, True), ("0", True), ("1", False)]
)
async def test_scout_disable_remote_file_cache_reads_remote_files_in_place(
    tmp_path: Path,
    remote_dir: UPath,
    monkeypatch: pytest.MonkeyPatch,
    setting: str | None,
    cached: bool,
) -> None:
    if setting is None:
        monkeypatch.delenv("SCOUT_DISABLE_REMOTE_FILE_CACHE", raising=False)
    else:
        monkeypatch.setenv("SCOUT_DISABLE_REMOTE_FILE_CACHE", setting)
    remote = remote_dir / "a.eval"
    remote.write_bytes(b"x")
    cache = LocalFilesCache(tmp_path / "cache")

    async with AsyncFilesystem() as fs:
        resolved = await cache.resolve_remote_uri_to_local(fs, remote.as_posix())

    assert (resolved != remote.as_posix()) is cached
    assert any(cache.cache_dir.iterdir()) is cached
