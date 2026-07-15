"""Tests for transcript caching."""

from contextlib import contextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Iterator
from unittest.mock import Mock, patch

import pandas as pd
import pytest
from inspect_ai._util.file import FileInfo
from inspect_ai._util.kvstore import KVStore
from inspect_ai.analysis import samples_df
from inspect_ai.log._file import EvalLogInfo
from inspect_scout._transcript.caching import samples_df_with_caching
from inspect_scout._transcript.eval_log import TranscriptColumns

LOGS_DIR = Path(__file__).parent.parent / "recorder" / "logs"


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
            "task": ["test_task", "test_task"],
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


def create_file_info(
    path: str, file_type: str = "file", etag: str | None = None
) -> FileInfo:
    """Helper to create FileInfo with all required fields."""
    return FileInfo(
        name=path,
        size=1024,
        type=file_type,
        mtime=1234567890.0,
        etag=etag,
    )


class MockAsyncFilesystem:
    """AsyncFilesystem stand-in: paths ending in "/" are directories, S3 files get etags."""

    async def __aenter__(self) -> "MockAsyncFilesystem":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        return None

    async def info(self, path: str) -> FileInfo:
        # Directories return directory type
        if path.endswith("/"):
            return create_file_info(path, "directory", None)
        # S3 files get etags, local files don't
        if path.startswith("s3://"):
            etag = f"etag_{hash(path) % 10000}"
            return create_file_info(path, "file", etag)
        return create_file_info(path, "file", None)

    async def iter_files(
        self,
        path: str,
        pattern: str = "*",
        *,
        recursive: bool = False,
        detail: bool = False,
    ) -> AsyncIterator[FileInfo]:
        # Return list of files for directory listings
        if path.rstrip("/") == "s3://bucket/dir":
            yield create_file_info("s3://bucket/dir/log1.json", "file", "etag_1")
            yield create_file_info("s3://bucket/dir/log2.json", "file", "etag_2")


def mock_log_files_from_ls(
    file_infos: list[FileInfo], sort: bool = True
) -> list[EvalLogInfo]:
    """Mock log_files_from_ls to convert FileInfo to EvalLogInfo."""
    return [
        create_evalloginfo(fi.name)
        for fi in file_infos
        if fi.type == "file" and fi.name.endswith(".json")
    ]


@pytest.fixture
def mock_filesystem() -> Iterator[Mock]:
    """Mock AsyncFilesystem that returns FileInfo with/without etag."""
    with (
        patch(
            "inspect_scout._transcript.caching.AsyncFilesystem",
            MockAsyncFilesystem,
        ),
        patch(
            "inspect_scout._transcript.caching.log_files_from_ls",
            side_effect=mock_log_files_from_ls,
        ),
    ):
        yield Mock()


def _paths_read(mock: Mock) -> list[str]:
    """All paths passed to a reader mock, across calls, in order."""
    return [call.args[0] for call in mock.call_args_list]


@pytest.fixture
def mock_reader() -> Mock:
    """Mock reader function that tracks calls and returns DataFrames."""
    path_counter = {"count": 0}

    def reader_impl(path: str) -> pd.DataFrame:
        path_num = path_counter["count"]
        path_counter["count"] += 1
        return pd.DataFrame(
            {
                "eval_id": [f"eval_{path_num}"],
                "id": [f"sample_{path_num}"],
                "score": [0.5 + path_num * 0.1],
            }
        )

    return Mock(side_effect=reader_impl)


@pytest.mark.parametrize(
    "logs_input,expected_paths,expected_rows",
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
    expected_paths: int,
    expected_rows: int,
) -> None:
    """Reads logs and concatenates into single DataFrame."""
    result = samples_df_with_caching(mock_reader, logs_input)
    assert len(_paths_read(mock_reader)) == expected_paths
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
    assert len(_paths_read(mock_reader)) == 1

    result2 = samples_df_with_caching(mock_reader, "s3://bucket/log.json")
    assert len(_paths_read(mock_reader)) == 1
    pd.testing.assert_frame_equal(result1, result2, check_dtype=False)


