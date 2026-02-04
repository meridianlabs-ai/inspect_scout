"""Tests for CompressedToUncompressedStream.

These tests ensure the CompressedToUncompressedStream class correctly decompresses
data in DEFLATE (8) and zstd (93) compression formats. Mode 0 (COMPRESSION_STORED)
is rejected since callers should use the source stream directly for uncompressed data.
"""

import zlib
from collections.abc import AsyncIterator, Callable
from typing import Literal, cast

import pytest
import zstandard
from anyio.abc import ByteReceiveStream
from inspect_scout._util.compression_transcoding import CompressedToUncompressedStream
from inspect_scout._util.zip_common import ZipCompressionMethod

# --- Test Helpers ---


class MockByteStream:
    """Mock byte stream that yields data in chunks.

    Implements the interface expected by CompressedToUncompressedStream:
    - __aiter__() returning an AsyncIterator[bytes]
    - aclose() for cleanup

    Note: CompressedToUncompressedStream is typed to expect ByteReceiveStream but actually
    uses AsyncIterable protocol. We cast to satisfy the type checker.
    """

    def __init__(self, data: bytes, chunk_size: int = 1024) -> None:
        self.data = data
        self.chunk_size = chunk_size
        self._position = 0
        self._closed = False

    def __aiter__(self) -> AsyncIterator[bytes]:
        return self

    async def __anext__(self) -> bytes:
        if self._closed or self._position >= len(self.data):
            raise StopAsyncIteration
        end = min(self._position + self.chunk_size, len(self.data))
        chunk = self.data[self._position : end]
        self._position = end
        return chunk

    async def aclose(self) -> None:
        self._closed = True

    def as_byte_receive_stream(self) -> ByteReceiveStream:
        """Cast to ByteReceiveStream for type checking."""
        return cast(ByteReceiveStream, self)


def deflate_compress(data: bytes) -> bytes:
    """Compress data using raw DEFLATE (no zlib header)."""
    compressor = zlib.compressobj(level=6, wbits=-15)
    return compressor.compress(data) + compressor.flush()


def zstd_compress(data: bytes) -> bytes:
    """Compress data using zstd."""
    cctx = zstandard.ZstdCompressor()
    return cctx.compress(data)


async def collect_stream(stream: CompressedToUncompressedStream) -> bytes:
    """Collect all chunks from a CompressedToUncompressedStream into bytes."""
    chunks = []
    async for chunk in stream:
        chunks.append(chunk)
    return b"".join(chunks)


# --- Tests for mode 8 (DEFLATE) ---


@pytest.mark.asyncio
async def test_mode_8_deflate_basic() -> None:
    """Test that mode 8 decompresses DEFLATE data."""
    original = b"Hello, World! " * 100
    compressed = deflate_compress(original)
    source = MockByteStream(compressed)
    stream = CompressedToUncompressedStream(
        source.as_byte_receive_stream(), ZipCompressionMethod.DEFLATE
    )

    try:
        result = await collect_stream(stream)
    finally:
        await stream.aclose()

    assert result == original


@pytest.mark.asyncio
async def test_mode_8_deflate_empty_data() -> None:
    """Test that mode 8 handles empty compressed data."""
    original = b""
    compressed = deflate_compress(original)
    source = MockByteStream(compressed)
    stream = CompressedToUncompressedStream(
        source.as_byte_receive_stream(), ZipCompressionMethod.DEFLATE
    )

    try:
        result = await collect_stream(stream)
    finally:
        await stream.aclose()

    assert result == original


@pytest.mark.asyncio
async def test_mode_8_deflate_large_data() -> None:
    """Test that mode 8 handles large data requiring multiple chunks."""
    original = b"The quick brown fox jumps over the lazy dog. " * 50000
    compressed = deflate_compress(original)
    source = MockByteStream(compressed, chunk_size=4096)
    stream = CompressedToUncompressedStream(
        source.as_byte_receive_stream(), ZipCompressionMethod.DEFLATE
    )

    try:
        result = await collect_stream(stream)
    finally:
        await stream.aclose()

    assert result == original


