import abc
from types import TracebackType
from typing import AsyncIterable, AsyncIterator, Iterable, Literal, Type

import pyarrow as pa
from typing_extensions import Self

from inspect_scout._transcript.transcripts import Transcripts

from ..columns import Condition
from ..types import (
    Transcript,
    TranscriptContent,
    TranscriptInfo,
)


class TranscriptsView(abc.ABC):
    """Read-only view of transcripts database."""

    @abc.abstractmethod
    async def connect(self) -> None:
        """Connect to transcripts database."""
        ...

    @abc.abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from transcripts database."""
        ...

    async def __aenter__(self) -> Self:
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
    async def transcript_ids(
        self,
        where: list[Condition] | None = None,
        limit: int | None = None,
        shuffle: bool | int = False,
        order_by: list[tuple[str, Literal["ASC", "DESC"]]] | None = None,
    ) -> dict[str, str | None]:
        """Get transcript IDs matching conditions.

        Optimized method that returns only transcript IDs without loading
        full metadata. Default implementation uses select(), but subclasses
        can override for better performance.

        Args:
            where: Condition(s) to filter by.
            limit: Maximum number to return.
            shuffle: Randomly shuffle results (pass `int` for reproducible seed).
            order_by: List of (column_name, direction) tuples for ordering.

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
        order_by: list[tuple[str, Literal["ASC", "DESC"]]] | None = None,
    ) -> AsyncIterator[TranscriptInfo]:
        """Select transcripts matching a condition.

        Args:
            where: Condition(s) to select for.
            limit: Maximum number to select.
            shuffle: Randomly shuffle transcripts selected (pass `int` for reproducible seed).
            order_by: List of (column_name, direction) tuples for ordering.
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


class TranscriptsDB(TranscriptsView):
    """Database of transcripts with write capability."""

    @abc.abstractmethod
    async def insert(
        self,
        transcripts: Iterable[Transcript]
        | AsyncIterable[Transcript]
        | Transcripts
        | pa.RecordBatchReader,
    ) -> None:
        """Insert transcripts into database.

        Args:
           transcripts: Transcripts to insert (iterable, async iterable, or source).
        """
        ...
