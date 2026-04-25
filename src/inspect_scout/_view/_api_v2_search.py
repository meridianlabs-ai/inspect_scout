"""Search API endpoint."""

import hashlib
import json
from collections.abc import Sequence
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import Response
from inspect_ai._util.kvstore import KVStore
from pydantic import TypeAdapter

from .._grep_scanner._grep_scanner import grep_scanner
from .._llm_scanner import ResultReducer
from .._llm_scanner._llm_scanner import llm_scanner
from .._query import Column, Query
from .._transcript.database.factory import transcripts_view
from .._transcript.types import TranscriptContent
from .._util.appdirs import scout_data_dir
from ._api_v2_types import (
    GrepSavedSearch,
    GrepSearchRequest,
    LlmSavedSearch,
    SavedSearch,
    SavedSearchListResponse,
    SearchRequest,
)
from ._server_common import decode_base64url

LLM_SEARCH_TEMPLATE = """\
You are a search assistant for LLM transcript analysis. A user is searching \
through a transcript and wants to find relevant information.

[BEGIN TRANSCRIPT]
===================================
{{ messages }}
===================================
[END TRANSCRIPT]

The user's search query is:
{{ question }}

Find the parts of the transcript most relevant to the query. \
Cite specific messages using their IDs (e.g. '[M1]', '[M5]'). \
Be concise — write short paragraphs, not essays. \
If nothing in the transcript matches the query, say so briefly.

{{ answer_format }}
"""

MAX_ENTRIES = 500
SAVED_SEARCH_ADAPTER: TypeAdapter[SavedSearch] = TypeAdapter(SavedSearch)


def _normalize_filter(
    value: str | None | Sequence[object],
) -> str | None | Sequence[str]:
    """Normalize a message/event filter for stable hashing."""
    if value is None or isinstance(value, str):
        return value
    # Sequence of types — sort for stability
    return sorted(str(item) for item in value)


def _search_id(request: SearchRequest) -> str:
    """Deterministic ID from search parameters."""
    parts: dict[str, object] = {
        "query": request.query,
        "type": request.type,
        "messages": _normalize_filter(request.messages),
        "events": _normalize_filter(request.events),
    }
    if isinstance(request, GrepSearchRequest):
        parts["regex"] = request.regex
        parts["ignore_case"] = request.ignore_case
        parts["word_boundary"] = request.word_boundary
    elif request.model is not None:
        parts["model"] = request.model
    canonical = json.dumps(parts, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]


def _dir_hash(transcript_dir: str) -> str:
    """Short hash of the transcript directory path."""
    return hashlib.sha256(transcript_dir.encode()).hexdigest()[:12]


def _transcript_prefix(transcript_dir: str, transcript_id: str) -> str:
    """Composite key prefix for all searches within a transcript."""
    return f"{_dir_hash(transcript_dir)}:{transcript_id}:"


def _composite_key(transcript_dir: str, transcript_id: str, search_id: str) -> str:
    """Full composite key for a single search."""
    return f"{_transcript_prefix(transcript_dir, transcript_id)}{search_id}"


def _search_store() -> KVStore:
    """Open the single search KVStore."""
    db_path = scout_data_dir("search") / "searches.db"
    return KVStore(db_path.as_posix(), max_entries=MAX_ENTRIES)


