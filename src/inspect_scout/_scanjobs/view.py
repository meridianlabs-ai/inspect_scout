"""Abstract base class for scan jobs view."""

import abc
from typing import AsyncIterator

from .._query import Condition, OrderBy
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
    def select(
        self,
        where: list[Condition] | None = None,
        limit: int | None = None,
        order_by: list[OrderBy] | None = None,
    ) -> AsyncIterator[Status]:
        """Select scan jobs matching criteria.

        Args:
            where: Filter conditions.
            limit: Maximum number of results.
            order_by: Sort order as list of (column, direction) tuples.

        Yields:
            Status objects matching the criteria.
        """
        ...

    @abc.abstractmethod
    async def count(self, where: list[Condition] | None = None) -> int:
        """Count scan jobs matching criteria.

        Args:
            where: Filter conditions.

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
