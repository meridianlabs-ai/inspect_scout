"""Tests for CompressedToDeflateStream."""

import zlib
from collections.abc import AsyncIterator
from typing import Any

import pytest
import zstandard
from inspect_scout._util.compression_transcoding import CompressedToDeflateStream
from inspect_scout._util.zip_common import ZipCompressionMethod

# --- Test Helpers ---


def deflate_compress(data: bytes) -> bytes:
    """Compress data using raw DEFLATE (no zlib header)."""
    compressor = zlib.compressobj(level=6, wbits=-15)
    return compressor.compress(data) + compressor.flush()


def deflate_decompress(data: bytes) -> bytes:
    """Decompress raw DEFLATE data."""
    decompressor = zlib.decompressobj(-15)
    return decompressor.decompress(data) + decompressor.flush()


def zstd_compress(data: bytes) -> bytes:
    """Compress data using zstd."""
    cctx = zstandard.ZstdCompressor()
    return cctx.compress(data)


class MockSourceContextManager:
    """Mock async context manager that yields chunks of data."""

    def __init__(
        self,
        data: bytes,
        chunk_size: int = 1024,
        fail_on_enter: bool = False,
    ) -> None:
        self.data = data
        self.chunk_size = chunk_size
        self.fail_on_enter = fail_on_enter
        self.entered = False
        self.exited = False
        self.exit_exc_info: tuple[Any, ...] | None = None

    async def __aenter__(self) -> AsyncIterator[bytes]:
        if self.fail_on_enter:
            raise RuntimeError("Simulated source entry failure")
        self.entered = True
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[bytes]:
        for i in range(0, len(self.data), self.chunk_size):
            yield self.data[i : i + self.chunk_size]

    async def __aexit__(self, *exc_info: object) -> None:
        self.exited = True
        self.exit_exc_info = exc_info


async def collect_stream(stream: AsyncIterator[bytes]) -> bytes:
    """Collect all chunks from an async iterator into bytes."""
    chunks = []
    async for chunk in stream:
        chunks.append(chunk)
    return b"".join(chunks)


# --- Tests for COMPRESSION_STORED (uncompressed → deflate) ---


@pytest.mark.asyncio
async def test_stored_to_deflate_basic() -> None:
    """Test that uncompressed data is deflate-compressed."""
    original = b"Hello, World! " * 100
    source = MockSourceContextManager(original)

    async with CompressedToDeflateStream(source, ZipCompressionMethod.STORED) as stream:
        compressed = await collect_stream(stream)

    # Verify we can decompress the output
    decompressed = deflate_decompress(compressed)
    assert decompressed == original


@pytest.mark.asyncio
async def test_stored_to_deflate_compresses_data() -> None:
    """Test that the output is actually smaller (compressed)."""
    # Highly compressible data
    original = b"A" * 10000
    source = MockSourceContextManager(original)

    async with CompressedToDeflateStream(source, ZipCompressionMethod.STORED) as stream:
        compressed = await collect_stream(stream)

    assert len(compressed) < len(original)
    assert deflate_decompress(compressed) == original


@pytest.mark.asyncio
async def test_stored_to_deflate_empty_data() -> None:
    """Test handling of empty input."""
    source = MockSourceContextManager(b"")

    async with CompressedToDeflateStream(source, ZipCompressionMethod.STORED) as stream:
        compressed = await collect_stream(stream)

    decompressed = deflate_decompress(compressed)
    assert decompressed == b""


@pytest.mark.asyncio
async def test_stored_to_deflate_large_data() -> None:
    """Test handling of large data that requires multiple chunks."""
    # 1MB of data
    original = b"The quick brown fox jumps over the lazy dog. " * 25000
    source = MockSourceContextManager(original, chunk_size=8192)

    async with CompressedToDeflateStream(source, ZipCompressionMethod.STORED) as stream:
        compressed = await collect_stream(stream)

    decompressed = deflate_decompress(compressed)
    assert decompressed == original


# --- Tests for COMPRESSION_ZSTD (zstd → deflate) ---