@pytest.mark.asyncio
async def test_mode_8_deflate_binary_data() -> None:
    """Test that mode 8 handles binary data with all byte values."""
    original = bytes(range(256)) * 100
    compressed = deflate_compress(original)
    source = MockByteStream(compressed)
    stream = CompressedToUncompressedStream(
        source.as_byte_receive_stream(), ZipCompressionMethod.DEFLATE
    )

    try:
        result = await collect_stream(stream)
    finally:
        await stream.aclose()

    assert result == original


@pytest.mark.asyncio
async def test_mode_8_deflate_small_chunks() -> None:
    """Test that mode 8 works with very small input chunks."""
    original = b"Small chunk test data. " * 50
    compressed = deflate_compress(original)
    # Very small chunks to stress the decompressor
    source = MockByteStream(compressed, chunk_size=10)
    stream = CompressedToUncompressedStream(
        source.as_byte_receive_stream(), ZipCompressionMethod.DEFLATE
    )

    try:
        result = await collect_stream(stream)
    finally:
        await stream.aclose()

    assert result == original


# --- Tests for mode 93 (zstd) ---


@pytest.mark.asyncio
async def test_mode_93_zstd_basic() -> None:
    """Test that mode 93 decompresses zstd data."""
    original = b"Hello from zstd! " * 100
    compressed = zstd_compress(original)
    source = MockByteStream(compressed)
    stream = CompressedToUncompressedStream(
        source.as_byte_receive_stream(), ZipCompressionMethod.ZSTD
    )

    try:
        result = await collect_stream(stream)
    finally:
        await stream.aclose()

    assert result == original


@pytest.mark.asyncio
async def test_mode_93_zstd_large_data() -> None:
    """Test that mode 93 handles large data."""
    original = b"Zstd handles large data well. " * 50000
    compressed = zstd_compress(original)
    source = MockByteStream(compressed, chunk_size=8192)
    stream = CompressedToUncompressedStream(
        source.as_byte_receive_stream(), ZipCompressionMethod.ZSTD
    )

    try:
        result = await collect_stream(stream)
    finally:
        await stream.aclose()

    assert result == original


@pytest.mark.asyncio
async def test_mode_93_zstd_binary_data() -> None:
    """Test that mode 93 handles binary data."""
    original = bytes(range(256)) * 100
    compressed = zstd_compress(original)
    source = MockByteStream(compressed)
    stream = CompressedToUncompressedStream(
        source.as_byte_receive_stream(), ZipCompressionMethod.ZSTD
    )

    try:
        result = await collect_stream(stream)
    finally:
        await stream.aclose()

    assert result == original


@pytest.mark.asyncio
async def test_mode_93_zstd_small_chunks() -> None:
    """Test that mode 93 works with small input chunks."""
    original = b"Small chunk zstd test. " * 50
    compressed = zstd_compress(original)
    source = MockByteStream(compressed, chunk_size=10)
    stream = CompressedToUncompressedStream(
        source.as_byte_receive_stream(), ZipCompressionMethod.ZSTD
    )

    try:
        result = await collect_stream(stream)
    finally:
        await stream.aclose()

    assert result == original


# --- Tests for aclose() behavior ---


@pytest.mark.asyncio
async def test_aclose_closes_underlying_stream() -> None:
    """Test that aclose() closes the underlying ByteReceiveStream."""
    compressed = deflate_compress(b"test data")
    source = MockByteStream(compressed)
    stream = CompressedToUncompressedStream(
        source.as_byte_receive_stream(), ZipCompressionMethod.DEFLATE
    )

    assert not source._closed
    await stream.aclose()
    assert source._closed


