"""Branded string type for filesystem paths."""

from pathlib import Path
from typing import NewType

from upath import UPath

PathStr = NewType("PathStr", str)
"""A filesystem path as a string (no encoding)."""


def make_path(path: Path | UPath) -> PathStr:
    """Convert a Path or UPath to PathStr."""
    return PathStr(str(path))


def as_path(raw: str) -> PathStr:
    """Assert that a string is already a filesystem path.

    Use when you know the string is a path but the type system doesn't.
    No transformation is performed.
    """
    return PathStr(raw)
