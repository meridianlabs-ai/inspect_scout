"""PathStr conversion functions."""

from pathlib import Path
from urllib.parse import unquote

from upath import UPath

from .str_types import PathStr, UriStr

__all__ = ["PathStr", "as_path", "make_path"]


def make_path(path: Path | UPath | UriStr) -> PathStr:
    """Convert a Path, UPath, or UriStr to PathStr.

    If passed a UriStr, decodes percent-encoded characters.
    """
    if isinstance(path, (Path, UPath)):
        return PathStr(str(path))
    # UriStr case - decode percent-encoding
    return PathStr(unquote(UPath(path).path))


def as_path(raw: str) -> PathStr:
    """Assert that a string is already a filesystem path.

    Use when you know the string is a path but the type system doesn't.
    No transformation is performed.
    """
    return PathStr(raw)
