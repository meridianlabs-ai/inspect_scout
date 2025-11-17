"""TranscriptsReader implementation for TranscriptDB backends."""

from types import TracebackType
from typing import AsyncIterator

from inspect_scout._scanspec import ScanTranscripts, TranscriptField
from typing_extensions import override

from ..transcripts import TranscriptsQuery, TranscriptsReader
from ..types import Transcript, TranscriptContent, TranscriptInfo
from .database import TranscriptDB


class TranscriptsDBReader(TranscriptsReader):
    """TranscriptsReader that delegates to a TranscriptDB backend."""

    def __init__(
        self,
        db: TranscriptDB,
        content_db: TranscriptDB | None,
        query: TranscriptsQuery,
    ) -> None:
        self._db = db
        self._content_db = content_db or db
        self._query = query

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
    async def count(self) -> int:
        """Count transcripts matching the query.

        Returns:
            Number of matching transcripts.
        """
        return await self._db.count(self._query.where, self._query.limit)

    @override
    def index(self) -> AsyncIterator[TranscriptInfo]:
        """Get index of transcripts matching the query.

        Returns:
            Async iterator of TranscriptInfo (metadata only).
        """
        return self._db.select(
            self._query.where,
            self._query.limit,
            self._query.shuffle,
        )

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
        return await self._content_db.read(transcript, content)

    @override
    async def snapshot(self) -> ScanTranscripts:
        """Create snapshot of current query results.

        Returns:
            ScanTranscripts snapshot for serialization.
        """
        # Collect all matching transcript IDs
        sample_ids = [info.id async for info in self.index()]

        # For now, create a simple snapshot
        # TODO: Implement proper Parquet-based snapshot
        import io

        import pandas as pd

        # Create minimal DataFrame with IDs
        df = pd.DataFrame({"id": sample_ids})

        # Convert to CSV
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        data = buffer.getvalue()

        # Create field definitions
        fields: list[TranscriptField] = [{"name": "id", "type": "string"}]

        return ScanTranscripts(
            type="parquet",
            fields=fields,
            count=len(sample_ids),
            data=data,
        )
