"""Async ZIP file reader with streaming decompression support.

Supports reading individual members from large ZIP archives (including ZIP64)
stored locally or remotely (e.g., S3) using async range requests.
"""

from __future__ import annotations

import struct
import zlib
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import anyio
from anyio.abc import ByteReceiveStream
from inspect_ai._util.asyncfiles import AsyncFilesystem
from typing_extensions import Self

# Default chunk size for streaming compressed data (1MB)
DEFAULT_CHUNK_SIZE = 1024 * 1024


@dataclass
class ZipEntry:
    """Metadata for a single ZIP archive member."""

    filename: str
    compression_method: int
    compressed_size: int
    uncompressed_size: int
    local_header_offset: int


# This is an exploratory cache of central directories keyed by filename
# It's not production ready for a variety of reasons.
# The file may have changed since the last read:
#   - for some filesystems, we could add the etag into the key
#   - we could fall back to modified time??
# I'm still not confident about the relationship between this class
# and the filesystem class.

central_directories_cache: dict[str, list[ZipEntry]] = {}
_filename_locks: dict[str, anyio.Lock] = {}
_locks_lock = anyio.Lock()


class _DecompressStream(AsyncIterator[bytes]):
    """AsyncIterator wrapper for decompressing ZIP member data streams.

    This class replaces the async generator pattern to provide explicit control
    over resource cleanup via the aclose() method. This fixes Python 3.12 issues
    where async generator cleanup could fail with "generator already running" errors
    during event loop shutdown.
    """

    def __init__(self, compressed_stream: ByteReceiveStream, compression_method: int):
        """Initialize the decompression stream.

        Args:
            compressed_stream: The input byte stream to decompress
            compression_method: ZIP compression method (0=none, 8=DEFLATE)
        """
        self._compressed_stream = compressed_stream
        self._compression_method = compression_method
        self._decompressor: zlib._Decompress | None = None
        self._stream_iterator: AsyncIterator[bytes] | None = None
        self._exhausted = False
        self._closed = False

    def __aiter__(self) -> AsyncIterator[bytes]:
        """Return self as the async iterator."""
        return self

    async def __anext__(self) -> bytes:
        """Get the next chunk of decompressed data.

        Returns:
            Next chunk of decompressed bytes

        Raises:
            StopAsyncIteration: When stream is exhausted
        """
        if self._closed:
            raise StopAsyncIteration

        if self._exhausted:
            raise StopAsyncIteration

        # Initialize stream iterator on first call
        if self._stream_iterator is None:
            self._stream_iterator = self._compressed_stream.__aiter__()

        try:
            if self._compression_method == 0:
                # No compression - pass through
                return await self._stream_iterator.__anext__()

            elif self._compression_method == 8:
                # DEFLATE compression
                if self._decompressor is None:
                    self._decompressor = zlib.decompressobj(-15)  # Raw DEFLATE

                # Keep reading until we have decompressed data to return
                while True:
                    try:
                        chunk = await self._stream_iterator.__anext__()
                        decompressed = self._decompressor.decompress(chunk)
                        if decompressed:
                            return decompressed
                        # If no decompressed data, continue reading
                    except StopAsyncIteration:
                        # Input stream exhausted, flush any remaining data
                        if self._decompressor:
                            final = self._decompressor.flush()
                            self._decompressor = None
                            self._exhausted = True
                            if final:
                                return final
                        raise

            else:
                raise NotImplementedError(
                    f"Unsupported compression method {self._compression_method}"
                )

        except StopAsyncIteration:
            self._exhausted = True
            raise

    async def aclose(self) -> None:
        """Explicitly close the stream and underlying resources.

        This method ensures the ByteReceiveStream is properly closed even
        when the iterator is not fully consumed.
        """
        if self._closed:
            return

        self._closed = True
        self._exhausted = True

        # Close the underlying stream
        await self._compressed_stream.aclose()


async def _get_central_directory(
    filesystem: AsyncFilesystem, filename: str
) -> list[ZipEntry]:
    # Fast path: check cache without locks
    if (entries := central_directories_cache.get(filename, None)) is not None:
        return entries

    # Get or create the lock for this specific filename
    async with _locks_lock:
        if filename not in _filename_locks:
            _filename_locks[filename] = anyio.Lock()
        file_lock = _filename_locks[filename]

    # Acquire the per-filename lock
    async with file_lock:
        # Double-check after acquiring lock
        if (entries := central_directories_cache.get(filename, None)) is not None:
            return entries

        entries = await _parse_central_directory(filesystem, filename)
        central_directories_cache[filename] = entries
        return entries


