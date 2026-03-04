"""Tests for /transcripts/{dir}/{id}/messages-events endpoint."""

import zlib
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from inspect_ai._util.zip_common import ZipCompressionMethod
from inspect_scout._transcript.types import TranscriptInfo, TranscriptMessagesAndEvents
from inspect_scout._view._api_v2 import v2_api_app


def _deflate_compress(data: bytes) -> bytes:
    """Compress data using raw DEFLATE (no zlib header)."""
    compressor = zlib.compressobj(level=6, wbits=-15)
    return compressor.compress(data) + compressor.flush()


def _base64url(s: str) -> str:
    """Encode string as base64url (URL-safe base64 without padding)."""
    import base64

    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


@dataclass
class MockBytesContextManager:
    """Mock async context manager that yields byte chunks."""

    data: bytes

    async def __aenter__(self) -> AsyncIterator[bytes]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[bytes]:
        yield self.data

    async def __aexit__(self, *_: object) -> None:
        pass

    async def aclose(self) -> None:
        pass


def _create_transcript_info(transcript_id: str = "t001") -> TranscriptInfo:
    """Create a test TranscriptInfo."""
    return TranscriptInfo(
        transcript_id=transcript_id,
        source_type="test",
        source_id="test-source",
        source_uri="test://uri",
    )


def _create_mock_view(
    *,
    transcript_info: TranscriptInfo | None = None,
    messages_events: TranscriptMessagesAndEvents | None = None,
) -> MagicMock:
    """Create a mock TranscriptsView for testing."""
    mock_view = AsyncMock()

    # Setup select to return transcript info
    async def mock_select(query: Any) -> Any:
        if transcript_info:
            yield transcript_info

    mock_view.select = mock_select
    mock_view.read_messages_events = AsyncMock(return_value=messages_events)

    return mock_view


class TestTranscriptMessagesEventsContentType:
    """Tests for Content-Type header in messages-events endpoint."""

    def test_raw_zstd_returns_octet_stream_content_type(self) -> None:
        """When client accepts raw zstd, response should be application/octet-stream."""
        transcript_info = _create_transcript_info()
        zstd_data = b"zstd compressed data"

        messages_events = TranscriptMessagesAndEvents(
            data=MockBytesContextManager(zstd_data),
            compression_method=ZipCompressionMethod.ZSTD,
            uncompressed_size=100,
        )

        mock_view = _create_mock_view(
            transcript_info=transcript_info,
            messages_events=messages_events,
        )

        client = TestClient(v2_api_app())

        with patch(
            "inspect_scout._view._api_v2_transcripts.transcripts_view",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_view)),
        ):
            response = client.get(
                f"/transcripts/{_base64url('/tmp')}/{transcript_info.transcript_id}"
                "/messages-events",
                headers={"X-Accept-Raw-Encoding": "zstd"},
            )

        assert response.status_code == 200
        # Raw compressed bytes should use application/octet-stream, not application/json
        assert response.headers["content-type"] == "application/octet-stream"
        assert response.headers["x-content-encoding"] == "zstd"

    def test_deflate_transcoded_returns_json_content_type(self) -> None:
        """When deflate is used with Content-Encoding, response should be application/json."""
        transcript_info = _create_transcript_info()
        json_data = b'{"messages": [], "events": []}'
        deflate_data = _deflate_compress(json_data)

        messages_events = TranscriptMessagesAndEvents(
            data=MockBytesContextManager(deflate_data),
            compression_method=ZipCompressionMethod.DEFLATE,
            uncompressed_size=len(json_data),
        )

        mock_view = _create_mock_view(
            transcript_info=transcript_info,
            messages_events=messages_events,
        )

        client = TestClient(v2_api_app())

        with patch(
            "inspect_scout._view._api_v2_transcripts.transcripts_view",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_view)),
        ):
            response = client.get(
                f"/transcripts/{_base64url('/tmp')}/{transcript_info.transcript_id}"
                "/messages-events",
            )

        assert response.status_code == 200
        # Deflate with Content-Encoding should use application/json
        # (browser will auto-decompress and see JSON)
        assert response.headers["content-type"] == "application/json"
        assert response.headers["content-encoding"] == "deflate"
        assert "x-content-encoding" not in response.headers

    def test_uncompressed_returns_json_content_type(self) -> None:
        """When uncompressed (STORED), response should be application/json."""
        transcript_info = _create_transcript_info()
        json_data = b'{"messages": [], "events": []}'

        messages_events = TranscriptMessagesAndEvents(
            data=MockBytesContextManager(json_data),
            compression_method=ZipCompressionMethod.STORED,
            uncompressed_size=len(json_data),
        )

        mock_view = _create_mock_view(
            transcript_info=transcript_info,
            messages_events=messages_events,
        )

        client = TestClient(v2_api_app())

        with patch(
            "inspect_scout._view._api_v2_transcripts.transcripts_view",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_view)),
        ):
            response = client.get(
                f"/transcripts/{_base64url('/tmp')}/{transcript_info.transcript_id}"
                "/messages-events",
            )

        assert response.status_code == 200
        # Uncompressed JSON should use application/json
        assert response.headers["content-type"] == "application/json"
        assert "content-encoding" not in response.headers
        assert "x-content-encoding" not in response.headers


class TestZstdTranscodingToDeflate:
    """Tests for zstd → deflate transcoding when client doesn't accept raw zstd."""

    def test_zstd_without_accept_header_returns_json_with_deflate(self) -> None:
        """When source is zstd but no X-Accept-Raw-Encoding header, transcode to deflate."""
        import zstandard

        transcript_info = _create_transcript_info()
        json_data = b'{"messages": [], "events": []}'
        zstd_data = zstandard.ZstdCompressor().compress(json_data)

        messages_events = TranscriptMessagesAndEvents(
            data=MockBytesContextManager(zstd_data),
            compression_method=ZipCompressionMethod.ZSTD,
            uncompressed_size=len(json_data),
        )

        mock_view = _create_mock_view(
            transcript_info=transcript_info,
            messages_events=messages_events,
        )

        client = TestClient(v2_api_app())

        with patch(
            "inspect_scout._view._api_v2_transcripts.transcripts_view",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_view)),
        ):
            response = client.get(
                f"/transcripts/{_base64url('/tmp')}/{transcript_info.transcript_id}"
                "/messages-events",
                # No X-Accept-Raw-Encoding header
            )

        assert response.status_code == 200
        # Should transcode to deflate and use application/json
        assert response.headers["content-type"] == "application/json"
        assert response.headers["content-encoding"] == "deflate"
        assert "x-content-encoding" not in response.headers
        # Verify the response body is valid JSON (browser would auto-decompress)
        assert response.json() == {"messages": [], "events": []}

    def test_invalid_accept_encoding_header_rejected(self) -> None:
        """When X-Accept-Raw-Encoding has invalid value, request is rejected."""
        transcript_info = _create_transcript_info()

        client = TestClient(v2_api_app())

        # Note: No need to mock the view since validation happens before the handler
        response = client.get(
            f"/transcripts/{_base64url('/tmp')}/{transcript_info.transcript_id}"
            "/messages-events",
            # Invalid value - only "zstd" is accepted
            headers={"X-Accept-Raw-Encoding": "br"},
        )

        # FastAPI validates the Literal type and rejects invalid values
        assert response.status_code == 422
