from inspect_scout._scanspec import ScanTranscripts
from inspect_scout._transcript.database.database import TranscriptsDB
from inspect_scout._transcript.database.parquet import (
    ParquetTranscripts,
    ParquetTranscriptsDB,
)
from inspect_scout._transcript.transcripts import Transcripts


def transcripts_db(location: str) -> TranscriptsDB:
    """Read/write interface to transcripts database.

    Args:
        location: Database location (e.g. directory or S3 bucket).

    Returns:
        Transcripts database for writing and reading.
    """
    return ParquetTranscriptsDB(location)


def transcripts_from_db(location: str) -> Transcripts:
    """Transcripts collection from database.

    Args:
        location: Database location (e.g. directory or S3 bucket).

    Returns:
        Transcripts collection for querying and scanning.

    Example:
        ```python
        from inspect_scout import transcripts_from_db, metadata as m

        # Load from local directory
        transcripts = transcripts_from_db("./transcript_db")

        # Load from S3
        transcripts = transcripts_from_db("s3://bucket/transcript_db")

        # Filter by metadata
        transcripts = transcripts.where(m.model == "gpt-4")
        transcripts = transcripts.limit(100)
        ```
    """
    return ParquetTranscripts(location=location)


def transcripts_from_db_snapshot(snapshot: ScanTranscripts) -> Transcripts:
    if not snapshot.type == "database":
        raise ValueError(
            f"Snapshot is of type '{snapshot.type}' (must be of type 'database')"
        )
    if snapshot.location is None:
        raise ValueError("Snapshot does not have a 'location' so cannot be restored.")

    # create transcripts
    transcripts = ParquetTranscripts(snapshot.location)

    # TODO: apply where clause to constrain to the IDs in the snapshot

    return transcripts
