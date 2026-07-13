"""Value coercion from OpenClaw content/usage structures into Inspect shapes.

Shared by the OpenClaw importers (``_telemetry_hal`` and ``_sessions``): both
formats carry the same message ``content`` block shapes (``text`` / ``thinking``
/ ``image`` / ``toolCall``) and the same ``usage`` keys. Stateless helpers that
pull a value out of a single raw OpenClaw structure; they hold no importer-wide
state and do no structural reconstruction — that belongs to each importer's
``parse`` module.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from inspect_ai.model import Content, ContentImage, ContentReasoning, ContentText
from inspect_ai.tool import ToolCall, ToolCallContent


def usage_to_inspect(usage: dict[str, Any] | None) -> dict[str, int]:
    """Rename OpenClaw ``usage`` keys to Inspect ``ModelUsage`` field names.

    ``total_tokens`` is computed as ``input + output + cacheRead + cacheWrite``
    (see :func:`tokens_from_usage`) rather than trusting the raw
    ``totalTokens``: the two usually agree, but raw ``totalTokens`` has been
    observed to exclude cache tokens on some turns of native session captures.

    NB OpenClaw's ``input`` is the *uncached/new* input only (exclusive-cache
    semantics). ``reasoning_tokens`` is left 0: OpenClaw *does* emit thinking
    blocks (surfaced as ``ContentReasoning``; see :func:`content_blocks`) but
    reports no separate reasoning-token count — reasoning is folded into
    ``output``, so it is already counted, just not broken out. ``cost`` is
    dropped (Inspect ``ModelUsage`` has no cost field).
    """
    usage = usage or {}
    return {
        "input_tokens": int(usage.get("input") or 0),
        "output_tokens": int(usage.get("output") or 0),
        "total_tokens": tokens_from_usage(usage),
        "input_tokens_cache_write": int(usage.get("cacheWrite") or 0),
        "input_tokens_cache_read": int(usage.get("cacheRead") or 0),
        "reasoning_tokens": 0,
    }


def tokens_from_usage(usage: dict[str, Any] | None) -> int:
    """Per-call token total for a turn = ``input + output + cacheRead + cacheWrite``.

    This is the conventional total used by the other Scout importers (e.g.
    ``claude_code`` sums each model call's ``ModelUsage.total_tokens``, which for
    Anthropic includes cache reads). Each of the four fields is a genuine per-call
    billed quantity, so summing them over deduped turns yields the true token
    spend — the basis for the transcript's headline ``total_tokens``.
    """
    usage = usage or {}
    inp = int(usage.get("input") or 0)
    out = int(usage.get("output") or 0)
    cr = int(usage.get("cacheRead") or 0)
    cw = int(usage.get("cacheWrite") or 0)
    return inp + out + cr + cw


def content_to_text(content: Any) -> str:
    """Flatten an OpenClaw message ``content`` (str | list[block]) to plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text" and block.get("text"):
                    parts.append(str(block["text"]))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return ""


def content_blocks(content: Any) -> list[Content]:
    """Map an OpenClaw message ``content`` to Inspect ``Content`` blocks.

    Preserves ``text`` (-> ``ContentText``), ``thinking`` (-> ``ContentReasoning``,
    carrying the ``thinkingSignature``) and ``image`` (-> ``ContentImage`` as a
    base64 data URI). ``toolCall`` blocks are surfaced separately as Inspect
    ``ToolCall``s (see :func:`toolcalls_of`) and are skipped here. A bare string
    becomes a single text block.
    """
    if isinstance(content, str):
        return [ContentText(text=content)] if content else []
    if not isinstance(content, list):
        return []
    blocks: list[Content] = []
    for block in content:
        if isinstance(block, str):
            if block:
                blocks.append(ContentText(text=block))
            continue
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        if btype == "text":
            text = block.get("text")
            if text:
                blocks.append(ContentText(text=str(text)))
        elif btype == "thinking":
            thinking = block.get("thinking")
            if thinking:
                signature = block.get("thinkingSignature")
                blocks.append(
                    ContentReasoning(
                        reasoning=str(thinking),
                        signature=str(signature) if signature else None,
                    )
                )
        elif btype == "image":
            data = block.get("data")
            if data:
                mime = block.get("mimeType") or "image/png"
                blocks.append(ContentImage(image=f"data:{mime};base64,{data}"))
    return blocks


def toolcalls_of(content: Any) -> list[dict[str, Any]]:
    """The raw OpenClaw ``toolCall`` blocks within an assistant ``content``.

    ``toolCall`` blocks are ``{type:"toolCall", id, name, arguments}``; they are
    surfaced as Inspect ``ToolCall``s, separate from the message ``content``.
    """
    if not isinstance(content, list):
        return []
    return [
        block
        for block in content
        if isinstance(block, dict) and block.get("type") == "toolCall"
    ]


def rich_or_text(content: Any) -> str | list[Content]:
    """Structured ``Content`` blocks for non-text content, else plain text.

    Returns ``Content`` blocks when the content carries non-text parts
    (images/reasoning) and a flattened string otherwise.

    Tool results and user prompts are text in the common case; only when an
    image (e.g. a screenshot tool result) or a reasoning block is present do
    they need the list form. Returning ``str`` otherwise keeps the overwhelming
    majority of turns as simple text.
    """
    blocks = content_blocks(content)
    if any(not isinstance(block, ContentText) for block in blocks):
        return blocks
    return content_to_text(content)


def ts_to_datetime(value: Any) -> datetime | None:
    """Convert an OpenClaw epoch-millisecond timestamp to a UTC ``datetime``."""
    if value is None:
        return None
    try:
        ms = int(value)
    except (TypeError, ValueError):
        return None
    if ms <= 0:
        return None
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)


def short_description(task: str | None, limit: int = 80) -> str | None:
    """First line of a spawn ``task``, trimmed for use as a span description."""
    if not task:
        return None
    first = task.strip().splitlines()[0].strip() if task.strip() else ""
    if len(first) > limit:
        first = first[: limit - 1].rstrip() + "…"
    return first or None


def tool_call_view(function: str, arguments: dict[str, Any]) -> ToolCallContent | None:
    """Custom rendering for known OpenClaw tools (mirrors Claude Code's views).

    A ``sessions_spawn`` is rendered as an ``Agent: <label>`` block with the
    delegated ``task`` as the body — the ``{{task}}`` placeholder is filled from
    the call's arguments by the viewer, exactly as Claude Code's Task/Agent view
    fills ``{{description}}``/``{{prompt}}``. Other tools have no custom view.
    """
    if function != "sessions_spawn":
        return None
    label = str(arguments.get("label") or "")
    return ToolCallContent(
        title=f"Agent: {label}" if label else "Agent",
        format="markdown",
        content="{{task}}",
    )


def to_tool_call(tc: dict[str, Any]) -> ToolCall:
    """Build an Inspect ``ToolCall`` from a raw OpenClaw ``toolCall`` block.

    Carries a custom ``view`` for tools that have one (see
    :func:`tool_call_view`) so the model-call rendering matches Claude Code's.
    """
    function = str(tc.get("name") or "unknown")
    arguments = tc.get("arguments") or {}
    arguments = arguments if isinstance(arguments, dict) else {}
    return ToolCall(
        id=str(tc.get("id") or ""),
        function=function,
        arguments=arguments,
        view=tool_call_view(function, arguments),
    )
