# tests/scanjobs/test_refresh.py
from inspect_ai._util.file import FileInfo
from inspect_scout._scanjobs.refresh import (
    ScanListing,
    compute_delta,
    listing_to_scans,
)


def _file(name: str, *, mtime: float, size: int, etag: str | None = None) -> FileInfo:
    return FileInfo(name=name, type="file", size=size, mtime=mtime, etag=etag)


def test_listing_token_prefers_summary_etag() -> None:
    infos = [
        _file("/s/scan_id=a/_scan.json", mtime=1.0, size=10),
        _file("/s/scan_id=a/_summary.json", mtime=2.0, size=20, etag="E"),
        _file("/s/scan_id=a/refusal.parquet", mtime=3.0, size=99),
    ]
    listed = listing_to_scans("/s", infos)

    assert listed["a"] == ScanListing("a", "/s/scan_id=a", "E")


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
