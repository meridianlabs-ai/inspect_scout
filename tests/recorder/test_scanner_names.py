"""Scanner names from a scan's `_scan.json` can't place files outside the scan."""

import hashlib
import json
import os
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from inspect_scout._recorder.buffer import RecorderBuffer, _sanitize_component
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

    with pytest.raises(ValueError, match="Invalid scan spec") as ex:
        await FileRecorder.sync(scan_dir.as_posix(), complete=True)
    assert "_scan.json" in str(ex.value)
    assert "not a valid scanner name" in str(ex.value)

    assert hashlib.sha256(victim.read_bytes()).hexdigest() == before


@pytest.mark.parametrize(
    "name",
    [
        "../victim",
        "a/../../victim",
        "..",
        "/abs/victim",
        "\\abs\\victim",
        "a\\..\\..\\victim",
        "C:victim",
        "C:/victim",
        # a single letter and a colon is a Windows drive, which drops the scan dir
        "x:v2",
        "\\\\server\\share\\victim",
    ],
)
def test_scan_spec_rejects_scanner_names_that_leave_the_scan_dir(name: str) -> None:
    with pytest.raises(ValidationError, match="not a valid scanner name"):
        ScanSpec(scan_name="test", scanners={name: ScannerSpec(name="s")})


@pytest.mark.parametrize(
    "name",
    [
        "s",
        "my_scanner_2",
        "My-Scanner",
        "scanner.v2",
        # project scanner names from scout.yaml are not sanitized
        "refusal:v2",
        "inspect_scout/llm_scanner",
    ],
)
def test_scan_spec_accepts_scanner_names_inside_the_scan_dir(name: str) -> None:
    spec = ScanSpec(scan_name="test", scanners={name: ScannerSpec(name="s")})
    assert list(spec.scanners) == [name]


async def _init_scan(tmp_path: Path, scanner: str, location: str | None = None) -> Path:
    recorder = FileRecorder()
    await recorder.init(
        ScanSpec(scan_name="test", scanners={"s": ScannerSpec(name="s")}),
        location or str(tmp_path / "scans"),
    )
    scan_dir = Path(recorder.scan_dir.path)
    spec_file = scan_dir / "_scan.json"
    spec = json.loads(spec_file.read_text())
    spec["scanners"] = {scanner: spec["scanners"]["s"]}
    spec_file.write_text(json.dumps(spec))
    return scan_dir


@pytest.mark.asyncio
async def test_sync_does_not_follow_a_tmp_file_symlink_out_of_the_scan_dir(
    tmp_path: Path, scout_buffer_dir: Path
) -> None:
    """A shared scan's `s.parquet.tmp` symlink must not redirect sync's write."""
    outside = tmp_path / "elsewhere" / "notes.txt"
    outside.parent.mkdir()
    outside.write_text("not a parquet file\n")
    before = hashlib.sha256(outside.read_bytes()).hexdigest()

    scan_dir = await _init_scan(tmp_path, "s")
    pq.write_table(pa.table({"x": [1, 2, 3]}), scan_dir / "s.parquet")
    (scan_dir / "s.parquet.tmp").symlink_to(outside)

    try:
        await FileRecorder.sync(scan_dir.as_posix(), complete=True)
    except Exception:
        pass

    assert hashlib.sha256(outside.read_bytes()).hexdigest() == before


@pytest.mark.asyncio
async def test_sync_does_not_follow_a_directory_symlink_out_of_the_scan_dir(
    tmp_path: Path, scout_buffer_dir: Path
) -> None:
    """A shared scan's `pkg` dir symlink must not route `pkg/victim` outside."""
    outside = tmp_path / "elsewhere" / "victim.parquet"
    outside.parent.mkdir()
    pq.write_table(pa.table({"x": [1, 2, 3]}), outside)
    before = hashlib.sha256(outside.read_bytes()).hexdigest()

    scan_dir = await _init_scan(tmp_path, "pkg/victim")
    (scan_dir / "pkg").symlink_to(outside.parent, target_is_directory=True)

    try:
        await FileRecorder.sync(scan_dir.as_posix(), complete=True)
    except Exception:
        pass

    assert hashlib.sha256(outside.read_bytes()).hexdigest() == before


@pytest.mark.asyncio
async def test_sync_does_not_decode_a_percent_encoded_dotdot_out_of_the_scan_dir(
    tmp_path: Path, scout_buffer_dir: Path
) -> None:
    """A `%2e%2e/victim` name in a file:// scan must not write to its parent."""
    name = "%2e%2e/victim"
    scan_dir = await _init_scan(tmp_path, name, "file://" + str(tmp_path / "scans"))
    outside = scan_dir.parent / "victim.parquet.tmp"
    outside.write_bytes(b"outside file must survive\n")
    before = hashlib.sha256(outside.read_bytes()).hexdigest()

    scan_uri = "file://" + str(scan_dir)
    buffered = (
        Path(RecorderBuffer.buffer_dir(scan_uri).as_posix())
        / f"scanner={_sanitize_component(name)}"
    )
    buffered.mkdir(parents=True)
    pq.write_table(pa.table({"x": [1, 2, 3]}), buffered / "t.parquet")

    try:
        await FileRecorder.sync(scan_uri, complete=True)
    except Exception:
        pass

    assert hashlib.sha256(outside.read_bytes()).hexdigest() == before
