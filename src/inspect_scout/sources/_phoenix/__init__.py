"""Phoenix transcript import functionality.

This module provides functions to import transcripts from Arize Phoenix
into an Inspect Scout transcript database. Phoenix uses OpenInference
semantic conventions which normalize trace data across all LLM providers,
so transcripts can be imported from any provider traced through Phoenix.

Authentication:
    Set PHOENIX_API_KEY environment variable or pass api_key parameter.
    Set PHOENIX_COLLECTOR_ENDPOINT for the base URL (defaults to http://localhost:6006).
"""

import json
import os
from collections import defaultdict
from datetime import datetime
from logging import getLogger
from typing import Any, AsyncIterator

from inspect_ai.event import ModelEvent
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageUser,
    stable_message_ids,
)

from inspect_scout._transcript.types import Transcript

from .client import (
    PHOENIX_SOURCE_TYPE,
    get_phoenix_client,
    retry_api_call_async,
)
from .detection import detect_provider, get_model_name
from .events import spans_to_events
from .extraction import sum_latency, sum_tokens
from .tree import build_span_tree, flatten_tree_chronological, get_llm_spans

logger = getLogger(__name__)


async def phoenix(
    project: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    trace_id: str | list[str] | None = None,
    session_id: str | list[str] | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, str] | None = None,
    limit: int | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> AsyncIterator[Transcript]:
    """Read transcripts from [Arize Phoenix](https://phoenix.arize.com/) traces.

    Each Phoenix trace (collection of spans with same trace_id) becomes one
    Scout transcript. Child spans (LLM calls, tools) become events within
    the transcript.

    Args:
        project: Phoenix project name or ID. Required for fetching spans.
        from_time: Only fetch traces created on or after this time
        to_time: Only fetch traces created before this time
        trace_id: Fetch specific trace(s) by ID (single string or list)
        session_id: Filter to traces belonging to specific session(s)
            (matches ``session.id`` attribute on root span)
        tags: Filter by tags on root span (all must match;
            stored in ``tag.tags`` attribute)
        metadata: Filter by metadata key-value pairs on root span
            (all must match; stored in ``metadata.*`` attributes)
        limit: Maximum number of transcripts to fetch
        api_key: Phoenix API key (or PHOENIX_API_KEY env var)
        base_url: Phoenix base URL (or PHOENIX_COLLECTOR_ENDPOINT env var)

    Yields:
        Transcript objects ready for insertion into transcript database

    Raises:
        ImportError: If arize-phoenix-client package is not installed
        ValueError: If required parameters are missing
    """
    if not project:
        raise ValueError(
            "Phoenix project name is required. Provide the project parameter."
        )

    client = get_phoenix_client(api_key, base_url)

    if trace_id and not session_id and not tags and not metadata:
        # Direct trace lookup (no client-side filtering needed)
        trace_ids = [trace_id] if isinstance(trace_id, str) else trace_id
        for tid in trace_ids:
            transcript = await _trace_to_transcript(client, project, tid, base_url)
            if transcript:
                yield transcript
    else:
        async for transcript in _from_project(
            client,
            project,
            from_time,
            to_time,
            trace_id,
            session_id,
            tags,
            metadata,
            limit,
            base_url,
        ):
            yield transcript


async def _from_project(
    client: Any,
    project: str,
    from_time: datetime | None,
    to_time: datetime | None,
    trace_id: str | list[str] | None,
    session_id: str | list[str] | None,
    tags: list[str] | None,
    metadata_filter: dict[str, str] | None,
    limit: int | None,
    base_url: str | None,
) -> AsyncIterator[Transcript]:
    """Fetch transcripts from Phoenix project.

    Args:
        client: Phoenix AsyncClient
        project: Project name or ID
        from_time: Start time filter
        to_time: End time filter
        trace_id: Filter to specific trace ID(s)
        session_id: Filter by session ID(s) on root span
        tags: Filter by tags on root span (all must match)
        metadata_filter: Filter by metadata key-value pairs on root span
        limit: Max transcripts
        base_url: Phoenix base URL for source URIs

    Yields:
        Transcript objects
    """
    try:
        all_spans = await _fetch_spans(client, project, from_time, to_time, limit)
    except Exception as e:
        logger.error(f"Failed to fetch spans from Phoenix: {e}")
        return

    # Normalize trace_id filter to a set for fast lookup
    trace_id_set: set[str] | None = None
    if trace_id:
        if isinstance(trace_id, str):
            trace_id_set = {trace_id}
        else:
            trace_id_set = set(trace_id)

    # Group spans by trace_id
    traces: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for span in all_spans:
        context = span.get("context") or {}
        tid = context.get("trace_id")
        if tid:
            tid_str = str(tid)
            # Apply trace_id filter early during grouping
            if trace_id_set and tid_str not in trace_id_set:
                continue
            traces[tid_str].append(span)

    count = 0
    for tid, trace_spans in traces.items():
        # Apply client-side filters
        if not _matches_filters(trace_spans, session_id, tags, metadata_filter):
            continue

        try:
            transcript = await _build_transcript(trace_spans, project, tid, base_url)
            if transcript:
                yield transcript
                count += 1
                if limit and count >= limit:
                    return
        except Exception as e:
            if os.environ.get("PHOENIX_STRICT_IMPORT"):
                raise
            logger.warning(f"Failed to process trace {tid}: {e}")
            continue


