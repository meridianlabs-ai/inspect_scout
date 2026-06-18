"""Lazy incremental refresh of the scan index from a directory listing.

A single recursive listing yields each scan's change-token; only new,
changed, or active scans are re-read from disk and upserted, and scans
whose directories vanished are deleted.
"""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from logging import getLogger
from typing import Protocol

from inspect_ai._util.asyncfiles import AsyncFilesystem
from inspect_ai._util.file import FileInfo
from upath import UPath

from .._recorder.active_scans_store import active_scans_store
from .._recorder.file import FileRecorder, _is_not_found
from .convert import scan_row_from_status
from .store import ScanIndexStore

logger = getLogger(__name__)

_SCAN_ID_SEGMENT = "scan_id="
_SUMMARY_FILE = "_summary.json"
_SPEC_FILE = "_scan.json"
_METADATA_CONCURRENCY = 50


class ScanListingFilesystem(Protocol):
    def iter_dirs(
        self, base: str, pattern: str = "*", *, recursive: bool = False
    ) -> AsyncIterator[str]: ...

    async def info(self, filename: str) -> FileInfo: ...


@dataclass
class ScanListing:
    scan_id: str
    dir_path: str
    token: str


@dataclass
class IndexDelta:
    to_read: list[ScanListing]
    to_delete: list[str]


def _scan_id_and_dir(file_path: str) -> tuple[str, str] | None:
    """Extract (scan_id, scan_dir) from a file path under a scan_id=<id> dir."""
    parts = file_path.split("/")
    for i, part in enumerate(parts):
        if part.startswith(_SCAN_ID_SEGMENT):
            scan_id = part[len(_SCAN_ID_SEGMENT) :]
            return scan_id, "/".join(parts[: i + 1])
    return None


def _token(info: FileInfo) -> str:
    return info.etag or f"{info.mtime}:{info.size}"


def _join_uri(base: str, name: str) -> str:
    return f"{base.rstrip('/')}/{name}"


def _normalize_scan_dir(location: str, uri: str) -> str:
    """Normalize iter_dirs output while preserving the caller's location protocol."""
    base = UPath(location)
    entry = UPath(uri.rstrip("/"))
    if base.protocol and not entry.protocol:
        plain = entry.as_posix()
        base_plain = UPath(base.path).as_posix()
        if plain.startswith(base_plain):
            rel = plain[len(base_plain) :].strip("/")
            entry = base / rel if rel else base
    return entry.as_posix()


async def _optional_info(fs: ScanListingFilesystem, filename: str) -> FileInfo | None:
    try:
        return await fs.info(filename)
    except Exception as exc:
        if _is_not_found(exc):
            return None
        raise


async def _listing_from_scan_dir(
    fs: ScanListingFilesystem,
    scan_dir: str,
    semaphore: asyncio.Semaphore,
) -> ScanListing | None:
    parsed = _scan_id_and_dir(scan_dir.rstrip("/"))
    if parsed is None:
        return None
    scan_id, normalized_scan_dir = parsed

    async with semaphore:
        summary_info = await _optional_info(
            fs, _join_uri(normalized_scan_dir, _SUMMARY_FILE)
        )
        spec_info = (
            None
            if summary_info is not None
            else await _optional_info(fs, _join_uri(normalized_scan_dir, _SPEC_FILE))
        )

    if summary_info is not None:
        token = _token(summary_info)
    elif spec_info is not None:
        token = _token(spec_info)
    else:
        token = "new"

    return ScanListing(scan_id, normalized_scan_dir, token)


async def async_listing_to_scans(
    fs: ScanListingFilesystem, location: str
) -> dict[str, ScanListing]:
    """List scan dirs and compute change tokens without sync recursive file walks."""
    scan_dirs: list[str] = []
    try:
        async for uri in fs.iter_dirs(location, "scan_id=*", recursive=True):
            scan_dirs.append(_normalize_scan_dir(location, uri))
    except Exception as exc:
        if _is_not_found(exc):
            return {}
        raise

    semaphore = asyncio.Semaphore(_METADATA_CONCURRENCY)
    listings = await asyncio.gather(
        *(_listing_from_scan_dir(fs, scan_dir, semaphore) for scan_dir in scan_dirs)
    )

    result: dict[str, ScanListing] = {}
    for listing in listings:
        if listing is not None:
            result[listing.scan_id] = listing
    return result


def listing_to_scans(location: str, infos: list[FileInfo]) -> dict[str, ScanListing]:
    # Group files by scan_id, tracking the _summary and _scan.json infos.
    summaries: dict[str, FileInfo] = {}
    specs: dict[str, FileInfo] = {}
    dirs: dict[str, str] = {}
    for info in infos:
        if info.type != "file":
            continue
        parsed = _scan_id_and_dir(info.name)
        if parsed is None:
            continue
        scan_id, scan_dir = parsed
        dirs[scan_id] = scan_dir
        basename = info.name.rsplit("/", 1)[-1]
        if basename == _SUMMARY_FILE:
            summaries[scan_id] = info
        elif basename == _SPEC_FILE:
            specs[scan_id] = info

    result: dict[str, ScanListing] = {}
    for scan_id, scan_dir in dirs.items():
        if scan_id in summaries:
            token = _token(summaries[scan_id])
        elif scan_id in specs:
            token = _token(specs[scan_id])
        else:
            token = "new"
        result[scan_id] = ScanListing(scan_id, scan_dir, token)
    return result


def compute_delta(
    listed: dict[str, ScanListing],
    stored_tokens: dict[str, str],
    active_scan_ids: set[str],
) -> IndexDelta:
    to_read = [
        listing
        for scan_id, listing in listed.items()
        if stored_tokens.get(scan_id) != listing.token or scan_id in active_scan_ids
    ]
    to_delete = [scan_id for scan_id in stored_tokens if scan_id not in listed]
    return IndexDelta(to_read=to_read, to_delete=to_delete)


async def refresh_index(store: ScanIndexStore, location: str) -> None:
    async with AsyncFilesystem() as fs:
        listed = await async_listing_to_scans(fs, location)

        with active_scans_store() as active_store:
            active = active_store.read_all()
        active_ids = {sid for sid in active if sid in listed}

        delta = compute_delta(listed, store.stored_tokens(), active_ids)

        # Read Status for the delta in parallel; missing scans are skipped.
        statuses = await asyncio.gather(
            *(FileRecorder.status(listing.dir_path) for listing in delta.to_read),
            return_exceptions=True,
        )

    rows = []
    for listing, status in zip(delta.to_read, statuses, strict=True):
        if isinstance(status, BaseException):
            # A single unreadable scan must not fail the whole listing. Missing
            # scans (deleted between listing and read) are skipped silently;
            # other errors — corrupt or version-incompatible status files,
            # transient remote errors — skip just that scan with a warning. A
            # previously-indexed scan keeps its last-good row: it stays in the
            # store (not in to_delete, since its dir still exists) and is
            # retried on the next refresh.
            if not isinstance(status, FileNotFoundError):
                logger.warning(
                    "Skipping scan %s: could not read status: %s",
                    listing.scan_id,
                    status,
                )
            continue
        rows.append(
            (
                scan_row_from_status(
                    status, active_scan_info=active.get(listing.scan_id)
                ),
                listing.token,
            )
        )

    # The listing snapshot, upsert, and delete are not one atomic transaction:
    # a scan created between another process's listing and its delete may be
    # dropped, but the next refresh re-inserts it from disk — transient, self-healing.
    store.upsert(rows)
    store.delete(delta.to_delete)
