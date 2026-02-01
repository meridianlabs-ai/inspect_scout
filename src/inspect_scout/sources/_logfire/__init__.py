"""Logfire transcript import functionality.

This module provides functions to import transcripts from Logfire
into an Inspect Scout transcript database.

Authentication:
    Set LOGFIRE_READ_TOKEN environment variable or pass read_token parameter.
    Generate a read token from the Logfire dashboard (Settings > Read Tokens).

Supports traces from instrumentors:
- Pydantic AI - logfire.instrument_pydantic_ai()
- OpenAI - logfire.instrument_openai()
- Anthropic - logfire.instrument_anthropic()
- Google GenAI - logfire.instrument_google_genai()
- LiteLLM - logfire.instrument_litellm()
"""

from datetime import datetime
from logging import getLogger
from typing import Any, AsyncIterator

from inspect_ai.event import ModelEvent
from inspect_ai.model._chat_message import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageUser,
)

from inspect_scout._transcript.types import Transcript
from inspect_scout._util.message_ids import stable_message_ids

from .client import (
    LOGFIRE_SOURCE_TYPE,
    get_logfire_client,
    retry_api_call_async,
)
from .detection import detect_instrumentor, get_model_name
from .events import spans_to_events
from .extraction import sum_latency, sum_tokens
from .tree import build_span_tree, flatten_tree_chronological, get_llm_spans

logger = getLogger(__name__)


async def logfire(
    project: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    filter: str | None = None,
    trace_id: str | None = None,
    limit: int | None = None,
    read_token: str | None = None,
) -> AsyncIterator[Transcript]:
    """Read transcripts from [Logfire](https://logfire.pydantic.dev/) traces.

    Each Logfire trace (collection of spans with same trace_id) becomes one
    Scout transcript. Child spans (LLM calls, tools) become events within
    the transcript.

    Args:
        project: Logfire project name in format "org/project". If not provided,
            queries across all accessible projects.
        from_time: Only fetch traces created on or after this time
        to_time: Only fetch traces created before this time
        filter: SQL WHERE fragment for additional filtering (e.g.,
            "attributes->>'gen_ai.request.model' = 'gpt-4o'")
        trace_id: Fetch a specific trace by ID instead of querying
        limit: Maximum number of transcripts to fetch
        read_token: Logfire read token (or LOGFIRE_READ_TOKEN env var).
            Generate from Logfire dashboard Settings > Read Tokens.

    Yields:
        Transcript objects ready for insertion into transcript database

    Raises:
        ImportError: If logfire package is not installed
        ValueError: If required parameters are missing
    """
    client = get_logfire_client(read_token)

    try:
        if trace_id:
            # Fetch specific trace
            transcript = await _trace_to_transcript(client, trace_id, project)
            if transcript:
                yield transcript
        else:
            # Query traces
            async for transcript in _from_project(
                client,
                project,
                from_time,
                to_time,
                filter,
                limit,
            ):
                yield transcript
    finally:
        # Close client if it has aclose method
        if hasattr(client, "aclose"):
            await client.aclose()


async def _from_project(
    client: Any,
    project: str | None,
    from_time: datetime | None,
    to_time: datetime | None,
    filter_sql: str | None,
    limit: int | None,
) -> AsyncIterator[Transcript]:
    """Fetch transcripts from Logfire project.

    Args:
        client: AsyncLogfireQueryClient
        project: Project name (org/project format)
        from_time: Start time filter
        to_time: End time filter
        filter_sql: Additional SQL WHERE fragment
        limit: Max transcripts

    Yields:
        Transcript objects
    """
    # Query for distinct trace IDs with LLM spans
    try:
        trace_ids = await _query_trace_ids(
            client, project, from_time, to_time, filter_sql, limit
        )
    except Exception as e:
        logger.error(f"Failed to query traces from Logfire: {e}")
        return

    count = 0
    for trace_id in trace_ids:
        try:
            transcript = await _trace_to_transcript(client, trace_id, project)
            if transcript:
                yield transcript
                count += 1
                if limit and count >= limit:
                    return
        except Exception as e:
            logger.warning(f"Failed to process trace {trace_id}: {e}")
            continue


