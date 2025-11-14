import json
from os import PathLike
from pathlib import Path
from typing import Sequence

import pandas as pd
from inspect_ai._util.file import FileInfo, filesystem
from inspect_ai._util.kvstore import KVStore
from inspect_ai.log._file import EvalLogInfo, log_files_from_ls


def resolve_logs_with_etag(
    logs: PathLike[str]
    | str
    | EvalLogInfo
    | Sequence[PathLike[str] | str | EvalLogInfo],
) -> list[tuple[str, str | None]]:
    """Resolve log paths to list of (path, etag) tuples.

    Similar to inspect_ai's resolve_logs(), but also returns etag for each log file.
    Etag is provided by S3 filesystems for cache invalidation.

    TODO: Consider updating inspect_ai's resolve_logs() to optionally return etags.

    Args:
        logs: Log paths to resolve (can be files, directories, or EvalLogInfo objects)

    Returns:
        List of (path, etag) tuples where etag may be None for non-S3 filesystems
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
    log_paths: list[FileInfo] = []
    for log_str in logs_str:
        fs = filesystem(log_str)
        info = fs.info(log_str)
        if info.type == "directory":
            log_paths.extend(
                [fi for fi in fs.ls(info.name, recursive=True) if fi.type == "file"]
            )
        else:
            log_paths.append(info)

    log_files = log_files_from_ls(log_paths, sort=False)

    # Create dict mapping log file name to etag from FileInfo
    etag_map = {fi.name: fi.etag for fi in log_paths}

    return [(log_file.name, etag_map.get(log_file.name)) for log_file in log_files]


def get_cached_df(
    kvstore: KVStore, log_path: str, current_etag: str | None
) -> pd.DataFrame | None:
    """Retrieve cached DataFrame for S3 log file if etag matches.

    Args:
        kvstore: KVStore instance for caching
        log_path: S3 path to log file
        current_etag: Current etag from S3

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

        # Reconstruct DataFrame from records
        records = cached_data.get("records", [])
        if not records:
            return None

        return pd.DataFrame.from_records(records)

    except Exception:
        # On any error, return None to fall back to reading from S3
        return None


def put_cached_df(
    kvstore: KVStore, log_path: str, etag: str | None, df: pd.DataFrame
) -> None:
    """Store DataFrame for S3 log file in cache with etag.

    Args:
        kvstore: KVStore instance for caching
        log_path: S3 path to log file
        etag: Etag from S3 for cache invalidation
        df: DataFrame to cache
    """
    try:
        kvstore.put(
            log_path,
            json.dumps(
                {
                    "etag": etag,
                    # Serialize DataFrame to JSON records. We can't go straight to Python because
                    # the df contains non-serializable data like timestamps
                    "records": json.loads(df.to_json(orient="records")),
                }
            ),
        )

    except Exception:
        # Silently fail on cache write errors
        pass
