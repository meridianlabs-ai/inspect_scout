from types import TracebackType
from typing import AsyncIterator, override

from inspect_scout._scanspec import ScanTranscripts
from inspect_scout._transcript.database.database import TranscriptDB
from inspect_scout._transcript.transcripts import TranscriptsQuery, TranscriptsReader
from inspect_scout._transcript.types import (
    Transcript,
    TranscriptContent,
    TranscriptInfo,
)


class TranscriptsDBReader(TranscriptsReader):
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
    async def __aenter__(self) -> "TranscriptsReader":
        """Enter the async context manager."""
        await self._db.connect()
        return self

    @override
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        await self._db.disconnect()
        return None

    @override
    async def count(self) -> int:
        """Number of transcripts in collection."""
        return await self._db.count(self._query.where, self._query.limit)

    @override
    def index(self) -> AsyncIterator[TranscriptInfo]:
        """Index of `TranscriptInfo` for the collection."""
        return self._db.select(
            self._query.where, self._query.limit, self._query.shuffle
        )

    @override
    async def read(
        self, transcript: TranscriptInfo, content: TranscriptContent
    ) -> Transcript:
        """Read transcript content.

        Args:
            transcript: Transcript to read.
            content: Content to read (e.g. specific message types, etc.)

        Returns:
            Transcript: Transcript with content.
        """
        return await self._content_db.read(transcript, content)

    @override
    async def snapshot(self) -> ScanTranscripts:
        return ScanTranscripts(type="database", fields=[], count=0, data="")
