"""Tests for transcript caching."""

from contextlib import contextmanager
from typing import Any, Iterator
from unittest.mock import Mock, patch

import pandas as pd
import pytest
from inspect_ai._util.file import FileInfo
from inspect_ai._util.kvstore import KVStore
from inspect_ai.log._file import EvalLogInfo
from inspect_scout._transcript.caching import samples_df_with_caching


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
            self.conn = self._create_mock_conn()

        def _create_mock_conn(self) -> Mock:
            """Create mock connection with execute() and commit() methods."""
            conn = Mock()

            def execute(sql: str) -> None:
                if sql == "DELETE FROM kv_store":
                    self._store.clear()

            conn.execute = execute
            conn.commit = Mock()
            return conn

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

    shared_store = MockKVStore()

    @contextmanager
    def mock_inspect_kvstore(name: str, **kwargs: Any) -> Iterator[MockKVStore]:
        yield shared_store

    with patch(
        "inspect_scout._transcript.caching.inspect_kvstore",
        side_effect=mock_inspect_kvstore,
    ) as mock:
        yield mock


@pytest.fixture
def mock_filesystem() -> Iterator[Mock]:
    """Mock filesystem that returns FileInfo with/without etag."""

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
            # Directories return directory type
            if path.endswith("/"):
                return create_file_info(path, "directory", None)
            # S3 files get etags, local files don't
            if path.startswith("s3://"):
                etag = f"etag_{hash(path) % 10000}"
                return create_file_info(path, "file", etag)
            return create_file_info(path, "file", None)

        def ls(self, path: str, recursive: bool = False) -> list[FileInfo]:
            # Return list of files for directory listings
            if path == "s3://bucket/dir/":
                return [
                    create_file_info("s3://bucket/dir/log1.json", "file", "etag_1"),
                    create_file_info("s3://bucket/dir/log2.json", "file", "etag_2"),
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

    def reader_impl(path: str) -> pd.DataFrame:
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


@pytest.mark.parametrize(
    "logs_input,expected_calls,expected_rows",
    [
        ("s3://bucket/log.json", 1, 1),
        (["s3://bucket/log1.json", "s3://bucket/log2.json"], 2, 2),
        ([create_evalloginfo("s3://bucket/log.json"), "s3://bucket/log2.json"], 2, 2),
    ],
)
def test_samples_df_with_caching_reads_and_concatenates(
    mock_kvstore: Mock,
    mock_filesystem: Mock,
    mock_reader: Mock,
    logs_input: Any,
    expected_calls: int,
    expected_rows: int,
) -> None:
    """Reads logs and concatenates into single DataFrame."""
    result = samples_df_with_caching(mock_reader, logs_input)
    assert mock_reader.call_count == expected_calls
    assert len(result) == expected_rows


def test_samples_df_with_caching_empty_input(
    mock_kvstore: Mock, mock_filesystem: Mock, mock_reader: Mock
) -> None:
    """Empty input returns empty DataFrame."""
    result = samples_df_with_caching(mock_reader, [])
    assert mock_reader.call_count == 0
    assert len(result) == 0


def test_samples_df_with_caching_uses_cache_on_second_read(
    mock_kvstore: Mock, mock_filesystem: Mock, mock_reader: Mock
) -> None:
    """Second read with same etag uses cache, doesn't call reader."""
    result1 = samples_df_with_caching(mock_reader, "s3://bucket/log.json")
    assert mock_reader.call_count == 1

    result2 = samples_df_with_caching(mock_reader, "s3://bucket/log.json")
    assert mock_reader.call_count == 1
    pd.testing.assert_frame_equal(result1, result2, check_dtype=False)


def test_samples_df_with_caching_invalidates_on_etag_change(
    mock_kvstore: Mock, mock_filesystem: Mock, mock_reader: Mock
) -> None:
    """Etag change invalidates cache and triggers re-read."""
    samples_df_with_caching(mock_reader, "s3://bucket/log.json")
    assert mock_reader.call_count == 1

    # Simulate etag change
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
        samples_df_with_caching(mock_reader, "s3://bucket/log.json")
        assert mock_reader.call_count == 2


def test_samples_df_with_caching_dataframe_roundtrip(
    mock_kvstore: Mock, mock_filesystem: Mock, sample_df: pd.DataFrame
) -> None:
    """Cached DataFrame preserves data through JSON serialization."""
    reader = Mock(return_value=sample_df)

    result1 = samples_df_with_caching(reader, "s3://bucket/log.json")
    result2 = samples_df_with_caching(reader, "s3://bucket/log.json")

    assert reader.call_count == 1
    pd.testing.assert_frame_equal(result1, sample_df, check_dtype=False)
    pd.testing.assert_frame_equal(result2, sample_df, check_dtype=False)


def test_samples_df_with_caching_files_without_etag(
    mock_kvstore: Mock, mock_filesystem: Mock, mock_reader: Mock
) -> None:
    """Files without native etag use mtime:size fallback for caching."""
    result1 = samples_df_with_caching(mock_reader, "/local/log.json")
    assert mock_reader.call_count == 1

    result2 = samples_df_with_caching(mock_reader, "/local/log.json")
    assert mock_reader.call_count == 1
    pd.testing.assert_frame_equal(result1, result2, check_dtype=False)


def test_samples_df_with_caching_directory_input(
    mock_kvstore: Mock, mock_filesystem: Mock, mock_reader: Mock
) -> None:
    """Directory input expands to multiple files."""
    result = samples_df_with_caching(mock_reader, "s3://bucket/dir/")
    assert mock_reader.call_count == 2
    assert len(result) == 2


def test_cached_dataframe_loses_datetime_dtype(mock_kvstore: Mock) -> None:
    """Cache roundtrip should preserve datetime dtype."""
    from inspect_scout._transcript.caching import _get_cached_df, _put_cached_df

    # Create DataFrame with datetime column
    original_df = pd.DataFrame(
        {
            "eval_id": ["eval_001"],
            "eval_created": [pd.Timestamp("2024-01-01T10:00:00")],
            "score": [0.85],
        }
    )
    assert original_df["eval_created"].dtype == "datetime64[ns]"

    # Roundtrip through cache
    path = "test.json"
    etag = "test_etag"

    # Use the mock kvstore directly
    from unittest.mock import MagicMock

    kvstore = MagicMock()
    stored_value = None

    def mock_put(key: str, value: str) -> None:
        nonlocal stored_value
        stored_value = value

    def mock_get(key: str) -> str | None:
        return stored_value

    kvstore.put = mock_put
    kvstore.get = mock_get

    _put_cached_df(kvstore, path, etag, original_df)
    cached_df = _get_cached_df(kvstore, path, etag)

    # Cached DataFrame should preserve datetime dtype
    assert cached_df is not None
    assert cached_df["eval_created"].dtype == "datetime64[ns]"

    # Values should be preserved
    pd.testing.assert_frame_equal(cached_df, original_df)


def test_cache_version_invalidation(
    mock_kvstore: Mock, mock_filesystem: Mock, mock_reader: Mock
) -> None:
    """Cache version mismatch clears cache and re-reads data."""
    from inspect_scout._transcript.caching import _CACHE_VERSION

    # First call populates cache with current version
    result1 = samples_df_with_caching(mock_reader, "s3://bucket/log.json")
    assert mock_reader.call_count == 1

    # Second call uses cache (same version)
    result2 = samples_df_with_caching(mock_reader, "s3://bucket/log.json")
    assert mock_reader.call_count == 1
    pd.testing.assert_frame_equal(result1, result2, check_dtype=False)

    # Simulate version change by patching _CACHE_VERSION
    with patch(
        "inspect_scout._transcript.caching._CACHE_VERSION",
        _CACHE_VERSION + 1,
    ):
        # Third call triggers cache invalidation and re-read
        result3 = samples_df_with_caching(mock_reader, "s3://bucket/log.json")
        assert mock_reader.call_count == 2

        # Fourth call uses cache again (with new version)
        result4 = samples_df_with_caching(mock_reader, "s3://bucket/log.json")
        assert mock_reader.call_count == 2
        pd.testing.assert_frame_equal(result3, result4, check_dtype=False)
