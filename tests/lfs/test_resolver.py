"""Tests for resolve_lfs_directory.

Mocks only the HTTP layer (client.fetch_download_urls / client.download_lfs_object)
so the full resolve → cache → pointer pipeline runs with real files.
"""

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from inspect_scout._lfs.client import LFSDownloadInfo
from inspect_scout._lfs.exceptions import LFSResolverError
from inspect_scout._lfs.pointer import LFS_POINTER_VERSION
from inspect_scout._lfs.resolver import resolve_lfs_directory

FAKE_REPO_URL = "https://github.com/example/repo.git"


def _write_real_file(path: Path, content: str = "<html>hello</html>") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_lfs_pointer(path: Path, content: bytes = b"real file content") -> str:
    """Write an LFS pointer file and return the OID for the real content."""
    oid = hashlib.sha256(content).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"{LFS_POINTER_VERSION}\noid sha256:{oid}\nsize {len(content)}\n",
        encoding="utf-8",
    )
    return oid


def _configure_lfs_mocks(
    mock_fetch: MagicMock,
    mock_download: MagicMock,
    content: bytes,
    oid: str,
) -> None:
    """Wire up fetch_download_urls and download_lfs_object mocks for one object."""
    mock_fetch.return_value = [
        LFSDownloadInfo(oid=oid, size=len(content), href="https://fake/download")
    ]

    def _download(_info: LFSDownloadInfo, dest_path: Path) -> None:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(content)

    mock_download.side_effect = _download


_PATCH_FETCH = patch("inspect_scout._lfs.cache.fetch_download_urls")
_PATCH_DOWNLOAD = patch("inspect_scout._lfs.cache.download_lfs_object")


def test_real_files_returns_source_dir(tmp_path: Path) -> None:
    """Directory with only real files is returned as-is."""
    source = tmp_path / "source"
    cache = tmp_path / "cache"
    _write_real_file(source / "index.html")

    result = resolve_lfs_directory(source, cache, FAKE_REPO_URL)

    assert result == source


@_PATCH_DOWNLOAD
@_PATCH_FETCH
def test_lfs_pointers_populates_cache(
    mock_fetch: MagicMock, mock_download: MagicMock, tmp_path: Path
) -> None:
    """LFS pointers are resolved: real content appears in cache_dir."""
    source = tmp_path / "source"
    cache = tmp_path / "cache"
    content = b"the real index content"
    oid = _make_lfs_pointer(source / "index.html", content)
    _configure_lfs_mocks(mock_fetch, mock_download, content, oid)

    result = resolve_lfs_directory(source, cache, FAKE_REPO_URL)

    assert result == cache
    assert (cache / "index.html").read_bytes() == content


@_PATCH_DOWNLOAD
@_PATCH_FETCH
def test_subdirectories_resolved_recursively(
    mock_fetch: MagicMock, mock_download: MagicMock, tmp_path: Path
) -> None:
    """Pointer in a subdirectory is detected and cached with structure preserved."""
    source = tmp_path / "source"
    cache = tmp_path / "cache"
    content = b"nested asset content"
    _write_real_file(source / "index.html")
    oid = _make_lfs_pointer(source / "assets" / "logo.png", content)
    _configure_lfs_mocks(mock_fetch, mock_download, content, oid)

    result = resolve_lfs_directory(source, cache, FAKE_REPO_URL)

    assert result == cache
    assert (cache / "assets" / "logo.png").read_bytes() == content
    assert (cache / "index.html").exists()


def test_force_cache_copies_real_files(tmp_path: Path) -> None:
    """force_cache=True populates cache even when no pointers exist."""
    source = tmp_path / "source"
    cache = tmp_path / "cache"
    _write_real_file(source / "index.html", "real content")

    result = resolve_lfs_directory(source, cache, FAKE_REPO_URL, force_cache=True)

    assert result == cache
    assert (cache / "index.html").read_text() == "real content"


def test_missing_directory_raises(tmp_path: Path) -> None:
    """Non-existent source_dir raises LFSResolverError."""
    with pytest.raises(LFSResolverError, match="Directory not found"):
        resolve_lfs_directory(
            tmp_path / "nonexistent", tmp_path / "cache", FAKE_REPO_URL
        )


@_PATCH_FETCH
def test_download_failure_raises(mock_fetch: MagicMock, tmp_path: Path) -> None:
    """Network failure in ensure_cached is wrapped in LFSResolverError."""
    source = tmp_path / "source"
    cache = tmp_path / "cache"
    _make_lfs_pointer(source / "file.txt")
    mock_fetch.side_effect = ConnectionError("network down")

    with pytest.raises(LFSResolverError, match="Failed to download LFS objects"):
        resolve_lfs_directory(source, cache, FAKE_REPO_URL)


def test_pruning_removes_orphaned_cache_entries(tmp_path: Path) -> None:
    """Files removed from source are pruned from cache on next resolve."""
    source = tmp_path / "source"
    cache = tmp_path / "cache"

    _write_real_file(source / "keep.html", "keep")
    _write_real_file(source / "remove.html", "remove")
    resolve_lfs_directory(source, cache, FAKE_REPO_URL, force_cache=True)
    assert (cache / "remove.html").exists()

    (source / "remove.html").unlink()
    resolve_lfs_directory(source, cache, FAKE_REPO_URL, force_cache=True)

    assert (cache / "keep.html").exists()
    assert not (cache / "remove.html").exists()
