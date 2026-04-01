"""Search API endpoint."""

import os

from fastapi import APIRouter, HTTPException

from .._grep_scanner._grep_scanner import _scan_single
from .._llm_scanner._llm_scanner import llm_scanner
from .._query import Column, Query
from .._transcript.database.factory import transcripts_view
from .._transcript.types import TranscriptContent
from ._api_v2_types import SearchRequest, SearchResponse


def create_search_router() -> APIRouter:
    """Create search API router.

    Returns:
        Configured APIRouter with search endpoint.
    """
    router = APIRouter(tags=["search"])

    @router.post("/search", summary="Search a transcript")
    async def search(request: SearchRequest) -> SearchResponse:
        """Search a transcript using grep or LLM-based search."""
        # Load transcript
        async with transcripts_view(request.transcript_dir) as view:
            condition = Column("transcript_id") == request.transcript_id
            infos = [info async for info in view.select(Query(where=[condition]))]
            if not infos:
                raise HTTPException(
                    status_code=404, detail="Transcript not found"
                )
            transcript = await view.read(
                infos[0], TranscriptContent(messages="all")
            )

        if request.type == "grep":
            result = _scan_single(
                transcript,
                request.query,
                regex=False,
                ignore_case=True,
                word_boundary=False,
            )
            results = [result]
        else:
            # LLM search
            model_name = os.getenv("SCOUT_SCAN_MODEL")
            scan = llm_scanner(
                question=request.query,
                answer="string",
                model=model_name,
            )
            # TODO: force this to throw and see what happens
            output = await scan(transcript)

            if isinstance(output, list):
                results = output
            else:
                results = [output]

        return SearchResponse(results=results)

    return router
