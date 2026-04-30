from os import PathLike
from pathlib import Path

from inspect_ai.log import EvalLogInfo
from typing_extensions import Literal
from upath import UPath

from inspect_scout._scanspec import ScanTranscripts
from inspect_scout._transcript.database.factory import transcripts_from_db
from inspect_scout._transcript.eval_log import Logs, transcripts_from_logs
from inspect_scout._transcript.transcripts import Transcripts
from inspect_scout._util.constants import (
    TRANSCRIPT_SOURCE_DATABASE,
    TRANSCRIPT_SOURCE_EVAL_LOG,
)
from inspect_scout._util.filesystem import ensure_filesystem_dependencies


def transcripts_from(location: str | Logs) -> Transcripts:
    """Read transcripts for scanning.

    Transcripts may be stored in a `TranscriptDB` or may be Inspect eval logs.

    Args:
        location: Transcripts location. Either a path to a transcript database or path(s) to Inspect eval logs.

    Returns:
        Transcripts: Collection of transcripts for scanning.
    """
    from inspect_scout._scan import init_environment

    init_environment()
    locations = (
        [location] if isinstance(location, str | PathLike | EvalLogInfo) else location
    )
    locations_str = [
        Path(loc).as_posix()
        if isinstance(loc, PathLike)
        else loc.name
        if isinstance(loc, EvalLogInfo)
        else loc
        for loc in locations
    ]

    # if its a single path it may be for a database
    if len(locations_str) == 1:
        match _location_type(locations_str[0]):
            case "database":
                return transcripts_from_db(locations_str[0])
            case "eval_log":
                return transcripts_from_logs(locations_str[0])
    else:
        # if any of the locations are "database" this is invalid
        if any(_location_type(loc) == "database" for loc in locations_str):
            raise RuntimeError(
                "Only one transcript database location may be specified."
            )
        return transcripts_from_logs(locations_str)


async def transcripts_from_snapshot(snapshot: ScanTranscripts) -> Transcripts:
    if snapshot.type == TRANSCRIPT_SOURCE_EVAL_LOG:
        from inspect_scout._transcript.eval_log import EvalLogTranscripts

        return EvalLogTranscripts.from_snapshot(snapshot)
    elif snapshot.type == TRANSCRIPT_SOURCE_DATABASE:
        from inspect_scout._transcript.database.parquet import ParquetTranscripts

        return ParquetTranscripts.from_snapshot(snapshot)
    else:
        raise ValueError(f"Unrecognized transcript type '{snapshot.type}")


def _location_type(location: str | PathLike[str]) -> Literal["eval_log", "database"]:
    """Determine the type of location based on its contents.

    A location is treated as eval log(s) if it is a path to a `.eval` file
    or a directory that contains any `.eval` files (recursively). Otherwise
    it is treated as a transcript database. We invert the check this way
    because users may bring their own parquet files with arbitrary names,
    so the presence of parquet files is not a reliable signal of a
    transcript database.

    Args:
        location: Path to location (local or S3 URI)

    Returns:
        "eval_log" if the location is or contains `.eval` files, otherwise
        "database".
    """
    # ensure any filesystem dependencies (as we'll be probing the fs w/ UPath)
    ensure_filesystem_dependencies(str(location))

    location_path = UPath(location)

    # A path to a single .eval file is itself an eval log. Check the suffix
    # first to avoid filesystem probing for remote URIs.
    if location_path.suffix == ".eval":
        return TRANSCRIPT_SOURCE_EVAL_LOG

    # Treat a directory as eval logs only if it actually contains `.eval`
    # files. Note: this does not detect the rarer JSON eval log format
    # (timestamped `*.json` files); revisit if that becomes a concern.
    if location_path.exists() and next(location_path.rglob("*.eval"), None) is not None:
        return TRANSCRIPT_SOURCE_EVAL_LOG

    return TRANSCRIPT_SOURCE_DATABASE
