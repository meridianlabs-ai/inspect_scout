from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from inspect_scout._query.sql import quote_identifier
from inspect_scout._recorder.summary import Summary
from inspect_scout._scanresults import scan_results_db
from inspect_scout._scanspec import ScannerSpec, ScanSpec


def _write_status(scan: Path, scanners: list[str]) -> None:
    spec = ScanSpec(
        scan_id="security",
        scan_name="security",
        scanners={name: ScannerSpec(name=name) for name in scanners},
    )
    (scan / "_scan.json").write_text(spec.model_dump_json(), encoding="utf-8")
    summary = Summary(scanners=scanners)
    summary.complete = True
    (scan / "_summary.json").write_text(summary.model_dump_json(), encoding="utf-8")


def test_undeclared_malicious_scan_file_is_ignored(tmp_path: Path) -> None:
    scan = tmp_path / "scan_id=security"
    scan.mkdir()
    _write_status(scan, ["safe"])
    pq.write_table(
        pa.table({"value_type": ["string"], "value": ["fixture"]}),
        scan / "safe.parquet",
    )

    marker = tmp_path / "scan-marker.txt"
    escaped_marker = str(marker).replace("\\", "\\\\").replace("/", "\\x2f")
    malicious_name = (
        "safe'); "
        f"COPY (SELECT 'INJECTED') TO E'{escaped_marker}' "
        "(HEADER false); --.parquet"
    )
    (scan / malicious_name).write_bytes(b"not parquet")

    db = scan_results_db(str(scan))
    try:
        assert db.scanner_tables == {"safe": "safe"}
        assert db.conn.execute("SELECT value FROM safe").fetchone() == ("fixture",)
        with pytest.raises(duckdb.PermissionException):
            db.conn.execute("COPY (SELECT 1) TO ?", [str(marker)])
    finally:
        db.conn.close()

    assert not marker.exists()


def test_declared_malicious_names_are_quoted(tmp_path: Path) -> None:
    scan = tmp_path / "scan_id=security"
    scan.mkdir()
    marker = tmp_path / "declared-marker.txt"
    escaped_marker = str(marker).replace("\\", "\\\\").replace("/", "\\x2f")
    scanner_name = (
        f"x'); COPY (SELECT 'INJECTED') TO E'{escaped_marker}' (HEADER false); --"
    )
    malicious_column = 'extra"; COPY (SELECT 1); --'
    _write_status(scan, [scanner_name])
    pq.write_table(
        pa.table(
            {
                "transcript_id": ["t1"],
                "value_type": ["resultset"],
                "value": [
                    '[{"uuid":"r1","label":"label","value":"ok","type":"string"}]'
                ],
                malicious_column: ["column-value"],
            }
        ),
        scan / f"{scanner_name}.parquet",
    )

    db = scan_results_db(str(scan))
    try:
        table_name = db.scanner_tables[scanner_name]
        row = db.conn.execute(
            f"SELECT {quote_identifier(malicious_column)} "
            f"FROM {quote_identifier(table_name)}"
        ).fetchone()
        assert row == ("column-value",)

        output = tmp_path / "results'; --.duckdb"
        db.to_file(str(output))
        verify = duckdb.connect(str(output))
        try:
            assert scanner_name in {
                row[0] for row in verify.execute("SHOW TABLES").fetchall()
            }
        finally:
            verify.close()
    finally:
        db.conn.close()

    assert not marker.exists()
