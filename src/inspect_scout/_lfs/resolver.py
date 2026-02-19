"""Directory resolution with LFS transparent fallback.

Determines whether a directory contains real files or LFS pointer files,
and returns a directory path with real content in either case.
"""

from pathlib import Path

from .cache import ensure_cached
from .exceptions import LFSResolverError
from .pointer import is_lfs_pointer


def resolve_lfs_directory(
    source_dir: Path,
    cache_dir: Path,
    repo_url: str,
    *,
    force_cache: bool = False,
) -> Path:
    """Resolve a directory that may contain LFS pointer files.

    Recursively checks source_dir for LFS pointers. If none are found,
    returns source_dir as-is (unless force_cache is True). If any pointer
    is found, populates cache_dir with real content for all files
    (downloading pointers, copying real files) and returns cache_dir.

    Args:
        source_dir: Directory to check recursively for LFS pointer files.
        cache_dir: Cache directory for downloaded LFS content.
        repo_url: HTTPS URL of the git repository (for LFS downloads).
        force_cache: Always populate and return cache_dir, even when source_dir
            contains no LFS pointers.

    Returns:
        Path to a directory tree containing real file content.

    Raises:
        LFSResolverError: If source_dir is missing or LFS download fails.
    """
    if not source_dir.is_dir():
        raise LFSResolverError(f"Directory not found: {source_dir}")

    if not force_cache and not _has_lfs_pointers(source_dir):
        return source_dir

    try:
        ensure_cached(source_dir, cache_dir, repo_url=repo_url)
    except Exception as e:
        raise LFSResolverError(f"Failed to download LFS objects: {e}") from e

    return cache_dir


def _has_lfs_pointers(directory: Path) -> bool:
    """Check if any file in the directory is an LFS pointer."""
    return any(is_lfs_pointer(f) for f in directory.rglob("*") if f.is_file())
