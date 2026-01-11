"""LangFuse transcript import functionality.

This module provides functions to import transcripts from LangFuse
into an Inspect Scout transcript database.
"""

from datetime import datetime
from logging import getLogger
from typing import Any, AsyncIterator

from inspect_ai.model._chat_message import (
    ChatMessage,
    ChatMessageUser,
)
from inspect_ai.model._model_output import ModelOutput, ModelUsage

from inspect_scout._transcript.types import Transcript

logger = getLogger(__name__)

# LangFuse source type constant
LANGFUSE_SOURCE_TYPE = "langfuse"


async def langfuse(
    project: str | None = None,
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
    langfuse_client = _get_langfuse_client(public_key, secret_key, host)

    # Resolve project name to ID if needed
    project_id = _resolve_project_id(langfuse_client, project) if project else None

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

        response = langfuse_client.api.trace.list(**query_params)

        for trace in response.data:
            session_id = getattr(trace, "sessionId", None)
            if session_id:
                session_ids.add(session_id)

        # Check if we've fetched all pages
        meta = getattr(response, "meta", None)
        if meta and page >= meta.totalPages:
            break
        page += 1

    # For each unique session, fetch full details and convert
    count = 0
    for session_id in session_ids:
        try:
            full_session = langfuse_client.api.sessions.get(session_id)
            transcript = await _session_to_transcript(
                full_session, langfuse_client, project_id, host
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
    project_id: str | None = None,
    host: str | None = None,
) -> Transcript | None:
    """Convert a LangFuse session to a Scout Transcript.

    Args:
        session: LangFuse session object with traces
        langfuse_client: LangFuse client for fetching trace details
        project_id: LangFuse project ID for URL construction
        host: LangFuse host URL for URL construction

    Returns:
        Transcript object or None if session has no valid data
    """
    # Collect all observations across all traces
    all_observations: list[Any] = []
    traces = getattr(session, "traces", [])

    for trace in traces:
        # Fetch full trace with observations
        full_trace = langfuse_client.api.trace.get(trace.id)
        observations = getattr(full_trace, "observations", [])
        all_observations.extend(observations)

    # Sort chronologically
    all_observations.sort(key=lambda o: o.startTime)

    if not all_observations:
        return None

    # Convert observations to Scout events by type
    events = await _observations_to_events(all_observations)

    # Find the last ModelEvent for messages
    model_events = [e for e in events if getattr(e, "event", "") == "model"]
    messages: list[ChatMessage] = []

    if model_events:
        final_model = model_events[-1]
        messages = list(final_model.input)
        if final_model.output and final_model.output.message:
            messages.append(final_model.output.message)

    # Get metadata from first trace
    first_trace = traces[0] if traces else None
    generations = [
        o for o in all_observations if getattr(o, "type", "") == "GENERATION"
    ]

    # Construct source URI
    base_url = (host or "https://cloud.langfuse.com").rstrip("/")
    if project_id:
        source_uri = f"{base_url}/project/{project_id}/sessions/{session.id}"
    else:
        source_uri = f"{base_url}/sessions/{session.id}"

    return Transcript(
        transcript_id=session.id,
        source_type=LANGFUSE_SOURCE_TYPE,
        source_id=session.id,
        source_uri=source_uri,
        date=str(session.createdAt) if hasattr(session, "createdAt") else None,
        task_id=getattr(first_trace, "name", None) if first_trace else None,
        model=generations[0].model if generations else None,
        total_tokens=_sum_tokens(generations),
        total_time=_sum_latency(all_observations),
        messages=messages,
        events=events,
        metadata=_extract_metadata(first_trace),
    )


def _get_langfuse_client(
    public_key: str | None = None,
    secret_key: str | None = None,
    host: str | None = None,
) -> Any:
    """Get or create a LangFuse client.

    Args:
        public_key: LangFuse public key (or use LANGFUSE_PUBLIC_KEY env var)
        secret_key: LangFuse secret key (or use LANGFUSE_SECRET_KEY env var)
        host: LangFuse host URL (or use LANGFUSE_HOST env var)

    Returns:
        LangFuse client instance

    Raises:
        ImportError: If langfuse package is not installed
    """
    try:
        from langfuse import Langfuse
    except ImportError as e:
        raise ImportError(
            "The langfuse package is required for LangFuse import. "
            "Install it with: pip install langfuse"
        ) from e

    kwargs: dict[str, Any] = {}
    if public_key:
        kwargs["public_key"] = public_key
    if secret_key:
        kwargs["secret_key"] = secret_key
    if host:
        kwargs["host"] = host

    return Langfuse(**kwargs)


def _resolve_project_id(langfuse_client: Any, project: str) -> str:
    """Resolve a project name or ID to a project ID.

    Args:
        langfuse_client: LangFuse client instance
        project: Project name or ID

    Returns:
        The project ID

    Raises:
        ValueError: If the project cannot be found
    """
    # Get list of projects from API
    try:
        projects_response = langfuse_client.api.projects.get()
        projects = getattr(projects_response, "data", [])
    except Exception as e:
        logger.warning(f"Failed to fetch projects list: {e}")
        # Fall back to using the value as-is (assume it's an ID)
        return project

    # First check if it matches any project ID
    for proj in projects:
        if getattr(proj, "id", None) == project:
            return project

    # Then check if it matches any project name
    for proj in projects:
        if getattr(proj, "name", None) == project:
            return str(proj.id)

    # If no match found, raise an error with available projects
    available = [
        f"{getattr(p, 'name', 'unknown')} ({getattr(p, 'id', 'unknown')})"
        for p in projects
    ]
    raise ValueError(
        f"Project '{project}' not found. Available projects: {', '.join(available)}"
    )


def _detect_provider_format(gen: Any) -> str:
    """Detect the provider format from generation data.

    Uses multiple signals: model name, output structure, input structure.

    Args:
        gen: LangFuse generation observation

    Returns:
        Provider format string: "openai", "anthropic", "google", "string", or "unknown"
    """
    input_data = gen.input
    output_data = gen.output
    model = gen.model or ""

    # 1. Model name is most reliable if available
    model_lower = model.lower()
    if any(p in model_lower for p in ["gpt-", "o1-", "text-davinci", "text-embedding"]):
        return "openai"
    if "claude" in model_lower:
        return "anthropic"
    if "gemini" in model_lower or "palm" in model_lower:
        return "google"

    # 2. Check output structure (often more standardized than input)
    if isinstance(output_data, dict):
        if "choices" in output_data:
            return "openai"
        if "candidates" in output_data:
            return "google"
        if "stop_reason" in output_data and isinstance(
            output_data.get("content"), list
        ):
            return "anthropic"

    # 3. Check input structure
    if isinstance(input_data, dict):
        if "messages" in input_data:
            return _detect_from_messages(input_data["messages"])
        if "contents" in input_data:
            return "google"

    if isinstance(input_data, list) and len(input_data) > 0:
        return _detect_from_messages(input_data)

    if isinstance(input_data, str):
        return "string"

    return "unknown"


def _detect_from_messages(messages: list[Any]) -> str:
    """Detect format from message list structure.

    Args:
        messages: List of message objects

    Returns:
        Provider format string
    """
    if not messages or not isinstance(messages[0], dict):
        return "unknown"

    first = messages[0]

    # Google: uses "parts" instead of "content", or role="model"
    if "parts" in first:
        return "google"
    if first.get("role") == "model":
        return "google"

    # Now distinguish OpenAI vs Anthropic
    # Both use role + content, but content structure differs
    content = first.get("content")

    if content is None:
        return "unknown"

    # String content → OpenAI (Anthropic always uses list)
    if isinstance(content, str):
        return "openai"

    # List content → need to check block types
    if isinstance(content, list) and len(content) > 0:
        block = content[0]
        if isinstance(block, dict):
            block_type = block.get("type")
            # Anthropic-specific types
            if block_type in ["tool_use", "tool_result"]:
                return "anthropic"
            # OpenAI-specific types
            if block_type == "image_url":
                return "openai"
            # Anthropic image format has "source" object
            if block_type == "image" and "source" in block:
                return "anthropic"
            # Both have "text" type - check other messages for distinguishing types
            if block_type == "text":
                for msg in messages:
                    msg_content = msg.get("content")
                    if isinstance(msg_content, list):
                        for b in msg_content:
                            if isinstance(b, dict):
                                if b.get("type") in [
                                    "tool_use",
                                    "tool_result",
                                    "image",
                                ]:
                                    return "anthropic"
                                if b.get("type") == "image_url":
                                    return "openai"
                # Default to Anthropic if content is list (more common case)
                return "anthropic"

    return "openai"  # Default fallback


async def _extract_input_messages(
    input_data: Any, format_type: str
) -> list[ChatMessage]:
    """Extract input messages using format-appropriate converter.

    Args:
        input_data: Raw input data from LangFuse
        format_type: Detected provider format

    Returns:
        List of ChatMessage objects
    """
    # Handle string input regardless of detected format
    if isinstance(input_data, str):
        return [ChatMessageUser(content=input_data)]

    match format_type:
        case "openai":
            from inspect_ai.model import messages_from_openai

            messages = (
                input_data.get("messages", input_data)
                if isinstance(input_data, dict)
                else input_data
            )
            return await messages_from_openai(messages)
        case "anthropic":
            from inspect_ai.model import messages_from_anthropic

            messages = (
                input_data.get("messages", input_data)
                if isinstance(input_data, dict)
                else input_data
            )
            system = input_data.get("system") if isinstance(input_data, dict) else None
            return await messages_from_anthropic(messages, system)
        case "google":
            from inspect_ai.model import messages_from_google

            contents = (
                input_data.get("contents", input_data)
                if isinstance(input_data, dict)
                else input_data
            )
            system = (
                input_data.get("system_instruction")
                if isinstance(input_data, dict)
                else None
            )
            return await messages_from_google(contents, system)
        case "string":
            return [ChatMessageUser(content=str(input_data))]
        case _:
            logger.warning(
                f"Unknown input format, creating simple message: {type(input_data)}"
            )
            return [
                ChatMessageUser(content=str(input_data)[:1000] if input_data else "")
            ]


def _extract_usage(gen: Any) -> ModelUsage | None:
    """Extract model usage from generation observation.

    Args:
        gen: LangFuse generation observation

    Returns:
        ModelUsage object or None
    """
    usage_details = getattr(gen, "usageDetails", None)
    if not usage_details:
        return None

    return ModelUsage(
        input_tokens=usage_details.get("input", 0),
        output_tokens=usage_details.get("output", 0),
        total_tokens=usage_details.get("total", 0),
    )


async def _extract_output(output_data: Any, gen: Any, format_type: str) -> ModelOutput:
    """Extract output using format-appropriate converter.

    Args:
        output_data: Raw output data from LangFuse
        gen: LangFuse generation observation (for usage data)
        format_type: Detected provider format

    Returns:
        ModelOutput object
    """
    model_name = gen.model or "unknown"

    if not output_data:
        return ModelOutput.from_content(model=model_name, content="")

    try:
        match format_type:
            case "openai":
                from inspect_ai.model import model_output_from_openai

                return await model_output_from_openai(output_data)
            case "anthropic":
                from inspect_ai.model import model_output_from_anthropic

                return await model_output_from_anthropic(output_data)
            case "google":
                from inspect_ai.model import model_output_from_google

                return await model_output_from_google(output_data)
            case _:
                # Fallback: extract text content
                content: str
                if isinstance(output_data, dict):
                    raw_content = output_data.get(
                        "content", output_data.get("text", str(output_data))
                    )
                    if isinstance(raw_content, list) and raw_content:
                        # Try to extract text from content blocks
                        texts = []
                        for block in raw_content:
                            if isinstance(block, dict) and "text" in block:
                                texts.append(str(block["text"]))
                            elif isinstance(block, str):
                                texts.append(block)
                        content = "\n".join(texts) if texts else str(output_data)
                    elif isinstance(raw_content, str):
                        content = raw_content
                    else:
                        content = str(raw_content)
                elif isinstance(output_data, str):
                    content = output_data
                else:
                    content = str(output_data)

                output = ModelOutput.from_content(model=model_name, content=content)
                # Add usage if available
                usage = _extract_usage(gen)
                if usage:
                    output.usage = usage
                return output
    except Exception as e:
        logger.warning(f"Failed to parse output: {e}, falling back to string")
        output = ModelOutput.from_content(
            model=model_name, content=str(output_data)[:1000]
        )
        usage = _extract_usage(gen)
        if usage:
            output.usage = usage
        return output


async def _to_model_event(gen: Any) -> Any:
    """Convert LangFuse generation to ModelEvent.

    Args:
        gen: LangFuse generation observation

    Returns:
        ModelEvent object
    """
    from inspect_ai.event import ModelEvent
    from inspect_ai.model._generate_config import GenerateConfig

    # Detect provider format
    format_type = _detect_provider_format(gen)

    # Extract input messages based on detected format
    input_messages = await _extract_input_messages(gen.input, format_type)

    # Extract output based on detected format
    output = await _extract_output(gen.output, gen, format_type)

    # Build GenerateConfig from modelParameters
    params = gen.modelParameters or {}
    config = GenerateConfig(
        temperature=params.get("temperature"),
        max_tokens=params.get("max_tokens"),
        top_p=params.get("top_p"),
        stop_seqs=params.get("stop"),
    )

    return ModelEvent(
        model=gen.model or "unknown",
        input=input_messages,
        tools=[],  # LangFuse doesn't capture tool definitions
        tool_choice="auto",  # Default
        config=config,
        output=output,
        timestamp=gen.startTime,
        completed=gen.endTime,
        span_id=getattr(gen, "parentObservationId", None),
    )


def _to_tool_event(obs: Any) -> Any:
    """Convert LangFuse TOOL observation to ToolEvent.

    Args:
        obs: LangFuse observation

    Returns:
        ToolEvent object
    """
    import uuid

    from inspect_ai.event import ToolEvent
    from inspect_ai.tool._tool_call import ToolCallError

    error = None
    if getattr(obs, "level", None) == "ERROR":
        error = ToolCallError(
            type="unknown", message=getattr(obs, "statusMessage", "Unknown error")
        )

    # Convert result to string if needed
    result = obs.output
    if result is not None and not isinstance(result, str):
        result = str(result)

    return ToolEvent(
        id=obs.id or str(uuid.uuid4()),
        type="function",
        function=obs.name or "unknown_tool",
        arguments=obs.input if isinstance(obs.input, dict) else {},
        result=result or "",
        timestamp=obs.startTime,
        completed=obs.endTime,
        error=error,
        span_id=getattr(obs, "parentObservationId", None),
    )


def _to_span_begin_event(obs: Any) -> Any:
    """Convert LangFuse SPAN/AGENT/CHAIN observation to SpanBeginEvent.

    Args:
        obs: LangFuse observation

    Returns:
        SpanBeginEvent object
    """
    from inspect_ai.event import SpanBeginEvent

    return SpanBeginEvent(
        id=obs.id,
        name=obs.name or obs.type.lower(),
        parent_id=getattr(obs, "parentObservationId", None),
        timestamp=obs.startTime,
        working_start=0.0,  # Required field
        metadata=getattr(obs, "metadata", None),
    )


def _to_span_end_event(obs: Any) -> Any:
    """Convert LangFuse observation end to SpanEndEvent.

    Args:
        obs: LangFuse observation

    Returns:
        SpanEndEvent object
    """
    from inspect_ai.event import SpanEndEvent

    return SpanEndEvent(
        id=obs.id,
        timestamp=obs.endTime,
        metadata=getattr(obs, "metadata", None),
    )


def _to_info_event(obs: Any) -> Any:
    """Convert LangFuse EVENT observation to InfoEvent.

    Args:
        obs: LangFuse observation

    Returns:
        InfoEvent object
    """
    from inspect_ai.event import InfoEvent

    return InfoEvent(
        source=obs.name or "langfuse",
        data=obs.input or obs.output or obs.name or "event",
        timestamp=obs.startTime,
        metadata=getattr(obs, "metadata", None),
    )


async def _observations_to_events(observations: list[Any]) -> list[Any]:
    """Convert LangFuse observations to Scout events by type.

    Args:
        observations: List of LangFuse observations

    Returns:
        List of Scout event objects
    """
    events = []
    for obs in observations:
        obs_type = getattr(obs, "type", "")
        match obs_type:
            case "GENERATION":
                events.append(await _to_model_event(obs))
            case "TOOL":
                events.append(_to_tool_event(obs))
            case "SPAN" | "AGENT" | "CHAIN":
                events.append(_to_span_begin_event(obs))
                if obs.endTime:
                    events.append(_to_span_end_event(obs))
            case "EVENT":
                events.append(_to_info_event(obs))
            # Skip: RETRIEVER, EMBEDDING, GUARDRAIL

    # Sort by timestamp to maintain chronological order
    events.sort(key=lambda e: e.timestamp)
    return events


def _sum_tokens(generations: list[Any]) -> int:
    """Sum tokens across all generations.

    Args:
        generations: List of generation observations

    Returns:
        Total token count
    """
    total = 0
    for g in generations:
        usage = getattr(g, "usageDetails", None)
        if usage:
            total += usage.get("input", 0) + usage.get("output", 0)
    return total


def _sum_latency(observations: list[Any]) -> float:
    """Sum latency across all observations.

    Args:
        observations: List of observations

    Returns:
        Total latency in seconds
    """
    total = 0.0
    for obs in observations:
        latency = getattr(obs, "latency", None)
        if latency:
            total += latency
    return total


def _extract_metadata(trace: Any) -> dict[str, Any]:
    """Extract metadata from trace for Scout transcript.

    Args:
        trace: LangFuse trace object

    Returns:
        Metadata dictionary
    """
    if not trace:
        return {}

    metadata: dict[str, Any] = {}

    if getattr(trace, "userId", None):
        metadata["user_id"] = trace.userId
    if getattr(trace, "sessionId", None):
        metadata["session_id"] = trace.sessionId
    if getattr(trace, "name", None):
        metadata["name"] = trace.name
    if getattr(trace, "tags", None):
        metadata["tags"] = trace.tags
    if getattr(trace, "version", None):
        metadata["version"] = trace.version
    if getattr(trace, "release", None):
        metadata["release"] = trace.release
    if getattr(trace, "environment", None):
        metadata["environment"] = trace.environment

    # Include any custom metadata from the trace
    trace_metadata = getattr(trace, "metadata", None)
    if trace_metadata:
        metadata.update(trace_metadata)

    return metadata
