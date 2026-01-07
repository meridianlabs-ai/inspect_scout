"""TranscriptsReader implementation for TranscriptDB backends."""

from types import TracebackType
from typing import AsyncIterator

from typing_extensions import override

from inspect_scout._query import Query
from inspect_scout._query.condition import Condition
from inspect_scout._query.condition_sql import conditions_as_filter
from inspect_scout._scanspec import ScanTranscripts
from inspect_scout._util.constants import TRANSCRIPT_SOURCE_DATABASE

from ..transcripts import TranscriptsReader
from ..types import Transcript, TranscriptContent, TranscriptInfo
from .database import TranscriptsView


class TranscriptsViewReader(TranscriptsReader):
    """TranscriptsReader that delegates to a TranscriptDB backend.

    Query filtering (WHERE/SHUFFLE/LIMIT) is applied at database creation time
    via ParquetTranscriptsDB's query parameter, not at the reader level.
    """

    def __init__(
        self, view: TranscriptsView, location: str, where: list[Condition] | None
    ) -> None:
        self._view = view
        self._location = location
        self._where = where

    @override
    async def __aenter__(self) -> "TranscriptsViewReader":
        """Enter async context - connect to database."""
        await self._view.connect()
        return self

    @override
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        """Exit async context - disconnect from database."""
        await self._view.disconnect()
        return None

    @override
    def index(self) -> AsyncIterator[TranscriptInfo]:
        """Get index of all transcripts.

        Returns:
            Async iterator of TranscriptInfo (metadata only).
        """
        # Empty query - filtering was done at database creation time
        return self._view.select(Query())

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
        return await self._view.read(transcript, content)

    @override
    async def snapshot(self) -> ScanTranscripts:
        """Create snapshot of database contents.

        Returns:
            ScanTranscripts snapshot for serialization.
        """
        return ScanTranscripts(
            type=TRANSCRIPT_SOURCE_DATABASE,
            location=self._location,
            filter=conditions_as_filter(self._where),
            # Empty query - filtering was done at database creation time
            transcript_ids=await self._view.transcript_ids(Query()),
        )
