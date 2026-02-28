"""Transcripts REST API endpoints."""

from collections.abc import AsyncIterator
from typing import Any, Literal

from fastapi import APIRouter, Header, HTTPException, Path
from fastapi.responses import StreamingResponse
from inspect_ai._util.compression_transcoding import CompressedToDeflateStream
from inspect_ai._util.zip_common import ZipCompressionMethod
from starlette.status import (
    HTTP_404_NOT_FOUND,
    HTTP_413_CONTENT_TOO_LARGE,
)

from .._project._project import read_project
from .._query import Column, Query, ScalarValue
from .._query.condition import Condition as ConditionType
from .._query.condition_sql import condition_from_sql
from .._query.order_by import OrderBy
from .._transcript.database.factory import transcripts_view
from .._transcript.types import TranscriptInfo
from ._api_v2_types import (
    DistinctRequest,
    MessagesEventsResponse,
    StreamMetadata,
    TranscriptsRequest,
    TranscriptsResponse,
)
from ._pagination_helpers import build_pagination_context
from ._server_common import InspectPydanticJSONResponse, decode_base64url

# Supported compression algorithms for X-Accept-Raw-Encoding header
RawEncoding = Literal["zstd"]

MAX_TRANSCRIPT_BYTES = 350 * 1024 * 1024  # 350MB


def create_transcripts_router() -> APIRouter:
    """Create transcripts API router.

    Returns:
        Configured APIRouter with transcripts endpoints.
    """
    router = APIRouter(tags=["transcripts"])

    @router.post(
        "/transcripts/{dir}",
        summary="List transcripts",
        description="Returns transcripts from specified directory. "
        "Optional filter condition uses SQL-like DSL. Optional order_by for sorting results. "
        "Optional pagination for cursor-based pagination.",
    )
    async def transcripts(
        dir: str = Path(description="Transcripts directory (base64url-encoded)"),
        body: TranscriptsRequest | None = None,
    ) -> TranscriptsResponse:
        """Filter transcript metadata from the transcripts directory."""
        transcripts_dir = decode_base64url(dir)

        try:
            ctx = build_pagination_context(
                body, "transcript_id", _get_project_filters()
            )

            async with transcripts_view(transcripts_dir) as view:
                count = await view.count(Query(where=ctx.filter_conditions or []))
                results = [
                    t
                    async for t in view.select(
                        Query(
                            where=ctx.conditions or [],
                            limit=ctx.limit,
                            order_by=ctx.db_order_columns or [],
                        )
                    )
                ]

            if ctx.needs_reverse:
                results = list(reversed(results))

            next_cursor = None
            if (
                body
                and body.pagination
                and len(results) == body.pagination.limit
                and results
            ):
                edge = (
                    results[-1]
                    if body.pagination.direction == "forward"
                    else results[0]
                )
                next_cursor = _build_transcripts_cursor(edge, ctx.order_columns)

            return TranscriptsResponse(
                items=results, total_count=count, next_cursor=next_cursor
            )
        except FileNotFoundError:
            return TranscriptsResponse(items=[], total_count=0, next_cursor=None)

    @router.head(
        "/transcripts/{dir}/{id}/info",
        summary="Check transcript existence",
        description="Checks if a transcript exists.",
    )
    @router.get(
        "/transcripts/{dir}/{id}/info",
        response_model=TranscriptInfo,
        response_class=InspectPydanticJSONResponse,
        summary="Get transcript info",
        description="Returns transcript metadata without messages or events.",
    )
    async def transcript_info(
        dir: str = Path(description="Transcripts directory (base64url-encoded)"),
        id: str = Path(description="Transcript ID"),
    ) -> TranscriptInfo:
        """Get transcript info (metadata only) by ID."""
        transcripts_dir = decode_base64url(dir)

        async with transcripts_view(transcripts_dir) as view:
            condition = Column("transcript_id") == id
            infos = [info async for info in view.select(Query(where=[condition]))]
            if not infos:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND, detail="Transcript not found"
                )
            return infos[0]

    @router.get(
        "/transcripts/{dir}/{id}/messages-events",
        response_model=MessagesEventsResponse,
        summary="Get transcript messages and events",
        description="Returns JSON bytes for transcript messages and events. "
        "May be compressed (check Content-Encoding or X-Content-Encoding headers). "
        "JSON may contain a top-level 'attachments' dict; strings within 'messages' "
        "and 'events' may contain 'attachment://<32-char-hex-id>' refs that must be "
        "resolved client-side by looking up the ID in the 'attachments' dict. "
        "Use X-Accept-Raw-Encoding header to bypass server transcoding and receive "
        "bytes in the source compression format (e.g., zstd); client must decompress.",
        responses={
            200: {
                "content": {
                    "application/octet-stream": {
                        "description": "Raw compressed bytes when X-Accept-Raw-Encoding "
                        "header matches the source compression (e.g., zstd). "
                        "Check X-Content-Encoding header for the compression format.",
                    },
                },
            }
        },
    )
    async def transcript_messages_and_events(
        dir: str = Path(description="Transcripts directory (base64url-encoded)"),
        id: str = Path(description="Transcript ID"),
        x_accept_raw_encoding: RawEncoding | None = Header(  # noqa: B008
            default=None,
            description="Comma-separated list of compression algorithms the client "
            "application can decompress in code (e.g., 'zstd'). Use this for algorithms "
            "browsers don't natively support. If the source uses a listed algorithm, "
            "raw compressed bytes are returned with X-Content-Encoding header (not "
            "Content-Encoding, so the browser won't attempt decompression). Otherwise, "
            "server transcodes to deflate for automatic browser decompression.",
        ),
    ) -> StreamingResponse:
        transcripts_dir = decode_base64url(dir)

        # Parse accepted raw encodings from header
        accepted_raw_encodings: set[str] = set()
        if x_accept_raw_encoding:
            accepted_raw_encodings = {
                enc.strip().lower() for enc in x_accept_raw_encoding.split(",")
            }

        stream = _stream_messages_events(
            transcripts_dir, id, accepted_raw_encodings=accepted_raw_encodings
        )
        metadata = await anext(stream)
        assert isinstance(metadata, StreamMetadata)

        async def bytes_only() -> AsyncIterator[bytes]:
            async for chunk in stream:
                assert isinstance(chunk, bytes)
                yield chunk

        # Map compression method to HTTP encoding name
        compression_to_encoding: dict[ZipCompressionMethod, str | None] = {
            ZipCompressionMethod.STORED: None,
            ZipCompressionMethod.DEFLATE: "deflate",
            ZipCompressionMethod.ZSTD: "zstd",
        }
        encoding_name = compression_to_encoding.get(
            metadata.compression_method or ZipCompressionMethod.STORED
        )

        # Determine response based on compression method
        if encoding_name and encoding_name in accepted_raw_encodings:
            # Client accepts this raw encoding - send with X-Content-Encoding
            # Use octet-stream since this is raw compressed bytes the client must decode
            return StreamingResponse(
                content=bytes_only(),
                media_type="application/octet-stream",
                headers={"X-Content-Encoding": encoding_name},
            )
        elif metadata.compression_method == ZipCompressionMethod.DEFLATE:
            # Deflate: use standard Content-Encoding (browser decompresses).
            # Note: HTTP/1.1 defines 'deflate' as zlib-wrapped (RFC 1950), but ZIP
            # files use raw DEFLATE (RFC 1951). We send raw DEFLATE anyway because
            # all browsers sniff the format and accept it. See:
            # https://en.wikipedia.org/wiki/HTTP_compression#Problems_preventing_the_use_of_HTTP_compression
            return StreamingResponse(
                content=bytes_only(),
                media_type="application/json",
                headers={"Content-Encoding": "deflate"},
            )
        else:
            # Uncompressed (stored) - no Content-Encoding header needed
            return StreamingResponse(
                content=bytes_only(),
                media_type="application/json",
            )

    @router.post(
        "/transcripts/{dir}/distinct",
        summary="Get distinct column values",
        description="Returns distinct values for a column, optionally filtered.",
    )
    async def transcripts_distinct(
        dir: str = Path(description="Transcripts directory (base64url-encoded)"),
        body: DistinctRequest | None = None,
    ) -> list[ScalarValue]:
        """Get distinct values for a column."""
        transcripts_dir = decode_base64url(dir)
        if body is None:
            return []
        async with transcripts_view(transcripts_dir) as view:
            return await view.distinct(body.column, body.filter)

    return router