@pytest.mark.asyncio
async def test_zstd_to_deflate_basic() -> None:
    """Test that zstd-compressed data is transcoded to deflate."""
    original = b"Hello from zstd! " * 100
    zstd_data = zstd_compress(original)
    source = MockSourceContextManager(zstd_data)

    async with CompressedToDeflateStream(source, ZipCompressionMethod.ZSTD) as stream:
        deflate_output = await collect_stream(stream)

    # Verify the output is valid deflate that decompresses to original
    decompressed = deflate_decompress(deflate_output)
    assert decompressed == original


@pytest.mark.asyncio
async def test_zstd_to_deflate_large_data() -> None:
    """Test zstd → deflate with large data."""
    original = b"Zstd test data pattern. " * 50000
    zstd_data = zstd_compress(original)
    source = MockSourceContextManager(zstd_data, chunk_size=4096)

    async with CompressedToDeflateStream(source, ZipCompressionMethod.ZSTD) as stream:
        deflate_output = await collect_stream(stream)

    decompressed = deflate_decompress(deflate_output)
    assert decompressed == original


# --- Tests for COMPRESSION_DEFLATE (passthrough) ---


@pytest.mark.asyncio
async def test_deflate_passthrough_basic() -> None:
    """Test that already-deflate data passes through unchanged."""
    original = b"Already compressed data. " * 100
    deflate_data = deflate_compress(original)
    source = MockSourceContextManager(deflate_data)

    async with CompressedToDeflateStream(
        source, ZipCompressionMethod.DEFLATE
    ) as stream:
        output = await collect_stream(stream)

    # Output should be identical to input (passthrough)
    assert output == deflate_data
    # And should decompress correctly
    assert deflate_decompress(output) == original


@pytest.mark.asyncio
async def test_deflate_passthrough_small_data() -> None:
    """Test that passthrough works when data is smaller than chunk size."""
    original = b"Small data"
    deflate_data = deflate_compress(original)
    # Chunk size larger than the data
    source = MockSourceContextManager(deflate_data, chunk_size=1000)

    async with CompressedToDeflateStream(
        source, ZipCompressionMethod.DEFLATE
    ) as stream:
        output = await collect_stream(stream)

    assert output == deflate_data
    assert deflate_decompress(output) == original


@pytest.mark.asyncio
async def test_deflate_passthrough_preserves_chunking() -> None:
    """Test that passthrough preserves the chunking pattern from source."""
    # Use data large enough to produce multiple chunks
    original = b"Test data pattern. " * 500
    deflate_data = deflate_compress(original)
    chunk_size = 50
    source = MockSourceContextManager(deflate_data, chunk_size=chunk_size)

    # Count chunks from source directly for comparison
    expected_chunk_count = (len(deflate_data) + chunk_size - 1) // chunk_size

    chunks_received = []
    async with CompressedToDeflateStream(
        source, ZipCompressionMethod.DEFLATE
    ) as stream:
        async for chunk in stream:
            chunks_received.append(chunk)

    # Passthrough should preserve the same number of chunks as source produces
    assert len(chunks_received) == expected_chunk_count
    assert b"".join(chunks_received) == deflate_data


@pytest.mark.asyncio
async def test_deflate_passthrough_no_double_compression() -> None:
    """Verify that deflate input is NOT double-compressed (regression test)."""
    original = b"This should not be double compressed! " * 100
    deflate_data = deflate_compress(original)
    source = MockSourceContextManager(deflate_data)

    async with CompressedToDeflateStream(
        source, ZipCompressionMethod.DEFLATE
    ) as stream:
        output = await collect_stream(stream)

    # If double-compressed, decompressing once would give deflate_data
    # If passthrough (correct), decompressing once gives original
    decompressed = deflate_decompress(output)
    assert decompressed == original, "Data was double-compressed!"


# --- Tests for context manager semantics ---


