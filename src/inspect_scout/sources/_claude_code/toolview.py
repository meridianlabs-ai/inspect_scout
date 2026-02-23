from posixpath import splitext
from textwrap import indent
from typing import Any, Callable

from inspect_ai.tool import ToolCallContent

_MARKDOWN_EXTENSIONS = {".md", ".qmd"}

_CODE_FENCE_LANGUAGES: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript",
    ".jsx": "jsx",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".css": "css",
    ".html": "html",
    ".sql": "sql",
    ".rs": "rust",
    ".go": "go",
    ".r": "r",
    ".R": "r",
}


def tool_view(tool: str, arguments: dict[str, Any]) -> ToolCallContent | None:
    tool_view = tool_views.get(tool)
    if tool_view:
        return tool_view(arguments)
    else:
        return None


def write_tool_view(arguments: dict[str, Any]) -> ToolCallContent:
    file_path = str(arguments.get("file_path", "") or "")
    file_content = str(arguments.get("content", "") or "")
    _, ext = splitext(file_path)
    ext_lower = ext.lower()
    if ext_lower in _MARKDOWN_EXTENSIONS:
        body = file_content
    elif ext_lower in _CODE_FENCE_LANGUAGES:
        lang = _CODE_FENCE_LANGUAGES[ext_lower]
        body = f"```{lang}\n{file_content}\n```"
    else:
        body = indent(file_content, "    ")
    content = f"`{file_path}`\n\n{body}\n"
    return ToolCallContent(title="Write", format="markdown", content=content)


def task_tool_view(arguments: dict[str, Any]) -> ToolCallContent | None:
    if arguments.get("subagent_type", None) == "Explore" and "prompt" in arguments:
        content = (
            f"_{arguments.get('description', '')}_\n\n{arguments.get('prompt', '')}\n"
        )

        return ToolCallContent(title="Explore", format="markdown", content=content)
    else:
        return None


tool_views: dict[str, Callable[[dict[str, Any]], ToolCallContent | None]] = {
    "Write": write_tool_view,
    "Task": task_tool_view,
}