def test_samples_df_with_caching_invalidates_on_etag_change(
    mock_kvstore: Mock, mock_filesystem: Mock, mock_reader: Mock
) -> None:
    """Etag change invalidates cache and triggers re-read."""
    samples_df_with_caching(mock_reader, "s3://bucket/log.json")
    assert len(_paths_read(mock_reader)) == 1

    # Simulate etag change
    class ChangedEtagFilesystem(MockAsyncFilesystem):
        async def info(self, path: str) -> FileInfo:
            return create_file_info(path, "file", "new_etag_changed")

    with patch(
        "inspect_scout._transcript.caching.AsyncFilesystem", ChangedEtagFilesystem
    ):
        samples_df_with_caching(mock_reader, "s3://bucket/log.json")
        assert len(_paths_read(mock_reader)) == 2


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
    assert len(_paths_read(mock_reader)) == 1

    result2 = samples_df_with_caching(mock_reader, "/local/log.json")
    assert len(_paths_read(mock_reader)) == 1
    pd.testing.assert_frame_equal(result1, result2, check_dtype=False)


def test_samples_df_with_caching_directory_input(
    mock_kvstore: Mock, mock_filesystem: Mock, mock_reader: Mock
) -> None:
    """Directory input expands to multiple files."""
    result = samples_df_with_caching(mock_reader, "s3://bucket/dir/")
    assert len(_paths_read(mock_reader)) == 2
    assert len(result) == 2


def test_samples_df_with_caching_caches_per_path(
    mock_kvstore: Mock, mock_filesystem: Mock
) -> None:
    """Each path gets its own cache entry, aligned with its data, in input order."""
    paths = [f"s3://bucket/log{i}.json" for i in range(4)]

    def reader(path: str) -> pd.DataFrame:
        return pd.DataFrame({"id": [path]})

    result = samples_df_with_caching(reader, paths)
    assert result["id"].tolist() == paths

    def fail_reader(path: str) -> pd.DataFrame:
        raise AssertionError("all paths should be cache hits")

    for path in paths:
        cached = samples_df_with_caching(fail_reader, path)
        assert cached["id"].tolist() == [path]


def test_samples_df_with_caching_failure_preserves_completed_reads(
    mock_kvstore: Mock, mock_filesystem: Mock
) -> None:
    """A failing read preserves cache entries for reads that succeeded."""
    paths = [f"s3://bucket/log{i}.json" for i in range(4)]

    def failing_reader(path: str) -> pd.DataFrame:
        if path == paths[2]:
            raise ValueError("boom")
        return pd.DataFrame({"id": [path]})

    with pytest.raises(ValueError, match="boom"):
        samples_df_with_caching(failing_reader, paths)

    read_paths: list[str] = []

    def reader(path: str) -> pd.DataFrame:
        read_paths.append(path)
        return pd.DataFrame({"id": [path]})

    result = samples_df_with_caching(reader, paths)
    assert read_paths == [paths[2]]  # the other paths came from the cache
    assert sorted(result["id"].tolist()) == sorted(paths)


def test_resolve_logs_concurrent_info_preserves_association(
    mock_kvstore: Mock,
) -> None:
    """Concurrent info fetches keep each etag associated with its path."""
    import anyio

    paths = [f"s3://bucket/log{i}.json" for i in range(4)]
    # earlier paths take longer, so completion order inverts input order
    delays = {path: 0.02 * (len(paths) - i) for i, path in enumerate(paths)}
    etags = {path: f"etag-{i}" for i, path in enumerate(paths)}

    class DelayedInfoFilesystem(MockAsyncFilesystem):
        async def info(self, path: str) -> FileInfo:
            await anyio.sleep(delays[path])
            return create_file_info(path, "file", etags[path])

    def reader(path: str) -> pd.DataFrame:
        return pd.DataFrame({"id": [path]})

    with (
        patch(
            "inspect_scout._transcript.caching.AsyncFilesystem",
            DelayedInfoFilesystem,
        ),
        patch(
            "inspect_scout._transcript.caching.log_files_from_ls",
            side_effect=lambda file_infos, sort: [
                create_evalloginfo(fi.name) for fi in file_infos
            ],
        ),
    ):
        result = samples_df_with_caching(reader, paths)
        assert result["id"].tolist() == paths

        # invalidate a single path's etag: exactly that path is re-read
        etags[paths[1]] = "etag-changed"
        read_paths: list[str] = []

        def reader2(path: str) -> pd.DataFrame:
            read_paths.append(path)
            return pd.DataFrame({"id": [path]})

        samples_df_with_caching(reader2, paths)
        assert read_paths == [paths[1]]