async def _find_central_directory(
    filesystem: AsyncFilesystem, filename: str
) -> tuple[int, int]:
    """Locate and parse the central directory metadata.

    Returns:
        Tuple of (cd_offset, cd_size) where cd_offset is the byte offset
        of the central directory and cd_size is its size in bytes.

    Raises:
        ValueError: If EOCD signature not found or ZIP64 structure is corrupt
    """
    size = await filesystem.get_size(filename)

    # Read last 64KB to find EOCD
    tail_start = max(0, size - 65536)
    tail = await filesystem.read_file_bytes_fully(filename, tail_start, size)

    # Search backward for EOCD signature
    eocd_sig = b"PK\x05\x06"
    idx = tail.rfind(eocd_sig)
    if idx == -1:
        raise ValueError("EOCD not found")

    # Parse 32-bit EOCD fields
    (
        _disk_no,
        _cd_start_disk,
        _num_entries_disk,
        _num_entries_total,
        cd_size_32,
        cd_offset_32,
        _comment_len,
    ) = struct.unpack_from("<HHHHIIH", tail, idx + 4)

    cd_offset = cd_offset_32
    cd_size = cd_size_32

    # Check for ZIP64 EOCD locator
    loc_sig = b"PK\x06\x07"
    loc_idx = tail.rfind(loc_sig, 0, idx)
    if loc_idx != -1:
        # Parse ZIP64 EOCD locator to get EOCD64 offset
        fields = struct.unpack_from("<IQI", tail, loc_idx + 4)
        eocd64_offset = fields[1]

        # Read ZIP64 EOCD
        eocd64_data = await filesystem.read_file_bytes_fully(
            filename, eocd64_offset, eocd64_offset + 56
        )

        # Verify ZIP64 EOCD signature
        eocd64_sig = b"PK\x06\x06"
        if not eocd64_data.startswith(eocd64_sig):
            raise ValueError("Corrupt ZIP64 structure")

        # Parse ZIP64 central directory size and offset
        cd_size, cd_offset = struct.unpack_from("<QQ", eocd64_data, 40)

    return cd_offset, cd_size


async def _parse_central_directory(
    filesystem: AsyncFilesystem, filename: str
) -> list[ZipEntry]:
    """Parse the central directory and return all entries.

    Returns:
        List of ZipEntry objects, one per member in the archive
    """
    cd_offset, cd_size = await _find_central_directory(filesystem, filename)
    buf = await filesystem.read_file_bytes_fully(
        filename, cd_offset, cd_offset + cd_size
    )

    entries = []
    pos = 0
    sig = b"PK\x01\x02"

    while pos < len(buf):
        if pos + 4 > len(buf) or not buf[pos : pos + 4] == sig:
            break

        # Parse central directory file header (46 bytes)
        (
            _ver_made,
            _ver_needed,
            _flags,
            method,
            _time,
            _date,
            _crc,
            compressed_size,
            uncompressed_size,
            name_len,
            extra_len,
            comment_len,
            _disk,
            _int_attr,
            _ext_attr,
            local_header_off,
        ) = struct.unpack_from("<HHHHHHIIIHHHHHII", buf, pos + 4)

        # Extract filename
        name_start = pos + 46
        name = buf[name_start : name_start + name_len].decode("utf-8")

        # Extract extra field
        extra_start = name_start + name_len
        extra = buf[extra_start : extra_start + extra_len]

        # Handle ZIP64 extra fields (0x0001)
        if (
            compressed_size == 0xFFFFFFFF
            or uncompressed_size == 0xFFFFFFFF
            or local_header_off == 0xFFFFFFFF
        ):
            i = 0
            while i + 4 <= len(extra):
                header_id, data_size = struct.unpack_from("<HH", extra, i)
                i += 4
                if header_id == 0x0001:  # ZIP64 extended information
                    # Parse available 64-bit fields in order
                    num_fields = data_size // 8
                    if num_fields > 0:
                        fields = struct.unpack_from(f"<{num_fields}Q", extra, i)
                        field_idx = 0
                        if uncompressed_size == 0xFFFFFFFF and field_idx < len(fields):
                            uncompressed_size = fields[field_idx]
                            field_idx += 1
                        if compressed_size == 0xFFFFFFFF and field_idx < len(fields):
                            compressed_size = fields[field_idx]
                            field_idx += 1
                        if local_header_off == 0xFFFFFFFF and field_idx < len(fields):
                            local_header_off = fields[field_idx]
                    break
                i += data_size

        entries.append(
            ZipEntry(
                name,
                method,
                compressed_size,
                uncompressed_size,
                local_header_off,
            )
        )
        pos += 46 + name_len + extra_len + comment_len

    return entries


