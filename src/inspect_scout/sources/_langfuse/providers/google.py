"""Google-specific parsing and extraction for LangFuse data.

Warning:
    The parsing in this module is inherently fragile as it relies on regex
    matching of Python repr() output, which is not a stable API. The repr
    format may change between SDK versions.
"""

import ast
import re
from logging import getLogger
from typing import Any

logger = getLogger(__name__)


def parse_google_content_repr(s: str) -> dict[str, Any]:
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
        - Thought/reasoning parts: Part(text='...', thought=True)
        - Function calls: Part(function_call=FunctionCall(args={...}, name='...'))
        - Function responses: Part(function_response=FunctionResponse(name='...'))

        Unrecognized patterns will result in empty parts arrays.

    Args:
        s: String representation of Google Content object

    Returns:
        Dict with 'role' and 'parts' keys
    """
    result: dict[str, Any] = {"parts": []}

    # Extract role
    role_match = re.search(r"role='([^']+)'", s)
    if role_match:
        result["role"] = role_match.group(1)

    # Check for text content (may include thought=True for reasoning)
    text_match = re.search(r"text='((?:[^'\\]|\\.)*)'", s, re.DOTALL)
    if text_match:
        text = text_match.group(1)
        # Check if this is a thought/reasoning part: Part(text='...', thought=True)
        # The thought=True flag may appear before or after the text
        is_thought = bool(re.search(r"\bthought=True\b", s))
        part: dict[str, Any] = {"text": text}
        if is_thought:
            part["thought"] = True
        result["parts"].append(part)
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

    # No patterns matched - log for debugging if input looks like it should be a Part
    if "Part(" in s and not result["parts"]:
        logger.debug(
            f"Google repr parsing: no patterns matched for input containing 'Part(': "
            f"{s[:200]}..."
        )

    return result


def parse_google_system_instruction(config_str: str) -> str | None:
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
    # Match system_instruction=['...', '...'] format
    si_match = re.search(r"system_instruction=\[([^\]]+)\]", config_str, re.DOTALL)
    if si_match:
        # Extract all quoted strings
        strings = re.findall(r"'((?:[^'\\]|\\.)*)'", si_match.group(1))
        if strings:
            return "\n".join(strings)
    return None


def parse_google_tools_from_config(config_str: str) -> list[dict[str, Any]]:
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
