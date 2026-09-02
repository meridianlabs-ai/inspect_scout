# tests/scanjobs/test_store.py
from datetime import datetime
from pathlib import Path

import pytest
from inspect_scout._query import Column, Query, UnknownColumnError
from inspect_scout._query.order_by import OrderBy
from inspect_scout._scanjobs.store import ScanIndexStore
from inspect_scout._view._api_v2_types import ScanRow


def make_row(
    scan_id: str,
    *,
    status: str = "complete",
    scan_name: str = "job",
    timestamp: datetime | None = None,
    total_results: int = 0,
) -> ScanRow:
    return ScanRow(
        scan_id=scan_id,
        scan_name=scan_name,
        scan_file="scan.py",
        timestamp=timestamp or datetime(2025, 1, 1, 0, 0, 0),
        packages={"inspect_scout": "1.0.0"},
        metadata={"k": "v"},
        scan_args={"a": 1},
        location=f"/scans/scan_id={scan_id}",
        status=status,  # type: ignore[arg-type]  # arbitrary status string for test
        scanners="refusal",
        model="openai/gpt-4",
        tags="",
        revision_version=None,
        revision_commit=None,
        revision_origin=None,
        total_results=total_results,
        total_errors=0,
        total_tokens=0,
        active_completion_pct=None,
        transcript_count=3,
    )


def test_upsert_roundtrip_preserves_json_and_scalars(tmp_path: Path) -> None:
    store = ScanIndexStore(tmp_path / "scans.sqlite")
    row = make_row("a")
    store.upsert([(row, "tok-a")])

    [got] = store.select(Query())

    assert got == row
    store.close()


def test_upsert_replaces_existing_scan_id(tmp_path: Path) -> None:
    store = ScanIndexStore(tmp_path / "scans.sqlite")
    store.upsert([(make_row("a", status="incomplete"), "t1")])
    store.upsert([(make_row("a", status="complete"), "t2")])

    rows = store.select(Query())
    assert len(rows) == 1
    assert rows[0].status == "complete"
    assert store.stored_tokens() == {"a": "t2"}
    store.close()


def test_filter_order_limit(tmp_path: Path) -> None:
    store = ScanIndexStore(tmp_path / "scans.sqlite")
    store.upsert(
        [
            (make_row("a", status="complete", total_results=5), "t"),
            (make_row("b", status="incomplete", total_results=9), "t"),
            (make_row("c", status="complete", total_results=1), "t"),
        ]
    )

    complete = store.select(Query(where=[Column("status") == "complete"]))
    assert {r.scan_id for r in complete} == {"a", "c"}
    assert store.count(Query(where=[Column("status") == "complete"])) == 2

    ordered = store.select(Query(order_by=[OrderBy("total_results", "DESC")]))
    assert [r.scan_id for r in ordered] == ["b", "a", "c"]

    assert len(store.select(Query(limit=2))) == 2
    store.close()


def test_delete_and_distinct(tmp_path: Path) -> None:
    store = ScanIndexStore(tmp_path / "scans.sqlite")
    store.upsert(
        [
            (make_row("a", scan_name="x"), "t"),
            (make_row("b", scan_name="y"), "t"),
        ]
    )

    store.delete(["a"])
    assert {r.scan_id for r in store.select(Query())} == {"b"}
    assert store.distinct("scan_name", None) == ["y"]
    store.close()


def test_persists_across_connections(tmp_path: Path) -> None:
    db = tmp_path / "scans.sqlite"
    s1 = ScanIndexStore(db)
    s1.upsert([(make_row("a"), "tok")])
    s1.close()

    s2 = ScanIndexStore(db)
    assert {r.scan_id for r in s2.select(Query())} == {"a"}
    assert s2.stored_tokens() == {"a": "tok"}
    s2.close()


def test_distinct_rejects_unknown_column(tmp_path: Path) -> None:
    store = ScanIndexStore(tmp_path / "scans.sqlite")
    store.upsert([(make_row("a"), "t")])
    with pytest.raises(ValueError):
        store.distinct('x" FROM scan_jobs; --', None)
    store.close()


def test_order_by_rejects_unknown_column(tmp_path: Path) -> None:
    store = ScanIndexStore(tmp_path / "scans.sqlite")
    store.upsert([(make_row("a"), "t")])
    with pytest.raises(UnknownColumnError):
        store.select(Query(order_by=[OrderBy('x"; DELETE FROM scan_jobs; --', "ASC")]))
    assert {row.scan_id for row in store.select()} == {"a"}
    store.close()
