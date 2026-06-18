"""Lazy incremental refresh of the scan index from a directory listing.

A single recursive listing yields each scan's change-token; only new,
changed, or active scans are re-read from disk and upserted, and scans
whose directories vanished are deleted.
"""

import asyncio
from dataclasses import dataclass

from inspect_ai._util.file import FileInfo, filesystem

from .._recorder.active_scans_store import active_scans_store
from .._recorder.file import FileRecorder
from .convert import scan_row_from_status
from .store import ScanIndexStore

_SCAN_ID_SEGMENT = "scan_id="
_SUMMARY_FILE = "_summary.json"
_SPEC_FILE = "_scan.json"


@dataclass
class ScanListing:
    scan_id: str
    dir_path: str
    token: str


@dataclass
class IndexDelta:
    to_read: list[ScanListing]
    to_delete: list[str]


def _scan_id_and_dir(location: str, file_path: str) -> tuple[str, str] | None:
    """Extract (scan_id, scan_dir) from a file path under a scan_id=<id> dir."""
    parts = file_path.split("/")
    for i, part in enumerate(parts):
        if part.startswith(_SCAN_ID_SEGMENT):
            scan_id = part[len(_SCAN_ID_SEGMENT) :]
            return scan_id, "/".join(parts[: i + 1])
    return None


def _token(info: FileInfo) -> str:
    return info.etag or f"{info.mtime}:{info.size}"


def listing_to_scans(location: str, infos: list[FileInfo]) -> dict[str, ScanListing]:
    # Group files by scan_id, tracking the _summary and _scan.json infos.
    summaries: dict[str, FileInfo] = {}
    specs: dict[str, FileInfo] = {}
    dirs: dict[str, str] = {}
    for info in infos:
        if info.type != "file":
            continue
        parsed = _scan_id_and_dir(location, info.name)
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
    fs = filesystem(location)
    try:
        infos = [fi for fi in fs.ls(location, recursive=True) if fi.type == "file"]
    except FileNotFoundError:
        infos = []

    listed = listing_to_scans(location, infos)

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
        if isinstance(status, FileNotFoundError):
            continue
        if isinstance(status, BaseException):
            raise status
        rows.append(
            (
                scan_row_from_status(
                    status, active_scan_info=active.get(listing.scan_id)
                ),
                listing.token,
            )
        )

    store.upsert(rows)
    store.delete(delta.to_delete)
