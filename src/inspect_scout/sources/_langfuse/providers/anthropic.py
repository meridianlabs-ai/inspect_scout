"""Anthropic-specific parsing and extraction for LangFuse data."""

from typing import Any


def parse_json_content(content: Any) -> Any:
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


def has_anthropic_tool_blocks(content: Any) -> bool:
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
