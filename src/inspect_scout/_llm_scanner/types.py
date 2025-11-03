from typing import NamedTuple


class LLMScannerLabels(NamedTuple):
    """Label descriptions for LLM scanner."""

    labels: list[str]
    """List of label descriptions.

    Label values (e.g. A, B, C) will be provided automatically.
    """

    multiple: bool = False
    """Allow answers with multiple labels."""
