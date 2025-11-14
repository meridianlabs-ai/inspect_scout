from collections.abc import Callable
from os import PathLike
from pathlib import Path
from typing import Sequence

import pandas as pd
from inspect_ai._util.asyncfiles import is_s3_filename
from inspect_ai._util.kvstore import inspect_kvstore
from inspect_ai.log._file import EvalLogInfo

from inspect_scout._transcript.s3_log_cache import (
    get_cached_df,
    put_cached_df,
    resolve_logs_with_etag,
)

from .types import LogPaths


def with_transcript_caching(
    reader: Callable[[Sequence[str]], pd.DataFrame],
    cache_store: str = "scout_s3_log_cache",
) -> Callable[[LogPaths], pd.DataFrame]:
    """Wrap a DataFrame reader with S3 caching.

    The wrapper:
    - Calls reader([path]) per S3 file (with caching by etag)
    - Calls reader(paths) once for all non-S3 files (no caching)
    - Concatenates all results into single DataFrame
    - Falls back to direct reader call on any cache errors

    Args:
        reader: Function taking sequence of paths, returning DataFrame
        cache_store: KVStore name for cache storage

    Returns:
        Wrapped reader with identical signature but S3 caching
    """

    def cached_reader(
        logs: PathLike[str]
        | str
        | EvalLogInfo
        | Sequence[PathLike[str] | str | EvalLogInfo],
    ) -> pd.DataFrame:
        try:
            # 1. Resolve logs to (path, etag) tuples
            resolved = resolve_logs_with_etag(logs)

            # 2. Split S3 vs non-S3
            s3_logs: list[tuple[str, str | None]] = []
            local_logs: list[str] = []
            for path, etag in resolved:
                if is_s3_filename(path):
                    s3_logs.append((path, etag))
                else:
                    local_logs.append(path)

            # 3. Process S3 logs with caching
            dfs: list[pd.DataFrame] = []

            if s3_logs:
                with inspect_kvstore(cache_store) as kvstore:
                    for path, etag in s3_logs:
                        # Try cache
                        cached = get_cached_df(kvstore, path, etag)
                        if cached is not None:
                            dfs.append(cached)
                        else:
                            # Cache miss - call reader with single-item list
                            fresh = reader([path])
                            dfs.append(fresh)
                            # Update cache (silent failure)
                            put_cached_df(kvstore, path, etag, fresh)

            # 4. Process non-S3 logs without caching
            if local_logs:
                dfs.append(reader(local_logs))

            # 5. Concatenate or return empty DataFrame
            if dfs:
                return pd.concat(dfs, ignore_index=True)
            else:
                # Return empty DataFrame - let reader define columns
                return reader([])

        except Exception:
            # Fallback: call reader directly without caching
            if isinstance(logs, Sequence) and not isinstance(logs, str):
                # Convert to list of strings
                logs_list = [
                    log.name
                    if isinstance(log, EvalLogInfo)
                    else Path(log).as_posix()
                    if isinstance(log, PathLike)
                    else log
                    for log in logs
                ]
            else:
                # Single log
                single_log = (
                    logs.name
                    if isinstance(logs, EvalLogInfo)
                    else Path(logs).as_posix()
                    if isinstance(logs, PathLike)
                    else logs
                )
                logs_list = [single_log]
            return reader(logs_list)

    return cached_reader
