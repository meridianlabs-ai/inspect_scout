"""ATIF event and message conversion helpers.

Pure helpers called by `_create_transcript` in transcripts.py. No
orchestration or recursion lives here — those are in transcripts.py
(matching CC's `_claude_code/transcripts.py` ↔ `events.py` split).

harbor's trajectory models are used only as type annotations here (the
`Step`/`ContentPart` objects are constructed by transcripts.py when it
parses a `Trajectory`), so this module never imports harbor at runtime.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from logging import getLogger
from pathlib import Path
from typing import TYPE_CHECKING, Any

from inspect_ai.event import CompactionEvent, ModelEvent
from inspect_ai.model import (
    ChatCompletionChoice,
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageTool,
    ChatMessageUser,
    Content,
    ContentImage,
    ContentReasoning,
    ContentText,
    GenerateConfig,
    ModelOutput,
    ModelUsage,
)
from inspect_ai.tool import ToolCall

if TYPE_CHECKING:
    from harbor.models.trajectories import ContentPart, Step

logger = getLogger(__name__)


def to_model_event(
    step: "Step",
    prior_messages: list[ChatMessage],
    new_messages: list[ChatMessage],
) -> ModelEvent | None:
    """Convert an ATIF agent step to a `ModelEvent`.

    Sentinel values fill in fields ATIF doesn't carry (`tools=[]`,
    `tool_choice="auto"`, `config=GenerateConfig()`). Returns None when the
    step carries no `metrics` (no real LLM call to model).
    """
    if step.metrics is None:
        return None

    assistant_msg = next(
        (m for m in new_messages if isinstance(m, ChatMessageAssistant)),
        None,
    )
    if assistant_msg is None:
        return None

    prompt_tokens = step.metrics.prompt_tokens or 0
    completion_tokens = step.metrics.completion_tokens or 0
    # harbor's `prompt_tokens` INCLUDES cached tokens; inspect_ai's `input_tokens`
    # EXCLUDES them (true total = input + cache_read + cache_write + output), so
    # subtract cached to avoid double-counting.
    cached_tokens = step.metrics.cached_tokens or 0
    usage = ModelUsage(
        input_tokens=prompt_tokens - cached_tokens,
        output_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        input_tokens_cache_read=step.metrics.cached_tokens,
        total_cost=step.metrics.cost_usd,
    )

    model_name = step.model_name or "unknown"
    timestamp = _parse_timestamp(step.timestamp) or utcnow()

    output = ModelOutput(
        model=model_name,
        choices=[ChatCompletionChoice(message=assistant_msg)],
        usage=usage,
        metadata={"atif_synthesized": True},
    )

    return ModelEvent(
        model=model_name,
        input=list(prior_messages),
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
        output=output,
        timestamp=timestamp,
    )


def to_compaction_event(step: "Step") -> CompactionEvent:
    """Convert an ATIF context-management step to a `CompactionEvent`.

    Following the existing producers (claude_code, codex_cli), `type` is left at
    its default ("summary") and the ATIF `context_management` dict (`type`,
    `boundary`) is preserved in `metadata` rather than mapped onto inspect_ai's
    disjoint `{summary, edit, trim}` enum.
    """
    return CompactionEvent(
        source="atif",
        metadata=(step.extra or {}).get("context_management") or None,
        timestamp=_parse_timestamp(step.timestamp) or utcnow(),
    )


def step_to_messages(
    step: "Step",
    tool_call_funcs: dict[str, str],
    parent_path: Path | None = None,
) -> list[ChatMessage]:
    """Convert one ATIF step to a list of ChatMessages.

    A single step can yield multiple messages: the step's own message
    (system/user/assistant) plus one `ChatMessageTool` per
    `observation.results[]` entry.
    """
    msgs: list[ChatMessage] = []
    content = _extract_content_blocks(
        step.message, step.reasoning_content, parent_path=parent_path
    )

    if step.source == "system":
        msgs.append(ChatMessageSystem(content=content))
    elif step.source == "user":
        msgs.append(ChatMessageUser(content=content))
    elif step.source == "agent":
        tool_calls: list[ToolCall] | None = None
        if step.tool_calls:
            tool_calls = [
                ToolCall(
                    id=tc.tool_call_id,
                    function=tc.function_name,
                    arguments=tc.arguments,
                )
                for tc in step.tool_calls
            ]
        msgs.append(
            ChatMessageAssistant(
                content=content,
                tool_calls=tool_calls,
                model=step.model_name,
            )
        )

    if step.observation is not None:
        for result in step.observation.results:
            tool_call_id = result.source_call_id or ""
            function = tool_call_funcs.get(tool_call_id, "unknown")
            msgs.append(
                ChatMessageTool(
                    tool_call_id=tool_call_id,
                    function=function,
                    content=_extract_content_blocks(
                        result.content, parent_path=parent_path
                    ),
                )
            )

    return msgs


def _extract_content_blocks(
    message: "str | list[ContentPart] | None",
    reasoning: str | None = None,
    parent_path: Path | None = None,
) -> str | list[Content]:
    """Extract text and image content blocks from ATIF message content.

    `reasoning` is optional and, when present, prepended as a
    `ContentReasoning` part — forces a multipart return.

    Image parts are read from `parent_path.parent / item.source.path` and
    base64-encoded into a data URI. Images are skipped (with a warning) when
    `parent_path` is None or the file can't be read.
    """
    blocks: list[Content] = []

    if reasoning:
        blocks.append(ContentReasoning(reasoning=reasoning))

    if isinstance(message, str):
        if not blocks:
            return message
        blocks.append(ContentText(text=message))
    elif isinstance(message, list):
        for item in message:
            if item.type == "text" and item.text is not None:
                blocks.append(ContentText(text=item.text))
            elif item.type == "image" and item.source is not None:
                data_uri = _image_as_data_uri(item.source, parent_path)
                if data_uri is not None:
                    blocks.append(ContentImage(image=data_uri))
            else:
                logger.warning("Unrecognized ATIF ContentPart: type=%r", item.type)
    elif message is None:
        # No content (e.g., observation result with only subagent_trajectory_ref)
        pass

    return blocks if blocks else ""


def _image_as_data_uri(
    source: Any,
    parent_path: Path | None,
) -> str | None:
    """Read an ATIF image file and return a base64 data URI."""
    if parent_path is None:
        logger.warning(
            "ATIF image cannot be resolved without parent_path: %s", source.path
        )
        return None
    base = parent_path.parent.resolve()
    image_path = (base / source.path).resolve()
    # Contain reads to the trajectory directory: `source.path` comes straight
    # from the (untrusted) trajectory file, so `../…` or an absolute path could
    # otherwise read arbitrary local files into the transcript DB.
    if not image_path.is_relative_to(base):
        logger.warning(
            "ATIF image path escapes the trajectory directory, skipping: %s",
            source.path,
        )
        return None
    try:
        data = base64.b64encode(image_path.read_bytes()).decode("ascii")
    except OSError as e:
        logger.warning("ATIF image not loadable %s: %s", image_path, e)
        return None
    return f"data:{source.media_type};base64,{data}"


def _parse_timestamp(ts_str: str | None) -> datetime | None:
    """Parse an ISO 8601 timestamp string to a tz-aware UTC datetime.

    Handles the common 'Z' suffix.

    Args:
        ts_str: ISO format timestamp string (with optional 'Z' suffix)

    Returns:
        Parsed UTC datetime, or None if parsing fails or input is empty
    """
    if not ts_str:
        return None
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except ValueError:
        logger.warning("Invalid ATIF timestamp: %r", ts_str)
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
