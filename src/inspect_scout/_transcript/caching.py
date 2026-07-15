import io
import json
import warnings
from collections.abc import Callable, Generator
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from functools import partial
from os import PathLike
from pathlib import Path

import pandas as pd
from inspect_ai._util._async import run_coroutine, tg_collect
from inspect_ai._util.asyncfiles import AsyncFilesystem
from inspect_ai._util.file import FileInfo
from inspect_ai._util.kvstore import KVStore, inspect_kvstore
from inspect_ai.log._file import EvalLogInfo, log_files_from_ls

from .types import LogPaths

DEFAULT_MAX_CACHE_ENTRIES = 5000
DEFAULT_READER_MAX_WORKERS = 16
_CACHE_VERSION = 10
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
    max_workers: int = DEFAULT_READER_MAX_WORKERS,
) -> pd.DataFrame:
    """Read transcript sample info from the logs with caching.

    Caching behavior:
    - Calls reader(path) per file (with caching by etag or mtime:size),
      reading cache misses concurrently on a thread pool
    - Each file is cached as soon as its read completes, so a failure part
      way through preserves the files already read
    - Concatenates all results into single DataFrame
    - Falls back to direct reader call on any cache errors

    Reads are one file per reader call (rather than one multi-file call)
    because inspect_ai's samples_df de-duplicates samples by uuid across
    all logs it is given: eval-set retry logs carry forward completed
    samples with identical uuids, so two such logs read in one call would
    each get a partial result. Per-file calls make de-duplication a no-op.

    Args:
        reader: Function taking a path, returning DataFrame
        logs: Log paths to read
        cache_store: KVStore name for cache storage
        max_workers: Maximum number of threads used to read cache misses

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

        # Read the cache misses concurrently, caching each file as its read
        # completes (on this thread -- the kvstore connection is not shared
        # with reader threads). On the first failure stop submitting new
        # reads, cache the reads still in flight, then re-raise.
        miss_df_by_path: dict[str, pd.DataFrame] = {}
        first_error: Exception | None = None
        futures: dict[Future[pd.DataFrame], tuple[str, str]] = {}
        if cache_misses:
            with ThreadPoolExecutor(
                max_workers=min(max_workers, len(cache_misses))
            ) as executor:
                futures = {
                    executor.submit(reader, path): (path, etag)
                    for path, etag in cache_misses
                }
                for future in as_completed(futures):
                    path, etag = futures[future]
                    try:
                        df = future.result()
                    except Exception as ex:
                        # as_completed never yields futures that
                        # shutdown(cancel_futures=True) drained from the
                        # queue, so stop iterating and harvest the reads
                        # still in flight below.
                        first_error = ex
                        executor.shutdown(wait=True, cancel_futures=True)
                        break
                    _put_cached_df(kvstore, path, etag, df)
                    miss_df_by_path[path] = df
        if first_error is not None:
            # cache the in-flight reads that completed after the failure
            for future, (path, etag) in futures.items():
                if path in miss_df_by_path or future.cancelled():
                    continue
                try:
                    _put_cached_df(kvstore, path, etag, future.result())
                except Exception:
                    pass
            raise first_error
        miss_dfs = [miss_df_by_path[path] for path, _ in cache_misses]

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

    file_infos = run_coroutine(_expand_logs(logs_str))

    # Create dict mapping log file name to etag (or fallback to mtime:size)
    etag_map = {fi.name: fi.etag or f"{fi.mtime}:{fi.size}" for fi in file_infos}

    eval_log_infos = log_files_from_ls(file_infos, sort=False)

    return [(log_file.name, etag_map[log_file.name]) for log_file in eval_log_infos]


async def _expand_logs(paths: list[str]) -> list[FileInfo]:
    """Fetch FileInfo (including etag) for each path, expanding directories.

    All paths are processed concurrently on a shared AsyncFilesystem client:
    one listing sweep per directory input (which yields file info from the
    listing itself, with no per-file stat calls) and one stat per file input.
    """
    async with AsyncFilesystem() as fs:
        expanded = await tg_collect([partial(_expand_log, fs, path) for path in paths])
    return [fi for fis in expanded for fi in fis]


async def _expand_log(fs: AsyncFilesystem, path: str) -> list[FileInfo]:
    async def list_files() -> list[FileInfo]:
        return [fi async for fi in fs.iter_files(path, recursive=True, detail=True)]

    try:
        info = await fs.info(path)
    except Exception:
        # S3 has no directory objects, so info() raises for directory
        # prefixes; a path that lists as a non-empty directory is one.
        # Anything else (missing path, bad credentials) re-raises.
        if files := await list_files():
            return files
        raise
    return await list_files() if info.type == "directory" else [info]


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
