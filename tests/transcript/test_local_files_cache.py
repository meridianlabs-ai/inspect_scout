"""Tests for the local cache of remote transcript files."""

import asyncio
from pathlib import Path

import pytest
from inspect_ai._util.asyncfiles import AsyncFilesystem
from inspect_scout._transcript.local_files_cache import LocalFilesCache


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
