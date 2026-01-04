"""Abstract base class for scan jobs view."""

import abc
from typing import AsyncIterator

from .._query import Query
from .._recorder.recorder import Status


class ScanJobsView(abc.ABC):
    """Read-only view of scan jobs for querying."""

    @abc.abstractmethod
    async def connect(self) -> None:
        """Connect to the view (initialize resources)."""
        ...

    @abc.abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the view (cleanup resources)."""
        ...

    @abc.abstractmethod
    def select(self, query: Query | None = None) -> AsyncIterator[Status]:
        """Select scan jobs matching query.

        Args:
            query: Query with where/limit/order_by criteria.

        Yields:
            Status objects matching the criteria.
        """
        ...

    @abc.abstractmethod
    async def count(self, query: Query | None = None) -> int:
        """Count scan jobs matching query.

        Args:
            query: Query with where criteria (limit/order_by ignored).

        Returns:
            Number of matching scan jobs.
        """
        ...

    async def __aenter__(self) -> "ScanJobsView":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Async context manager exit."""
        await self.disconnect()
