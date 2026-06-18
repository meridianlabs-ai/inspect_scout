# tests/scanjobs/test_sqlite_view.py
import shutil
from datetime import datetime
from pathlib import Path

import pytest
from inspect_scout._query import Column, Query
from inspect_scout._query.order_by import OrderBy
from inspect_scout._recorder.summary import Summary
from inspect_scout._scanjobs.sqlite import SqliteScanJobsView, scan_jobs_view
from inspect_scout._scanspec import ScannerSpec, ScanSpec
from inspect_scout._view._api_v2_types import ScanRow

# Real recorder filenames (inspect_scout._recorder.buffer / .file).
_SCAN_JSON = "_scan.json"
_SUMMARY_JSON = "_summary.json"


def _write_scan(scans_dir: Path, scan_id: str, *, complete: bool, when: int) -> None:
    """Write a minimal on-disk scan dir using real model serialization.

    ScanSpec requires only scan_name + scanners; everything else defaults.
    """
    scan_dir = scans_dir / f"scan_id={scan_id}"
    scan_dir.mkdir(parents=True)

    spec = ScanSpec(
        scan_id=scan_id,
        scan_name="job",
        scan_file="scan.py",
        timestamp=datetime(2025, 1, 1, when, 0, 0),
        scanners={"refusal": ScannerSpec(name="refusal")},
    )
    (scan_dir / _SCAN_JSON).write_text(spec.model_dump_json())

    summary = Summary(scanners=["refusal"])
    summary.complete = complete
    (scan_dir / _SUMMARY_JSON).write_text(summary.model_dump_json())


@pytest.fixture
def scans_dir(tmp_path: Path) -> Path:
    d = tmp_path / "scans"
    d.mkdir()
    _write_scan(d, "a", complete=True, when=1)
    _write_scan(d, "b", complete=False, when=2)
    _write_scan(d, "c", complete=True, when=3)
    return d


@pytest.mark.asyncio
async def test_select_count_distinct_over_real_dirs(scans_dir: Path) -> None:
    async with await scan_jobs_view(str(scans_dir)) as view:
        rows = [r async for r in view.select(Query())]
        assert {r.scan_id for r in rows} == {"a", "b", "c"}
        assert all(isinstance(r, ScanRow) for r in rows)

        complete = [
            r async for r in view.select(Query(where=[Column("status") == "complete"]))
        ]
        assert {r.scan_id for r in complete} == {"a", "c"}

        assert await view.count(Query()) == 3
        assert await view.distinct("scan_name", None) == ["job"]


@pytest.mark.asyncio
async def test_order_by_timestamp(scans_dir: Path) -> None:
    async with await scan_jobs_view(str(scans_dir)) as view:
        rows = [
            r async for r in view.select(Query(order_by=[OrderBy("timestamp", "ASC")]))
        ]
        assert [r.scan_id for r in rows] == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_refresh_picks_up_new_and_removed_scans(scans_dir: Path) -> None:
    async with await scan_jobs_view(str(scans_dir)) as view:
        assert await view.count(Query()) == 3

    # Add one scan, remove another, then reconnect (new view => fresh refresh).
    _write_scan(scans_dir, "d", complete=True, when=4)
    shutil.rmtree(scans_dir / "scan_id=a")

    async with await scan_jobs_view(str(scans_dir)) as view:
        rows = [r async for r in view.select(Query())]
        assert {r.scan_id for r in rows} == {"b", "c", "d"}


@pytest.mark.asyncio
async def test_uses_isolated_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Redirect the cache into tmp so the test never touches the real cache dir.
    cache = tmp_path / "cache"
    monkeypatch.setattr(
        "inspect_scout._scanjobs.cache_path.scout_cache_dir",
        lambda subdir=None: cache / subdir if subdir else cache,
    )
    (cache).mkdir(parents=True, exist_ok=True)

    scans = tmp_path / "scans"
    scans.mkdir()
    _write_scan(scans, "a", complete=True, when=1)

    view = SqliteScanJobsView(str(scans))
    await view.connect()
    assert await view.count(Query()) == 1
    await view.disconnect()
