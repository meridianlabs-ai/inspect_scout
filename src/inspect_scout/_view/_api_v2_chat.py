"""Chat API endpoint."""

import os

from fastapi import APIRouter, HTTPException
from inspect_ai.model import ChatMessageAssistant, ChatMessageSystem, get_model

from .._query import Column, Query
from .._scanner.extract import messages_as_str
from .._transcript.database.factory import transcripts_view
from .._transcript.types import TranscriptContent
from ._api_v2_types import ChatRequest

CHAT_SYSTEM_PROMPT = """\
You are a helpful assistant for analyzing LLM transcripts. \
The user wants to discuss the following transcript. Answer their questions about it.

[BEGIN TRANSCRIPT]
===================================
{transcript}
===================================
[END TRANSCRIPT]

When referring to specific messages, use the message IDs (e.g. '[M1]', '[M2]') \
shown in the transcript."""


def create_chat_router() -> APIRouter:
    """Create chat API router.

    Returns:
        Configured APIRouter with chat endpoint.
    """
    router = APIRouter(tags=["chat"])

    @router.post("/chat", summary="Send chat messages for a transcript")
    async def chat(request: ChatRequest) -> ChatMessageAssistant:
        """Send chat messages and receive an LLM response about a transcript."""
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

        # Format transcript messages with [M1], [M2] IDs
        transcript_str, _extract_refs = await messages_as_str(
            transcript, include_ids=True
        )

        # Build message list: system prompt with transcript + user conversation
        system_message = ChatMessageSystem(
            content=CHAT_SYSTEM_PROMPT.format(transcript=transcript_str)
        )
        llm_messages = [system_message, *request.messages]

        # Call the model
        # TODO: should this be a default? client should at least be able to override
        model_name = os.getenv("SCOUT_SCAN_MODEL")
        model = get_model(model_name)
        try:
            output = await model.generate(input=llm_messages)
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e)) from e

        return output.message

    return router
