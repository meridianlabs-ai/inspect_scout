"""Async ZIP file reader with streaming decompression support.

Supports reading individual members from large ZIP archives (including ZIP64)
stored locally or remotely (e.g., S3) using async range requests.
"""

import struct
import zlib
from collections.abc import AsyncIterator
from dataclasses import dataclass

import anyio
from anyio.abc import ByteReceiveStream
from inspect_ai._util.asyncfiles import AsyncFilesystem

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


class AsyncZipReader:
    """Async ZIP reader that supports streaming decompression of individual members.

    This reader minimizes data transfer by using range requests to read only
    the necessary portions of the ZIP file (central directory + requested member).
    Supports ZIP64 archives and streams decompressed data incrementally.

    Example:
        async with AsyncFilesystem() as fs:
            reader = AsyncZipReader(fs, "s3://bucket/large-archive.zip")
            async for chunk in reader.open_member("trajectory_001.json"):
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

    async def open_member(self, member: str | ZipEntry) -> AsyncIterator[bytes]:
        """Open a ZIP member and stream its decompressed contents.

        Args:
            member: Name or ZipEntry of the member file within the archive

        Returns:
            AsyncIterator of decompressed data chunks

        Raises:
            KeyError: If member_name not found in archive
            NotImplementedError: If compression method is not supported
        """
        offset, end, method = await self._get_member_range_and_method(member)
        return self._decompress_stream(
            await self._filesystem.read_file_bytes(self._filename, offset, end),
            method,
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

    async def _decompress_stream(
        self, compressed_stream: ByteReceiveStream, compression_method: int
    ) -> AsyncIterator[bytes]:
        # Yield stream based on compression method
        if compression_method == 0:
            # No compression - just iterate over the stream
            async for chunk in compressed_stream:
                yield chunk

        elif compression_method == 8:
            # DEFLATE compression - decompress while iterating
            decompressor = zlib.decompressobj(-15)  # Raw DEFLATE (no header)
            async for chunk in compressed_stream:
                decompressed = decompressor.decompress(chunk)
                if decompressed:
                    yield decompressed
            # Flush any remaining decompressed data
            final = decompressor.flush()
            if final:
                yield final

        else:
            raise NotImplementedError(
                f"Unsupported compression method {compression_method}"
            )
