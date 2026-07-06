"""OpenClaw native session transcript import functionality."""

from __future__ import annotations

from datetime import datetime
from os import PathLike
from typing import TYPE_CHECKING, AsyncIterator

if TYPE_CHECKING:
    from inspect_scout import Transcript


async def openclaw(
    path: str | PathLike[str] | None = None,
    session_id: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    limit: int | None = None,
) -> AsyncIterator["Transcript"]:
    """Read transcripts from native OpenClaw session files."""
    raise NotImplementedError
    yield  # pragma: no cover — marks this as an async generator
