"""Chat API endpoint."""

from fastapi import APIRouter

from ._api_v2_types import ChatRequest


def create_chat_router() -> APIRouter:
    """Create chat API router.

    Returns:
        Configured APIRouter with chat endpoint.
    """
    router = APIRouter(tags=["chat"])

    @router.post("/chat", summary="Send chat messages for a transcript")
    async def chat(request: ChatRequest) -> None:
        """Receive chat messages associated with a transcript."""
        print(
            f"Chat for {request.transcript_dir}/{request.transcript_id}: "
            f"{len(request.messages)} messages"
        )
        for message in request.messages:
            print(f"  [{message.role}]: {message.text}")

    return router
