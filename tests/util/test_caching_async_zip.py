"""Tests for the global central-directory cache in cached_async_zip.

Verifies cross-instance sharing, cache-hit fast path, separate entries
for different files, and concurrent access correctness.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from unittest.mock import patch

import anyio
import pytest
from inspect_ai._util import async_zip as async_zip_mod
from inspect_ai._util.async_zip import CentralDirectory
from inspect_ai._util.asyncfiles import AsyncFilesystem
from inspect_ai._util.zip_common import ZipCompressionMethod, ZipEntry
from inspect_scout._util import caching_async_zip as cached_async_zip_mod
from inspect_scout._util.caching_async_zip import CachingAsyncZipReader


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    """Clear global cache before each test to ensure isolation."""
    cached_async_zip_mod._cache.clear()
    cached_async_zip_mod._filename_locks.clear()


@pytest.fixture
def zip_file_a(tmp_path: Path) -> Path:
    p = tmp_path / "a.zip"
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("hello.json", json.dumps({"src": "a"}))
    return p


@pytest.fixture
def zip_file_b(tmp_path: Path) -> Path:
    p = tmp_path / "b.zip"
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("world.json", json.dumps({"src": "b"}))
    return p


@pytest.mark.asyncio
async def test_cross_instance_sharing(zip_file_a: Path) -> None:
    """Two readers on the same file share one cached central directory."""
    path = str(zip_file_a)

    async with AsyncFilesystem() as fs:
        reader1 = CachingAsyncZipReader(fs, path)
        entry1 = await reader1.get_member_entry("hello.json")

        assert path in cached_async_zip_mod._cache

        reader2 = CachingAsyncZipReader(fs, path)
        entry2 = await reader2.get_member_entry("hello.json")

    assert entry1 == entry2


@pytest.mark.asyncio
async def test_cache_hit_fast_path() -> None:
    """Pre-populated cache is used even when the file doesn't exist on disk."""
    fake_path = "/nonexistent/fake.zip"
    fake_entry = ZipEntry(
        filename="cached.json",
        compression_method=ZipCompressionMethod.STORED,
        compressed_size=100,
        uncompressed_size=100,
        local_header_offset=0,
    )
    cached_async_zip_mod._cache[fake_path] = CentralDirectory(entries=[fake_entry])

    async with AsyncFilesystem() as fs:
        reader = CachingAsyncZipReader(fs, fake_path)
        entry = await reader.get_member_entry("cached.json")

    assert entry == fake_entry


@pytest.mark.asyncio
async def test_different_files_separate_entries(
    zip_file_a: Path, zip_file_b: Path
) -> None:
    """Different files get independent cache entries."""
    path_a, path_b = str(zip_file_a), str(zip_file_b)

    async with AsyncFilesystem() as fs:
        reader_a = CachingAsyncZipReader(fs, path_a)
        entry_a = await reader_a.get_member_entry("hello.json")

        reader_b = CachingAsyncZipReader(fs, path_b)
        entry_b = await reader_b.get_member_entry("world.json")

    assert path_a in cached_async_zip_mod._cache
    assert path_b in cached_async_zip_mod._cache
    assert entry_a.filename == "hello.json"
    assert entry_b.filename == "world.json"


@pytest.mark.asyncio
async def test_concurrent_access_parses_once(zip_file_a: Path) -> None:
    """Concurrent readers on the same file parse the central directory only once."""
    path = str(zip_file_a)

    parse_count = 0
    original_parse = async_zip_mod._parse_central_directory

    async def counting_parse(
        filesystem: AsyncFilesystem, filename: str
    ) -> CentralDirectory:
        nonlocal parse_count
        parse_count += 1
        return await original_parse(filesystem, filename)

    with patch.object(async_zip_mod, "_parse_central_directory", counting_parse):
        async with AsyncFilesystem() as fs:
            async with anyio.create_task_group() as tg:

                async def read_member() -> None:
                    reader = CachingAsyncZipReader(fs, path)
                    await reader.get_member_entry("hello.json")

                for _ in range(10):
                    tg.start_soon(read_member)

    assert parse_count == 1