@pytest.mark.asyncio
async def test_context_manager_enters_source() -> None:
    """Test that __aenter__ enters the source context manager."""
    source = MockSourceContextManager(b"test")

    assert not source.entered
    async with CompressedToDeflateStream(source, ZipCompressionMethod.STORED) as stream:
        assert source.entered
        await collect_stream(stream)


@pytest.mark.asyncio
async def test_context_manager_exits_source() -> None:
    """Test that __aexit__ exits the source context manager."""
    source = MockSourceContextManager(b"test")

    async with CompressedToDeflateStream(source, ZipCompressionMethod.STORED) as stream:
        await collect_stream(stream)
        assert not source.exited

    assert source.exited


@pytest.mark.asyncio
async def test_context_manager_exits_source_on_exception() -> None:
    """Test that source is cleaned up even when an exception occurs."""
    source = MockSourceContextManager(b"test")

    with pytest.raises(ValueError, match="test error"):
        async with CompressedToDeflateStream(
            source, ZipCompressionMethod.STORED
        ) as stream:
            await collect_stream(stream)
            raise ValueError("test error")

    assert source.exited


@pytest.mark.asyncio
async def test_context_manager_passes_exception_info() -> None:
    """Test that exception info is passed to source __aexit__."""
    source = MockSourceContextManager(b"test")

    with pytest.raises(ValueError):
        async with CompressedToDeflateStream(
            source, ZipCompressionMethod.STORED
        ) as stream:
            await collect_stream(stream)
            raise ValueError("propagate this")

    assert source.exit_exc_info is not None
    assert source.exit_exc_info[0] is ValueError


@pytest.mark.asyncio
async def test_double_exit_is_idempotent() -> None:
    """Test that calling __aexit__ multiple times is safe."""
    source = MockSourceContextManager(b"test")
    transcoder = CompressedToDeflateStream(source, ZipCompressionMethod.STORED)

    async with transcoder as stream:
        await collect_stream(stream)

    # Call __aexit__ again - should not raise
    await transcoder.__aexit__(None, None, None)
    assert source.exited


@pytest.mark.asyncio
async def test_aclose_without_context() -> None:
    """Test that aclose() works without using context manager."""
    source = MockSourceContextManager(b"test")
    transcoder = CompressedToDeflateStream(source, ZipCompressionMethod.STORED)

    # aclose without entering should be safe (nothing to close)
    await transcoder.aclose()


@pytest.mark.asyncio
async def test_aclose_is_idempotent() -> None:
    """Test that calling aclose() multiple times is safe."""
    source = MockSourceContextManager(b"test")
    transcoder = CompressedToDeflateStream(source, ZipCompressionMethod.STORED)

    stream = await transcoder.__aenter__()
    await collect_stream(stream)

    await transcoder.aclose()
    await transcoder.aclose()  # Should not raise


# --- Tests for cleanup on source __aenter__ failure ---


class FailingSourceContextManager:
    """Mock that fails during __aenter__."""

    def __init__(self) -> None:
        self.exited = False

    async def __aenter__(self) -> AsyncIterator[bytes]:
        raise RuntimeError("Source failed to open")

    async def __aexit__(self, *exc_info: object) -> None:
        self.exited = True


@pytest.mark.asyncio
async def test_source_enter_failure_propagates() -> None:
    """Test that source __aenter__ failure propagates correctly."""
    source = FailingSourceContextManager()

    with pytest.raises(RuntimeError, match="Source failed to open"):
        async with CompressedToDeflateStream(source, ZipCompressionMethod.STORED):
            pass


# --- Tests for cleanup on stream creation failure ---


class FailingIteratorSourceContextManager:
    """Mock where __aenter__ succeeds but iteration setup could fail."""

    def __init__(self, fail_on_iter: bool = False) -> None:
        self.fail_on_iter = fail_on_iter
        self.exited = False

    async def __aenter__(self) -> AsyncIterator[bytes]:
        if self.fail_on_iter:
            # Simulate returning something that fails when __aiter__ is called
            raise RuntimeError("Iterator creation failed")
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[bytes]:
        yield b"test"

    async def __aexit__(self, *exc_info: object) -> None:
        self.exited = True


