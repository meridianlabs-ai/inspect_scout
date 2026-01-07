import io
import json
import warnings
from collections.abc import Callable, Generator
from contextlib import contextmanager
from os import PathLike
from pathlib import Path

import pandas as pd
from inspect_ai._util.file import FileInfo, filesystem
from inspect_ai._util.kvstore import KVStore, inspect_kvstore
from inspect_ai.log._file import EvalLogInfo, log_files_from_ls

from .types import LogPaths

DEFAULT_MAX_CACHE_ENTRIES = 5000
_CACHE_VERSION = 8
_CACHE_VERSION_KEY = "__cache_version__"


@contextmanager
def _transcript_info_kvstore(
    name: str, max_entries: int | None = None
) -> Generator[KVStore, None, None]:
    """Wrap inspect_kvstore with version management for cache invalidation.

    Validates cache version on entry. If version key is missing or doesn't match
    CACHE_VERSION, clears all cache entries and writes current version.

    Args:
        name: KVStore name for cache storage
        max_entries: Maximum number of entries to keep in cache

    Yields:
        KVStore instance with validated version
    """
    with inspect_kvstore(name, max_entries=max_entries) as kvstore:
        stored_version = kvstore.get(_CACHE_VERSION_KEY)
        if stored_version != str(_CACHE_VERSION):
            kvstore.conn.execute("DELETE FROM kv_store")
            kvstore.conn.commit()
            kvstore.put(_CACHE_VERSION_KEY, str(_CACHE_VERSION))
        yield kvstore


def _get_cached_dfs(
    kvstore: KVStore, paths_and_etags: list[tuple[str, str]]
) -> tuple[list[pd.DataFrame], list[tuple[str, str]]]:
    """Get cached DataFrames and identify cache misses.

    Args:
        kvstore: KVStore instance for caching
        paths_and_etags: List of (path, etag) tuples

    Returns:
        Tuple of (cache_hit_dfs, cache_miss_paths_with_etags)
    """
    from functools import reduce

    def partition(
        acc: tuple[list[pd.DataFrame], list[tuple[str, str]]],
        path_etag: tuple[str, str],
    ) -> tuple[list[pd.DataFrame], list[tuple[str, str]]]:
        hits, misses = acc
        cached = _get_cached_df(kvstore, path_etag[0], path_etag[1])
        return (
            (hits + [cached], misses)
            if cached is not None
            else (hits, misses + [path_etag])
        )

    return reduce(
        partition, paths_and_etags, (list[pd.DataFrame](), list[tuple[str, str]]())
    )


def samples_df_with_caching(
    reader: Callable[[str], pd.DataFrame],
    logs: LogPaths,
    cache_store: str = "scout_transcript_info_cache",
) -> pd.DataFrame:
    """Read transcript sample info from the logs with caching.

    Caching behavior:
    - Calls reader(path) per file (with caching by etag or mtime:size)
    - Concatenates all results into single DataFrame
    - Falls back to direct reader call on any cache errors

    Args:
        reader: Function taking a path, returning DataFrame
        logs: Log paths to read
        cache_store: KVStore name for cache storage

    Returns:
        DataFrame with transcript data
    """
    # Resolve logs to a list of (path, etag) tuples
    if not (paths_and_etags := _resolve_logs(logs)):
        return pd.DataFrame()

    with _transcript_info_kvstore(
        cache_store, max_entries=DEFAULT_MAX_CACHE_ENTRIES
    ) as kvstore:
        cache_hits, cache_misses = _get_cached_dfs(kvstore, paths_and_etags)

        # Read and cache the dataframes for all of the cache misses.
        miss_dfs = [reader(path) for path, _ in cache_misses]
        for (path, etag), df in zip(cache_misses, miss_dfs, strict=True):
            _put_cached_df(kvstore, path, etag, df)

    all_dfs = [df for df in cache_hits + miss_dfs if not df.empty]
    if not all_dfs:
        return pd.DataFrame()
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning)
        return pd.concat(all_dfs, ignore_index=True)


def _resolve_logs(logs: LogPaths) -> list[tuple[str, str]]:
    """Resolve log paths to list of (path, etag) tuples.

    Similar to inspect_ai's resolve_logs(), but also returns etag for each log file.
    Etag is provided by remote filesystems (e.g., S3). For local files, a fallback
    cache key based on modification time and file size is used.

    TODO: Consider updating inspect_ai's resolve_logs() to optionally return etags.

    Args:
        logs: Log paths to resolve (can be files, directories, or EvalLogInfo objects)

    Returns:
        List of (path, etag) tuples where etag is either from filesystem or mtime:size fallback
    """
    # Normalize to list of str
    logs_list = [logs] if isinstance(logs, str | PathLike | EvalLogInfo) else logs
    logs_str = [
        Path(log).as_posix()
        if isinstance(log, PathLike)
        else log.name
        if isinstance(log, EvalLogInfo)
        else log
        for log in logs_list
    ]

    # Expand directories
    file_infos: list[FileInfo] = []
    for log_str in logs_str:
        fs = filesystem(log_str)
        info = fs.info(log_str)
        if info.type == "directory":
            file_infos.extend(
                [fi for fi in fs.ls(info.name, recursive=True) if fi.type == "file"]
            )
        else:
            file_infos.append(info)

    # Create dict mapping log file name to etag (or fallback to mtime:size)
    etag_map = {fi.name: fi.etag or f"{fi.mtime}:{fi.size}" for fi in file_infos}

    eval_log_infos = log_files_from_ls(file_infos, sort=False)

    return [(log_file.name, etag_map[log_file.name]) for log_file in eval_log_infos]


def _get_cached_df(
    kvstore: KVStore, log_path: str, current_etag: str
) -> pd.DataFrame | None:
    """Retrieve cached DataFrame for log file if etag matches.

    Args:
        kvstore: KVStore instance for caching
        log_path: Path to log file
        current_etag: Current etag for cache invalidation

    Returns:
        Cached DataFrame if etag matches, None otherwise
    """
    try:
        cached_value = kvstore.get(log_path)
        if cached_value is None:
            return None

        cached_data = json.loads(cached_value)
        cached_etag = cached_data.get("etag")

        # Check if etag matches
        if cached_etag != current_etag:
            return None

        result = pd.read_json(
            io.StringIO(cached_data.get("table")), orient="table", convert_dates=False
        )
        return result

    except Exception:
        # On any error, return None to fall back to reading from source
        return None


def _put_cached_df(
    kvstore: KVStore, log_path: str, etag: str, df: pd.DataFrame
) -> None:
    """Store DataFrame for log file in cache with etag.

    Args:
        kvstore: KVStore instance for caching
        log_path: Path to log file
        etag: Etag for cache invalidation
        df: DataFrame to cache
    """
    try:
        kvstore.put(
            log_path,
            json.dumps({"etag": etag, "table": df.to_json(orient="table")}),
        )

    except Exception:
        # Silently fail on cache write errors
        pass
