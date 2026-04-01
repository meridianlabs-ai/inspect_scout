"""Search API endpoint."""

import os

from fastapi import APIRouter, HTTPException

from .._grep_scanner._grep_scanner import _scan_single
from .._llm_scanner._llm_scanner import llm_scanner
from .._query import Column, Query
from .._transcript.database.factory import transcripts_view
from .._transcript.types import TranscriptContent
from ._api_v2_types import SearchRequest, SearchResponse

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


def create_search_router() -> APIRouter:
    """Create search API router.

    Returns:
        Configured APIRouter with search endpoint.
    """
    router = APIRouter(tags=["search"])

    @router.post("/search", summary="Search a transcript")
    async def search(request: SearchRequest) -> SearchResponse:
        """Search a transcript using grep or LLM-based search."""

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
            model_name = os.getenv("SCOUT_SCAN_MODEL")
            scan = llm_scanner(
                question=request.query,
                answer="string",
                template=LLM_SEARCH_TEMPLATE,
                model=model_name,
            )
            # TODO: force this to throw and see what FastAPI does
            output = await scan(transcript)

            if isinstance(output, list):
                results = output
            else:
                results = [output]

        return SearchResponse(results=results)

    return router
