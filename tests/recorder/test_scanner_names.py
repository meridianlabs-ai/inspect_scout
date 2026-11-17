"""Scanner names from a scan's `_scan.json` can't place files outside the scan."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from inspect_ai.model import ChatMessageUser
from inspect_scout import Result
from inspect_scout._recorder import file as recorder_file
from inspect_scout._recorder.buffer import (
    RecorderBuffer,
    _sanitize_component,
    scanner_table,
)
from inspect_scout._recorder.file import FileRecorder
from inspect_scout._scanner.result import ResultReport
from inspect_scout._scanresults import scan_results_df_async
from inspect_scout._scanspec import ScannerSpec, ScanSpec, ScanTranscripts
from inspect_scout._transcript.types import TranscriptInfo
from pydantic import ValidationError
from upath import UPath


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
        # a file:// scan's paths are percent-decoded, so these would be `..`
        "%2e%2e/victim",
        "a%2f..%2f..%2fvictim",
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


async def _scan_with_row(location: str, scanner: str) -> str:
    """Create a scan at `location` with one buffered result; return its location."""
    recorder = FileRecorder()
    await recorder.init(
        ScanSpec(scan_name="test", scanners={scanner: ScannerSpec(name=scanner)}),
        location,
    )
    await recorder.record(
        TranscriptInfo(
            transcript_id="t",
            source_type="test",
            source_id="src",
            source_uri="test://t",
        ),
        scanner,
        [
            ResultReport(
                input_type="message",
                input_ids=[],
                input=ChatMessageUser(content=""),
                result=Result(value=1),
                validation=None,
                error=None,
                events=[],
                model_usage={},
            )
        ],
        None,
    )
    return recorder.scan_dir.as_posix()


async def _result_count(location: str, scanner: str) -> int:
    """The number of result rows read back from the scan at `location`."""
    results = await scan_results_df_async(location, scanner=scanner)
    return len(results.scanners[scanner])


@pytest.mark.parametrize(
    ("scheme", "scanner", "link", "target", "refused"),
    [
        # sync writes to a new temp name, so it never opens this symlink
        ("", "s", "s.parquet.tmp", "victim.parquet", False),
        ("", "s", "s.parquet", "victim.parquet", True),
        ("", "pkg/victim", "pkg", ".", True),
        ("", "s", "_summary.json", "victim.parquet", True),
        ("", "s", "_errors.jsonl", "victim.parquet", True),
        ("local://", "s", "s.parquet", "victim.parquet", True),
        ("local://", "s", "_summary.json", "victim.parquet", True),
    ],
)
@pytest.mark.asyncio
async def test_sync_does_not_follow_a_symlink_out_of_the_scan_dir(
    tmp_path: Path,
    scout_buffer_dir: Path,
    scheme: str,
    scanner: str,
    link: str,
    target: str,
    refused: bool,
) -> None:
    """A symlink in a shared scan must not redirect a write by sync."""
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    victim = elsewhere / "victim.parquet"
    pq.write_table(pa.table({"x": [1, 2, 3]}), victim)
    before = hashlib.sha256(victim.read_bytes()).hexdigest()

    location = await _scan_with_row(scheme + str(tmp_path / "scans"), scanner)
    scan_dir = Path(UPath(location).path)
    (scan_dir / link).unlink(missing_ok=True)
    (scan_dir / link).symlink_to(elsewhere / target)

    if refused:
        with pytest.raises(ValueError, match="Refusing to write"):
            await FileRecorder.sync(location, complete=True)
    else:
        status = await FileRecorder.sync(location, complete=True)
        assert status.summary.complete

    assert hashlib.sha256(victim.read_bytes()).hexdigest() == before
    assert [p.name for p in elsewhere.iterdir()] == ["victim.parquet"]


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


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
@pytest.mark.asyncio
async def test_sync_keeps_file_permissions(
    tmp_path: Path, scout_buffer_dir: Path
) -> None:
    """New outputs get the umask's defaults; existing ones keep their mode."""
    umask = os.umask(0)
    os.umask(umask)
    scan_dir = await _init_scan(tmp_path, "s")
    pq.write_table(pa.table({"x": [1, 2, 3]}), scan_dir / "s.parquet")
    (scan_dir / "s.parquet").chmod(0o640)
    (scan_dir / "_summary.json").unlink(missing_ok=True)

    await FileRecorder.sync(scan_dir.as_posix(), complete=True)

    assert (scan_dir / "s.parquet").stat().st_mode & 0o777 == 0o640
    assert (scan_dir / "_summary.json").stat().st_mode & 0o777 == 0o666 & ~umask


@pytest.mark.asyncio
async def test_sync_handles_a_long_scanner_name(
    tmp_path: Path, scout_buffer_dir: Path
) -> None:
    """A name whose `<name>.parquet` fills the 255-byte file name limit syncs."""
    name = "s" * 247
    location = await _scan_with_row(str(tmp_path / "scans"), name)

    await FileRecorder.sync(location, complete=True)

    assert (Path(location) / f"{name}.parquet").is_file()
    assert await _result_count(location, name) == 1