# --- Tests for default compression parameter ---


@pytest.mark.asyncio
async def test_default_compression_is_stored() -> None:
    """Test that default source_compression is COMPRESSION_STORED."""
    original = b"Test default compression. " * 50
    source = MockSourceContextManager(original)

    # Don't specify source_compression - should default to STORED
    async with CompressedToDeflateStream(source) as stream:
        compressed = await collect_stream(stream)

    decompressed = deflate_decompress(compressed)
    assert decompressed == original


# --- Tests for binary data ---


@pytest.mark.asyncio
async def test_handles_binary_data() -> None:
    """Test that binary data (non-text) is handled correctly."""
    # Random binary data with all byte values
    original = bytes(range(256)) * 100
    source = MockSourceContextManager(original)

    async with CompressedToDeflateStream(source, ZipCompressionMethod.STORED) as stream:
        compressed = await collect_stream(stream)

    decompressed = deflate_decompress(compressed)
    assert decompressed == original


@pytest.mark.asyncio
async def test_handles_binary_data_zstd() -> None:
    """Test that binary data transcodes correctly from zstd."""
    original = bytes(range(256)) * 100
    zstd_data = zstd_compress(original)
    source = MockSourceContextManager(zstd_data)

    async with CompressedToDeflateStream(source, ZipCompressionMethod.ZSTD) as stream:
        deflate_output = await collect_stream(stream)

    decompressed = deflate_decompress(deflate_output)
    assert decompressed == original


# --- Parameterized tests for all compression types ---


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "compression,prepare_data",
    [
        (ZipCompressionMethod.STORED, lambda d: d),
        (ZipCompressionMethod.DEFLATE, deflate_compress),
        (ZipCompressionMethod.ZSTD, zstd_compress),
    ],
    ids=["stored", "deflate", "zstd"],
)
async def test_all_compression_types_produce_valid_deflate(
    compression: ZipCompressionMethod,
    prepare_data: Any,
) -> None:
    """Test that all source compression types produce valid deflate output."""
    original = b"Universal test data. " * 100
    source_data = prepare_data(original)
    source = MockSourceContextManager(source_data)

    async with CompressedToDeflateStream(source, compression) as stream:
        output = await collect_stream(stream)

    # All outputs should decompress to the original data
    decompressed = deflate_decompress(output)
    assert decompressed == original


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "compression,prepare_data",
    [
        (ZipCompressionMethod.STORED, lambda d: d),
        (ZipCompressionMethod.DEFLATE, deflate_compress),
        (ZipCompressionMethod.ZSTD, zstd_compress),
    ],
    ids=["stored", "deflate", "zstd"],
)
async def test_all_compression_types_cleanup_source(
    compression: ZipCompressionMethod,
    prepare_data: Any,
) -> None:
    """Test that all compression types properly clean up the source."""
    original = b"Cleanup test. " * 50
    source_data = prepare_data(original)
    source = MockSourceContextManager(source_data)

    async with CompressedToDeflateStream(source, compression) as stream:
        await collect_stream(stream)

    assert source.exited


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "compression,prepare_data",
    [
        (ZipCompressionMethod.STORED, lambda d: d),
        (ZipCompressionMethod.DEFLATE, deflate_compress),
        (ZipCompressionMethod.ZSTD, zstd_compress),
    ],
    ids=["stored", "deflate", "zstd"],
)
async def test_all_compression_types_handle_data_smaller_than_chunk(
    compression: ZipCompressionMethod,
    prepare_data: Any,
) -> None:
    """Test that all compression types work when source data is smaller than chunk size."""
    original = b"Small"  # Very small data
    source_data = prepare_data(original)
    # Chunk size much larger than the data
    source = MockSourceContextManager(source_data, chunk_size=10000)

    async with CompressedToDeflateStream(source, compression) as stream:
        output = await collect_stream(stream)

    decompressed = deflate_decompress(output)
    assert decompressed == original
