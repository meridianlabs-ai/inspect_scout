"""TranscriptsReader implementation for TranscriptDB backends."""

import io
from types import TracebackType
from typing import AsyncIterator

import pandas as pd
from typing_extensions import override

from inspect_scout._scanspec import ScanTranscripts, TranscriptField
from inspect_scout._util.constants import TRANSCRIPT_SOURCE_DATABASE

from ..transcripts import TranscriptsReader
from ..types import Transcript, TranscriptContent, TranscriptInfo
from .database import TranscriptsDB


class TranscriptsDBReader(TranscriptsReader):
    """TranscriptsReader that delegates to a TranscriptDB backend.

    Query filtering (WHERE/SHUFFLE/LIMIT) is applied at database creation time
    via ParquetTranscriptsDB's query parameter, not at the reader level.
    """

    def __init__(self, db: TranscriptsDB) -> None:
        self._db = db

    @override
    async def __aenter__(self) -> "TranscriptsDBReader":
        """Enter async context - connect to database."""
        await self._db.connect()
        return self

    @override
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        """Exit async context - disconnect from database."""
        await self._db.disconnect()
        return None

    @override
    def index(self) -> AsyncIterator[TranscriptInfo]:
        """Get index of all transcripts.

        Returns:
            Async iterator of TranscriptInfo (metadata only).
        """
        return self._db.select()

    @override
    async def read(
        self, transcript: TranscriptInfo, content: TranscriptContent
    ) -> Transcript:
        """Read full transcript content.

        Args:
            transcript: TranscriptInfo identifying the transcript.
            content: Filter for which messages/events to load.

        Returns:
            Full Transcript with content.
        """
        return await self._db.read(transcript, content)

    @override
    async def snapshot(self) -> tuple[ScanTranscripts, list[str]]:
        """Create snapshot of database contents.

        Returns:
            ScanTranscripts snapshot for serialization.
        """
        # Collect all transcript IDs (uses optimized path when available)
        transcript_ids = await self._db.transcript_ids()

        # Create minimal DataFrame with IDs
        df = pd.DataFrame({"transcript_id": transcript_ids})

        # Convert to CSV
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        data = buffer.getvalue()

        # Create field definitions
        fields: list[TranscriptField] = [{"name": "transcript_id", "type": "string"}]

        return ScanTranscripts(
            type=TRANSCRIPT_SOURCE_DATABASE,
            location=self._db._location,
            fields=fields,
            count=len(transcript_ids),
            data=data,
        ), transcript_ids
