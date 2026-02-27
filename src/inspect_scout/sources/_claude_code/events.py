"""Claude Code event conversion — scout-specific agent loading.

Most conversion logic lives in inspect_swe._claude_code._events.events.
This module provides:
- File-based agent loading (via client.py) injected as an AgentEventLoader
- _extract_agent_id_from_result (scout-specific JSON/regex parsing)
- Thin wrappers for claude_code_events / process_parsed_events
- Re-exports of to_model_event / to_tool_event used by tests
"""

import json
import re
from collections.abc import AsyncIterable, AsyncIterator, Iterable, Sequence
from logging import getLogger
from pathlib import Path
from typing import Any

from inspect_ai.event import Event
from inspect_swe._claude_code._events.events import (
    claude_code_events as _swe_claude_code_events,
)
from inspect_swe._claude_code._events.events import (
    process_parsed_events as _swe_process_parsed_events,
)
from inspect_swe._claude_code._events.events import to_model_event, to_tool_event
from inspect_swe._claude_code._events.models import (
    BaseEvent,
    consolidate_assistant_events,
    parse_events,
)
from inspect_swe._claude_code._events.tree import (
    build_event_tree,
    flatten_tree_chronological,
    get_conversation_events,
)

logger = getLogger(__name__)


# ── Scout-specific helpers ──────────────────────────────────────────────


def _extract_agent_id_from_result(tool_result: dict[str, Any]) -> str | None:
    """Extract agent ID from a Task tool result using JSON parsing.

    Args:
        tool_result: The tool_result block containing agent response

    Returns:
        The agent ID if found, None otherwise
    """
    content = tool_result.get("content", [])

    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = str(item.get("text", ""))
                # Try to parse as JSON first (more robust)
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict) and "agentId" in parsed:
                        return str(parsed["agentId"])
                except json.JSONDecodeError:
                    logger.debug("Failed to parse tool result as JSON, trying regex")
                # Fallback: regex for partial JSON or embedded JSON
                match = re.search(r'"agentId"\s*:\s*"([^"]+)"', text)
                if match:
                    return match.group(1)
                # Plain-text format from Claude Code output:
                #   "agentId: aa9e523 (for resuming...)"
                match = re.search(r"agentId:\s*([a-f0-9]+)", text)
                if match:
                    return match.group(1)

    logger.debug("Could not extract agentId from tool result")
    return None


async def _load_agent_events(
    project_dir: Path | None,
    tool_result: dict[str, Any],
    subagent_events: dict[str, list[dict[str, Any]]] | None = None,
    max_depth: int = 5,
    session_file: Path | None = None,
    agent_id: str | None = None,
) -> list[Event]:
    """Load and process events from an agent session file or stream.

    Scout-specific: supports file-based loading via ``client.py`` in
    addition to stream-provided subagent events.

    Args:
        project_dir: Path to project directory (for file-based loading)
        tool_result: The tool_result block that completed the agent
        subagent_events: Pre-grouped subagent events by sessionId (streaming mode).
            Note: In streaming mode, events are keyed by sessionId (not agentId).
        max_depth: Maximum remaining depth for loading nested subagents (0 = no loading)
        session_file: Path to the parent session JSONL file (for locating subagent files)
        agent_id: Pre-extracted agent ID (e.g., from toolUseResult.agentId)

    Returns:
        List of Scout events from the agent session
    """
    from .client import find_agent_file, read_jsonl_events

    # Try to extract agent ID from the tool result content, fall back to provided
    agent_id = _extract_agent_id_from_result(tool_result) or agent_id

    raw_events: list[dict[str, Any]] | None = None
    agent_file: Path | None = None

    # Try stream-provided events first
    if subagent_events:
        all_events = []
        for session_events in subagent_events.values():
            all_events.extend(session_events)
        if all_events:
            raw_events = all_events

    # Fall back to file loading if we have an agent_id and project_dir
    if not raw_events and agent_id and project_dir:
        agent_file = find_agent_file(project_dir, agent_id, session_file=session_file)
        if not agent_file:
            logger.debug(f"Agent file not found for ID: {agent_id}")
            return []
        raw_events = read_jsonl_events(agent_file)

    if not raw_events:
        return []

    # Parse to Pydantic models and consolidate assistant fragments
    agent_events = parse_events(raw_events)
    agent_events = consolidate_assistant_events(agent_events)

    # Build tree and flatten
    tree = build_event_tree(agent_events)
    flat_events = flatten_tree_chronological(tree)

    # Filter to conversation events
    conversation_events = get_conversation_events(flat_events)

    # Convert to Scout events, with bounded recursion for nested subagents
    next_depth = max_depth - 1
    next_project_dir = project_dir if next_depth > 0 else None
    # The loaded agent file becomes the session_file for further nesting
    next_session_file = agent_file if next_depth > 0 else None
    result: list[Event] = []
    async for event in process_parsed_events(
        conversation_events,
        project_dir=next_project_dir,
        max_depth=next_depth,
        session_file=next_session_file,
    ):
        result.append(event)
    return result


# ── Public wrappers that inject the scout agent loader ──────────────────


async def claude_code_events(
    raw_events: Iterable[dict[str, Any]] | AsyncIterable[dict[str, Any]],
    project_dir: Path | None = None,
    max_depth: int = 5,
    session_file: Path | None = None,
) -> AsyncIterator[Event]:
    """Convert raw Claude Code JSONL events to Inspect AI events.

    Thin wrapper around the shared implementation that injects the
    scout file-based agent loader.
    """
    async for event in _swe_claude_code_events(
        raw_events,
        project_dir=project_dir,
        max_depth=max_depth,
        session_file=session_file,
        agent_loader=_load_agent_events,
    ):
        yield event


async def process_parsed_events(
    events: Sequence[BaseEvent],
    project_dir: Path | None = None,
    max_depth: int = 5,
    session_file: Path | None = None,
) -> AsyncIterator[Event]:
    """Convert parsed Claude Code events to Scout events.

    Thin wrapper around the shared implementation that injects the
    scout file-based agent loader.
    """
    async for event in _swe_process_parsed_events(
        events,
        project_dir=project_dir,
        max_depth=max_depth,
        session_file=session_file,
        agent_loader=_load_agent_events,
    ):
        yield event


__all__ = [
    "_extract_agent_id_from_result",
    "claude_code_events",
    "process_parsed_events",
    "to_model_event",
    "to_tool_event",
]