def create_search_router() -> APIRouter:
    """Create search API router.

    Returns:
        Configured APIRouter with search endpoints.
    """
    router = APIRouter(tags=["search"])

    @router.post(
        "/transcripts/{dir}/{id}/search",
        summary="Search a transcript",
    )
    async def search(
        request: SearchRequest,
        dir: str = Path(description="Transcripts directory (base64url-encoded)"),
        id: str = Path(description="Transcript ID"),
    ) -> SavedSearch:
        """Search a transcript using grep or LLM-based search.

        Returns cached results if the same search was run before.
        """
        transcript_dir = decode_base64url(dir)
        sid = _search_id(request)
        key = _composite_key(transcript_dir, id, sid)

        # Check cache
        with _search_store() as store:
            cached = store.get(key)
        if cached:
            return SAVED_SEARCH_ADAPTER.validate_json(cached)

        # Load transcript
        async with transcripts_view(transcript_dir) as view:
            condition = Column("transcript_id") == id
            infos = [info async for info in view.select(Query(where=[condition]))]
            if not infos:
                raise HTTPException(status_code=404, detail="Transcript not found")
            transcript = await view.read(
                infos[0],
                TranscriptContent(
                    messages=request.messages,
                    events=request.events,
                ),
            )

        # Run search
        if isinstance(request, GrepSearchRequest):
            output = await grep_scanner(
                request.query,
                regex=request.regex,
                ignore_case=request.ignore_case,
                word_boundary=request.word_boundary,
            )(transcript)
        else:
            try:
                output = await llm_scanner(
                    question=request.query,
                    answer="string",
                    template=LLM_SEARCH_TEMPLATE,
                    model=request.model,
                    reducer=ResultReducer.llm(model=request.model),
                )(transcript)
            except Exception as err:
                raise HTTPException(
                    status_code=502,
                    detail=str(err),
                ) from err

        if isinstance(output, list):
            raise RuntimeError(
                "Single-transcript search returned multiple results unexpectedly"
            )

        created_at = datetime.now(timezone.utc).isoformat()
        if isinstance(request, GrepSearchRequest):
            saved: SavedSearch = GrepSavedSearch(
                search_id=sid,
                query=request.query,
                regex=request.regex,
                ignore_case=request.ignore_case,
                word_boundary=request.word_boundary,
                result=output,
                created_at=created_at,
            )
        else:
            saved = LlmSavedSearch(
                search_id=sid,
                query=request.query,
                model=request.model,
                result=output,
                created_at=created_at,
            )

        with _search_store() as store:
            store.put(key, saved.model_dump_json())

        return saved

    @router.get(
        "/transcripts/{dir}/{id}/searches",
        summary="List saved searches for a transcript",
    )
    async def list_searches(
        dir: str = Path(description="Transcripts directory (base64url-encoded)"),
        id: str = Path(description="Transcript ID"),
    ) -> SavedSearchListResponse:
        """List all saved searches for a transcript, newest first."""
        transcript_dir = decode_base64url(dir)
        prefix = _transcript_prefix(transcript_dir, id)

        with _search_store() as store:
            rows = store.list_by_prefix(prefix)

        items = [SAVED_SEARCH_ADAPTER.validate_json(value) for _, value in rows]
        return SavedSearchListResponse(items=items)

    @router.get(
        "/transcripts/{dir}/{id}/searches/{search_id}",
        summary="Get a saved search",
    )
    async def get_search(
        dir: str = Path(description="Transcripts directory (base64url-encoded)"),
        id: str = Path(description="Transcript ID"),
        search_id: str = Path(description="Search ID"),
    ) -> SavedSearch:
        """Get a single saved search by ID."""
        transcript_dir = decode_base64url(dir)
        key = _composite_key(transcript_dir, id, search_id)

        with _search_store() as store:
            value = store.get(key)

        if value is None:
            raise HTTPException(status_code=404, detail="Search not found")
        return SAVED_SEARCH_ADAPTER.validate_json(value)

    @router.delete(
        "/transcripts/{dir}/{id}/searches/{search_id}",
        summary="Delete a saved search",
        status_code=204,
    )
    async def delete_search(
        dir: str = Path(description="Transcripts directory (base64url-encoded)"),
        id: str = Path(description="Transcript ID"),
        search_id: str = Path(description="Search ID"),
    ) -> Response:
        """Delete a saved search by ID."""
        transcript_dir = decode_base64url(dir)
        key = _composite_key(transcript_dir, id, search_id)

        with _search_store() as store:
            deleted = store.delete(key)

        if not deleted:
            raise HTTPException(status_code=404, detail="Search not found")
        return Response(status_code=204)

    return router