class _ZipMemberBytes:
    """AsyncIterable + AsyncContextManager for zip member data.

    Each iteration creates a fresh decompression stream, enabling re-reads:

        async with await zip_reader.open_member("file.json") as member:
            async for chunk in member:  # first read
                process(chunk)

            async for chunk in member:  # second read (e.g., retry on error)
                process_differently(chunk)
    """

    def __init__(
        self,
        filesystem: AsyncFilesystem,
        filename: str,
        range_and_method: tuple[int, int, int],
    ):
        self._filesystem = filesystem
        self._filename = filename
        self._offset, self._end, self._method = range_and_method
        self._active_streams: set[_DecompressStream] = set()

    async def __aiter__(self) -> AsyncIterator[bytes]:
        stream = _DecompressStream(
            await self._filesystem.read_file_bytes(
                self._filename, self._offset, self._end
            ),
            self._method,
        )
        self._active_streams.add(stream)
        try:
            async for chunk in stream:
                yield chunk
        finally:
            self._active_streams.discard(stream)
            await stream.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_args: Any) -> None:
        for stream in list(self._active_streams):
            await stream.aclose()
        self._active_streams.clear()


class AsyncZipReader:
    """Async ZIP reader that supports streaming decompression of individual members.

    This reader minimizes data transfer by using range requests to read only
    the necessary portions of the ZIP file (central directory + requested member).
    Supports ZIP64 archives and streams decompressed data incrementally.

    For example:

        async with AsyncFilesystem() as fs:
            reader = AsyncZipReader(fs, "s3://bucket/large-archive.zip")
            async with await reader.open_member("trajectory_001.json") as iterable:
                async for chunk in iterable:
                    process(chunk)
    """

    def __init__(
        self,
        filesystem: AsyncFilesystem,
        filename: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ):
        """Initialize the async ZIP reader.

        Args:
            filesystem: AsyncFilesystem instance for reading files
            filename: Path or URL to ZIP file (local path or s3:// URL)
            chunk_size: Size of chunks for streaming compressed data
        """
        self._filesystem = filesystem
        self._filename = filename
        self._chunk_size = chunk_size
        self._entries: list[ZipEntry] | None = None
        self._entries_lock = anyio.Lock()

    async def get_member_entry(self, member_name: str) -> ZipEntry:
        entries = await _get_central_directory(self._filesystem, self._filename)
        entry = next((e for e in entries if e.filename == member_name), None)
        if entry is None:
            raise KeyError(member_name)
        return entry

    async def open_member(self, member: str | ZipEntry) -> _ZipMemberBytes:
        """Open a ZIP member and stream its decompressed contents.

        Must be used as an async context manager to ensure proper cleanup.
        Can be re-iterated within the same context manager scope.

        Args:
            member: Name or ZipEntry of the member file within the archive

        Returns:
            AsyncIterable of decompressed data chunks

        Raises:
            KeyError: If member_name not found in archive
            NotImplementedError: If compression method is not supported

        Example:
            async with await zip_reader.open_member("file.json") as stream:
                async for chunk in stream:
                    process(chunk)
        """
        return _ZipMemberBytes(
            self._filesystem,
            self._filename,
            await self._get_member_range_and_method(member),
        )

    async def _get_member_range_and_method(
        self, member: str | ZipEntry
    ) -> tuple[int, int, int]:
        entry = (
            member
            if isinstance(member, ZipEntry)
            else await self.get_member_entry(member)
        )

        # Read local file header to determine actual data offset
        local_header = await self._filesystem.read_file_bytes_fully(
            self._filename,
            entry.local_header_offset,
            entry.local_header_offset + 30,
        )
        _, _, _, _, _, _, _, _, _, name_len, extra_len = struct.unpack_from(
            "<4sHHHHHIIIHH", local_header
        )

        data_offset = entry.local_header_offset + 30 + name_len + extra_len
        data_end = data_offset + entry.compressed_size
        return (data_offset, data_end, entry.compression_method)
