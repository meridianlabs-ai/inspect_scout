"""LFS transparent fallback for dist/ files."""

from .exceptions import LFSError
from .resolver import resolve_dist_directory

__all__ = ["LFSError", "resolve_dist_directory"]
