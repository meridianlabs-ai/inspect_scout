"""Codex rollout event conversion — scout-specific child-thread loading.

Most conversion logic lives in inspect_swe._codex_cli._events.rollout.
This module provides the file-based child-thread loader (spawned agents
live in their own rollout files, located by thread id) injected as a
ChildThreadLoader, plus a thin wrapper for process_rollout_events.
"""

from collections.abc import AsyncIterator, Sequence
from logging import getLogger
from pathlib import Path

from inspect_ai.event import Event
from inspect_swe._codex_cli._events.rollout import (
    ChildThreadLoader,
)
from inspect_swe._codex_cli._events.rollout import (
    process_rollout_events as _swe_process_rollout_events,
)
from inspect_swe._codex_cli._events.rollout_models import (
    RolloutEvent,
    parse_rollout_events,
)

from .client import find_rollout_by_thread_id, read_rollout_lines

logger = getLogger(__name__)


def make_child_loader(search_roots: list[Path]) -> ChildThreadLoader:
    """Create a file-based child-thread loader for spawned agents.

    The loader locates ``rollout-*-<thread-id>.jsonl`` under the given
    search roots (the parent's sessions tree), converts it, and recurses
    for nested spawns (bounded by max_depth).
    """

    async def load_child_thread(thread_id: str, max_depth: int) -> list[Event]:
        child_file = find_rollout_by_thread_id(thread_id, search_roots)
        if child_file is None:
            logger.debug(f"Child rollout not found for thread: {thread_id}")
            return []
        raw_lines = read_rollout_lines(child_file)
        if not raw_lines:
            return []
        child_events = parse_rollout_events(raw_lines)
        result: list[Event] = []
        async for event in _swe_process_rollout_events(
            child_events,
            max_depth=max_depth,
            child_loader=load_child_thread if max_depth > 0 else None,
        ):
            result.append(event)
        return result

    return load_child_thread


async def process_rollout_events(
    events: Sequence[RolloutEvent],
    search_roots: list[Path],
    max_depth: int = 5,
) -> AsyncIterator[Event]:
    """Convert parsed rollout events to Scout events.

    Thin wrapper around the shared implementation that injects the
    scout file-based child-thread loader.
    """
    async for event in _swe_process_rollout_events(
        events,
        max_depth=max_depth,
        child_loader=make_child_loader(search_roots),
    ):
        yield event


__all__ = ["make_child_loader", "process_rollout_events"]
