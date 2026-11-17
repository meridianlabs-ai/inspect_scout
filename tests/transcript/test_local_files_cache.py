"""Tests for the local cache of remote transcript files."""

import asyncio
import threading
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from inspect_ai._util.asyncfiles import AsyncFilesystem
from inspect_scout._transcript.local_files_cache import LocalFilesCache
from upath import UPath


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


@pytest.fixture
def remote_dir() -> Iterator[UPath]:
    """A unique directory on the process-global fsspec memory filesystem."""
    root = UPath(f"memory://{uuid.uuid4().hex}")
    yield root
    if root.exists():
        root.rmdir(recursive=True)


def _remote_files(root: UPath, count: int, size: int) -> list[str]:
    uris = []
    for i in range(count):
        path = root / f"{i}.eval"
        path.write_bytes(b"x" * size)
        uris.append(path.as_posix())
    return uris


@pytest.mark.asyncio
async def test_a_concurrent_download_renaming_its_temp_file_is_not_an_error(
    tmp_path: Path, remote_dir: UPath
) -> None:
    cache = LocalFilesCache(tmp_path / "cache")
    stop = threading.Event()

    # A download running off the event loop (an async fsspec filesystem runs it on
    # fsspec's thread) writes a temp file beside its target and renames it into place.
    def download_on_another_thread() -> None:
        temp, target = cache.cache_dir / "download.part", cache.cache_dir / "download"
        while not stop.is_set():
            temp.write_bytes(b"x")
            temp.replace(target)

    thread = threading.Thread(target=download_on_another_thread)
    thread.start()
    try:
        async with AsyncFilesystem() as fs:
            for uri in _remote_files(remote_dir, count=1000, size=1):
                await cache.resolve_remote_uri_to_local(fs, uri)
    finally:
        stop.set()
        thread.join()


@pytest.mark.asyncio
async def test_files_are_not_cached_once_the_cache_exceeds_its_size_cap(
    tmp_path: Path, remote_dir: UPath, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(LocalFilesCache, "MAX_CACHE_FILE_SIZE", 250)
    cache = LocalFilesCache(tmp_path / "cache")
    uris = _remote_files(remote_dir, count=4, size=100)

    async with AsyncFilesystem() as fs:
        resolved = [await cache.resolve_remote_uri_to_local(fs, uri) for uri in uris]

    # The cap is checked before each download, so the third one takes the cache past it.
    assert [Path(path).parent == cache.cache_dir for path in resolved[:3]] == [True] * 3
    assert resolved[3] == uris[3]
