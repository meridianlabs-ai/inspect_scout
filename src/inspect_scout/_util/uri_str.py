"""UriStr conversion functions."""

from pathlib import Path

from upath import UPath

from .str_types import PathStr, UriStr

__all__ = ["UriStr", "as_uri", "make_uri"]


def make_uri(path: Path | UPath | PathStr) -> UriStr:
    """Convert a path to a percent-encoded file:// URI.

    Resolves the path to an absolute path before encoding.
    """
    return UriStr(UPath(path).resolve().as_uri())


def as_uri(raw: str) -> UriStr:
    """Assert that a string is already a valid percent-encoded URI.

    Use when you know the string is a URI but the type system doesn't.
    No transformation is performed.
    """
    return UriStr(raw)
