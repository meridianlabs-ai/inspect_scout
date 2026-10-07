"""Codex rollout event conversion — scout-specific child-thread loading.

Most conversion logic lives in inspect_swe._codex_cli._events.rollout.
This module injects a file-based child-thread loader (spawned agents
live in their own rollout files, located by thread id).
"""

from collections.abc import AsyncIterator, Sequence
from logging import getLogger

from inspect_ai.event import Event
from inspect_swe._codex_cli._events.rollout import (
    process_rollout_events as _swe_process_rollout_events,
)
from inspect_swe._codex_cli._events.rollout_models import (
    RolloutEvent,
    parse_rollout_events,
)

from .client import RolloutFinder, read_rollout_lines

logger = getLogger(__name__)


async def process_rollout_events(
    events: Sequence[RolloutEvent],
    finder: RolloutFinder,
    max_depth: int = 5,
) -> AsyncIterator[Event]:
    """Convert parsed rollout events to Scout events.

    Thin wrapper around the shared implementation that injects a
    file-based child-thread loader: spawned-agent rollouts are located
    via the finder, converted, and recursed into for nested spawns
    (depth accounting is handled by the shared processor).
    """

    async def load_child_thread(thread_id: str, max_depth: int) -> list[Event]:
        child_file = finder.find(thread_id)
        if child_file is None:
            logger.debug(f"Child rollout not found for thread: {thread_id}")
            return []
        raw_lines = read_rollout_lines(child_file)
        if not raw_lines:
            return []
        child_events = parse_rollout_events(raw_lines)
        return [
            event
            async for event in _swe_process_rollout_events(
                child_events,
                max_depth=max_depth,
                child_loader=load_child_thread,
            )
        ]

    async for event in _swe_process_rollout_events(
        events,
        max_depth=max_depth,
        child_loader=load_child_thread,
    ):
        yield event


__all__ = ["process_rollout_events"]
