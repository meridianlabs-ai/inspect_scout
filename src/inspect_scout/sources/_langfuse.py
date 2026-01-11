"""LangFuse transcript import functionality.

This module provides functions to import transcripts from LangFuse
into an Inspect Scout transcript database.
"""

from datetime import datetime
from logging import getLogger
from typing import Any, AsyncIterator, Callable, TypeVar

from inspect_ai.model._chat_message import (
    ChatMessage,
    ChatMessageUser,
)
from inspect_ai.model._model_output import ModelOutput, ModelUsage
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from inspect_scout._transcript.types import Transcript

logger = getLogger(__name__)

T = TypeVar("T")


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

        def _list_traces(qp: dict[str, Any] = query_params) -> Any:
            return langfuse_client.api.trace.list(**qp)

        response = _retry_api_call(_list_traces)

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

            full_session = _retry_api_call(_get_session)
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
    all_observations.sort(key=lambda o: o.start_time)

    if not all_observations:
        return None

    # Convert observations to Scout events by type
    events = await _observations_to_events(all_observations)

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
        best_resp_gen = _find_best_responses_api_generation(generations)
        if best_resp_gen is not None:
            resp_idx, resp_gen = best_resp_gen
            final_model = model_events[-1]

            # Extract base messages from Responses API format (has system/user)
            base_messages = await _extract_input_messages(
                resp_gen.input, "openai_responses"
            )

            # If final generation is different, merge additional messages from it
            if resp_idx != len(generations) - 1:
                final_messages = list(final_model.input)
                messages = _merge_transcript_messages(base_messages, final_messages)
            else:
                messages = base_messages

            # Always add final output message
            if final_model.output and final_model.output.message:
                messages.append(final_model.output.message)
        else:
            # Build messages from events - this captures the full conversation
            # including all model outputs (with reasoning, tool calls) and tool results
            messages = _build_messages_from_events(events)

    # Get metadata from first trace
    first_trace = traces[0] if traces else None

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
        date=str(session.created_at) if hasattr(session, "created_at") else None,
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
    # Get list of projects from API (with retry for transient errors)
    try:
        projects_response = _retry_api_call(lambda: langfuse_client.api.projects.get())
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

    Detection priority:
    1. OpenAI Responses API: input has "input" key with typed messages
    2. Native OpenAI Chat Completions: output has "choices"
    3. Native Google: output has "candidates" OR input has "contents"
    4. OTEL-normalized: output is list with finish_reason (returns "openai")
    5. Anthropic content blocks: messages contain tool_use/tool_result blocks
    6. Model name hints as fallback

    Note: Anthropic OTEL instrumentation may produce OpenAI-like structure but with
    Anthropic-style content blocks (tool_use, tool_result). We detect these and
    return "anthropic" to ensure proper message conversion.

    Args:
        gen: LangFuse generation observation

    Returns:
        Format string: "openai_responses", "openai", "google", "string", or "unknown"
    """
    input_data = gen.input
    output_data = gen.output
    model = gen.model or ""
    model_lower = model.lower()

    # 1. Check for OpenAI Responses API format (special case)
    # Input: {"input": [{"type": "message", ...}]}
    if isinstance(input_data, dict) and "input" in input_data:
        input_items = input_data.get("input", [])
        if isinstance(input_items, list) and input_items:
            first = input_items[0]
            if isinstance(first, dict) and first.get("type") == "message":
                return "openai_responses"

    # Also check output for Responses API format
    # Output: {"output": [{"type": "function_call"|"reasoning"|...}]}
    if isinstance(output_data, dict) and "output" in output_data:
        output_items = output_data.get("output", [])
        if isinstance(output_items, list) and output_items:
            first = output_items[0]
            if isinstance(first, dict) and first.get("type") in [
                "function_call",
                "reasoning",
                "message",
                "web_search_call",
                "file_search_call",
                "computer_call",
            ]:
                return "openai_responses"

    # 2. Check output structure for clear provider signals
    if isinstance(output_data, dict):
        if "choices" in output_data:
            return "openai"
        if "candidates" in output_data:
            return "google"

    # 3. Check for Anthropic content blocks in messages (OTEL may serialize as JSON)
    # This MUST run before the OTEL check since Anthropic OTEL data has finish_reason
    # but also has Anthropic-style content blocks that need special handling
    messages = None
    if isinstance(input_data, dict) and "messages" in input_data:
        messages = input_data["messages"]
    elif isinstance(input_data, list):
        messages = input_data

    if messages and isinstance(messages, list):
        for msg in messages:
            if isinstance(msg, dict) and "content" in msg:
                content = msg["content"]
                # Try parsing JSON string content
                parsed = _parse_json_content(content)
                if _has_anthropic_tool_blocks(parsed):
                    return "anthropic"

    # 4. Check for OTEL-normalized list format (after Anthropic check)
    if isinstance(output_data, list) and output_data:
        first = output_data[0]
        if isinstance(first, dict):
            if "tool_calls" in first or "finish_reason" in first:
                return "openai"

    # 5. Check input structure
    if isinstance(input_data, dict):
        if "contents" in input_data:
            return "google"

    # 6. Fall back to model name hints
    if any(p in model_lower for p in ["gpt-", "o1-", "text-davinci", "text-embedding"]):
        return "openai"
    if "claude" in model_lower:
        return "openai"  # OTEL-normalized
    if "gemini" in model_lower or "palm" in model_lower:
        return "google"

    # 6. Final fallback: check input structure
    if isinstance(input_data, dict) and "messages" in input_data:
        return _detect_from_messages(input_data["messages"])
    if isinstance(input_data, list) and input_data:
        return _detect_from_messages(input_data)
    if isinstance(input_data, str):
        return "string"

    return "unknown"


def _find_best_responses_api_generation(
    generations: list[Any],
) -> tuple[int, Any] | None:
    """Find the last generation with OpenAI Responses API format input.

    The Responses API format has complete message history including system/user
    messages that are often missing from OTEL-captured generations.

    Args:
        generations: List of LangFuse generation observations

    Returns:
        Tuple of (index, generation) or None if no Responses API format found
    """
    # Search backwards to find the last (most complete) one
    for i in range(len(generations) - 1, -1, -1):
        if _detect_provider_format(generations[i]) == "openai_responses":
            return (i, generations[i])
    return None


def _message_key(msg: "ChatMessage") -> tuple[str, str]:
    """Create a key for message deduplication.

    Args:
        msg: ChatMessage to create key for

    Returns:
        Tuple of (role, content_prefix) for deduplication
    """
    content = ""
    if isinstance(msg.content, str):
        content = msg.content[:200]  # First 200 chars for comparison
    elif isinstance(msg.content, list):
        # Extract text from content blocks
        texts = []
        for c in msg.content:
            if hasattr(c, "text"):
                texts.append(c.text)
        content = " ".join(texts)[:200]
    return (msg.role, content)


def _merge_transcript_messages(
    base_messages: list["ChatMessage"],
    additional_messages: list["ChatMessage"],
) -> list["ChatMessage"]:
    """Merge message lists, avoiding duplicates while preserving order.

    Strategy:
    - Start with base_messages (has system/user context from Responses API)
    - Append additional_messages that aren't already present
    - Use message role + content prefix for deduplication

    Args:
        base_messages: Base messages (typically from Responses API format)
        additional_messages: Additional messages to merge (typically from final OTEL)

    Returns:
        Merged list of messages
    """
    if not additional_messages:
        return base_messages

    if not base_messages:
        return additional_messages

    # Create set of keys from base messages for O(1) lookup
    base_keys = {_message_key(msg) for msg in base_messages}

    # Start with base and add unique additional messages
    merged = list(base_messages)

    for msg in additional_messages:
        key = _message_key(msg)
        if key not in base_keys:
            merged.append(msg)
            base_keys.add(key)

    return merged


def _build_messages_from_events(events: list[Any]) -> list[ChatMessage]:
    """Build message list from model events.

    This reconstructs the full conversation using the LAST model event's input
    (which contains the complete conversation history) plus its output.

    For OTEL-instrumented providers (Anthropic, Google, OpenAI):
    - Each model event's input contains the full conversation up to that point
    - The last model event's input has all messages including system, user, and tool
    - OpenAI Responses API is handled separately before this function is called

    Args:
        events: List of events (ModelEvent, ToolEvent, etc.)

    Returns:
        List of ChatMessage objects representing the full conversation
    """
    messages: list[ChatMessage] = []

    # Find model events
    model_events = [e for e in events if getattr(e, "event", "") == "model"]

    if not model_events:
        return messages

    last_model = model_events[-1]

    # Use the last model event's input - it has the complete conversation
    if last_model.input:
        for msg in last_model.input:
            messages.append(msg)

    # Add the output message (the final assistant response)
    if last_model.output and last_model.output.message:
        messages.append(last_model.output.message)

    return messages


def _parse_google_content_repr(s: str) -> dict[str, Any]:
    """Parse Google Content repr string to ContentDict format.

    The Google OTEL instrumentation serializes SDK objects using repr(),
    producing strings like:
        parts=[Part(text='...')] role='user'
        parts=[Part(function_call=FunctionCall(args={...}, name='...'))] role='model'

    This function parses these back into ContentDict format that
    messages_from_google can consume.

    Warning:
        This parsing is inherently fragile as it relies on regex matching
        of repr() output, which is not a stable API. The repr format may
        change between SDK versions. Currently handles:
        - Text parts: Part(text='...')
        - Function calls: Part(function_call=FunctionCall(args={...}, name='...'))
        - Function responses: Part(function_response=FunctionResponse(name='...'))

        Unrecognized patterns will result in empty parts arrays.

    Args:
        s: String representation of Google Content object

    Returns:
        Dict with 'role' and 'parts' keys
    """
    import ast
    import re

    result: dict[str, Any] = {"parts": []}

    # Extract role
    role_match = re.search(r"role='([^']+)'", s)
    if role_match:
        result["role"] = role_match.group(1)

    # Check for text content
    text_match = re.search(r"text='((?:[^'\\]|\\.)*)'", s, re.DOTALL)
    if text_match:
        text = text_match.group(1)
        result["parts"].append({"text": text})
        return result

    # Check for function_call
    fc_match = re.search(
        r"function_call=FunctionCall\(\s*args=(\{[^}]*\})", s, re.DOTALL
    )
    name_match = re.search(r"name='([^']+)'", s)

    if fc_match and name_match:
        args_str = fc_match.group(1)
        name = name_match.group(1)
        try:
            args = ast.literal_eval(args_str)
            result["parts"].append({"function_call": {"name": name, "args": args}})
        except Exception:
            result["parts"].append({"function_call": {"name": name, "args": {}}})
        return result

    # Check for function_response
    fr_name_match = re.search(
        r"function_response=FunctionResponse\(\s*name='([^']+)'", s
    )
    if fr_name_match:
        name = fr_name_match.group(1)
        # Try to extract response content (triple-quoted string)
        resp_match = re.search(
            r"response=\{\s*'content':\s*\"\"\"(.+?)\"\"\"", s, re.DOTALL
        )
        if resp_match:
            content = resp_match.group(1)
            result["parts"].append(
                {"function_response": {"name": name, "response": {"content": content}}}
            )
        else:
            result["parts"].append(
                {"function_response": {"name": name, "response": {}}}
            )
        return result

    return result


def _parse_google_system_instruction(config_str: str) -> str | None:
    """Extract system instruction from Google config repr string.

    Parses the system_instruction=['...', '...'] format from repr output.

    Warning:
        This parsing is inherently fragile as it relies on regex matching
        of repr() output. The format may change between SDK versions.

    Args:
        config_str: String representation of Google GenerateContentConfig

    Returns:
        System instruction text or None
    """
    import re

    # Match system_instruction=['...', '...'] format
    si_match = re.search(r"system_instruction=\[([^\]]+)\]", config_str, re.DOTALL)
    if si_match:
        # Extract all quoted strings
        strings = re.findall(r"'((?:[^'\\]|\\.)*)'", si_match.group(1))
        if strings:
            return "\n".join(strings)
    return None


def _parse_google_tools_from_config(config_str: str) -> list[dict[str, Any]]:
    """Extract tool definitions from Google config repr string.

    The config contains FunctionDeclaration objects like:
        FunctionDeclaration(
            description='...',
            name='bash',
            parameters=Schema(...)
        )

    Warning:
        This parsing is inherently fragile as it relies on regex matching
        of repr() output. Currently only extracts name and description.
        The parameters Schema is complex and difficult to parse from repr,
        so tool parameters are omitted (returned as empty properties/required).

    Args:
        config_str: String representation of Google GenerateContentConfig

    Returns:
        List of tool dicts with name, description, and parameters (always empty)
    """
    import re

    tools: list[dict[str, Any]] = []

    # Find all FunctionDeclaration blocks
    fd_pattern = r"FunctionDeclaration\(\s*description='([^']*)',\s*name='([^']+)'"
    for match in re.finditer(fd_pattern, config_str):
        description = match.group(1)
        name = match.group(2)
        tools.append(
            {
                "name": name,
                "description": description,
                "properties": {},
                "required": [],
            }
        )

    return tools


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


def _extract_text_from_otel_contents(contents: Any) -> str:
    """Extract text content from OTEL contents array.

    OTEL instrumentations may store content as a list of typed objects:
    - [{message_content: {type: "text", text: "..."}}]
    - [{type: "text", text: "..."}]
    - [{type: "input_text", text: "..."}]

    Args:
        contents: List of content objects or string

    Returns:
        Extracted text as a string
    """
    if isinstance(contents, str):
        return contents

    if not isinstance(contents, list):
        return str(contents) if contents else ""

    texts: list[str] = []
    for c in contents:
        if isinstance(c, str):
            texts.append(c)
        elif isinstance(c, dict):
            # Handle nested message_content wrapper
            mc = c.get("message_content", c)
            if isinstance(mc, dict):
                content_type = mc.get("type", "")
                if content_type in ["text", "input_text", "output_text"]:
                    texts.append(mc.get("text", ""))
            elif isinstance(mc, str):
                texts.append(mc)

    return "\n".join(texts) if texts else ""


def _parse_json_content(content: Any) -> Any:
    """Parse content if it's a JSON string containing Anthropic content blocks.

    OTEL instrumentations may serialize Anthropic content blocks as JSON strings.
    This function detects and parses such strings back to structured data.

    Args:
        content: Message content (string, list, or other)

    Returns:
        Parsed list if content was JSON array string, otherwise original content
    """
    if not isinstance(content, str):
        return content

    # Check if it looks like a JSON array
    stripped = content.strip()
    if not (stripped.startswith("[") and stripped.endswith("]")):
        return content

    try:
        import json

        parsed = json.loads(content)
        # Validate it looks like Anthropic content blocks
        if isinstance(parsed, list) and len(parsed) > 0:
            if isinstance(parsed[0], dict) and "type" in parsed[0]:
                return parsed
    except (json.JSONDecodeError, ValueError):
        pass

    return content


def _has_anthropic_tool_blocks(content: Any) -> bool:
    """Check if content contains Anthropic tool_use or tool_result blocks.

    Args:
        content: Message content (list or other)

    Returns:
        True if content contains tool_use or tool_result blocks
    """
    if not isinstance(content, list):
        return False
    return any(
        isinstance(c, dict) and c.get("type") in ("tool_use", "tool_result")
        for c in content
    )


def _normalize_otel_messages_to_openai(messages: Any) -> Any:
    """Normalize OTEL-instrumented messages to proper OpenAI format.

    OTEL instrumentations may produce messages with:
    - Nested 'message' wrapper (OpenAI OTEL): {"message": {"role": "...", ...}}
    - tool_calls that lack 'type' field (OpenAI requires type='function')
    - tool_calls using 'name' instead of nested 'function.name'
    - Missing 'tool_call_id' in tool response messages
    - 'contents' (plural) instead of 'content'

    Args:
        messages: List of message dicts from OTEL instrumentation

    Returns:
        Messages normalized to OpenAI format
    """
    if not isinstance(messages, list):
        return messages

    normalized = []
    for msg in messages:
        # Skip None messages (OpenAI OTEL instrumentation sometimes captures None)
        if msg is None:
            continue

        if not isinstance(msg, dict):
            normalized.append(msg)
            continue

        # Unwrap nested 'message' structure (OpenAI OTEL format)
        if "message" in msg and isinstance(msg["message"], dict):
            msg = msg["message"]

        # Copy the message to avoid mutating the original
        new_msg = dict(msg)

        # Add role if missing but can be inferred
        if "role" not in new_msg:
            # Tool response: has tool_call_id but no role
            if "tool_call_id" in new_msg:
                new_msg["role"] = "tool"
            # Otherwise skip this message as it's malformed
            else:
                continue

        # Convert 'contents' (plural) to 'content' for OpenAI compatibility
        if "contents" in new_msg and "content" not in new_msg:
            contents = new_msg.pop("contents")
            # Try parsing as JSON first (may contain Anthropic tool blocks)
            parsed = _parse_json_content(contents)
            if _has_anthropic_tool_blocks(parsed):
                # Keep structured Anthropic content with tool blocks
                new_msg["content"] = parsed
            else:
                new_msg["content"] = _extract_text_from_otel_contents(contents)

        # Handle 'content' field - may be JSON string or list
        if "content" in new_msg:
            # Try parsing JSON string content
            new_msg["content"] = _parse_json_content(new_msg["content"])
            # Only flatten to text if it's a list without tool blocks
            if isinstance(new_msg["content"], list):
                if not _has_anthropic_tool_blocks(new_msg["content"]):
                    new_msg["content"] = _extract_text_from_otel_contents(
                        new_msg["content"]
                    )

        # Normalize tool_calls in assistant messages
        if new_msg.get("role") == "assistant" and "tool_calls" in new_msg:
            tool_calls = new_msg.get("tool_calls", [])
            if isinstance(tool_calls, list):
                normalized_calls = []
                for tc in tool_calls:
                    if isinstance(tc, dict):
                        # Unwrap nested 'tool_call' wrapper (OpenAI OTEL format)
                        if "tool_call" in tc and isinstance(tc["tool_call"], dict):
                            tc = tc["tool_call"]
                        new_tc = dict(tc)
                        # Add type='function' if missing
                        if "type" not in new_tc:
                            new_tc["type"] = "function"
                        # Convert flat 'name'/'arguments' to nested 'function' structure
                        if "function" not in new_tc and "name" in new_tc:
                            new_tc["function"] = {
                                "name": new_tc.pop("name"),
                                "arguments": new_tc.pop("arguments", "{}"),
                            }
                        normalized_calls.append(new_tc)
                    else:
                        normalized_calls.append(tc)
                new_msg["tool_calls"] = normalized_calls

        # Normalize tool response messages
        if new_msg.get("role") == "tool":
            # Ensure tool_call_id exists
            if "tool_call_id" not in new_msg:
                new_msg["tool_call_id"] = new_msg.get("id", "unknown")

        normalized.append(new_msg)

    return normalized


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
        case "openai_responses":
            from inspect_ai.model import messages_from_openai_responses

            # Responses API: input is a dict with "input" array containing the conversation
            if isinstance(input_data, dict) and "input" in input_data:
                input_items = input_data["input"]
            elif isinstance(input_data, list):
                input_items = input_data
            else:
                return []

            if not input_items:
                return []

            return await messages_from_openai_responses(input_items)
        case "openai":
            from inspect_ai.model import messages_from_openai

            messages = (
                input_data.get("messages", input_data)
                if isinstance(input_data, dict)
                else input_data
            )

            # Transform OTEL-normalized messages to proper OpenAI format
            # OTEL tool_calls lack 'type' field and use 'name' instead of 'function'
            # Also filters out None messages from some OTEL instrumentations
            messages = _normalize_otel_messages_to_openai(messages)

            # Handle empty messages (e.g., OpenAI OTEL may not capture input)
            if not messages:
                return []

            return await messages_from_openai(messages)
        case "anthropic":
            from inspect_ai.model import messages_from_anthropic

            messages = (
                input_data.get("messages", input_data)
                if isinstance(input_data, dict)
                else input_data
            )
            system = input_data.get("system") if isinstance(input_data, dict) else None

            # Handle inline system message in list format (OpenTelemetry instrumentation)
            if isinstance(messages, list) and len(messages) > 0:
                first_msg = messages[0]
                if isinstance(first_msg, dict) and first_msg.get("role") == "system":
                    # Extract system from messages and remove it from the list
                    system = first_msg.get("content", "")
                    messages = messages[1:]

            # Parse JSON string content that contains tool_use/tool_result blocks
            # OTEL instrumentation may serialize Anthropic content blocks as JSON strings
            if isinstance(messages, list):
                for msg in messages:
                    if isinstance(msg, dict) and "content" in msg:
                        msg["content"] = _parse_json_content(msg["content"])

            return await messages_from_anthropic(messages, system)
        case "google":
            from inspect_ai.model import messages_from_google

            contents = (
                input_data.get("contents", input_data)
                if isinstance(input_data, dict)
                else input_data
            )

            # Handle string-serialized contents from Google OTEL instrumentation
            # The instrumentation uses repr() which produces strings like:
            # "parts=[Part(text='...')] role='user'"
            if isinstance(contents, list) and contents:
                if isinstance(contents[0], str) and "parts=" in contents[0]:
                    # Parse repr strings to ContentDict format
                    parsed_contents = []
                    for c in contents:
                        if isinstance(c, str):
                            parsed = _parse_google_content_repr(c)
                            if parsed.get("parts"):
                                parsed_contents.append(parsed)
                    contents = parsed_contents

            # Extract system instruction
            system = None
            if isinstance(input_data, dict):
                # Try direct system_instruction field first
                si = input_data.get("system_instruction")
                if si:
                    if isinstance(si, list):
                        system = "\n".join(str(s) for s in si)
                    elif isinstance(si, str):
                        system = si

                # If not found, try parsing from config repr string
                if not system:
                    config = input_data.get("config")
                    if isinstance(config, str) and "system_instruction=" in config:
                        system = _parse_google_system_instruction(config)

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
    usage_details = getattr(gen, "usage_details", None)
    if not usage_details:
        return None

    return ModelUsage(
        input_tokens=usage_details.get("input", 0),
        output_tokens=usage_details.get("output", 0),
        total_tokens=usage_details.get("total", 0),
    )


def _build_tool_info(
    name: str,
    description: str,
    properties: dict[str, Any] | None = None,
    required: list[str] | None = None,
) -> Any:
    """Build a ToolInfo object with consistent structure.

    Args:
        name: Tool name
        description: Tool description
        properties: Parameter properties dict
        required: List of required parameter names

    Returns:
        ToolInfo object
    """
    from inspect_ai.tool import ToolInfo, ToolParams

    return ToolInfo(
        name=name,
        description=description,
        parameters=ToolParams(
            type="object",
            properties=properties or {},
            required=required or [],
        ),
    )


def _extract_tools(gen: Any) -> list[Any]:
    """Extract tool definitions from generation data.

    Tools can be stored in multiple locations depending on the format:
    - Native OpenAI: gen.input['tools'] (list of tool definitions)
    - Native Google: gen.input['config'] (string with FunctionDeclaration)
    - Anthropic OTEL: metadata.attributes['llm.request.functions.{N}.*']
    - OpenAI OTEL: metadata.attributes['llm.tools.{N}.tool.json_schema']

    Args:
        gen: LangFuse generation observation

    Returns:
        List of ToolInfo objects
    """
    import json

    tools: list[Any] = []
    input_data = getattr(gen, "input", None)

    # Try native OpenAI format: tools in gen.input['tools']
    if isinstance(input_data, dict) and "tools" in input_data:
        input_tools = input_data["tools"]
        if isinstance(input_tools, list):
            for tool in input_tools:
                if not isinstance(tool, dict):
                    continue
                func = tool.get("function", {})
                if not isinstance(func, dict):
                    continue
                name = func.get("name", "")
                if not name:
                    continue
                params = func.get("parameters", {})
                props = params.get("properties", {}) if isinstance(params, dict) else {}
                req = params.get("required", []) if isinstance(params, dict) else []
                tools.append(
                    _build_tool_info(name, func.get("description", ""), props, req)
                )
            if tools:
                return tools

    # Try Google format: tools in gen.input['config'] (serialized as string)
    # Note: Google tool extraction only gets name/description, not parameters
    if isinstance(input_data, dict) and "config" in input_data:
        config = input_data["config"]
        if isinstance(config, str) and "FunctionDeclaration" in config:
            for gt in _parse_google_tools_from_config(config):
                tools.append(
                    _build_tool_info(
                        gt["name"],
                        gt["description"],
                        gt.get("properties"),
                        gt.get("required"),
                    )
                )
            if tools:
                return tools

    # Fall back to metadata attributes (OTEL format)
    metadata = getattr(gen, "metadata", None)
    if not metadata:
        return []

    attributes = metadata.get("attributes", {}) if isinstance(metadata, dict) else {}
    if not attributes:
        return []

    # Try Anthropic OTEL format: llm.request.functions.{N}.*
    i = 0
    while True:
        name = attributes.get(f"llm.request.functions.{i}.name")
        if name is None:
            break
        description = attributes.get(f"llm.request.functions.{i}.description", "")
        schema = attributes.get(f"llm.request.functions.{i}.input_schema", {})
        props = schema.get("properties", {}) if isinstance(schema, dict) else {}
        req = schema.get("required", []) if isinstance(schema, dict) else []
        tools.append(_build_tool_info(name, description, props, req))
        i += 1

    # Try OpenAI OTEL format: llm.tools.{N}.tool.json_schema
    if not tools:
        i = 0
        while True:
            schema_raw = attributes.get(f"llm.tools.{i}.tool.json_schema")
            if schema_raw is None:
                break
            # Parse JSON schema if it's a string
            if isinstance(schema_raw, str):
                try:
                    schema = json.loads(schema_raw)
                except json.JSONDecodeError:
                    i += 1
                    continue
            elif isinstance(schema_raw, dict):
                schema = schema_raw
            else:
                i += 1
                continue
            name = schema.get("name", "")
            if name:
                params = schema.get("parameters", {})
                props = params.get("properties", {}) if isinstance(params, dict) else {}
                req = params.get("required", []) if isinstance(params, dict) else []
                tools.append(
                    _build_tool_info(name, schema.get("description", ""), props, req)
                )
            i += 1

    return tools


def _extract_otel_output(
    output_data: list[Any], model_name: str, gen: Any
) -> ModelOutput:
    """Extract output from OTEL-normalized format.

    Note: This function handles similar OTEL patterns as _normalize_otel_messages_to_openai()
    but constructs a ModelOutput directly. The patterns are kept separate because input
    normalization prepares data for messages_from_openai(), while this builds the final output.

    OTEL instrumentations normalize provider outputs in different formats:

    Anthropic OTEL format:
    - `[{content, role, finish_reason, tool_calls}]`
    - `tool_calls` is `[{id, name, arguments}]`

    OpenAI OTEL format:
    - `[{message: {role, contents, tool_calls}}]`
    - `contents` is `[{message_content: {type, text}}]`
    - `tool_calls` is `[{tool_call: {id, function: {name, arguments}}}]`

    Args:
        output_data: List of message dicts from OTEL instrumentation
        model_name: Model name for the output
        gen: Generation observation for usage data

    Returns:
        ModelOutput object
    """
    import json

    from inspect_ai.model import (
        ChatMessageAssistant,
        ModelOutput,
        StopReason,
    )
    from inspect_ai.model._model_output import ChatCompletionChoice
    from inspect_ai.tool import ToolCall

    if not output_data:
        return ModelOutput.from_content(model=model_name, content="")

    # Take the first message (typically there's only one)
    msg = output_data[0]
    if not isinstance(msg, dict):
        return ModelOutput.from_content(model=model_name, content=str(output_data))

    # Handle nested 'message' wrapper (OpenAI OTEL format)
    if "message" in msg and isinstance(msg["message"], dict):
        msg = msg["message"]

    # Extract content - handle both 'content' and 'contents' (plural, OpenAI OTEL)
    content = ""
    if "content" in msg:
        raw_content = msg["content"]
        if isinstance(raw_content, str):
            content = raw_content
        elif raw_content:
            content = str(raw_content)
    elif "contents" in msg:
        # OpenAI OTEL: contents is list of {message_content: {type, text}}
        contents = msg.get("contents", [])
        if isinstance(contents, list):
            texts = []
            for c in contents:
                if isinstance(c, dict):
                    mc = c.get("message_content", c)
                    if isinstance(mc, dict) and mc.get("type") == "text":
                        texts.append(mc.get("text", ""))
            content = "\n".join(texts)

    # Extract tool calls - handle both flat and nested formats
    tool_calls: list[ToolCall] = []
    raw_tool_calls = msg.get("tool_calls", [])
    if isinstance(raw_tool_calls, list):
        for tc in raw_tool_calls:
            if isinstance(tc, dict):
                # OpenAI OTEL: nested {tool_call: {id, function: {name, arguments}}}
                if "tool_call" in tc and isinstance(tc["tool_call"], dict):
                    tc = tc["tool_call"]

                tc_id = tc.get("id", "")
                tc_args: dict[str, Any] = {}

                # Get function name and arguments
                if "function" in tc and isinstance(tc["function"], dict):
                    tc_name = tc["function"].get("name", "")
                    tc_args_raw = tc["function"].get("arguments", "{}")
                else:
                    # Flat format (Anthropic OTEL)
                    tc_name = tc.get("name", "")
                    tc_args_raw = tc.get("arguments", "{}")

                # Parse arguments (may be JSON string)
                if isinstance(tc_args_raw, str):
                    try:
                        tc_args = json.loads(tc_args_raw)
                    except json.JSONDecodeError:
                        tc_args = {"raw": tc_args_raw}
                elif isinstance(tc_args_raw, dict):
                    tc_args = tc_args_raw

                if tc_name:
                    tool_calls.append(
                        ToolCall(
                            id=tc_id,
                            function=tc_name,
                            arguments=tc_args,
                            type="function",
                        )
                    )

    # Map finish_reason to StopReason
    finish_reason = msg.get("finish_reason", "stop")
    stop_reason: StopReason
    if finish_reason in ["tool_use", "tool_calls"]:
        stop_reason = "tool_calls"
    elif finish_reason == "length":
        stop_reason = "max_tokens"
    elif finish_reason == "content_filter":
        stop_reason = "content_filter"
    else:
        stop_reason = "stop"

    # Build assistant message
    assistant_msg = ChatMessageAssistant(
        content=content,
        tool_calls=tool_calls if tool_calls else None,
    )

    # Wrap in ChatCompletionChoice
    choice = ChatCompletionChoice(
        message=assistant_msg,
        stop_reason=stop_reason,
    )

    # Build output
    output = ModelOutput(
        model=model_name,
        choices=[choice],
    )

    # Add usage if available
    usage = _extract_usage(gen)
    if usage:
        output.usage = usage

    return output


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
            case "openai_responses":
                from inspect_ai.model import model_output_from_openai_responses

                # OpenAI Responses API: output_data is the full Response object
                return await model_output_from_openai_responses(output_data)
            case "openai":
                from inspect_ai.model import model_output_from_openai

                # Handle OTEL-normalized format: output is a list with message dicts
                # This format doesn't match OpenAI schema, so handle it specially
                if isinstance(output_data, list) and len(output_data) > 0:
                    first = output_data[0]
                    if isinstance(first, dict) and "finish_reason" in first:
                        return _extract_otel_output(output_data, model_name, gen)

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

    # Build GenerateConfig from model_parameters
    params = gen.model_parameters or {}
    config = GenerateConfig(
        temperature=params.get("temperature"),
        max_tokens=params.get("max_tokens"),
        top_p=params.get("top_p"),
        stop_seqs=params.get("stop"),
    )

    return ModelEvent(
        model=gen.model or "unknown",
        input=input_messages,
        tools=_extract_tools(gen),
        tool_choice="auto",
        config=config,
        output=output,
        timestamp=gen.start_time,
        completed=gen.end_time,
        span_id=getattr(gen, "parent_observation_id", None),
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
            type="unknown", message=getattr(obs, "status_message", "Unknown error")
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
        timestamp=obs.start_time,
        completed=obs.end_time,
        error=error,
        span_id=getattr(obs, "parent_observation_id", None),
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
        parent_id=getattr(obs, "parent_observation_id", None),
        timestamp=obs.start_time,
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
        timestamp=obs.end_time,
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
        timestamp=obs.start_time,
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
                if obs.end_time:
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
        usage = getattr(g, "usage_details", None)
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

    if getattr(trace, "user_id", None):
        metadata["user_id"] = trace.user_id
    if getattr(trace, "session_id", None):
        metadata["session_id"] = trace.session_id
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


def _is_retryable_error(exception: BaseException) -> bool:
    """Check if an exception is retryable (timeout, rate limit, server error).

    Args:
        exception: The exception to check

    Returns:
        True if the error is transient and should be retried
    """
    # Import httpx types if available
    try:
        import httpx

        if isinstance(exception, (httpx.TimeoutException, httpx.ConnectError)):
            return True
        if isinstance(exception, httpx.HTTPStatusError):
            # Retry on rate limits (429) and server errors (5xx)
            return exception.response.status_code in (429, 500, 502, 503, 504)
    except ImportError:
        pass

    # Check for generic timeout/connection errors by name
    exc_name = type(exception).__name__
    if "Timeout" in exc_name or "ConnectionError" in exc_name:
        return True

    return False


def _retry_api_call(func: Callable[[], T]) -> T:
    """Execute a LangFuse API call with retry logic for transient errors.

    Retries up to 3 times with exponential backoff (1s, 2s, 4s) on:
    - Network timeouts (httpx.TimeoutException)
    - Connection errors (httpx.ConnectError)
    - Rate limits (HTTP 429)
    - Server errors (HTTP 5xx)

    Args:
        func: Zero-argument callable that makes the API call

    Returns:
        The result of the API call

    Raises:
        The original exception if all retries fail or error is not retryable
    """

    def _log_retry(retry_state: Any) -> None:
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        exc_name = type(exc).__name__ if exc else "Unknown"
        sleep_time = retry_state.next_action.sleep if retry_state.next_action else 0
        logger.warning(
            f"LangFuse API call failed ({exc_name}), "
            f"retrying in {sleep_time:.1f}s... "
            f"(attempt {retry_state.attempt_number}/3)"
        )

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=_log_retry,
        reraise=True,
    )
    def _call_with_retry() -> T:
        try:
            return func()
        except Exception as e:
            if _is_retryable_error(e):
                raise
            # Non-retryable errors should not be retried
            raise e from None

    return _call_with_retry()
