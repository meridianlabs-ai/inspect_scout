"""Pydantic models for llm_scanner REST API params.

This is a temporary, hardcoded solution for llm_scanner specifically.
The general problem of exposing arbitrary scanner params via REST API
(introspecting function signatures, handling complex types, etc.) is
not yet solved. This serves as a starting point for the UI while we
determine the right approach for arbitrary scanners.
"""

from typing import Literal

from pydantic import BaseModel

from inspect_scout._scanner.extract import MessageFormatOptions


class LlmScannerParams(BaseModel):
    """Parameters for llm_scanner."""

    question: str
    answer: Literal["boolean", "numeric", "string"]
    # NYI: list[str] for label sets
    # NYI: AnswerMultiLabel
    # NYI: AnswerStructured
    # TODO: Obviously, this is just the scalars from MessagesPreprocessor
    preprocessor: MessageFormatOptions | None = None
