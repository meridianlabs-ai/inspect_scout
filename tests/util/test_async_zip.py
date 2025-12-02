import json
import os
import zipfile
from pathlib import Path

import pytest
from inspect_ai._util.asyncfiles import AsyncFilesystem
from inspect_scout._util.async_zip import AsyncZipReader


@pytest.fixture
def test_zip_file(tmp_path: Path) -> Path:
    """Create a test ZIP file with sample data."""
    zip_path = tmp_path / "test_data.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add test.json
        zf.writestr("test.json", json.dumps({"message": "hello world"}))
        # Add nested file
        zf.writestr("nested/data.txt", "This is nested data")

    return zip_path


@pytest.mark.asyncio
async def test_read_local_zip_member(test_zip_file: Path) -> None:
    """Test reading a member from a local ZIP file."""
    zip_path = str(test_zip_file)

    async with AsyncFilesystem() as fs:
        reader = AsyncZipReader(fs, zip_path)

        # Read the test.json member
        chunks = []
        async with reader.open_member("test.json") as stream:
            async for chunk in stream:
                chunks.append(chunk)

        # Verify content
        data = b"".join(chunks)
        parsed = json.loads(data.decode("utf-8"))
        assert parsed["message"] == "hello world"


@pytest.mark.asyncio
async def test_read_nested_member(test_zip_file: Path) -> None:
    """Test reading a nested member from a local ZIP file."""
    zip_path = str(test_zip_file)

    async with AsyncFilesystem() as fs:
        reader = AsyncZipReader(fs, zip_path)

        # Read the nested member
        chunks = []
        async with reader.open_member("nested/data.txt") as stream:
            async for chunk in stream:
                chunks.append(chunk)

        data = b"".join(chunks)
        assert data == b"This is nested data"


@pytest.mark.asyncio
async def test_open_member_reiteration(test_zip_file: Path) -> None:
    """Test that a member can be iterated multiple times within same context."""
    zip_path = str(test_zip_file)

    async with AsyncFilesystem() as fs:
        reader = AsyncZipReader(fs, zip_path)

        async with reader.open_member("test.json") as member:
            data1 = b"".join([chunk async for chunk in member])
            data2 = b"".join([chunk async for chunk in member])

        assert data1 == data2
        assert json.loads(data1.decode("utf-8"))["message"] == "hello world"


@pytest.mark.asyncio
async def test_concurrent_iteration(tmp_path: Path) -> None:
    """Test that multiple concurrent iterators work correctly."""
    # Create zip with large incompressible file to force multiple chunks
    zip_path = tmp_path / "large.zip"
    large_data = os.urandom(1024 * 1024 * 2)  # 2MB random data

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("large.bin", large_data)

    async with AsyncFilesystem() as fs:
        reader = AsyncZipReader(fs, str(zip_path))

        async with reader.open_member("large.bin") as member:
            # Get two independent iterators
            iter1 = aiter(member)
            iter2 = aiter(member)

            # Interleave: get first chunk from iter1, then from iter2
            chunk1_first = await anext(iter1)

            # Starting iter2 should NOT break iter1
            chunk2_first = await anext(iter2)

            # Continue iter1 - this is where the bug manifests
            chunks1 = [chunk1_first] + [chunk async for chunk in iter1]
            chunks2 = [chunk2_first] + [chunk async for chunk in iter2]

            data1 = b"".join(chunks1)
            data2 = b"".join(chunks2)

            # Both should get complete data
            assert data1 == large_data
            assert data2 == large_data


@pytest.mark.asyncio
async def test_member_not_found(test_zip_file: Path) -> None:
    """Test that KeyError is raised for non-existent member."""
    zip_path = str(test_zip_file)

    async with AsyncFilesystem() as fs:
        reader = AsyncZipReader(fs, zip_path)

        with pytest.raises(KeyError):
            async with reader.open_member("nonexistent.txt") as stream:
                async for _ in stream:
                    pass


@pytest.mark.asyncio
@pytest.mark.slow
async def test_read_s3_zip_member() -> None:
    """Test reading a specific member from a ZIP file stored in S3 (public bucket)."""
    zip_url = "s3://slow-tests/swe_bench.eval"
    member_name = "samples/astropy__astropy-14309_epoch_1.json"

    # Use anonymous S3 access for public bucket
    async with AsyncFilesystem() as fs:
        reader = AsyncZipReader(fs, zip_url)

        # Read the member and collect all chunks
        chunks: list[bytes] = []
        async with reader.open_member(member_name) as stream:
            async for chunk in stream:
                chunks.append(chunk)

        # Verify we got data
        _the_json = json.loads(b"".join(chunks).decode("utf-8"))