def test_resolve_logs_s3_directory_prefix(
    mock_kvstore: Mock, mock_reader: Mock
) -> None:
    """A directory prefix where info() raises (S3) expands via a listing sweep."""

    class S3PrefixFilesystem(MockAsyncFilesystem):
        async def info(self, path: str) -> FileInfo:
            raise FileNotFoundError(path)

    with (
        patch("inspect_scout._transcript.caching.AsyncFilesystem", S3PrefixFilesystem),
        patch(
            "inspect_scout._transcript.caching.log_files_from_ls",
            side_effect=mock_log_files_from_ls,
        ),
    ):
        result = samples_df_with_caching(mock_reader, "s3://bucket/dir")
        assert sorted(_paths_read(mock_reader)) == [
            "s3://bucket/dir/log1.json",
            "s3://bucket/dir/log2.json",
        ]
        assert len(result) == 2


def test_resolve_logs_missing_path_raises(mock_kvstore: Mock) -> None:
    """A path where info() raises and nothing lists re-raises the info error."""

    class MissingPathFilesystem(MockAsyncFilesystem):
        async def info(self, path: str) -> FileInfo:
            raise FileNotFoundError(path)

        async def iter_files(
            self,
            path: str,
            pattern: str = "*",
            *,
            recursive: bool = False,
            detail: bool = False,
        ) -> AsyncIterator[FileInfo]:
            return
            yield

    def fail_reader(path: str) -> pd.DataFrame:
        raise AssertionError("reader should not be called")

    with patch(
        "inspect_scout._transcript.caching.AsyncFilesystem", MissingPathFilesystem
    ):
        with pytest.raises(FileNotFoundError):
            samples_df_with_caching(fail_reader, "s3://bucket/nope.json")


def test_cache_version_invalidation(
    mock_kvstore: Mock, mock_filesystem: Mock, mock_reader: Mock
) -> None:
    """Cache version mismatch clears cache and re-reads data."""
    from inspect_scout._transcript.caching import _CACHE_VERSION

    # First call populates cache with current version
    result1 = samples_df_with_caching(mock_reader, "s3://bucket/log.json")
    assert len(_paths_read(mock_reader)) == 1

    # Second call uses cache (same version)
    result2 = samples_df_with_caching(mock_reader, "s3://bucket/log.json")
    assert len(_paths_read(mock_reader)) == 1
    pd.testing.assert_frame_equal(result1, result2, check_dtype=False)

    # Simulate version change by patching _CACHE_VERSION
    with patch(
        "inspect_scout._transcript.caching._CACHE_VERSION",
        _CACHE_VERSION + 1,
    ):
        # Third call triggers cache invalidation and re-read
        result3 = samples_df_with_caching(mock_reader, "s3://bucket/log.json")
        assert len(_paths_read(mock_reader)) == 2

        # Fourth call uses cache again (with new version)
        result4 = samples_df_with_caching(mock_reader, "s3://bucket/log.json")
        assert len(_paths_read(mock_reader)) == 2
        pd.testing.assert_frame_equal(result3, result4, check_dtype=False)


def test_dataframe_cache_roundtrip(mock_filesystem: Mock) -> None:
    """Cache roundtrip preserves realistic DataFrame with pyarrow dtypes."""
    fresh = samples_df([LOGS_DIR.as_posix()], TranscriptColumns)
    reader = Mock(return_value=fresh)

    first = samples_df_with_caching(reader, "s3://bucket/log.json")
    second = samples_df_with_caching(reader, "s3://bucket/log.json")

    assert reader.call_count == 1
    pd.testing.assert_frame_equal(first, fresh, check_dtype=False)
    pd.testing.assert_frame_equal(second, fresh, check_dtype=False)