@pytest.mark.asyncio
async def test_sync_does_not_follow_a_directory_swapped_in_during_the_write(
    tmp_path: Path, scout_buffer_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Replacing `pkg` with a symlink after sync checked it must not redirect it."""
    outside = tmp_path / "elsewhere" / "victim.parquet"
    outside.parent.mkdir()
    pq.write_table(pa.table({"x": [1, 2, 3]}), outside)
    before = hashlib.sha256(outside.read_bytes()).hexdigest()

    scan_dir = await _init_scan(tmp_path, "pkg/victim")
    (scan_dir / "pkg").mkdir()
    pq.write_table(pa.table({"x": [4, 5, 6]}), scan_dir / "pkg" / "victim.parquet")

    def swap_then_compact(*args: Any, **kwargs: Any) -> bool:
        (scan_dir / "pkg").rename(scan_dir / "pkg.real")
        (scan_dir / "pkg").symlink_to(outside.parent, target_is_directory=True)
        return scanner_table(*args, **kwargs)

    monkeypatch.setattr(recorder_file, "scanner_table", swap_then_compact)
    try:
        await FileRecorder.sync(scan_dir.as_posix(), complete=True)
    except Exception:
        pass

    assert hashlib.sha256(outside.read_bytes()).hexdigest() == before
    assert sorted(p.name for p in outside.parent.iterdir()) == ["victim.parquet"]


@pytest.mark.parametrize("name", ["B%20dir", "scans#run", "scans?run"])
@pytest.mark.asyncio
async def test_sync_writes_where_fsspec_reads_a_file_uri_scan_location(
    tmp_path: Path, scout_buffer_dir: Path, name: str
) -> None:
    """Fsspec reads `%20`, `#` and `?` in a file:// location literally; so must sync."""
    location = await _scan_with_row("file://" + str(tmp_path / name), "s")

    status = await FileRecorder.sync(location, complete=True)

    assert status.summary.complete
    assert {p.name for p in tmp_path.iterdir()} == {"buffer", name}
    [scan_dir] = (tmp_path / name).iterdir()
    assert (scan_dir / "s.parquet").is_file()
    assert await _result_count(location, "s") == 1


@pytest.mark.asyncio
async def test_sync_writes_where_fsspec_reads_a_tilde_scan_location(
    tmp_path: Path, scout_buffer_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fsspec expands `~` in a scan location; so must sync."""
    (tmp_path / "home" / "scans").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.chdir(tmp_path)
    location = await _scan_with_row("~/scans", "s")

    status = await FileRecorder.sync(location, complete=True)

    assert status.summary.complete
    # init creates an empty literal `~/scans/scan_id=...` (unchanged here)
    assert not [p for p in (tmp_path / "~").rglob("*") if p.is_file()]
    [scan_dir] = (tmp_path / "home" / "scans").iterdir()
    assert (scan_dir / "s.parquet").is_file()
    assert await _result_count(location, "s") == 1


@pytest.mark.asyncio
async def test_resume_does_not_write_the_scan_spec_through_a_symlink(
    tmp_path: Path, scout_buffer_dir: Path
) -> None:
    """A shared scan's `_scan.json` symlink must not redirect the spec write."""
    scan_dir = await _init_scan(tmp_path, "s")
    outside = tmp_path / "elsewhere" / "_scan.json"
    outside.parent.mkdir()
    (scan_dir / "_scan.json").rename(outside)
    (scan_dir / "_scan.json").symlink_to(outside)
    before = hashlib.sha256(outside.read_bytes()).hexdigest()

    recorder = FileRecorder()
    await recorder.resume(scan_dir.as_posix())
    with pytest.raises(ValueError, match="Refusing to write"):
        await recorder.snapshot_transcripts(
            ScanTranscripts(type="eval_log", transcript_ids={"t": None})
        )

    assert hashlib.sha256(outside.read_bytes()).hexdigest() == before


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
@pytest.mark.asyncio
async def test_sync_does_not_chmod_through_a_directory_swapped_in_after_create(
    tmp_path: Path, scout_buffer_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Copying the target's mode must not follow a swapped `pkg` to a victim."""
    victim = tmp_path / "home" / "private_key"
    victim.parent.mkdir()
    victim.write_text("secret\n")
    victim.chmod(0o600)
    decoy = tmp_path / "decoy"
    decoy.mkdir()
    pq.write_table(pa.table({"x": [1]}), decoy / "victim.parquet")
    (decoy / "victim.parquet").chmod(0o644)

    scan_dir = await _init_scan(tmp_path, "pkg/victim")
    (scan_dir / "pkg").mkdir()
    pq.write_table(pa.table({"x": [4, 5, 6]}), scan_dir / "pkg" / "victim.parquet")

    real_open = os.open

    def open_then_swap(path: Any, flags: int, mode: int = 0o777) -> int:
        fd = real_open(path, flags, mode)
        name = Path(path).name
        if name.startswith(".scout-") and (scan_dir / "pkg").is_dir():
            (scan_dir / "pkg").rename(scan_dir / "pkg.old")
            (scan_dir / "pkg").symlink_to(decoy, target_is_directory=True)
            (decoy / name).symlink_to(victim)
        return fd

    monkeypatch.setattr(os, "open", open_then_swap)
    try:
        await FileRecorder.sync(scan_dir.as_posix(), complete=True)
    except Exception:
        pass
    monkeypatch.undo()

    assert victim.stat().st_mode & 0o777 == 0o600
