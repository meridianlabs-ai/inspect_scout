from typing import NamedTuple


class LLMScannerMessages(NamedTuple):
    """Message content options for LLM scanner."""

    exclude_system: bool = True
    """Exclude system messages (defaults to `True`)"""

    exclude_reasoning: bool = False
    """Exclude reasoning content (defaults to `False`)."""

    exclude_tool_usage: bool = False
    """Exclude tool usage (defaults to `False`)"""


class LLMScannerLabels(NamedTuple):
    """Label descriptions for LLM scanner."""

    labels: list[str]
    """List of label descriptions.

    Label values (e.g. A, B, C) will be provided automatically.
    """

    multiple: bool = False
    """Allow answers with multiple labels."""
