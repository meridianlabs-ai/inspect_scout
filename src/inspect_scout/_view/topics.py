"""Topic-based cache invalidation via pub/sub."""

import json
from datetime import datetime, timezone
from typing import Literal, TypeAlias

import anyio

Topic: TypeAlias = Literal["project-config"]

_startup_timestamp = datetime.now(timezone.utc).isoformat()
_versions: dict[Topic, str] = {"project-config": _startup_timestamp}
_condition: anyio.Condition | None = None


def get_topic_versions() -> dict[Topic, str]:
    return _versions.copy()


def get_condition() -> anyio.Condition:
    global _condition
    if _condition is None:
        _condition = anyio.Condition()
    return _condition


async def notify_topics(topics: list[Topic]) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    for topic in topics:
        _versions[topic] = timestamp
    async with get_condition():
        get_condition().notify_all()


def topic_versions_json() -> str:
    return json.dumps(_versions)
