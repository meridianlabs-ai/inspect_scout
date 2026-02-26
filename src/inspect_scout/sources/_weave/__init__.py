"""W&B Weave transcript import functionality.

This module provides functions to import transcripts from W&B Weave
into an Inspect Scout transcript database.

Supports traces from:
- OpenAI API calls
- Anthropic API calls
- Google/Gemini API calls
- Custom instrumented code
"""

from datetime import datetime
from logging import getLogger
from typing import Any, AsyncIterator

from inspect_ai.event import ModelEvent
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageUser,
    stable_message_ids,
)

from inspect_scout._transcript.types import Transcript

from .client import (
    WEAVE_SOURCE_TYPE,
    retry_api_call,
)
from .detection import detect_provider_format, get_model_name
from .events import calls_to_events
from .extraction import (
    extract_bool,
    extract_dict,
    extract_int,
    extract_json,
    extract_metadata,
    extract_str,
    sum_latency,
    sum_tokens,
)
from .tree import build_call_tree, flatten_tree_chronological, get_llm_calls

logger = getLogger(__name__)


async def weave(
    project: str,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    filter: dict[str, Any] | None = None,
    limit: int | None = None,
    api_key: str | None = None,
) -> AsyncIterator[Transcript]:
    """Read transcripts from [W&B Weave](https://wandb.ai/site/weave) traces.

    Each Weave trace (root call + children) becomes one Scout transcript.
    Child calls (LLM calls, tools) become events within the transcript.

    Args:
        project: W&B project name in format "entity/project"
        from_time: Only fetch traces created on or after this time
        to_time: Only fetch traces created before this time
        filter: Dictionary of filters to apply to call query
        limit: Maximum number of transcripts to fetch
        api_key: W&B API key (or WANDB_API_KEY env var)

    Yields:
        Transcript objects ready for insertion into transcript database

    Raises:
        ImportError: If weave package is not installed
        ValueError: If required parameters are missing
    """
    if not project:
        raise ValueError("'project' must be provided")

    try:
        import weave
        from weave.trace_server.trace_server_interface import CallsFilter
    except ImportError as e:
        raise ImportError(
            "The weave package is required for Weave import. "
            "Install it with: pip install weave"
        ) from e

    # Initialize weave client
    client = weave.init(project)

    # Build filter for root calls
    call_filter = CallsFilter()

    # Apply time filters if provided
    # Note: Weave API may have different filter semantics

    # Fetch root calls (calls without parent_id)
    count = 0
    try:
        # Get all calls and filter to root calls
        def _list_calls() -> list[Any]:
            calls_iter = client.get_calls(filter=call_filter)
            return list(calls_iter)

        all_calls = retry_api_call(_list_calls)
    except Exception as e:
        logger.error(f"Failed to list calls from project {project}: {e}")
        return

    # Group calls by trace_id (root call id)
    traces: dict[str, list[Any]] = {}
    for call in all_calls:
        # Get trace_id - this is the root call's id
        trace_id = getattr(call, "trace_id", None)
        if not trace_id:
            # If no trace_id, use the call's own id if it's a root call
            parent_id = getattr(call, "parent_id", None)
            if not parent_id:
                trace_id = str(getattr(call, "id", ""))
            else:
                continue  # Skip non-root calls without trace_id

        trace_id = str(trace_id)
        if trace_id not in traces:
            traces[trace_id] = []
        traces[trace_id].append(call)

    # Apply time filtering
    filtered_traces: dict[str, list[Any]] = {}
    for trace_id, calls in traces.items():
        # Find root call for time filtering
        root_call = None
        for call in calls:
            if not getattr(call, "parent_id", None):
                root_call = call
                break

        if root_call:
            started_at = getattr(root_call, "started_at", None)
            if started_at:
                if from_time and started_at < from_time:
                    continue
                if to_time and started_at >= to_time:
                    continue

        filtered_traces[trace_id] = calls

    # Process each trace
    for _trace_id, trace_calls in filtered_traces.items():
        # Find root call
        root_call = None
        for call in trace_calls:
            if not getattr(call, "parent_id", None):
                root_call = call
                break

        if not root_call:
            continue

        try:
            transcript = await _trace_to_transcript(
                trace_calls, root_call, project, client
            )
            if transcript:
                yield transcript
                count += 1
                if limit and count >= limit:
                    return
        except Exception as e:
            call_id = getattr(root_call, "id", "unknown")
            logger.warning(f"Failed to process trace {call_id}: {e}")
            continue


