"""Topics REST API endpoints for cache invalidation."""

from collections.abc import AsyncGenerator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from .invalidationTopics import (
    InvalidationTopic,
    get_condition,
    get_topic_versions,
    topic_versions_json,
)


def create_topics_router() -> APIRouter:
    """Create topics API router.

    Returns:
        Configured APIRouter with topics endpoints.
    """
    router = APIRouter(tags=["topics"])

    @router.get(
        "/topics",
        summary="Get current topic versions",
        description="Returns current topic versions dict for polling clients.",
    )
    async def get_topics() -> dict[InvalidationTopic, str]:
        """Return current topic versions."""
        return get_topic_versions()

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
