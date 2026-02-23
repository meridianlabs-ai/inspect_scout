import json
from unittest.mock import AsyncMock, patch

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from inspect_scout._recorder.buffer import SCAN_SUMMARY, _sanitize_component
from inspect_scout._recorder.file import _seed_buffer_from_remote
from inspect_scout._scanspec import ScannerSpec, ScanSpec
from upath import UPath


def _minimal_spec(scanners: list[str]) -> ScanSpec:
    return ScanSpec(
        scan_name="test",
        scanners={s: ScannerSpec(name=s) for s in scanners},
        transcripts=None,
    )


def _write_parquet(path: UPath) -> bytes:
    """Write a minimal parquet file and return its bytes."""
    table = pa.table({"transcript_id": ["t1", "t2"], "value": ["a", "b"]})
    pq.write_table(table, path.as_posix())
    return path.read_bytes()


def _summary_json() -> bytes:
    return json.dumps({"complete": False, "scanners": ["s1"]}).encode()


@pytest.mark.asyncio
async def test_skips_when_buffer_dir_exists(tmp_path: UPath) -> None:
    buffer_dir = UPath(tmp_path / "buffer")
    buffer_dir.mkdir()
    scan_dir = UPath(tmp_path / "scan")
    spec = _minimal_spec(["s1"])
    synced_ids = {("t1", "s1")}

    with patch("inspect_scout._recorder.file.AsyncFilesystem") as mock_fs_cls:
        await _seed_buffer_from_remote(scan_dir, spec, buffer_dir, synced_ids)
        mock_fs_cls.assert_not_called()


@pytest.mark.asyncio
async def test_noop_when_no_synced_ids(tmp_path: UPath) -> None:
    buffer_dir = UPath(tmp_path / "buffer")
    scan_dir = UPath(tmp_path / "scan")
    spec = _minimal_spec(["s1"])

    await _seed_buffer_from_remote(scan_dir, spec, buffer_dir, synced_ids=set())

    assert not buffer_dir.exists()


@pytest.mark.asyncio
async def test_downloads_remote_parquets_and_summary(tmp_path: UPath) -> None:
    buffer_dir = UPath(tmp_path / "buffer")
    scan_dir = UPath(tmp_path / "scan")
    scan_dir.mkdir()
    spec = _minimal_spec(["s1"])
    synced_ids = {("t1", "s1")}

    parquet_path = scan_dir / "s1.parquet"
    parquet_bytes = _write_parquet(parquet_path)
    summary_bytes = _summary_json()

    async def fake_read_file(path: str) -> bytes:
        if path.endswith(".parquet"):
            return parquet_bytes
        if path.endswith(SCAN_SUMMARY):
            return summary_bytes
        raise FileNotFoundError(path)

    mock_fs = AsyncMock()
    mock_fs.read_file = AsyncMock(side_effect=fake_read_file)
    mock_fs.__aenter__ = AsyncMock(return_value=mock_fs)
    mock_fs.__aexit__ = AsyncMock(return_value=False)

    with patch("inspect_scout._recorder.file.AsyncFilesystem", return_value=mock_fs):
        await _seed_buffer_from_remote(scan_dir, spec, buffer_dir, synced_ids)

    synced_parquet = (
        buffer_dir / f"scanner={_sanitize_component('s1')}" / "_synced.parquet"
    )
    assert synced_parquet.exists()
    assert synced_parquet.read_bytes() == parquet_bytes

    local_summary = buffer_dir / SCAN_SUMMARY
    assert local_summary.exists()
    assert local_summary.read_bytes() == summary_bytes