async def _trace_to_transcript(
    calls: list[Any],
    root_call: Any,
    project: str,
    client: Any,
) -> Transcript | None:
    """Convert a Weave trace (root call + children) to a Scout Transcript.

    Args:
        calls: All calls in the trace
        root_call: The root call object
        project: Project name for metadata
        client: Weave client for building URLs

    Returns:
        Transcript object or None if trace has no valid data
    """
    if not calls:
        return None

    # Build tree and flatten chronologically
    tree = build_call_tree(calls)
    ordered_calls = flatten_tree_chronological(tree)

    # Convert calls to events
    events = await calls_to_events(ordered_calls)

    # Get LLM calls for message extraction and metadata
    llm_calls = get_llm_calls(ordered_calls)

    # Build messages from LLM inputs + outputs
    messages: list[ChatMessage] = []

    # For traces with LLM calls, use the full conversation from the
    # last LLM event which includes all intermediate turns (tool calls, results).
    if llm_calls:
        model_events = [e for e in events if isinstance(e, ModelEvent)]
        if model_events:
            last_model = model_events[-1]
            # Use the LLM's input which has the full conversation
            messages = list(last_model.input)
            # Append the final assistant response from output
            if last_model.output and last_model.output.message:
                messages.append(last_model.output.message)

    # Fallback: for traces without LLM events, try root inputs
    if not messages:
        root_inputs = getattr(root_call, "inputs", None) or {}
        if isinstance(root_inputs, dict):
            root_messages = root_inputs.get("messages", [])
            for msg in root_messages:
                if isinstance(msg, dict):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if content:
                        if role == "user":
                            messages.append(ChatMessageUser(content=str(content)))
                        elif role == "system":
                            messages.append(ChatMessageSystem(content=str(content)))
                        elif role == "assistant":
                            messages.append(ChatMessageAssistant(content=str(content)))

    # Apply stable message IDs
    apply_ids = stable_message_ids()
    for event in events:
        if isinstance(event, ModelEvent):
            apply_ids(event)
    apply_ids(messages)

    # Extract metadata from root call
    metadata = extract_metadata(root_call)
    task_repeat = extract_int("task_repeat", metadata)
    agent = extract_str("agent", metadata)
    agent_args = extract_dict("agent_args", metadata)
    model_options = extract_dict("model_options", metadata)
    error = extract_str("error", metadata) or (
        str(root_call.exception) if getattr(root_call, "exception", None) else None
    )
    limit_val = extract_str("limit", metadata)
    score = extract_json("score", metadata)
    success = extract_bool("success", metadata)

    # Get model name
    model_name = get_model_name(llm_calls[0]) if llm_calls else None

    # Construct source URI
    call_id = getattr(root_call, "id", "unknown")
    # Parse project to get entity and project name
    entity = ""
    project_name = project
    if "/" in project:
        parts = project.split("/", 1)
        entity = parts[0]
        project_name = parts[1]

    source_uri = f"https://wandb.ai/{entity}/{project_name}/weave/calls/{call_id}"

    # Get display name or op_name for task_id
    task_id = (
        getattr(root_call, "display_name", None)
        or getattr(root_call, "op_name", None)
        or None
    )

    return Transcript(
        transcript_id=str(call_id),
        source_type=WEAVE_SOURCE_TYPE,
        source_id=project,
        source_uri=source_uri,
        date=str(root_call.started_at)
        if getattr(root_call, "started_at", None)
        else None,
        task_set=project,
        task_id=task_id,
        task_repeat=task_repeat,
        agent=agent,
        agent_args=agent_args,
        model=model_name,
        model_options=model_options,
        score=score,
        success=success,
        message_count=len(messages),
        total_tokens=sum_tokens(llm_calls),
        total_time=sum_latency(ordered_calls),
        error=error,
        limit=limit_val,
        messages=messages,
        events=events,
        metadata=metadata,
    )


# Re-exports
__all__ = ["weave", "WEAVE_SOURCE_TYPE", "detect_provider_format"]
