"""Branded string types for type-safe URI and path handling."""

from typing import NewType

UriStr = NewType("UriStr", str)
"""A percent-encoded URI string per RFC 3986."""

PathStr = NewType("PathStr", str)
"""A filesystem path as a string (no encoding)."""
