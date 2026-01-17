"""LangFuse transcript import functionality.

This module provides functions to import transcripts from LangFuse
into an Inspect Scout transcript database.
"""

from datetime import datetime
from logging import getLogger
from typing import Any, AsyncIterator

from inspect_ai.model._chat_message import ChatMessage

from inspect_scout._transcript.types import Transcript

from .client import (
    LANGFUSE_SOURCE_TYPE,
    get_langfuse_client,
    resolve_project,
    retry_api_call,
)
from .detection import (
    detect_provider_format,
    find_best_responses_api_generation,
)
from .events import observations_to_events
from .extraction import (
    extract_bool,
    extract_dict,
    extract_input_messages,
    extract_int,
    extract_json,
    extract_metadata,
    extract_str,
    sum_latency,
    sum_tokens,
)
from .messages import (
    build_google_messages_from_events,
    build_messages_from_events,
    merge_transcript_messages,
)

logger = getLogger(__name__)


async def langfuse(
    project: str,
    environment: str | list[str] | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    tags: list[str] | None = None,
    user_id: str | None = None,
    name: str | None = None,
    version: str | None = None,
    release: str | None = None,
    limit: int | None = None,
    public_key: str | None = None,
    secret_key: str | None = None,
    host: str | None = None,
) -> AsyncIterator[Transcript]:
    """Read transcripts from LangFuse sessions.

    Each LangFuse session (multi-turn conversation) becomes one Scout transcript.
    All traces within a session are combined chronologically into the transcript's
    message history.

    Args:
        project: LangFuse project name or ID. Used for constructing source URLs.
            Accepts either the human-readable name (e.g., "my-project") or the
            opaque ID. If a name is provided, it will be resolved to an ID via
            the LangFuse API.
        environment: Filter by environment(s) (e.g., "production", "staging")
        from_time: Only fetch traces created on or after this time
        to_time: Only fetch traces created before this time
        tags: Filter by tags (all must match)
        user_id: Filter by user ID
        name: Filter by trace name
        version: Filter by version string
        release: Filter by release string
        limit: Maximum number of sessions to fetch
        public_key: LangFuse public key (or LANGFUSE_PUBLIC_KEY env var)
        secret_key: LangFuse secret key (or LANGFUSE_SECRET_KEY env var)
        host: LangFuse host URL (or LANGFUSE_HOST env var, defaults to cloud)

    Yields:
        Transcript objects ready for insertion into transcript database

    Raises:
        ImportError: If langfuse package is not installed
        ValueError: If project name cannot be resolved to an ID
    """
    langfuse_client = get_langfuse_client(public_key, secret_key, host)

    # Resolve project name to ID if needed
    project_id, project_name = resolve_project(langfuse_client, project)

    # Since the traces API has more filters than the sessions API,
    # we query traces first, then group by session_id
    session_ids: set[str] = set()
    page = 1

    while True:
        # Build query parameters
        query_params: dict[str, Any] = {
            "page": page,
            "limit": 100,
        }
        if from_time:
            query_params["from_timestamp"] = from_time.isoformat()
        if to_time:
            query_params["to_timestamp"] = to_time.isoformat()
        if user_id:
            query_params["user_id"] = user_id
        if name:
            query_params["name"] = name
        if tags:
            query_params["tags"] = tags
        if version:
            query_params["version"] = version
        if release:
            query_params["release"] = release
        if environment:
            query_params["environment"] = (
                environment if isinstance(environment, list) else [environment]
            )

        def _list_traces(qp: dict[str, Any] = query_params) -> Any:
            return langfuse_client.api.trace.list(**qp)

        response = retry_api_call(_list_traces)

        for trace in response.data:
            session_id = getattr(trace, "session_id", None)
            if session_id:
                session_ids.add(session_id)

        # Check if we've fetched all pages
        meta = getattr(response, "meta", None)
        if meta and page >= meta.total_pages:
            break
        page += 1

    # For each unique session, fetch full details and convert
    count = 0
    for session_id in session_ids:
        try:

            def _get_session(sid: Any = session_id) -> Any:
                return langfuse_client.api.sessions.get(sid)

            full_session = retry_api_call(_get_session)
            transcript = await _session_to_transcript(
                full_session, langfuse_client, project_id, project_name, host
            )
            if transcript:
                yield transcript
                count += 1
                if limit and count >= limit:
                    return
        except Exception as e:
            logger.warning(f"Failed to process session {session_id}: {e}")
            continue


