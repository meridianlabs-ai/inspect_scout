import abc
from types import TracebackType
from typing import AsyncIterator, Iterable, Type

from ..metadata import Condition
from ..types import (
    Transcript,
    TranscriptContent,
    TranscriptInfo,
)


class TranscriptDB(abc.ABC):
    def __init__(self, location: str) -> None:
        self._location: str | None = location

    @abc.abstractmethod
    async def connect(self) -> None: ...

    @abc.abstractmethod
    async def disconnect(self) -> None: ...

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

    @abc.abstractmethod
    async def insert(
        self, transcripts: Iterable[Transcript] | AsyncIterator[Transcript]
    ) -> None: ...

    @abc.abstractmethod
    async def update(
        self,
        transcripts: Iterable[tuple[str, Transcript]]
        | AsyncIterator[tuple[str, Transcript]],
    ) -> None: ...

    @abc.abstractmethod
    async def delete(self, transcripts: Iterable[str]) -> None: ...

    @abc.abstractmethod
    async def count(
        self,
        where: list[Condition],
        limit: int | None = None,
    ) -> int: ...

    @abc.abstractmethod
    def select(
        self,
        where: list[Condition],
        limit: int | None = None,
        shuffle: bool | int = False,
    ) -> AsyncIterator[TranscriptInfo]: ...

    @abc.abstractmethod
    async def read(
        self, t: TranscriptInfo, content: TranscriptContent
    ) -> Transcript: ...
