import io

import pandas as pd

from inspect_scout._scanspec import ScanTranscripts
from inspect_scout._transcript.database.database import TranscriptsDB
from inspect_scout._transcript.metadata import Column
from inspect_scout._transcript.transcripts import Transcripts
from inspect_scout._util.constants import TRANSCRIPT_SOURCE_DATABASE


def transcripts_db(location: str) -> TranscriptsDB:
    """Read/write interface to transcripts database.

    Args:
        location: Database location (e.g. directory or S3 bucket).

    Returns:
        Transcripts database for writing and reading.
    """
    from inspect_scout._scan import init_environment
    from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB

    init_environment()
    return ParquetTranscriptsDB(location)


def transcripts_from_db(location: str) -> Transcripts:
    """Transcripts collection from database.

    Args:
        location: Database location (e.g. directory or S3 bucket).

    Returns:
        Transcripts collection for querying and scanning.

    Example:
        ```python
        from inspect_scout import transcripts_from, metadata as m

        # Load from local directory
        transcripts = transcripts_from("./transcript_db")

        # Load from S3
        transcripts = transcripts_from("s3://bucket/transcript_db")

        # Filter by metadata
        transcripts = transcripts.where(m.model == "gpt-4")
        transcripts = transcripts.limit(100)
        ```
    """
    from inspect_scout._transcript.database.parquet import ParquetTranscripts

    return ParquetTranscripts(location=location)


def transcripts_from_db_snapshot(snapshot: ScanTranscripts) -> Transcripts:
    from inspect_scout._transcript.database.parquet import ParquetTranscripts

    if not snapshot.type == TRANSCRIPT_SOURCE_DATABASE:
        raise ValueError(
            f"Snapshot is of type '{snapshot.type}' (must be of type '{TRANSCRIPT_SOURCE_DATABASE}')"
        )
    if snapshot.location is None:
        raise ValueError("Snapshot does not have a 'location' so cannot be restored.")

    # create transcripts
    transcripts: Transcripts = ParquetTranscripts(snapshot.location)

    # read legacy snapshot format
    if snapshot.data:
        # parse IDs from snapshot CSV
        df = pd.read_csv(io.StringIO(snapshot.data))
        sample_ids = df["transcript_id"].tolist()
    else:
        sample_ids = list(snapshot.transcript_ids.keys())

    # filter to only the transcripts in the snapshot
    transcripts = transcripts.where(Column("transcript_id").in_(sample_ids))

    return transcripts
