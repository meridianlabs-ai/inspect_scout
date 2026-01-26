import abc
from types import TracebackType
from typing import AsyncIterable, AsyncIterator, Iterable, Type

import pyarrow as pa
from typing_extensions import Self

from inspect_scout._transcript.transcripts import Transcripts

from ..._query import Query
from ..._query.condition import Condition, ScalarValue
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
    async def transcript_ids(self, query: Query | None = None) -> dict[str, str | None]:
        """Get transcript IDs matching query.

        Optimized method that returns only transcript IDs without loading
        full metadata.

        Args:
            query: Query with where/limit/shuffle/order_by criteria.

        Returns:
            Dict of transcript IDs => location | None
        """
        ...

    @abc.abstractmethod
    def select(self, query: Query | None = None) -> AsyncIterator[TranscriptInfo]:
        """Select transcripts matching query.

        Args:
            query: Query with where/limit/shuffle/order_by criteria.
        """
        ...

    @abc.abstractmethod
    async def count(self, query: Query | None = None) -> int:
        """Count transcripts matching query.

        Args:
            query: Query with where criteria (limit/shuffle/order_by ignored).

        Returns:
            Number of matching transcripts.
        """
        ...

    @abc.abstractmethod
    async def read(
        self,
        t: TranscriptInfo,
        content: TranscriptContent,
        max_bytes: int | None = None,
    ) -> Transcript:
        """Read transcript content.

        Args:
            t: Transcript to read.
            content: Content to read (messages, events, etc.)
            max_bytes: Max content size in bytes. Raises TranscriptTooLargeError if exceeded.
        """
        ...

    @abc.abstractmethod
    async def distinct(
        self, column: str, condition: Condition | None
    ) -> list[ScalarValue]:
        """Get distinct values of a column, sorted ascending.

        Args:
            column: Column to get distinct values for.
            condition: Filter condition, or None for no filter.

        Returns:
            Distinct values, sorted by column ascending.
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
        session_id: str | None = None,
        commit: bool = True,
    ) -> None:
        """Insert transcripts into database.

        Args:
            transcripts: Transcripts to insert (iterable, async iterable, or source).
            session_id: Optional session ID to include in parquet filenames.
                Used for session-scoped compaction at commit time.
            commit: If True (default), commit after insert (compact + index).
                If False, defer commit for batch operations. Call commit()
                explicitly when ready to finalize.
        """
        ...

    @abc.abstractmethod
    async def commit(self, session_id: str | None = None) -> None:
        """Commit pending changes.

        For parquet: compacts data files + rebuilds index.
        For relational DBs: may be a no-op or transaction commit.

        This is called automatically when insert() is called with commit=True
        (the default). Only call this manually when using commit=False with
        insert() for batch operations.

        Args:
            session_id: Optional session ID for session-scoped compaction.
                When provided, parquet files created during this session are
                compacted into fewer larger files before index compaction.
        """
        ...