async def _query_trace_ids(
    client: Any,
    project: str | None,
    from_time: datetime | None,
    to_time: datetime | None,
    filter_sql: str | None,
    limit: int | None,
) -> list[str]:
    """Query distinct trace IDs that have LLM spans.

    The filter is applied at the trace level: we find traces where ANY span
    matches the filter AND the trace contains at least one GenAI span.
    This allows filtering by parent span attributes (like span_name) while
    still requiring the trace to have LLM operations.

    Args:
        client: AsyncLogfireQueryClient
        project: Project name filter
        from_time: Start time filter
        to_time: End time filter
        filter_sql: Additional WHERE fragment (applied to any span in trace)
        limit: Max traces to return

    Returns:
        List of trace_id strings
    """
    limit_clause = f"LIMIT {limit}" if limit else "LIMIT 500"

    # Build time filter conditions
    time_conditions: list[str] = []
    if from_time:
        time_conditions.append(f"start_timestamp >= '{from_time.isoformat()}'")
    if to_time:
        time_conditions.append(f"start_timestamp < '{to_time.isoformat()}'")
    time_where = " AND ".join(time_conditions) if time_conditions else "TRUE"

    if filter_sql:
        # When a filter is provided, we need to find traces where:
        # 1. At least one span matches the filter
        # 2. At least one span has gen_ai.operation.name (is an LLM trace)
        # These may be different spans within the same trace.
        sql = f"""
            SELECT r1.trace_id, MIN(r1.start_timestamp) as first_timestamp
            FROM records r1
            WHERE r1.trace_id IN (
                SELECT DISTINCT trace_id
                FROM records
                WHERE attributes->>'gen_ai.operation.name' IS NOT NULL
                  AND {time_where}
            )
            AND ({filter_sql})
            AND {time_where}
            GROUP BY r1.trace_id
            ORDER BY first_timestamp DESC
            {limit_clause}
        """
    else:
        # No filter - just find traces with GenAI operations
        genai_condition = "attributes->>'gen_ai.operation.name' IS NOT NULL"
        conditions = [genai_condition]
        if time_conditions:
            conditions.extend(time_conditions)
        where_clause = " AND ".join(conditions)

        sql = f"""
            SELECT trace_id, MIN(start_timestamp) as first_timestamp
            FROM records
            WHERE {where_clause}
            GROUP BY trace_id
            ORDER BY first_timestamp DESC
            {limit_clause}
        """

    async def _query() -> dict[str, Any]:
        result: dict[str, Any] = await client.query_json_rows(sql=sql)
        return result

    try:
        result = await retry_api_call_async(_query)
        rows = result.get("rows", [])
        return [row["trace_id"] for row in rows if row.get("trace_id")]
    except Exception as e:
        logger.error(f"Failed to query trace IDs: {e}")
        return []


async def _query_trace_spans(client: Any, trace_id: str) -> list[dict[str, Any]]:
    """Fetch all spans for a specific trace.

    Args:
        client: AsyncLogfireQueryClient
        trace_id: Trace ID to fetch

    Returns:
        List of span dictionaries
    """
    sql = f"""
        SELECT
            trace_id,
            span_id,
            parent_span_id,
            span_name,
            message,
            start_timestamp,
            end_timestamp,
            duration,
            attributes,
            is_exception,
            exception_type,
            exception_message,
            otel_scope_name,
            otel_events,
            level,
            tags,
            service_name
        FROM records
        WHERE trace_id = '{trace_id}'
        ORDER BY start_timestamp ASC
    """

    async def _query() -> dict[str, Any]:
        result: dict[str, Any] = await client.query_json_rows(sql=sql)
        return result

    result: dict[str, Any] = await retry_api_call_async(_query)
    rows: list[dict[str, Any]] = result.get("rows", [])
    return rows


