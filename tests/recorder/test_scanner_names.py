"""Scanner names from a scan's `_scan.json` can't place files outside the scan."""

import hashlib
import json
import os
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from inspect_scout._recorder.file import FileRecorder
from inspect_scout._scanspec import ScannerSpec, ScanSpec
from pydantic import ValidationError


@pytest.fixture
def scout_buffer_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    buf_dir = tmp_path / "buffer"
    monkeypatch.setenv("SCOUT_SCANBUFFER_DIR", str(buf_dir))
    return buf_dir


@pytest.mark.asyncio
async def test_sync_does_not_write_outside_the_scan_dir(
    tmp_path: Path, scout_buffer_dir: Path
) -> None:
    victim = tmp_path / "elsewhere" / "victim.parquet"
    victim.parent.mkdir()
    pq.write_table(pa.table({"x": [1, 2, 3]}), victim)
    before = hashlib.sha256(victim.read_bytes()).hexdigest()

    recorder = FileRecorder()
    await recorder.init(
        ScanSpec(scan_name="test", scanners={"s": ScannerSpec(name="s")}),
        str(tmp_path / "scans"),
    )
    scan_dir = Path(recorder.scan_dir.as_posix())
    spec_file = scan_dir / "_scan.json"
    spec = json.loads(spec_file.read_text())
    escape = os.path.relpath(victim.with_suffix(""), scan_dir)
    spec["scanners"] = {escape: spec["scanners"]["s"]}
    spec_file.write_text(json.dumps(spec))

    with pytest.raises(ValidationError, match="not a valid scanner name"):
        await FileRecorder.sync(scan_dir.as_posix(), complete=True)

    assert hashlib.sha256(victim.read_bytes()).hexdigest() == before


@pytest.mark.parametrize(
    "name", ["../victim", "a/b", "/abs/victim", "a\\b", "C:victim", "", ".", ".."]
)
def test_scan_spec_rejects_scanner_names_that_are_not_file_names(name: str) -> None:
    with pytest.raises(ValidationError, match="not a valid scanner name"):
        ScanSpec(scan_name="test", scanners={name: ScannerSpec(name="s")})


@pytest.mark.parametrize("name", ["s", "my_scanner_2", "My-Scanner", "scanner.v2"])
def test_scan_spec_accepts_plain_scanner_names(name: str) -> None:
    spec = ScanSpec(scan_name="test", scanners={name: ScannerSpec(name="s")})
    assert list(spec.scanners) == [name]
