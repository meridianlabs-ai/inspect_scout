from types import TracebackType
from typing import AsyncIterator, Iterable, Type

from ..metadata import Condition
from ..types import (
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

    async def update(
        self,
        transcripts: Iterable[tuple[str, Transcript]]
        | AsyncIterator[tuple[str, Transcript]],
    ) -> None:
        pass

    async def delete(self, transcripts: Iterable[str]) -> None:
        pass

    async def count(
        self,
        where: list[Condition],
        limit: int | None = None,
    ) -> int:
        return 0

    async def select(
        self,
        where: list[Condition],
        limit: int | None = None,
        shuffle: bool | int = False,
    ) -> AsyncIterator[TranscriptInfo]:
        # when we are restored from a snapshot this is hard coded
        yield TranscriptInfo(id="id", source_id="source_id", source_uri="source_uri")

    async def read(self, t: TranscriptInfo, content: TranscriptContent) -> Transcript:
        return Transcript(id=t.id, source_id=t.source_id, source_uri=t.source_uri)