async def _trace_to_transcript(
    client: Any,
    trace_id: str,
    project: str | None,
) -> Transcript | None:
    """Convert a Logfire trace to a Scout Transcript.

    Args:
        client: AsyncLogfireQueryClient
        trace_id: Trace ID to convert
        project: Project name for metadata

    Returns:
        Transcript object or None if trace has no valid data
    """
    # Fetch all spans in the trace
    try:
        all_spans = await _query_trace_spans(client, trace_id)
    except Exception as e:
        logger.warning(f"Failed to fetch spans for trace {trace_id}: {e}")
        return None

    if not all_spans:
        return None

    # Build tree and flatten chronologically
    tree = build_span_tree(all_spans)
    ordered_spans = flatten_tree_chronological(tree)

    # Convert spans to events
    events = await spans_to_events(ordered_spans)

    # Get LLM spans for message extraction and metadata
    llm_spans = get_llm_spans(ordered_spans)

    # Build messages from LLM inputs + outputs
    messages: list[ChatMessage] = []

    # For traces with LLM calls, find the ModelEvent with the most complete
    # conversation. Some instrumentors create multiple spans (e.g., Pydantic AI
    # creates both framework-level spans and SDK-level spans), so we need to
    # pick the one with the full conversation history.
    if llm_spans:
        model_events = [e for e in events if isinstance(e, ModelEvent)]
        if model_events:
            # Find the model event with the most input messages
            best_model = max(model_events, key=lambda e: len(e.input))
            # Use the LLM's input which has the full conversation
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

    # Extract metadata from root span
    root_span = ordered_spans[0] if ordered_spans else {}
    metadata = _extract_metadata(root_span)

    # Get model name
    model_name = get_model_name(llm_spans[0]) if llm_spans else None

    # Get root span info for task identification
    root_name = root_span.get("span_name") or root_span.get("message") or "trace"
    root_start = root_span.get("start_timestamp")

    # Detect any errors
    error = None
    for span in ordered_spans:
        if span.get("is_exception"):
            error = span.get("exception_message") or "Unknown error"
            break

    # Construct source URI
    source_uri = f"https://logfire.pydantic.dev/trace/{trace_id}"
    if project:
        source_uri = f"https://logfire.pydantic.dev/{project}/trace/{trace_id}"

    return Transcript(
        transcript_id=trace_id,
        source_type=LOGFIRE_SOURCE_TYPE,
        source_id=project or "logfire",
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


def _extract_root_messages(span: dict[str, Any]) -> list[ChatMessage]:
    """Extract messages from root span attributes.

    Args:
        span: Root span dictionary

    Returns:
        List of ChatMessage objects
    """
    messages: list[ChatMessage] = []
    attributes = span.get("attributes") or {}

    # Try to get input from common attribute patterns
    input_text = attributes.get("input") or attributes.get("query")
    if input_text:
        messages.append(ChatMessageUser(content=str(input_text)))

    # Try to get output
    output_text = attributes.get("output") or attributes.get("response")
    if output_text:
        messages.append(ChatMessageAssistant(content=str(output_text)))

    return messages


def _extract_metadata(span: dict[str, Any]) -> dict[str, Any]:
    """Extract metadata from span for Scout transcript.

    Args:
        span: Logfire span dictionary

    Returns:
        Metadata dictionary
    """
    metadata: dict[str, Any] = {}
    attributes = span.get("attributes") or {}

    # Add service info
    if span.get("service_name"):
        metadata["service_name"] = span["service_name"]

    # Add instrumentor info
    instrumentor = detect_instrumentor(span)
    if instrumentor.value != "unknown":
        metadata["instrumentor"] = instrumentor.value

    # Add tags
    if span.get("tags"):
        metadata["tags"] = span["tags"]

    # Add otel scope
    if span.get("otel_scope_name"):
        metadata["otel_scope_name"] = span["otel_scope_name"]

    # Copy relevant attributes
    for key in ["agent", "agent_args", "score", "success"]:
        if key in attributes:
            metadata[key] = attributes[key]

    return metadata


# Re-exports
__all__ = ["logfire", "LOGFIRE_SOURCE_TYPE", "detect_instrumentor"]
