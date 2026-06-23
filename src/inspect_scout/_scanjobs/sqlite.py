"""SQLite-file-backed ScanJobsView with lazy incremental refresh."""

from typing import AsyncIterator

from typing_extensions import override

from .._query import Query, ScalarValue
from .._query.condition import Condition
from .._view._api_v2_types import ScanRow
from .cache_path import scans_index_db_path
from .refresh import refresh_index
from .store import ScanIndexStore
from .view import ScanJobsView


class SqliteScanJobsView(ScanJobsView):
    """Persistent SQLite implementation of ScanJobsView.

    Queries a per-location SQLite index that is lazily refreshed (delta
    only) from the scans directory on connect.
    """

    def __init__(self, scans_location: str) -> None:
        self._scans_location = scans_location
        self._store: ScanIndexStore | None = None

    @override
    async def connect(self) -> None:
        if self._store is not None:
            return
        self._store = ScanIndexStore(scans_index_db_path(self._scans_location))
        await refresh_index(self._store, self._scans_location)

    @override
    async def disconnect(self) -> None:
        if self._store is not None:
            self._store.close()
            self._store = None

    @override
    async def select(self, query: Query | None = None) -> AsyncIterator[ScanRow]:
        assert self._store is not None, "Not connected"
        for row in self._store.select(query):
            yield row

    @override
    async def count(self, query: Query | None = None) -> int:
        assert self._store is not None, "Not connected"
        return self._store.count(query)

    @override
    async def distinct(
        self, column: str, condition: Condition | None
    ) -> list[ScalarValue]:
        assert self._store is not None, "Not connected"
        return self._store.distinct(column, condition)


async def scan_jobs_view(scans_location: str) -> ScanJobsView:
    """Create a persistent SQLite-backed ScanJobsView for a scans location."""
    return SqliteScanJobsView(scans_location)
