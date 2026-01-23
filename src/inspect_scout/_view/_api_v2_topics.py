"""Topics REST API endpoints for cache invalidation."""

from collections.abc import AsyncGenerator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from .invalidationTopics import get_condition, topic_versions_json


def create_topics_router() -> APIRouter:
    """Create topics API router.

    Returns:
        Configured APIRouter with topics endpoints.
    """
    router = APIRouter(tags=["topics"])

    @router.get(
        "/topics/stream",
        summary="Stream topic updates",
        description="SSE endpoint that pushes topic versions when they change. "
        "Each message is a JSON dict mapping topic names to timestamps.",
    )
    async def topics_stream() -> EventSourceResponse:
        """Stream topic version updates via SSE."""

        async def event_generator() -> AsyncGenerator[dict[str, str], None]:
            yield {"data": topic_versions_json()}
            condition = get_condition()
            while True:
                async with condition:
                    await condition.wait()
                yield {"data": topic_versions_json()}

        return EventSourceResponse(event_generator())

    return router
