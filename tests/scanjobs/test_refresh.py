# tests/scanjobs/test_refresh.py
import asyncio
import logging
import sys
from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager
from pathlib import Path
from types import TracebackType

import inspect_scout._scanjobs.refresh as refresh_module
import pytest
from inspect_ai._util.file import FileInfo
from inspect_scout._recorder.file import FileRecorder
from inspect_scout._scanjobs.refresh import (
    ScanListing,
    async_listing_to_scans,
    compute_delta,
    listing_to_scans,
)
from inspect_scout._scanjobs.store import ScanIndexStore

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup


def _file(name: str, *, mtime: float, size: int, etag: str | None = None) -> FileInfo:
    return FileInfo(name=name, type="file", size=size, mtime=mtime, etag=etag)


class _FakeAsyncFilesystem:
    def __init__(self, dirs: list[str], infos: dict[str, FileInfo]) -> None:
        self._dirs = dirs
        self._infos = infos

    async def iter_dirs(
        self, base: str, pattern: str = "*", *, recursive: bool = False
    ) -> AsyncIterator[str]:
        for dirname in self._dirs:
            yield dirname

    async def info(self, filename: str) -> FileInfo:
        info = self._infos.get(filename)
        if info is None:
            raise FileNotFoundError(filename)
        return info


class _MetadataErrorFilesystem(_FakeAsyncFilesystem):
    def __init__(
        self,
        dirs: list[str],
        infos: dict[str, FileInfo],
        error_prefixes: list[str],
    ) -> None:
        super().__init__(dirs, infos)
        self._error_prefixes = error_prefixes

    async def info(self, filename: str) -> FileInfo:
        if any(filename.startswith(prefix) for prefix in self._error_prefixes):
            raise PermissionError(filename)
        return await super().info(filename)


class _AsyncFilesystemContext:
    def __init__(self, fs: _FakeAsyncFilesystem) -> None:
        self._fs = fs

    async def __aenter__(self) -> _FakeAsyncFilesystem:
        return self._fs

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


class _EmptyActiveScansStore:
    def read_all(self) -> dict[str, object]:
        return {}


@contextmanager
def _empty_active_scans_store() -> Iterator[_EmptyActiveScansStore]:
    yield _EmptyActiveScansStore()


def _patch_refresh_filesystem(
    monkeypatch: pytest.MonkeyPatch, fs: _FakeAsyncFilesystem
) -> None:
    def async_filesystem() -> _AsyncFilesystemContext:
        return _AsyncFilesystemContext(fs)

    monkeypatch.setattr(refresh_module, "AsyncFilesystem", async_filesystem)


def test_listing_token_prefers_summary_etag() -> None:
    infos = [
        _file("/s/scan_id=a/_scan.json", mtime=1.0, size=10),
        _file("/s/scan_id=a/_summary.json", mtime=2.0, size=20, etag="E"),
        _file("/s/scan_id=a/refusal.parquet", mtime=3.0, size=99),
    ]
    listed = listing_to_scans("/s", infos)

    assert listed["a"] == ScanListing("a", "/s/scan_id=a", "E")


@pytest.mark.asyncio
async def test_async_listing_to_scans_uses_async_dir_and_metadata_apis() -> None:
    fs = _FakeAsyncFilesystem(
        dirs=["/s/scan_id=a/", "/s/scan_id=b/", "/s/scan_id=c/"],
        infos={
            "/s/scan_id=a/_summary.json": _file(
                "/s/scan_id=a/_summary.json", mtime=2.0, size=20, etag="E"
            ),
            "/s/scan_id=a/_scan.json": _file(
                "/s/scan_id=a/_scan.json", mtime=1.0, size=10
            ),
            "/s/scan_id=b/_scan.json": _file(
                "/s/scan_id=b/_scan.json", mtime=5.0, size=7
            ),
        },
    )

    listed = await async_listing_to_scans(fs, "/s")

    assert listed == {
        "a": ScanListing("a", "/s/scan_id=a", "E"),
        "b": ScanListing("b", "/s/scan_id=b", "5.0:7"),
        "c": ScanListing("c", "/s/scan_id=c", "new"),
    }


