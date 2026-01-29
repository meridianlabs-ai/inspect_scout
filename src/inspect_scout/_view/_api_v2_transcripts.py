"""Transcripts REST API endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import StreamingResponse
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
from .._transcript.types import (
    Transcript,
    TranscriptContent,
    TranscriptInfo,
    TranscriptTooLargeError,
)
from ._api_v2_types import (
    DistinctRequest,
    TranscriptsRequest,
    TranscriptsResponse,
)
from ._pagination_helpers import build_pagination_context
from ._server_common import InspectPydanticJSONResponse, decode_base64url

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
        "/transcripts/{dir}/{id}",
        summary="Check transcript existence",
        description="Checks if a transcript exists.",
    )
    @router.get(
        "/transcripts/{dir}/{id}",
        response_model=Transcript,
        response_class=InspectPydanticJSONResponse,
        summary="Get transcript",
        description="Returns a single transcript with full content (messages and events).",
    )
    async def transcript(
        dir: str = Path(description="Transcripts directory (base64url-encoded)"),
        id: str = Path(description="Transcript ID"),
    ) -> Transcript:
        """Get a single transcript by ID."""
        transcripts_dir = decode_base64url(dir)

        async with transcripts_view(transcripts_dir) as view:
            condition = Column("transcript_id") == id
            infos = [info async for info in view.select(Query(where=[condition]))]
            if not infos:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND, detail="Transcript not found"
                )

            content = TranscriptContent(messages="all", events="all")
            try:
                return await view.read(
                    infos[0], content, max_bytes=MAX_TRANSCRIPT_BYTES
                )
            except TranscriptTooLargeError as e:
                raise HTTPException(
                    status_code=HTTP_413_CONTENT_TOO_LARGE,
                    detail=f"Transcript too large: {e.size} bytes exceeds {e.max_size} limit",
                ) from None

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
        summary="Get transcript messages and events (raw)",
        description="Returns raw JSON bytes for transcript messages and events. "
        "May be DEFLATE-compressed (check Content-Encoding header). "
        "JSON may contain 'attachments' dict; strings with 'attachment://<id>' refs "
        "must be resolved client-side.",
    )
    async def transcript_messages_and_events(
        dir: str = Path(description="Transcripts directory (base64url-encoded)"),
        id: str = Path(description="Transcript ID"),
    ) -> StreamingResponse:
        """Stream raw transcript messages/events JSON.

        Returns the raw JSON bytes from the underlying storage, potentially
        DEFLATE-compressed. When compressed, the Content-Encoding header is set
        to 'deflate' so browsers auto-decompress.

        NOTE ON ATTACHMENTS: The JSON may contain an 'attachments' dict at the
        top level. Strings within 'messages' and 'events' may contain references
        like 'attachment://<32-char-hex-id>' that must be resolved client-side
        by looking up the ID in the 'attachments' dict.

        NOTE ON CONTENT-ENCODING: HTTP/1.1 defines 'deflate' as zlib-wrapped
        (RFC 1950), but ZIP files use raw DEFLATE (RFC 1951). We send raw
        DEFLATE with Content-Encoding: deflate anyway because:
        1. All browsers accept raw DEFLATE (they sniff the format)
        2. IE only accepts raw DEFLATE (not zlib-wrapped)
        3. This matches what most servers historically sent
        See: https://en.wikipedia.org/wiki/HTTP_compression#Problems_preventing_the_use_of_HTTP_compression
        """
        transcripts_dir = decode_base64url(dir)

        async with transcripts_view(transcripts_dir) as view:
            condition = Column("transcript_id") == id
            infos = [info async for info in view.select(Query(where=[condition]))]
            if not infos:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND, detail="Transcript not found"
                )

            result = await view.read_messages_events(infos[0])

            headers: dict[str, str] = {}
            # ZIP compression method 8 = DEFLATE
            if result.compression_method == 8:
                headers["Content-Encoding"] = "deflate"

            return StreamingResponse(
                content=result.data,
                media_type="application/json",
                headers=headers or None,
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


# --- Private helpers ---


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
