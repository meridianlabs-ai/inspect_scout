"""Scanner IR module for code round-tripping.

This module provides infrastructure for parsing and generating scanner Python files,
enabling a UI to create and edit scanners while preserving formatting.
"""

from .formatter import detect_ruff_config, format_with_ruff, is_ruff_available
from .generator import (
    SourceChangedError,
    apply_scanner_changes,
    generate_scanner_file,
    source_unchanged,
)
from .parser import parse_scanner_file
from .types import (
    GrepScannerSpec,
    LLMScannerSpec,
    ParseResult,
    ScannerDecoratorSpec,
    ScannerFile,
    StructuredAnswerSpec,
    StructuredField,
)

__all__ = [
    # Functions
    "apply_scanner_changes",
    "detect_ruff_config",
    "format_with_ruff",
    "generate_scanner_file",
    "is_ruff_available",
    "parse_scanner_file",
    "source_unchanged",
    # Types
    "GrepScannerSpec",
    "LLMScannerSpec",
    "ParseResult",
    "ScannerDecoratorSpec",
    "ScannerFile",
    "SourceChangedError",
    "StructuredAnswerSpec",
    "StructuredField",
]