def _build_transcripts_cursor(
    transcript: TranscriptInfo,
    order_columns: list[OrderBy],
) -> dict[str, Any]:
    """Build cursor from transcript using sort columns."""
    return {ob.column: getattr(transcript, ob.column, None) for ob in order_columns}


def _get_project_filters() -> list[ConditionType]:
    """Get filter conditions from project configuration."""
    project = read_project()
    return [
        condition_from_sql(f)
        for f in (
            project.filter if isinstance(project.filter, list) else [project.filter]
        )
        if f
    ]


async def _stream_messages_events(
    transcripts_dir: str,
    transcript_id: str,
    *,
    accepted_raw_encodings: set[str] | None = None,
) -> AsyncIterator[StreamMetadata | bytes]:
    """Stream transcript messages/events with metadata-first protocol.

    First yield: StreamMetadata with compression info
    Subsequent yields: raw bytes chunks

    All resources are owned by the generator and cleaned up when
    Starlette calls aclose().

    Transcoding logic (HTTP concern, handled here not in data layer):
    - If source is zstd and client doesn't accept zstd: transcode to deflate
    - Otherwise: pass through raw bytes

    Args:
        transcripts_dir: Directory containing transcripts
        transcript_id: ID of transcript to stream
        accepted_raw_encodings: Set of encoding names (e.g., {"zstd"}) that
            the client can decompress. If source uses one of these, raw bytes
            are returned. Otherwise, transcodes to deflate for browser compat.
    """
    async with transcripts_view(transcripts_dir) as view:
        condition = Column("transcript_id") == transcript_id
        infos = [info async for info in view.select(Query(where=[condition]))]
        if not infos:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail="Transcript not found"
            )

        result = await view.read_messages_events(infos[0])

        # Determine if we need to transcode
        needs_transcode = result.compression_method == ZipCompressionMethod.ZSTD and (
            not accepted_raw_encodings or "zstd" not in accepted_raw_encodings
        )

        # Wrap with transcoder if needed (create new object, don't mutate)
        if needs_transcode:
            result = type(result)(
                data=CompressedToDeflateStream(
                    result.data, source_compression=ZipCompressionMethod.ZSTD
                ),
                compression_method=ZipCompressionMethod.DEFLATE,
                uncompressed_size=result.uncompressed_size,
            )

        if (
            result.uncompressed_size is not None
            and result.uncompressed_size > MAX_TRANSCRIPT_BYTES
        ):
            raise HTTPException(
                status_code=HTTP_413_CONTENT_TOO_LARGE,
                detail=f"Transcript too large: {result.uncompressed_size} bytes "
                f"exceeds {MAX_TRANSCRIPT_BYTES} limit",
            )

        yield StreamMetadata(
            compression_method=result.compression_method,
            uncompressed_size=result.uncompressed_size,
        )

        # async with handles cleanup via __aexit__
        async with result.data as data:
            async for chunk in data:
                yield chunk
