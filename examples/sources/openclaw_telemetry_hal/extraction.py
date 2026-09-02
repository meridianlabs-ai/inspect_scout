"""Value coercion from OpenClaw telemetry-hal content/usage into Inspect shapes.

Stateless helpers that pull a value out of a single raw OpenClaw structure
(a ``usage`` dict, a message ``content``). They hold no telemetry-wide state and
do no structural reconstruction — that belongs to :mod:`.parse`.
"""

from __future__ import annotations

from typing import Any

from inspect_ai.model import Content, ContentImage, ContentReasoning, ContentText


def usage_to_inspect(usage: dict[str, Any] | None) -> dict[str, int]:
    """Rename OpenClaw ``usage`` keys to Inspect ``ModelUsage`` field names.

    NB OpenClaw's ``input`` is the *uncached/new* input only (exclusive-cache
    semantics). ``reasoning_tokens`` is left 0: OpenClaw *does* emit thinking
    blocks (surfaced as ``ContentReasoning``; see :func:`content_blocks`) but
    reports no separate reasoning-token count — reasoning is folded into
    ``output`` (verified across the CRUX1 capture: ``input + output + cacheRead
    + cacheWrite == totalTokens`` for every turn), so it is already counted,
    just not broken out. ``cost`` is dropped (Inspect ``ModelUsage`` has no
    cost field).
    """
    usage = usage or {}
    return {
        "input_tokens": int(usage.get("input") or 0),
        "output_tokens": int(usage.get("output") or 0),
        "total_tokens": int(usage.get("totalTokens") or 0),
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
