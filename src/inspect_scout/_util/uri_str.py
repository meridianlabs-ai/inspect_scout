"""Branded string type for URIs (percent-encoded per RFC 3986)."""

from pathlib import Path
from typing import NewType, overload
from urllib.parse import unquote

from upath import UPath

from .path_str import PathStr, as_path

UriStr = NewType("UriStr", str)
"""A percent-encoded URI string per RFC 3986."""


@overload
def make_uri(path: Path) -> UriStr: ...


@overload
def make_uri(path: UPath) -> UriStr: ...


@overload
def make_uri(path: PathStr) -> UriStr: ...


def make_uri(path: Path | UPath | PathStr) -> UriStr:
    """Convert a path to a percent-encoded file:// URI.

    Resolves the path to an absolute path before encoding.
    """
    return UriStr(UPath(path).resolve().as_uri())


def uri_to_path(uri: UriStr) -> PathStr:
    """Convert a file:// URI to a decoded path string."""
    return as_path(unquote(UPath(uri).path))


def as_uri(raw: str) -> UriStr:
    """Assert that a string is already a valid percent-encoded URI.

    Use when you know the string is a URI but the type system doesn't.
    No transformation is performed.
    """
    return UriStr(raw)