async def _fetch_spans(
    client: Any,
    project: str,
    from_time: datetime | None,
    to_time: datetime | None,
    limit: int | None,
) -> list[dict[str, Any]]:
    """Fetch spans from Phoenix API.

    Args:
        client: Phoenix AsyncClient
        project: Project identifier
        from_time: Start time filter
        to_time: End time filter
        limit: Max spans to fetch

    Returns:
        List of span dictionaries
    """
    fetch_limit = min(limit * 50, 10000) if limit else 5000

    async def _query() -> list[Any]:
        kwargs: dict[str, Any] = {
            "project_identifier": project,
            "limit": fetch_limit,
        }
        if from_time:
            kwargs["start_time"] = from_time
        if to_time:
            kwargs["end_time"] = to_time

        result: list[Any] = await client.spans.get_spans(**kwargs)
        return result

    spans = await retry_api_call_async(_query)

    # Convert Span TypedDicts to regular dicts
    return [dict(span) for span in spans]


async def _trace_to_transcript(
    client: Any,
    project: str,
    trace_id: str,
    base_url: str | None,
) -> Transcript | None:
    """Fetch all spans for a trace and convert to Transcript.

    Args:
        client: Phoenix AsyncClient
        project: Project identifier
        trace_id: Trace ID to fetch
        base_url: Phoenix base URL

    Returns:
        Transcript object or None
    """
    try:
        all_spans = await _fetch_spans(client, project, None, None, None)
    except Exception as e:
        logger.warning(f"Failed to fetch spans for trace {trace_id}: {e}")
        return None

    # Filter to the specific trace
    trace_spans = [
        span
        for span in all_spans
        if (span.get("context") or {}).get("trace_id") == trace_id
    ]

    if not trace_spans:
        return None

    return await _build_transcript(trace_spans, project, trace_id, base_url)


async def _build_transcript(
    trace_spans: list[dict[str, Any]],
    project: str,
    trace_id: str,
    base_url: str | None,
) -> Transcript | None:
    """Build a Transcript from a set of spans belonging to one trace.

    Args:
        trace_spans: All spans for a single trace
        project: Project name
        trace_id: Trace ID
        base_url: Phoenix base URL

    Returns:
        Transcript object or None
    """
    if not trace_spans:
        return None

    # Build tree and flatten chronologically
    tree = build_span_tree(trace_spans)
    ordered_spans = flatten_tree_chronological(tree)

    # Convert spans to events
    events = await spans_to_events(ordered_spans)

    # Get LLM spans for message extraction and metadata
    llm_spans = get_llm_spans(ordered_spans)

    # Build messages from LLM inputs + outputs
    messages: list[ChatMessage] = []

    if llm_spans:
        model_events = [e for e in events if isinstance(e, ModelEvent)]
        if model_events:
            # Find the model event with the most input messages
            best_model = max(model_events, key=lambda e: len(e.input))
            messages = list(best_model.input)
            # Append the final assistant response from output
            if best_model.output and best_model.output.message:
                messages.append(best_model.output.message)

    # Fallback: try to extract from root span
    if not messages:
        root_span = ordered_spans[0] if ordered_spans else None
        if root_span:
            messages = _extract_root_messages(root_span)

    # Apply stable message IDs
    apply_ids = stable_message_ids()
    for event in events:
        if isinstance(event, ModelEvent):
            apply_ids(event)
    apply_ids(messages)

    # Get model name
    model_name = get_model_name(llm_spans[0]) if llm_spans else None

    # Get root span info
    root_span = ordered_spans[0] if ordered_spans else {}
    root_name = root_span.get("name") or "trace"
    root_start = root_span.get("start_time")

    # Detect any errors
    error = None
    for span in ordered_spans:
        if str(span.get("status_code", "")).upper() == "ERROR":
            error = span.get("status_message") or "Unknown error"
            break

    # Extract metadata
    metadata = _extract_metadata(root_span)

    # Construct source URI
    effective_url = base_url or "https://app.phoenix.arize.com"
    source_uri = f"{effective_url}/projects/{project}/traces/{trace_id}"

    return Transcript(
        transcript_id=trace_id,
        source_type=PHOENIX_SOURCE_TYPE,
        source_id=project,
        source_uri=source_uri,
        date=str(root_start) if root_start else None,
        task_set=project,
        task_id=root_name,
        task_repeat=None,
        agent=metadata.get("agent"),
        agent_args=metadata.get("agent_args"),
        model=model_name,
        model_options=None,
        score=metadata.get("score"),
        success=metadata.get("success"),
        message_count=len(messages),
        total_tokens=sum_tokens(llm_spans),
        total_time=sum_latency(ordered_spans),
        error=error,
        limit=None,
        messages=messages,
        events=events,
        metadata=metadata,
    )


