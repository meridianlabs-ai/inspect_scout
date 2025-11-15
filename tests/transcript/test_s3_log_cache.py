"""Tests for transcript caching without hitting actual S3."""

import json
from contextlib import contextmanager
from typing import Any, Iterator, Sequence
from unittest.mock import Mock, patch

import pandas as pd
import pytest
from inspect_ai._util.file import FileInfo
from inspect_ai._util.kvstore import KVStore
from inspect_ai.log._file import EvalLogInfo
from inspect_scout._transcript.caching import (
    _get_cached_df,
    _put_cached_df,
    _resolve_logs,
    samples_df_with_caching,
)


def create_evalloginfo(name: str) -> EvalLogInfo:
    """Helper to create EvalLogInfo with all required fields."""
    return EvalLogInfo(
        name=name,
        type="file",
        size=1024,
        mtime=1234567890.0,
        task="test_task",
        task_id="task_123",
        suffix=".json",
    )


# Fixtures
@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Sample DataFrame with typical transcript structure."""
    return pd.DataFrame(
        {
            "eval_id": ["eval_001", "eval_001"],
            "task_name": ["test_task", "test_task"],
            "model": ["gpt-4", "gpt-4"],
            "id": ["sample_001", "sample_002"],
            "score": [0.85, 0.92],
        }
    )


@pytest.fixture
def mock_kvstore() -> Iterator[Mock]:
    """Mock KVStore that uses in-memory dict."""

    class MockKVStore(KVStore):
        def __init__(self) -> None:
            self._store: dict[str, str] = {}

        def get(self, key: str) -> str | None:
            return self._store.get(key)

        def put(self, key: str, value: str) -> None:
            self._store[key] = value

        def delete(self, key: str) -> bool:
            if key in self._store:
                del self._store[key]
                return True
            return False

        def clear(self) -> None:
            self._store.clear()

        def keys(self) -> list[str]:
            return list(self._store.keys())

    # Create single shared store instance for the test
    shared_store = MockKVStore()

    @contextmanager
    def mock_inspect_kvstore(name: str) -> Iterator[MockKVStore]:
        yield shared_store

    with patch(
        "inspect_scout._transcript.caching.inspect_kvstore",
        side_effect=mock_inspect_kvstore,
    ) as mock:
        yield mock


@pytest.fixture
def mock_filesystem() -> Iterator[Mock]:
    """Mock filesystem that returns fake FileInfo objects."""

    def create_file_info(
        path: str, file_type: str = "file", etag: str | None = None
    ) -> FileInfo:
        return FileInfo(
            name=path,
            size=1024,
            type=file_type,
            mtime=1234567890.0,
            etag=etag,
        )

    class MockFilesystem:
        def __init__(self, path: str):
            self.path = path

        def info(self, path: str) -> FileInfo:
            # S3 files get etags, local files don't
            if path.startswith("s3://"):
                # Extract a stable etag from the path for testing
                etag = f"etag_{hash(path) % 10000}"
                return create_file_info(path, "file", etag)
            else:
                return create_file_info(path, "file", None)

        def ls(self, path: str, recursive: bool = False) -> list[FileInfo]:
            # Simulate directory listing
            if path == "s3://bucket/dir/":
                return [
                    create_file_info("s3://bucket/dir/log1.json", "file", "etag_001"),
                    create_file_info("s3://bucket/dir/log2.json", "file", "etag_002"),
                ]
            return []

    def mock_log_files_from_ls(
        file_infos: list[FileInfo], sort: bool = True
    ) -> list[EvalLogInfo]:
        """Mock log_files_from_ls to convert FileInfo to EvalLogInfo."""
        return [
            create_evalloginfo(fi.name)
            for fi in file_infos
            if fi.type == "file" and fi.name.endswith(".json")
        ]

    with (
        patch(
            "inspect_scout._transcript.caching.filesystem",
            side_effect=lambda path: MockFilesystem(path),
        ),
        patch(
            "inspect_scout._transcript.caching.log_files_from_ls",
            side_effect=mock_log_files_from_ls,
        ),
    ):
        yield Mock()


@pytest.fixture
def mock_reader() -> Mock:
    """Mock reader function that tracks calls and returns DataFrames."""
    call_counter = {"count": 0}

    def reader_impl(paths: Sequence[str]) -> pd.DataFrame:
        if not paths:
            return pd.DataFrame({"eval_id": [], "id": [], "score": []})
        # Return unique DataFrame per call using call counter
        call_num = call_counter["count"]
        call_counter["count"] += 1
        return pd.DataFrame(
            {
                "eval_id": [f"eval_{call_num}"],
                "id": [f"sample_{call_num}"],
                "score": [0.5 + call_num * 0.1],
            }
        )

    return Mock(side_effect=reader_impl)


# Tests for resolve_logs_with_etag


def test_resolve_logs_with_etag_single_file(mock_filesystem: Mock) -> None:
    """Single S3 file resolves to (path, etag) tuple."""
    result = _resolve_logs("s3://bucket/log.json")
    assert len(result) == 1
    path, etag = result[0]
    assert path == "s3://bucket/log.json"
    assert etag is not None
    assert etag.startswith("etag_")


def test_resolve_logs_with_etag_directory(mock_filesystem: Mock) -> None:
    """Directory expands to multiple (path, etag) tuples."""

    # Patch filesystem to return directory type
    def mock_fs(path: str) -> Any:
        fs = Mock()
        if path == "s3://bucket/dir/":
            fs.info.return_value = FileInfo(
                name="s3://bucket/dir/",
                size=0,
                type="directory",
                mtime=1234567890.0,
                etag=None,
            )
            fs.ls.return_value = [
                FileInfo(
                    name="s3://bucket/dir/log1.json",
                    size=1024,
                    type="file",
                    mtime=1234567890.0,
                    etag="etag_001",
                ),
                FileInfo(
                    name="s3://bucket/dir/log2.json",
                    size=2048,
                    type="file",
                    mtime=1234567890.0,
                    etag="etag_002",
                ),
            ]
        return fs

    with patch("inspect_scout._transcript.caching.filesystem", side_effect=mock_fs):
        result = _resolve_logs("s3://bucket/dir/")
        assert len(result) == 2
        paths = [r[0] for r in result]
        etags = [r[1] for r in result]
        assert "s3://bucket/dir/log1.json" in paths
        assert "s3://bucket/dir/log2.json" in paths
        assert "etag_001" in etags
        assert "etag_002" in etags


def test_resolve_logs_with_etag_local_file(mock_filesystem: Mock) -> None:
    """Local file resolves with fallback etag (mtime:size)."""
    result = _resolve_logs("/local/log.json")
    assert len(result) == 1
    path, etag = result[0]
    assert path == "/local/log.json"
    # Local files without native etag should get mtime:size fallback
    assert etag == "1234567890.0:1024"


def test_resolve_logs_with_etag_mixed_paths(mock_filesystem: Mock) -> None:
    """Mixed S3 and local paths resolve correctly."""
    result = _resolve_logs(["s3://bucket/log.json", "/local/log.json"])
    assert len(result) == 2
    # S3 file has native etag
    s3_result = [r for r in result if r[0].startswith("s3://")][0]
    assert s3_result[1] is not None
    assert s3_result[1].startswith("etag_")
    # Local file has fallback etag (mtime:size)
    local_result = [r for r in result if r[0].startswith("/local")][0]
    assert local_result[1] == "1234567890.0:1024"


def test_resolve_logs_with_etag_evalloginfo(mock_filesystem: Mock) -> None:
    """EvalLogInfo object resolves correctly."""
    eval_log_info = create_evalloginfo("s3://bucket/log.json")
    result = _resolve_logs(eval_log_info)
    assert len(result) == 1
    path, etag = result[0]
    assert path == "s3://bucket/log.json"
    assert etag is not None


# Tests for get_cached_df


def test_get_cached_df_cache_miss(mock_kvstore: Mock) -> None:
    """Cache miss returns None."""
    with mock_kvstore("test") as kvstore:
        result = _get_cached_df(kvstore, "s3://bucket/log.json", "etag123")
        assert result is None


def test_get_cached_df_cache_hit_matching_etag(
    mock_kvstore: Mock, sample_df: pd.DataFrame
) -> None:
    """Cache hit with matching etag returns DataFrame."""
    with mock_kvstore("test") as kvstore:
        # Populate cache
        cached_data = {
            "etag": "etag123",
            "records": json.loads(sample_df.to_json(orient="records")),
        }
        kvstore.put("s3://bucket/log.json", json.dumps(cached_data))

        # Retrieve
        result = _get_cached_df(kvstore, "s3://bucket/log.json", "etag123")
        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert list(result["eval_id"]) == ["eval_001", "eval_001"]


def test_get_cached_df_cache_invalidation_stale_etag(
    mock_kvstore: Mock, sample_df: pd.DataFrame
) -> None:
    """Stale etag returns None (cache invalidation)."""
    with mock_kvstore("test") as kvstore:
        # Populate cache with old etag
        cached_data = {
            "etag": "old_etag",
            "records": json.loads(sample_df.to_json(orient="records")),
        }
        kvstore.put("s3://bucket/log.json", json.dumps(cached_data))

        # Try to retrieve with different etag
        result = _get_cached_df(kvstore, "s3://bucket/log.json", "new_etag")
        assert result is None


def test_get_cached_df_corrupted_json(mock_kvstore: Mock) -> None:
    """Corrupted JSON returns None gracefully."""
    with mock_kvstore("test") as kvstore:
        kvstore.put("s3://bucket/log.json", "not valid json {{{")
        result = _get_cached_df(kvstore, "s3://bucket/log.json", "etag123")
        assert result is None


def test_get_cached_df_empty_records(mock_kvstore: Mock) -> None:
    """Empty records list returns None."""
    with mock_kvstore("test") as kvstore:
        cached_data = {"etag": "etag123", "records": []}
        kvstore.put("s3://bucket/log.json", json.dumps(cached_data))
        result = _get_cached_df(kvstore, "s3://bucket/log.json", "etag123")
        assert result is None


def test_get_cached_df_missing_etag_field(
    mock_kvstore: Mock, sample_df: pd.DataFrame
) -> None:
    """Missing etag field returns None."""
    with mock_kvstore("test") as kvstore:
        cached_data = {
            "records": json.loads(sample_df.to_json(orient="records")),
        }
        kvstore.put("s3://bucket/log.json", json.dumps(cached_data))
        result = _get_cached_df(kvstore, "s3://bucket/log.json", "etag123")
        assert result is None


# Tests for put_cached_df


def test_put_cached_df_successful_write(
    mock_kvstore: Mock, sample_df: pd.DataFrame
) -> None:
    """Successful write stores DataFrame with etag."""
    with mock_kvstore("test") as kvstore:
        _put_cached_df(kvstore, "s3://bucket/log.json", "etag123", sample_df)

        # Verify stored data
        stored = kvstore.get("s3://bucket/log.json")
        assert stored is not None
        data = json.loads(stored)
        assert data["etag"] == "etag123"
        assert "records" in data
        assert len(data["records"]) == 2


def test_put_cached_df_dataframe_roundtrip(
    mock_kvstore: Mock, sample_df: pd.DataFrame
) -> None:
    """Put then get returns equivalent DataFrame."""
    with mock_kvstore("test") as kvstore:
        _put_cached_df(kvstore, "s3://bucket/log.json", "etag123", sample_df)
        result = _get_cached_df(kvstore, "s3://bucket/log.json", "etag123")

        assert result is not None
        # Compare values (ignore dtypes which may differ after JSON roundtrip)
        pd.testing.assert_frame_equal(result, sample_df, check_dtype=False)


def test_put_cached_df_handles_write_errors(sample_df: pd.DataFrame) -> None:
    """Write errors are silently ignored."""

    class FailingKVStore(KVStore):
        def __init__(self) -> None:
            # Don't call super().__init__() to avoid needing filename
            self._store: dict[str, str] = {}

        def get(self, key: str) -> str | None:
            return None

        def put(self, key: str, value: str) -> None:
            raise RuntimeError("Storage failed")

        def delete(self, key: str) -> bool:
            return False

        def clear(self) -> None:
            pass

        def keys(self) -> list[str]:
            return []

    kvstore = FailingKVStore()
    # Should not raise
    _put_cached_df(kvstore, "s3://bucket/log.json", "etag123", sample_df)


# Tests for with_transcript_caching


def test_with_transcript_caching_s3_cache_miss_then_hit(
    mock_kvstore: Mock, mock_filesystem: Mock, mock_reader: Mock
) -> None:
    """First call reads S3 and caches, second call uses cache."""
    # First call - cache miss
    result1 = samples_df_with_caching(mock_reader, "s3://bucket/log.json")
    assert mock_reader.call_count == 1
    assert len(result1) == 1

    # Second call - cache hit
    result2 = samples_df_with_caching(mock_reader, "s3://bucket/log.json")
    # Reader should not be called again
    assert mock_reader.call_count == 1
    # Results should be same
    pd.testing.assert_frame_equal(result1, result2, check_dtype=False)


def test_with_transcript_caching_s3_etag_changed(
    mock_kvstore: Mock, mock_filesystem: Mock, mock_reader: Mock
) -> None:
    """Etag change invalidates cache and re-reads."""
    # First call
    _ = samples_df_with_caching(mock_reader, "s3://bucket/log.json")
    assert mock_reader.call_count == 1

    # Simulate etag change by modifying filesystem mock
    def new_mock_fs(path: str) -> Any:
        fs = Mock()
        fs.info.return_value = FileInfo(
            name=path,
            size=1024,
            type="file",
            mtime=1234567890.0,
            etag="new_etag_changed",
        )
        return fs

    with patch("inspect_scout._transcript.caching.filesystem", side_effect=new_mock_fs):
        # Second call with changed etag
        _ = samples_df_with_caching(mock_reader, "s3://bucket/log.json")
        # Reader should be called again
        assert mock_reader.call_count == 2


def test_with_transcript_caching_local_files_bypass_cache(
    mock_kvstore: Mock, mock_filesystem: Mock, mock_reader: Mock
) -> None:
    """Local files now cached with fallback etag."""
    # Call with local file
    _ = samples_df_with_caching(mock_reader, "/local/log.json")
    assert mock_reader.call_count == 1
    # Called with single-item list
    mock_reader.assert_called_once_with(["/local/log.json"])


def test_with_transcript_caching_mixed_s3_and_local(
    mock_kvstore: Mock, mock_filesystem: Mock, mock_reader: Mock
) -> None:
    """Mixed S3 and local files handled correctly."""
    result = samples_df_with_caching(
        mock_reader, ["s3://bucket/log.json", "/local/log.json"]
    )

    # Reader called for S3 file individually and local file
    assert mock_reader.call_count == 2
    # Result is concatenation
    assert len(result) == 2


def test_with_transcript_caching_empty_input(
    mock_kvstore: Mock, mock_filesystem: Mock, mock_reader: Mock
) -> None:
    """Empty input returns empty DataFrame from reader."""
    result = samples_df_with_caching(mock_reader, [])
    assert mock_reader.call_count == 1
    mock_reader.assert_called_once_with([])
    assert len(result) == 0


def test_with_transcript_caching_error_fallback(
    mock_kvstore: Mock, mock_filesystem: Mock
) -> None:
    """Caching error falls back to direct reader call."""

    # Create reader that works but filesystem that fails
    def working_reader(paths: Sequence[str]) -> pd.DataFrame:
        return pd.DataFrame({"eval_id": ["eval_001"], "score": [0.5]})

    reader_mock = Mock(side_effect=working_reader)

    with patch(
        "inspect_scout._transcript.caching.filesystem",
        side_effect=RuntimeError("Filesystem failed"),
    ):
        result = samples_df_with_caching(reader_mock, "s3://bucket/log.json")

        # Should fall back to reader
        assert reader_mock.call_count == 1
        assert len(result) == 1


def test_with_transcript_caching_concat_multiple_s3_files(
    mock_kvstore: Mock, mock_filesystem: Mock, mock_reader: Mock
) -> None:
    """Multiple S3 files concatenated into single DataFrame."""
    result = samples_df_with_caching(
        mock_reader, ["s3://bucket/log1.json", "s3://bucket/log2.json"]
    )

    # Reader called once per S3 file
    assert mock_reader.call_count == 2
    # Result is concatenation
    assert len(result) == 2
    # Should have rows from both calls
    assert "eval_0" in result["eval_id"].values
    assert "eval_1" in result["eval_id"].values


# Tests for EvalLogInfo handling


def test_with_transcript_caching_single_evalloginfo(
    mock_kvstore: Mock, mock_filesystem: Mock, mock_reader: Mock
) -> None:
    """Single EvalLogInfo object handled correctly."""
    eval_log_info = create_evalloginfo("s3://bucket/log.json")

    result = samples_df_with_caching(mock_reader, eval_log_info)
    assert mock_reader.call_count == 1
    assert len(result) == 1


def test_with_transcript_caching_list_of_evalloginfo(
    mock_kvstore: Mock, mock_filesystem: Mock, mock_reader: Mock
) -> None:
    """List of EvalLogInfo objects handled correctly."""
    logs = [
        create_evalloginfo("s3://bucket/log1.json"),
        create_evalloginfo("s3://bucket/log2.json"),
    ]

    result = samples_df_with_caching(mock_reader, logs)
    assert mock_reader.call_count == 2
    assert len(result) == 2


def test_with_transcript_caching_mixed_evalloginfo_and_str(
    mock_kvstore: Mock, mock_filesystem: Mock, mock_reader: Mock
) -> None:
    """Mixed EvalLogInfo and string paths handled correctly."""
    logs: list[EvalLogInfo | str] = [
        create_evalloginfo("s3://bucket/log1.json"),
        "s3://bucket/log2.json",
    ]

    result = samples_df_with_caching(mock_reader, logs)
    assert mock_reader.call_count == 2
    assert len(result) == 2
