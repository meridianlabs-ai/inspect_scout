from io import BytesIO
from typing import AsyncIterator

import pytest
from inspect_scout._util.async_bytes_reader import adapt_to_reader


async def bytes_iterator(data: bytes, chunk_size: int) -> AsyncIterator[bytes]:
    """Create an async iterator that yields bytes in chunks."""
    for i in range(0, len(data), chunk_size):
        yield data[i : i + chunk_size]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data,read_sizes,expected_results",
    [
        # Simple read
        (b"hello world", [11], [b"hello world"]),
        # Multiple reads
        (b"hello world", [5, 6], [b"hello", b" world"]),
        # Read more than available
        (b"hello", [10], [b"hello"]),
        # Multiple reads with last one exceeding data
        (b"hello world", [5, 10], [b"hello", b" world"]),
        # Read zero bytes
        (b"hello", [0, 5], [b"", b"hello"]),
        # Multiple small reads
        (b"abcdefghij", [1, 2, 3, 4], [b"a", b"bc", b"def", b"ghij"]),
        # Empty data
        (b"", [10], [b""]),
        # Single byte reads
        (b"abc", [1, 1, 1], [b"a", b"b", b"c"]),
        # Read after exhaustion
        (b"hi", [2, 5], [b"hi", b""]),
    ],
)
async def test_io_bytes_reader(
    data: bytes, read_sizes: list[int], expected_results: list[bytes]
) -> None:
    """Test adapt_to_reader with IO[bytes] input."""
    io = BytesIO(data)
    reader = adapt_to_reader(io)

    for size, expected in zip(read_sizes, expected_results, strict=True):
        result = await reader.read(size)
        assert result == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data,chunk_size,read_sizes,expected_results",
    [
        # Simple read with single chunk
        (b"hello world", 11, [11], [b"hello world"]),
        # Multiple reads with single chunk
        (b"hello world", 11, [5, 6], [b"hello", b" world"]),
        # Multiple reads with multiple chunks
        (b"hello world", 3, [5, 6], [b"hello", b" world"]),
        # Read more than available
        (b"hello", 2, [10], [b"hello"]),
        # Multiple reads with last one exceeding data
        (b"hello world", 4, [5, 10], [b"hello", b" world"]),
        # Read zero bytes
        (b"hello", 2, [0, 5], [b"", b"hello"]),
        # Multiple small reads with small chunks
        (b"abcdefghij", 2, [1, 2, 3, 4], [b"a", b"bc", b"def", b"ghij"]),
        # Empty data
        (b"", 10, [10], [b""]),
        # Single byte reads with single byte chunks
        (b"abc", 1, [1, 1, 1], [b"a", b"b", b"c"]),
        # Read after exhaustion
        (b"hi", 1, [2, 5], [b"hi", b""]),
        # Large read size with small chunks (buffering test)
        (b"0123456789", 2, [10], [b"0123456789"]),
        # Read spanning multiple chunks
        (b"abcdefghij", 3, [7], [b"abcdefg"]),
    ],
)
async def test_async_iterator_reader(
    data: bytes, chunk_size: int, read_sizes: list[int], expected_results: list[bytes]
) -> None:
    """Test adapt_to_reader with AsyncIterator[bytes] input."""
    async_iter = bytes_iterator(data, chunk_size)
    reader = adapt_to_reader(async_iter)

    for size, expected in zip(read_sizes, expected_results, strict=True):
        result = await reader.read(size)
        assert result == expected