async def _session_to_transcript(
    session: Any,
    langfuse_client: Any,
    project_id: str,
    project_name: str,
    host: str | None = None,
) -> Transcript | None:
    """Convert a LangFuse session to a Scout Transcript.

    Args:
        session: LangFuse session object with traces
        langfuse_client: LangFuse client for fetching trace details
        project_id: LangFuse project ID for URL construction
        project_name: LangFuse project name
        host: LangFuse host URL for URL construction

    Returns:
        Transcript object or None if session has no valid data
    """
    # Collect all observations across all traces
    all_observations: list[Any] = []
    traces = getattr(session, "traces", [])

    for trace in traces:
        # Fetch full trace with observations (with retry for transient errors)
        def _get_trace(tid: Any = trace.id) -> Any:
            return langfuse_client.api.trace.get(tid)

        full_trace = retry_api_call(_get_trace)
        observations = getattr(full_trace, "observations", [])
        all_observations.extend(observations)

    # Sort chronologically (handle None timestamps safely)
    all_observations.sort(key=lambda o: o.start_time or datetime.min)

    if not all_observations:
        return None

    # Convert observations to Scout events by type
    events = await observations_to_events(all_observations)

    # Get generations for message extraction and metadata
    generations = [
        o for o in all_observations if getattr(o, "type", "") == "GENERATION"
    ]

    # Find model events for message extraction
    model_events = [e for e in events if getattr(e, "event", "") == "model"]
    messages: list[ChatMessage] = []

    if model_events:
        # For OpenAI, try to use hybrid extraction to preserve system/user context
        # The Responses API format has complete message history that OTEL often lacks
        best_resp_gen = find_best_responses_api_generation(generations)
        if best_resp_gen is not None:
            resp_idx, resp_gen = best_resp_gen
            final_model = model_events[-1]

            # Extract base messages from Responses API format (has system/user)
            base_messages = await extract_input_messages(
                resp_gen.input, "openai_responses"
            )

            # If final generation is different, merge additional messages from it
            if resp_idx != len(generations) - 1:
                final_messages = list(final_model.input)
                messages = merge_transcript_messages(base_messages, final_messages)
            else:
                messages = base_messages

            # Always add final output message
            if final_model.output and final_model.output.message:
                messages.append(final_model.output.message)
        else:
            # Google-specific: use outputs for assistant messages to preserve reasoning
            # Google's scaffold doesn't replay reasoning, so it only exists in outputs
            model_name = generations[0].model if generations else ""
            if model_name and "gemini" in model_name.lower():
                messages = build_google_messages_from_events(events)
            else:
                # Build messages from events - this captures the full conversation
                messages = build_messages_from_events(events)

    # Get metadata from first trace
    first_trace = traces[0] if traces else None
    metadata = extract_metadata(first_trace)
    task_repeat = extract_int("task_repeat", metadata)
    agent = extract_str("agent", metadata)
    agent_args = extract_dict("agent_args", metadata)
    model_options = extract_dict("model_options", metadata)
    error = extract_str("error", metadata)
    limit = extract_str("limit", metadata)
    score = extract_json("score", metadata)
    success = extract_bool("success", metadata)

    # Construct source URI
    base_url = (host or "https://cloud.langfuse.com").rstrip("/")
    source_uri = f"{base_url}/project/{project_id}/sessions/{session.id}"

    return Transcript(
        transcript_id=session.id,
        source_type=LANGFUSE_SOURCE_TYPE,
        source_id=project_id,
        source_uri=source_uri,
        date=str(session.created_at) if hasattr(session, "created_at") else None,
        task_set=project_name,
        task_id=getattr(first_trace, "name", None) if first_trace else None,
        task_repeat=task_repeat,
        agent=agent,
        agent_args=agent_args,
        model=generations[0].model if generations else None,
        model_options=model_options,
        score=score,
        success=success,
        message_count=len(messages),
        total_tokens=sum_tokens(generations),
        total_time=sum_latency(all_observations),
        error=error,
        limit=limit,
        messages=messages,
        events=events,
        metadata=metadata,
    )


# Re-exports
__all__ = ["langfuse", "LANGFUSE_SOURCE_TYPE", "detect_provider_format"]
