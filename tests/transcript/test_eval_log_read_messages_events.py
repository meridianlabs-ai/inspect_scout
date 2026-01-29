"""Tests for EvalLogTranscriptsView.read_messages_events()."""

import zipfile
from pathlib import Path

import pytest
from inspect_scout._transcript.eval_log import EvalLogTranscriptsView
from inspect_scout._transcript.types import TranscriptInfo

TEST_EVAL_LOGS_DIR = Path(__file__).parent.parent / "recorder" / "logs"


async def _get_first_transcript_info(view: EvalLogTranscriptsView) -> TranscriptInfo:
    """Get first transcript info from view."""
    async for info in view.select():
        return info
    raise AssertionError("No transcripts found")


def _get_raw_zip_entry_bytes(eval_path: Path, entry_name: str) -> tuple[bytes, int]:
    """Extract raw compressed bytes and compression method from ZIP entry.

    Returns:
        Tuple of (raw_bytes, compression_method)
    """
    with zipfile.ZipFile(eval_path) as zf:
        info = zf.getinfo(entry_name)
        # Read raw compressed data by seeking to the entry
        with open(eval_path, "rb") as f:
            # Skip local file header to get to compressed data
            f.seek(info.header_offset)
            # Local file header: 4 sig + 22 fixed + variable name + extra
            header = f.read(30)
            name_len = int.from_bytes(header[26:28], "little")
            extra_len = int.from_bytes(header[28:30], "little")
            f.seek(info.header_offset + 30 + name_len + extra_len)
            raw_bytes = f.read(info.compress_size)
        return raw_bytes, info.compress_type


@pytest.mark.asyncio
async def test_read_messages_events_returns_raw_zip_bytes() -> None:
    """Returned bytes exactly match raw ZIP entry bytes (passthrough)."""
    eval_path = (
        TEST_EVAL_LOGS_DIR
        / "2025-11-07T10-59-47-05-00_websearch-addition-problem_LqPDntDnkk4h2fSqQ8i6CE.eval"
    )

    async with EvalLogTranscriptsView(str(eval_path)) as view:
        info = await _get_first_transcript_info(view)
        result = await view.read_messages_events(info)
    # view closed, but result.data hasn't opened anything yet

    # Collect all bytes from the async iterable
    chunks: list[bytes] = []
    async with result.data as data:
        async for chunk in data:
            chunks.append(chunk)
    returned_bytes = b"".join(chunks)

    # Get ground truth: raw bytes directly from ZIP
    # The sample file naming convention is samples/{id}_epoch_{epoch}.json
    sample_entry_name = "samples/1_epoch_1.json"
    expected_bytes, expected_method = _get_raw_zip_entry_bytes(
        eval_path, sample_entry_name
    )

    assert result.compression_method == expected_method
    assert returned_bytes == expected_bytes


@pytest.mark.asyncio
async def test_read_messages_events_compression_method_matches_zip() -> None:
    """compression_method matches the ZIP entry's compression method."""
    eval_path = (
        TEST_EVAL_LOGS_DIR
        / "2025-11-07T10-59-47-05-00_websearch-addition-problem_LqPDntDnkk4h2fSqQ8i6CE.eval"
    )

    async with EvalLogTranscriptsView(str(eval_path)) as view:
        info = await _get_first_transcript_info(view)
        result = await view.read_messages_events(info)

    # Get compression method directly from ZIP
    with zipfile.ZipFile(eval_path) as zf:
        zip_info = zf.getinfo("samples/1_epoch_1.json")
        expected_method = zip_info.compress_type

    assert result.compression_method == expected_method


@pytest.mark.asyncio
async def test_read_messages_events_decompresses_to_valid_json() -> None:
    """When decompressed, data is valid JSON with messages and events."""
    import json
    import zlib

    eval_path = (
        TEST_EVAL_LOGS_DIR
        / "2025-11-07T10-59-47-05-00_websearch-addition-problem_LqPDntDnkk4h2fSqQ8i6CE.eval"
    )

    async with EvalLogTranscriptsView(str(eval_path)) as view:
        info = await _get_first_transcript_info(view)
        result = await view.read_messages_events(info)
    # view closed, but result.data hasn't opened anything yet

    chunks: list[bytes] = []
    async with result.data as data:
        async for chunk in data:
            chunks.append(chunk)
    raw_bytes = b"".join(chunks)

    # Decompress based on compression method
    if result.compression_method == 8:  # DEFLATE
        decompressed = zlib.decompress(raw_bytes, -15)  # raw DEFLATE
    elif result.compression_method == 0:  # stored
        decompressed = raw_bytes
    else:
        pytest.fail(f"Unexpected compression method: {result.compression_method}")

    data = json.loads(decompressed)
    assert "messages" in data
    assert "events" in data


@pytest.mark.asyncio
async def test_read_messages_events_cleans_up_via_aclose() -> None:
    """Resources are cleaned up via aclose() even if context manager is never entered.

    This tests the scenario where read_messages_events() returns successfully,
    but caller needs to clean up without entering `async with result.data`.
    For example, if a size check raises an exception after read_messages_events()
    returns but before the context manager is entered.
    """
    eval_path = (
        TEST_EVAL_LOGS_DIR
        / "2025-11-07T10-59-47-05-00_websearch-addition-problem_LqPDntDnkk4h2fSqQ8i6CE.eval"
    )

    # Track whether AsyncFilesystem.close() was called
    close_called = False

    async with EvalLogTranscriptsView(str(eval_path)) as view:
        info = await _get_first_transcript_info(view)
        result = await view.read_messages_events(info)

        # Wrap the close method to track calls
        original_close = result.data._fs.close

        async def tracking_close() -> None:
            nonlocal close_called
            close_called = True
            await original_close()

        result.data._fs.close = tracking_close

    # At this point:
    # - view has been closed (exited async with)
    # - result.data context manager was NEVER entered
    # - Call aclose() to clean up resources

    await result.data.aclose()

    assert close_called, (
        "AsyncFilesystem.close() was not called. "
        "aclose() should clean up resources when context manager is never entered."
    )
