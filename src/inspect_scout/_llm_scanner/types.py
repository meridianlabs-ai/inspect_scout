from dataclasses import dataclass
from typing import Literal, NamedTuple


@dataclass
class LLMScannerMessages:
    exclude_system: bool = True
    exclude_reasoning: bool = False
    exclude_tool_usage: bool = False


@dataclass
class LLMScannerAnswer:
    type: Literal[
        # rate on 1-10, xxx
        "number",
        # yes/no
        "bool",
        # list discussed celebrities by name
        "str",
        # Which of the categories defined above are xxx
        "labels",
    ]
    labels: list[str] | None = None
    multi_classification: bool = False


class LLMScannerLabels(NamedTuple):
    """Label descriptions for LLM scanner."""

    labels: list[str]
    """List of label descriptions.

    Label values (e.g. A, B, C) will be provided automatically.
    """

    multiple: bool = False
    """Allow answers with multiple labels."""
