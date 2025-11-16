from types import TracebackType
from typing import AsyncIterator, Iterable, Type, override

from inspect_scout._scanspec import ScanTranscripts
from inspect_scout._transcript.metadata import Condition
from inspect_scout._transcript.transcripts import (
    Transcripts,
    TranscriptsQuery,
    TranscriptsReader,
)
from inspect_scout._transcript.types import (
    Transcript,
    TranscriptContent,
    TranscriptInfo,
)


class TranscriptDB:
    def __init__(self, location: str) -> None:
        self._location: str | None = location

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def __aenter__(self) -> "TranscriptDB":
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        await self.disconnect()
        return None

    async def insert(
        self, transcripts: Iterable[Transcript] | AsyncIterator[Transcript]
    ) -> None:
        pass

    async def update(self, transcripts: Iterable[tuple[str, Transcript]]) -> None:
        pass

    async def delete(self, transcripts: Iterable[str]) -> None:
        pass

    async def count(
        self,
        where: list[Condition],
        limit: int | None = None,
    ) -> int:
        return 0

    async def query(
        self,
        where: list[Condition],
        limit: int | None = None,
        shuffle: bool | int = False,
    ) -> AsyncIterator[TranscriptInfo]:
        # when we are restored from a snapshot this is hard coded
        yield TranscriptInfo(id="id", source_id="source_id", source_uri="source_uri")

    async def read(self, t: TranscriptInfo, content: TranscriptContent) -> Transcript:
        return Transcript(id=t.id, source_id=t.source_id, source_uri=t.source_uri)


class TranscriptsDBTranscripts(Transcripts):
    def __init__(self, db: TranscriptDB) -> None:
        self._db = db

    @override
    def reader(self) -> TranscriptsReader:
        return TranscriptsDBReader(self._db, self._query)


class TranscriptsDBReader(TranscriptsReader):
    def __init__(self, db: TranscriptDB, query: TranscriptsQuery) -> None:
        self._db = db
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
        return self._db.query(self._query.where, self._query.limit, self._query.shuffle)

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
        return await self._db.read(transcript, content)

    @override
    async def snapshot(self) -> ScanTranscripts:
        return ScanTranscripts(type="foo", fields=[], count=0, data="")


def transcripts_from(location: str) -> Transcripts:
    db = TranscriptDB(location)
    return TranscriptsDBTranscripts(db)
