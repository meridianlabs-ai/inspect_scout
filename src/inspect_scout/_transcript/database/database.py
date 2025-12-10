import abc
from types import TracebackType
from typing import AsyncIterable, AsyncIterator, Iterable, Type

from inspect_scout._transcript.transcripts import Transcripts

from ..metadata import Condition
from ..types import (
    Transcript,
    TranscriptContent,
    TranscriptInfo,
)
from .source import TranscriptsSource


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
        self,
        transcripts: Iterable[Transcript]
        | AsyncIterable[Transcript]
        | Transcripts
        | TranscriptsSource,
    ) -> None:
        """Insert transcripts into database.

        Args:
           transcripts: Transcripts to insert (iterable, async iterable, or source).
        """
        ...

    @abc.abstractmethod
    async def transcript_ids(
        self,
        where: list[Condition] | None = None,
        limit: int | None = None,
        shuffle: bool | int = False,
    ) -> dict[str, str | None]:
        """Get transcript IDs matching conditions.

        Optimized method that returns only transcript IDs without loading
        full metadata. Default implementation uses select(), but subclasses
        can override for better performance.

        Args:
            where: Condition(s) to filter by.
            limit: Maximum number to return.
            shuffle: Randomly shuffle results (pass `int` for reproducible seed).

        Returns:
            Dict of transcript IDs => location | None
        """
        ...

    @abc.abstractmethod
    def select(
        self,
        where: list[Condition] | None = None,
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
