"""IR types for scanner code round-tripping.

These Pydantic models represent the intermediate representation (IR) for scanner
definitions, enabling parsing and generation of scanner Python files.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ============ LLM Scanner Types ============


class StructuredField(BaseModel):
    """A field in a Pydantic model for structured answers."""

    name: str
    field_type: str  # Any valid Python type annotation as string
    description: str
    alias: str | None = Field(default=None)


class StructuredAnswerSpec(BaseModel):
    """Specification for a Pydantic model. Supports nested models."""

    class_name: str
    fields: list[StructuredField]
    is_list: bool = Field(default=False)
    nested_models: list[StructuredAnswerSpec] | None = Field(default=None)


class LLMScannerSpec(BaseModel):
    """Specification for an llm_scanner() call."""

    question: str
    answer_type: Literal[
        "boolean", "numeric", "string", "labels", "multi_labels", "structured"
    ]
    labels: list[str] | None = Field(default=None)
    structured_spec: StructuredAnswerSpec | None = Field(default=None)
    model: str | None = Field(default=None)
    retry_refusals: int | None = Field(default=None)
    template: str | None = Field(default=None)


# ============ Grep Scanner Types ============


class GrepScannerSpec(BaseModel):
    """Specification for a grep_scanner() call."""

    pattern_type: Literal["single", "list", "labeled"]
    pattern: str | None = Field(default=None)
    patterns: list[str] | None = Field(default=None)
    labeled_patterns: dict[str, list[str]] | None = Field(default=None)
    regex: bool = Field(default=False)
    ignore_case: bool = Field(default=True)
    word_boundary: bool = Field(default=False)


# ============ Scanner File Types ============


class ScannerDecoratorSpec(BaseModel):
    """Specification for the @scanner decorator."""

    messages: Literal["all"] | list[str] | None = Field(default=None)
    events: list[str] | None = Field(default=None)
    name: str | None = Field(default=None)
    version: int = Field(default=0)


class ScannerFile(BaseModel):
    """A single scanner file - either editable or advanced."""

    function_name: str
    decorator: ScannerDecoratorSpec
    scanner_type: Literal["llm", "grep"]
    llm_scanner: LLMScannerSpec | None = Field(default=None)
    grep_scanner: GrepScannerSpec | None = Field(default=None)
    structured_model: StructuredAnswerSpec | None = Field(default=None)


class ParseResult(BaseModel):
    """Result of parsing a scanner file."""

    editable: bool
    scanner: ScannerFile | None = Field(default=None)
    source: str
    advanced_reason: str | None = Field(default=None)