def _find_root_span(trace_spans: list[dict[str, Any]]) -> dict[str, Any]:
    """Find root span (no parent_id, or earliest start_time as fallback).

    Args:
        trace_spans: All spans for a single trace

    Returns:
        The root span dictionary, or empty dict if no spans
    """
    if not trace_spans:
        return {}

    for span in trace_spans:
        if not span.get("parent_id"):
            return span

    return min(trace_spans, key=lambda s: s.get("start_time") or "")


def _matches_filters(
    trace_spans: list[dict[str, Any]],
    session_id: str | list[str] | None,
    tags: list[str] | None,
    metadata_filter: dict[str, str] | None,
) -> bool:
    """Check whether a trace matches the given client-side filters.

    Filters are checked against the root span's attributes. All specified
    filters must match (AND semantics).

    Args:
        trace_spans: All spans for a single trace
        session_id: Required session ID(s) (matches ``session.id`` attribute)
        tags: Required tags (all must be present in ``tag.tags`` attribute)
        metadata_filter: Required metadata key-value pairs
            (all must match ``metadata.*`` attributes)

    Returns:
        True if the trace matches all filters, or no filters are specified
    """
    if not session_id and not tags and not metadata_filter:
        return True

    root = _find_root_span(trace_spans)
    attrs = root.get("attributes") or {}

    if session_id:
        span_session = attrs.get("session.id")
        if isinstance(session_id, str):
            if span_session != session_id:
                return False
        else:
            if span_session not in session_id:
                return False

    if tags:
        span_tags = attrs.get("tag.tags")
        if not isinstance(span_tags, list):
            return False
        if not all(t in span_tags for t in tags):
            return False

    if metadata_filter:
        for key, value in metadata_filter.items():
            if attrs.get(f"metadata.{key}") != value:
                return False

    return True


def _extract_root_messages(span: dict[str, Any]) -> list[ChatMessage]:
    """Extract messages from root span attributes.

    Args:
        span: Root span dictionary

    Returns:
        List of ChatMessage objects
    """
    messages: list[ChatMessage] = []
    attributes = span.get("attributes") or {}

    input_text = attributes.get("input.value")
    if input_text:
        if isinstance(input_text, str):
            try:
                parsed = json.loads(input_text)
                if isinstance(parsed, dict):
                    input_text = (
                        parsed.get("query") or parsed.get("input") or str(parsed)
                    )
                elif isinstance(parsed, str):
                    input_text = parsed
            except json.JSONDecodeError:
                pass
        messages.append(ChatMessageUser(content=str(input_text)))

    output_text = attributes.get("output.value")
    if output_text:
        if isinstance(output_text, str):
            try:
                parsed = json.loads(output_text)
                if isinstance(parsed, dict):
                    output_text = (
                        parsed.get("response") or parsed.get("output") or str(parsed)
                    )
                elif isinstance(parsed, str):
                    output_text = parsed
            except json.JSONDecodeError:
                pass
        messages.append(ChatMessageAssistant(content=str(output_text)))

    return messages


def _extract_metadata(span: dict[str, Any]) -> dict[str, Any]:
    """Extract metadata from span for Scout transcript.

    Automatically extracts OpenInference context attributes when present:
    ``session.id``, ``user.id``, ``tag.tags``, and ``metadata.*``.

    Args:
        span: Phoenix span dictionary

    Returns:
        Metadata dictionary
    """
    metadata: dict[str, Any] = {}
    attributes = span.get("attributes") or {}

    # Add provider info
    provider = detect_provider(span)
    if provider.value != "unknown":
        metadata["provider"] = provider.value

    # Add span_kind
    span_kind = span.get("span_kind")
    if span_kind:
        metadata["span_kind"] = span_kind

    # Copy relevant attributes
    for key in ["agent", "agent_args", "score", "success"]:
        if key in attributes:
            metadata[key] = attributes[key]

    # Extract OpenInference context attributes
    session_id = attributes.get("session.id")
    if session_id:
        metadata["session_id"] = session_id

    user_id = attributes.get("user.id")
    if user_id:
        metadata["user_id"] = user_id

    tag_tags = attributes.get("tag.tags")
    if isinstance(tag_tags, list) and tag_tags:
        metadata["tags"] = tag_tags

    # Extract metadata.* attributes into a nested dict
    span_metadata: dict[str, Any] = {}
    for key, value in attributes.items():
        if key.startswith("metadata."):
            meta_key = key[len("metadata.") :]
            span_metadata[meta_key] = value
    if span_metadata:
        metadata["metadata"] = span_metadata

    return metadata


# Re-exports
__all__ = ["phoenix", "PHOENIX_SOURCE_TYPE", "detect_provider"]
