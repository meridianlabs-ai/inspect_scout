"""LFS dist cache management.

Mirrors the repository's dist/ directory structure in a local cache,
downloading real file content from GitHub LFS when the repo contains
pointer files.
"""

import logging
import os
import time
from pathlib import Path

from .client import (
    LFSDownloadInfo,
    download_lfs_object,
    fetch_download_urls,
)
from .exceptions import LFSDownloadError
from .pointer import LFSPointer, is_lfs_pointer, parse_lfs_pointer

logger = logging.getLogger(__name__)


def ensure_cached(
    repo_dist_dir: Path,
    cache_dist_dir: Path,
    repo_url: str,
) -> None:
    """Populate the cache with real files for all LFS pointers in dist/.

    Walks repo_dist_dir, identifies LFS pointer files, checks the cache
    for each one, and downloads any missing files via the LFS batch API.

    The cache mirrors the dist/ directory structure so that StaticFiles
    can serve it directly.

    Args:
        repo_dist_dir: Path to repository's dist/ directory (contains pointers).
        cache_dist_dir: Path to cache directory (will contain real files).
        repo_url: HTTPS URL of the git repository.

    Raises:
        LFSDownloadError: If any critical file fails to download.
    """
    # Collect pointers and check cache status.
    needs_download: list[tuple[Path, LFSPointer]] = []

    for repo_file in _walk_files(repo_dist_dir):
        if not is_lfs_pointer(repo_file):
            # Real file — copy to cache if not already there.
            rel = repo_file.relative_to(repo_dist_dir)
            cache_file = cache_dist_dir / rel
            if not cache_file.exists():
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                _copy_file(repo_file, cache_file)
            continue

        pointer = parse_lfs_pointer(repo_file)
        if pointer is None:
            logger.warning("Could not parse LFS pointer: %s", repo_file)
            continue

        rel = repo_file.relative_to(repo_dist_dir)
        cache_file = cache_dist_dir / rel
        oid_file = cache_file.with_suffix(cache_file.suffix + ".oid")

        # Cache hit: file exists and OID matches.
        if cache_file.exists() and oid_file.exists():
            cached_oid = oid_file.read_text(encoding="utf-8").strip()
            if cached_oid == pointer.oid:
                continue
            # OID mismatch — remove stale cache files before re-download.
            cache_file.unlink(missing_ok=True)
            oid_file.unlink(missing_ok=True)
        elif cache_file.exists() or oid_file.exists():
            # Incomplete cache entry — clean up orphaned files.
            cache_file.unlink(missing_ok=True)
            oid_file.unlink(missing_ok=True)

        needs_download.append((repo_file, pointer))

    if not needs_download:
        logger.debug("LFS cache is up to date")
        return

    logger.info("Downloading %d LFS objects...", len(needs_download))

    # Batch request for download URLs.
    batch_objects = [(p.oid, p.size) for _, p in needs_download]
    download_infos = fetch_download_urls(batch_objects, repo_url=repo_url)

    # Index by OID for lookup.
    info_by_oid: dict[str, LFSDownloadInfo] = {d.oid: d for d in download_infos}

    # Download each file.
    failed: list[str] = []
    for repo_file, pointer in needs_download:
        rel = repo_file.relative_to(repo_dist_dir)
        cache_file = cache_dist_dir / rel
        oid_file = cache_file.with_suffix(cache_file.suffix + ".oid")
        marker_file = cache_file.with_suffix(cache_file.suffix + ".downloading")

        info = info_by_oid.get(pointer.oid)
        if info is None:
            logger.warning("No download URL for %s (%s)", rel, pointer.oid[:12])
            failed.append(str(rel))
            continue

        # Multiprocess coordination: skip if another process is downloading.
        if not _try_create_marker(marker_file):
            logger.debug("Another process is downloading %s, waiting...", rel)
            _wait_for_marker(marker_file)
            if cache_file.exists():
                continue
            # Other process may have failed; try to acquire marker ourselves.
            if not _try_create_marker(marker_file):
                _wait_for_marker(marker_file)
                if cache_file.exists():
                    continue
                logger.warning("Could not acquire download marker for %s", rel)
                failed.append(str(rel))
                continue

        try:
            download_lfs_object(info, marker_file)
            marker_file.rename(cache_file)
            oid_file.write_text(pointer.oid, encoding="utf-8")
            logger.info("Cached %s", rel)
        except Exception as e:
            # Clean up all partial state.
            marker_file.unlink(missing_ok=True)
            cache_file.unlink(missing_ok=True)
            oid_file.unlink(missing_ok=True)
            failed.append(str(rel))
            logger.warning("Failed to cache %s: %s", rel, e, exc_info=True)

    if failed:
        raise LFSDownloadError(
            f"Failed to download {len(failed)} LFS object(s): {', '.join(failed)}"
        )


def _walk_files(directory: Path) -> list[Path]:
    """Recursively list all files in a directory."""
    files: list[Path] = []
    for entry in sorted(directory.rglob("*")):
        if entry.is_file():
            files.append(entry)
    return files


def _copy_file(src: Path, dest: Path) -> None:
    """Copy a file, preserving content only."""
    dest.write_bytes(src.read_bytes())


def _try_create_marker(marker_file: Path) -> bool:
    """Atomically create a marker file. Returns True if we created it."""
    marker_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(marker_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
        return True
    except FileExistsError:
        return False


def _wait_for_marker(marker_file: Path, timeout_seconds: int = 60) -> None:
    """Wait for a marker file to be removed (another process finished).

    If the marker still exists after timeout, removes it as likely orphaned.
    """
    deadline = time.monotonic() + timeout_seconds
    while marker_file.exists() and time.monotonic() < deadline:
        time.sleep(0.5)

    # If marker still exists after timeout, it's likely orphaned by a crashed
    # process. Remove it so subsequent attempts can proceed.
    if marker_file.exists():
        marker_file.unlink(missing_ok=True)
        logger.warning("Removed orphaned marker file: %s", marker_file)
