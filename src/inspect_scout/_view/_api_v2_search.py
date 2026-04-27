"""Search API endpoint."""

import hashlib
import json
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Path
from fastapi import Query as QueryParam
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
    GrepSavedSearchResult,
    GrepSearchInput,
    GrepSearchRequest,
    LlmSavedSearchResult,
    LlmSearchInput,
    SavedSearchResult,
    SearchInput,
    SearchInputListResponse,
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
SAVED_SEARCH_RESULT_ADAPTER: TypeAdapter[SavedSearchResult] = TypeAdapter(
    SavedSearchResult
)
SEARCH_INPUT_ADAPTER: TypeAdapter[SearchInput] = TypeAdapter(SearchInput)


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
    }
    if isinstance(request, GrepSearchRequest):
        parts["regex"] = request.regex
        parts["ignore_case"] = request.ignore_case
        parts["word_boundary"] = request.word_boundary
    else:
        parts["model"] = request.model
    canonical = json.dumps(parts, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]


def _scope_id(
    messages: str | None | Sequence[object],
    events: str | None | Sequence[object],
) -> str:
    """Deterministic ID from transcript content filters."""
    canonical = json.dumps(
        {
            "messages": _normalize_filter(messages),
            "events": _normalize_filter(events),
        },
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]


def _dir_hash(transcript_dir: str) -> str:
    """Short hash of the transcript directory path."""
    return hashlib.sha256(transcript_dir.encode()).hexdigest()[:12]


def _search_input_key(search_type: Literal["grep", "llm"], search_id: str) -> str:
    """Full key for a global search input."""
    return f"{search_type}:{search_id}"


def _search_input_prefix(search_type: Literal["grep", "llm"]) -> str:
    """Key prefix for search inputs of a given type."""
    return f"{search_type}:"


def _result_key(
    transcript_dir: str,
    transcript_id: str,
    search_id: str,
    *,
    messages: str | None | Sequence[object],
    events: str | None | Sequence[object],
) -> str:
    """Full key for one transcript-specific cached search result."""
    return (
        f"{_dir_hash(transcript_dir)}:{transcript_id}:"
        f"{_scope_id(messages, events)}:{search_id}"
    )


def _search_input_from_request(
    request: SearchRequest,
    *,
    search_id: str,
    created_at: str,
) -> SearchInput:
    """Build the global input-history object for a search request."""
    if isinstance(request, GrepSearchRequest):
        return GrepSearchInput(
            search_id=search_id,
            query=request.query,
            regex=request.regex,
            ignore_case=request.ignore_case,
            word_boundary=request.word_boundary,
            created_at=created_at,
        )
    return LlmSearchInput(
        search_id=search_id,
        query=request.query,
        model=request.model,
        created_at=created_at,
    )


def _save_search_input(search_input: SearchInput) -> None:
    """Persist or refresh one global search input."""
    with _search_input_store() as store:
        store.put(
            _search_input_key(search_input.type, search_input.search_id),
            search_input.model_dump_json(),
        )


def _parse_scope_filter(value: str | None) -> str | None:
    """Parse transcript scope query parameters for cached-result lookups."""
    if value is None or value == "all":
        return value
    return value


def _search_input_store() -> KVStore:
    """Open the global search input-history KVStore."""
    db_path = scout_data_dir("search") / "search_inputs.db"
    return KVStore(db_path.as_posix(), max_entries=MAX_ENTRIES)


def _search_result_store() -> KVStore:
    """Open the transcript-specific search result KVStore."""
    db_path = scout_data_dir("search") / "search_results.db"
    return KVStore(db_path.as_posix(), max_entries=MAX_ENTRIES)


def create_search_router() -> APIRouter:
    """Create search API router.

    Returns:
        Configured APIRouter with search endpoints.
    """
    router = APIRouter(tags=["search"])

    @router.get("/searches", summary="List recent search inputs")
    async def list_search_inputs(
        search_type: Literal["grep", "llm"] = QueryParam(
            alias="type", description="Search input type to list"
        ),
        count: int = QueryParam(
            default=20,
            ge=1,
            le=100,
            description="Maximum number of recent search inputs to return",
        ),
    ) -> SearchInputListResponse:
        """List recent global search inputs, newest first."""
        with _search_input_store() as store:
            rows = store.list_by_prefix(_search_input_prefix(search_type))

        items = [SEARCH_INPUT_ADAPTER.validate_json(value) for _, value in rows[:count]]
        return SearchInputListResponse(items=items)

    @router.post("/transcripts/{dir}/{id}/search", summary="Search a transcript")
    async def search(
        request: SearchRequest,
        dir: str = Path(description="Transcripts directory (base64url-encoded)"),
        id: str = Path(description="Transcript ID"),
    ) -> SavedSearchResult:
        """Search a transcript using grep or LLM-based search.

        Returns cached results if the same search was run before.
        """
        transcript_dir = decode_base64url(dir)
        sid = _search_id(request)
        key = _result_key(
            transcript_dir,
            id,
            sid,
            messages=request.messages,
            events=request.events,
        )

        # Check cache
        with _search_result_store() as store:
            cached = store.get(key)
        if cached:
            _save_search_input(
                _search_input_from_request(
                    request,
                    search_id=sid,
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
            )
            return SAVED_SEARCH_RESULT_ADAPTER.validate_json(cached)

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
        search_input = _search_input_from_request(
            request,
            search_id=sid,
            created_at=created_at,
        )
        if isinstance(request, GrepSearchRequest):
            saved: SavedSearchResult = GrepSavedSearchResult(
                search_id=sid,
                query=request.query,
                regex=request.regex,
                ignore_case=request.ignore_case,
                word_boundary=request.word_boundary,
                result=output,
                created_at=created_at,
            )
        else:
            saved = LlmSavedSearchResult(
                search_id=sid,
                query=request.query,
                model=request.model,
                result=output,
                created_at=created_at,
            )

        _save_search_input(search_input)
        with _search_result_store() as store:
            store.put(key, saved.model_dump_json())

        return saved

    @router.get(
        "/transcripts/{dir}/{id}/searches/{search_id}",
        summary="Get a saved search result",
    )
    async def get_search(
        dir: str = Path(description="Transcripts directory (base64url-encoded)"),
        id: str = Path(description="Transcript ID"),
        search_id: str = Path(description="Search ID"),
        messages: str | None = QueryParam(
            default=None,
            description="Message filter used for the cached search result",
        ),
        events: str | None = QueryParam(
            default=None,
            description="Event filter used for the cached search result",
        ),
    ) -> SavedSearchResult:
        """Get a cached search result by search input ID and transcript scope."""
        transcript_dir = decode_base64url(dir)
        key = _result_key(
            transcript_dir,
            id,
            search_id,
            messages=_parse_scope_filter(messages),
            events=_parse_scope_filter(events),
        )

        with _search_result_store() as store:
            value = store.get(key)

        if value is None:
            raise HTTPException(status_code=404, detail="Search result not found")
        return SAVED_SEARCH_RESULT_ADAPTER.validate_json(value)

    return router