@pytest.mark.asyncio
async def test_async_listing_to_scans_skips_scan_with_unreadable_metadata() -> None:
    fs = _MetadataErrorFilesystem(
        dirs=["/s/scan_id=bad/", "/s/scan_id=good/"],
        infos={
            "/s/scan_id=good/_summary.json": _file(
                "/s/scan_id=good/_summary.json", mtime=2.0, size=20
            )
        },
        error_prefixes=["/s/scan_id=bad/"],
    )

    listed = await async_listing_to_scans(fs, "/s")

    assert listed == {
        "good": ScanListing("good", "/s/scan_id=good", "2.0:20"),
    }


def test_listing_token_falls_back_to_mtime_size_then_scan_json() -> None:
    summary_only = listing_to_scans(
        "/s", [_file("/s/scan_id=a/_summary.json", mtime=2.0, size=20)]
    )
    assert summary_only["a"].token == "2.0:20"

    spec_only = listing_to_scans(
        "/s", [_file("/s/scan_id=b/_scan.json", mtime=5.0, size=7)]
    )
    assert spec_only["b"].token == "5.0:7"


def test_listing_ignores_non_scan_files() -> None:
    listed = listing_to_scans("/s", [_file("/s/_index/foo.idx", mtime=1.0, size=1)])
    assert listed == {}


def test_compute_delta_new_changed_unchanged_deleted_active() -> None:
    listed = {
        "new": ScanListing("new", "/s/scan_id=new", "t-new"),
        "changed": ScanListing("changed", "/s/scan_id=changed", "t2"),
        "same": ScanListing("same", "/s/scan_id=same", "t-same"),
        "active": ScanListing("active", "/s/scan_id=active", "t-active"),
    }
    stored = {
        "changed": "t1",
        "same": "t-same",
        "active": "t-active",
        "gone": "t-gone",
    }

    delta = compute_delta(listed, stored, active_scan_ids={"active"})

    assert {s.scan_id for s in delta.to_read} == {"new", "changed", "active"}
    assert delta.to_delete == ["gone"]


@pytest.mark.asyncio
async def test_refresh_index_logs_inner_exception_for_grouped_status_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    fs = _FakeAsyncFilesystem(
        dirs=["/s/scan_id=bad/"],
        infos={
            "/s/scan_id=bad/_summary.json": _file(
                "/s/scan_id=bad/_summary.json", mtime=2.0, size=20
            )
        },
    )
    _patch_refresh_filesystem(monkeypatch, fs)
    monkeypatch.setattr(refresh_module, "active_scans_store", _empty_active_scans_store)

    async def status(_location: str) -> object:
        raise ExceptionGroup("outer", [PermissionError("metadata denied")])

    monkeypatch.setattr(FileRecorder, "status", staticmethod(status))
    caplog.set_level(logging.WARNING, logger=refresh_module.__name__)
    store = ScanIndexStore(tmp_path / "index.db")

    try:
        await refresh_module.refresh_index(store, "/s")
    finally:
        store.close()

    assert "metadata denied" in caplog.text
    assert "outer (1 sub-exception)" not in caplog.text


@pytest.mark.asyncio
async def test_refresh_index_propagates_cancelled_status_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fs = _FakeAsyncFilesystem(
        dirs=["/s/scan_id=cancelled/"],
        infos={
            "/s/scan_id=cancelled/_summary.json": _file(
                "/s/scan_id=cancelled/_summary.json", mtime=2.0, size=20
            )
        },
    )
    _patch_refresh_filesystem(monkeypatch, fs)
    monkeypatch.setattr(refresh_module, "active_scans_store", _empty_active_scans_store)

    async def status(_location: str) -> object:
        raise asyncio.CancelledError("stop refresh")

    monkeypatch.setattr(FileRecorder, "status", staticmethod(status))
    store = ScanIndexStore(tmp_path / "index.db")

    try:
        with pytest.raises(asyncio.CancelledError):
            await refresh_module.refresh_index(store, "/s")
    finally:
        store.close()