@pytest.mark.asyncio
async def test_aclose_is_idempotent() -> None:
    """Test that calling aclose() multiple times is safe."""
    compressed = deflate_compress(b"test data")
    source = MockByteStream(compressed)
    stream = CompressedToUncompressedStream(
        source.as_byte_receive_stream(), ZipCompressionMethod.DEFLATE
    )

    await stream.aclose()
    await stream.aclose()  # Should not raise
    assert source._closed


@pytest.mark.asyncio
async def test_aclose_before_iteration() -> None:
    """Test that aclose() before iteration is safe."""
    compressed = deflate_compress(b"test data")
    source = MockByteStream(compressed)
    stream = CompressedToUncompressedStream(
        source.as_byte_receive_stream(), ZipCompressionMethod.DEFLATE
    )

    await stream.aclose()

    # Iteration after close should immediately stop
    result = await collect_stream(stream)
    assert result == b""


@pytest.mark.asyncio
async def test_aclose_during_iteration() -> None:
    """Test that aclose() during iteration stops the stream."""
    # Use enough data to generate multiple decompressed chunks
    original = b"The quick brown fox jumps over the lazy dog. " * 1000
    compressed = deflate_compress(original)
    source = MockByteStream(compressed, chunk_size=100)
    stream = CompressedToUncompressedStream(
        source.as_byte_receive_stream(), ZipCompressionMethod.DEFLATE
    )

    chunks = []
    async for chunk in stream:
        chunks.append(chunk)
        if len(chunks) >= 1:
            # Close after receiving at least one chunk
            await stream.aclose()
            break

    # Should have received at least one chunk before close
    assert len(chunks) >= 1
    assert source._closed


# --- Tests for iteration after exhaustion ---


@pytest.mark.asyncio
async def test_iteration_after_exhaustion() -> None:
    """Test that iterating an exhausted stream yields nothing."""
    original = b"short data for exhaustion test"
    compressed = deflate_compress(original)
    source = MockByteStream(compressed)
    stream = CompressedToUncompressedStream(
        source.as_byte_receive_stream(), ZipCompressionMethod.DEFLATE
    )

    try:
        # First iteration
        result1 = await collect_stream(stream)
        assert result1 == original

        # Second iteration should yield nothing
        result2 = await collect_stream(stream)
        assert result2 == b""
    finally:
        await stream.aclose()


# --- Parameterized tests across supported modes ---


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mode,prepare_data",
    [
        (ZipCompressionMethod.DEFLATE, deflate_compress),
        (ZipCompressionMethod.ZSTD, zstd_compress),
    ],
    ids=["deflate", "zstd"],
)
async def test_all_modes_produce_correct_output(
    mode: Literal[ZipCompressionMethod.DEFLATE, ZipCompressionMethod.ZSTD],
    prepare_data: Callable[[bytes], bytes],
) -> None:
    """Test that all supported modes produce correct output."""
    original = b"Universal test data pattern. " * 100
    source_data = prepare_data(original)
    source = MockByteStream(source_data)
    stream = CompressedToUncompressedStream(source.as_byte_receive_stream(), mode)

    try:
        result = await collect_stream(stream)
    finally:
        await stream.aclose()

    assert result == original


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mode,prepare_data",
    [
        (ZipCompressionMethod.DEFLATE, deflate_compress),
        (ZipCompressionMethod.ZSTD, zstd_compress),
    ],
    ids=["deflate", "zstd"],
)
async def test_all_modes_close_underlying_stream(
    mode: Literal[ZipCompressionMethod.DEFLATE, ZipCompressionMethod.ZSTD],
    prepare_data: Callable[[bytes], bytes],
) -> None:
    """Test that all modes close the underlying stream on aclose()."""
    original = b"Test data"
    source_data = prepare_data(original)
    source = MockByteStream(source_data)
    stream = CompressedToUncompressedStream(source.as_byte_receive_stream(), mode)

    try:
        await collect_stream(stream)
    finally:
        await stream.aclose()

    assert source._closed
