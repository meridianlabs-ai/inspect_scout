import abc
from types import TracebackType
from typing import AsyncIterator, Iterable, Type

from ..metadata import Condition
from ..types import (
    Transcript,
    TranscriptContent,
    TranscriptInfo,
)


class TranscriptsDB(abc.ABC):
    """Database of transcripts."""

    def __init__(self, location: str) -> None:
        """Create a transcripts database.

        Args:
            location: Database location (e.g. local or S3 file path)
        """
        self._location: str | None = location

    @abc.abstractmethod
    async def connect(self) -> None:
        """Connect to transcripts database."""
        ...

    @abc.abstractmethod
    async def disconnect(self) -> None:
        """Disconnect to transcripts database."""
        ...

    async def __aenter__(self) -> "TranscriptsDB":
        """Connect to transcripts database."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        """Disconnect from transcripts database."""
        await self.disconnect()
        return None

    @abc.abstractmethod
    async def insert(
        self, transcripts: Iterable[Transcript] | AsyncIterator[Transcript]
    ) -> None:
        """Insert transcripts into database.

        Args:
           transcripts: Transcripts to insert as iterable or async iterator.
        """
        ...

    @abc.abstractmethod
    async def count(
        self,
        where: list[Condition],
        limit: int | None = None,
    ) -> int:
        """Count transcripts matching a condition.

        Args:
           where: Condition(s) to count.
           limit: Maximum number to count.
        """
        ...

    @abc.abstractmethod
    def select(
        self,
        where: list[Condition],
        limit: int | None = None,
        shuffle: bool | int = False,
    ) -> AsyncIterator[TranscriptInfo]:
        """Select transcripts matching a condition.

        Args:
            where: Condition(s) to select for.
            limit: Maximum number to select.
            shuffle: Randomly shuffle transcripts selected (pass `int` for reproducible seed).
        """
        ...

    @abc.abstractmethod
    async def read(self, t: TranscriptInfo, content: TranscriptContent) -> Transcript:
        """Read transcript content.

        Args:
            t: Transcript to read.
            content: Content to read (messages, events, etc.)
        """
        ...
