"""Dist directory resolution with LFS transparent fallback.

Determines whether the repository's dist/ directory contains real files
or LFS pointer files, and returns a servable directory path in either case.
"""

import logging
from pathlib import Path

from inspect_scout._util.appdirs import scout_cache_dir

from .cache import ensure_cached
from .client import DEFAULT_REPO_URL
from .exceptions import LFSResolverError
from .pointer import is_lfs_pointer

logger = logging.getLogger(__name__)


def resolve_dist_directory(
    repo_dist_dir: Path,
    repo_url: str = DEFAULT_REPO_URL,
) -> Path:
    """Resolve a servable dist directory.

    Checks whether the repository's dist/ contains real files or LFS
    pointer files. If real files, returns repo_dist_dir directly. If
    pointers, populates a cache directory and returns that instead.

    Args:
        repo_dist_dir: Path to the repository's dist/ directory.
        repo_url: HTTPS URL of the git repository (for LFS downloads).

    Returns:
        Path to a directory containing real files suitable for StaticFiles.

    Raises:
        LFSResolverError: If dist/ is missing or cannot be resolved.
    """
    if not repo_dist_dir.is_dir():
        raise LFSResolverError(
            f"dist/ directory not found at {repo_dist_dir}.\n"
            "To fix this, either:\n"
            "  1. Install Git LFS and re-clone: brew install git-lfs && git lfs install\n"
            "  2. Build locally: cd src/inspect_scout/_view/frontend && pnpm build"
        )

    # Check index.html — it must exist and tells us if we have real files
    # or pointers.
    index_html = repo_dist_dir / "index.html"
    if not index_html.is_file():
        raise LFSResolverError(
            f"index.html not found in {repo_dist_dir}. The dist/ directory may be corrupted."
        )

    if not is_lfs_pointer(index_html):
        # Real files — serve directly from the repo.
        logger.debug("dist/ contains real files, serving from repo")
        return repo_dist_dir

    # LFS pointers detected — resolve via cache.
    logger.info("dist/ contains LFS pointer files, resolving via cache...")
    cache_dir = scout_cache_dir("dist")

    try:
        ensure_cached(repo_dist_dir, cache_dir, repo_url=repo_url)
    except Exception as e:
        raise LFSResolverError(
            f"Failed to download LFS dist files: {e}\n"
            "To fix this, either:\n"
            "  1. Install Git LFS: brew install git-lfs && git lfs install && git lfs pull\n"
            "  2. Check your network connection\n"
            "  3. Build locally: cd src/inspect_scout/_view/frontend && pnpm build"
        ) from e

    logger.info("Serving dist/ from cache at %s", cache_dir)
    return cache_dir
