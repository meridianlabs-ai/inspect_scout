"""DuckDB implementation of ScanJobsView."""

from typing import AsyncIterator

import duckdb
import pandas as pd
from typing_extensions import override

from .._query import Query
from .._query.sql import SQLDialect
from .._recorder.recorder import Status
from .view import ScanJobsView

SCAN_JOBS_TABLE = "scan_jobs"


class DuckDBScanJobsView(ScanJobsView):
    """In-memory DuckDB implementation of ScanJobsView.

    Loads Status objects into an in-memory DuckDB table for efficient
    SQL-based filtering, sorting, and pagination.
    """

    def __init__(self, statuses: list[Status]) -> None:
        """Initialize with Status objects.

        Args:
            statuses: List of Status objects to index.
        """
        self._statuses = statuses
        self._status_by_scan_id: dict[str, Status] = {
            s.spec.scan_id: s for s in statuses
        }
        self._conn: duckdb.DuckDBPyConnection | None = None

    @override
    async def connect(self) -> None:
        """Connect to in-memory DuckDB and load data."""
        if self._conn is not None:
            return

        self._conn = duckdb.connect(":memory:")

        # Flatten Status objects to DataFrame
        df = self._statuses_to_dataframe(self._statuses)

        # Register DataFrame as table
        self._conn.register("scan_jobs_df", df)
        self._conn.execute(
            f"CREATE TABLE {SCAN_JOBS_TABLE} AS SELECT * FROM scan_jobs_df"
        )
        self._conn.unregister("scan_jobs_df")

    @override
    async def disconnect(self) -> None:
        """Disconnect from DuckDB."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @override
    async def select(self, query: Query | None = None) -> AsyncIterator[Status]:
        """Select scan jobs matching query."""
        assert self._conn is not None, "Not connected"
        query = query or Query()

        # Build SQL suffix using Query (no shuffle for scan jobs)
        suffix, params, _ = query.to_sql_suffix(SQLDialect.DUCKDB)
        sql = f"SELECT scan_id FROM {SCAN_JOBS_TABLE}{suffix}"

        # Execute query
        result = self._conn.execute(sql, params).fetchall()

        # Yield Status objects
        for (scan_id,) in result:
            status = self._status_by_scan_id.get(scan_id)
            if status is not None:
                yield status

    @override
    async def count(self, query: Query | None = None) -> int:
        """Count scan jobs matching query."""
        assert self._conn is not None, "Not connected"
        query = query or Query()

        # For count, only WHERE matters (ignore limit/order_by)
        count_query = Query(where=query.where)
        suffix, params, _ = count_query.to_sql_suffix(SQLDialect.DUCKDB)
        sql = f"SELECT COUNT(*) FROM {SCAN_JOBS_TABLE}{suffix}"

        result = self._conn.execute(sql, params).fetchone()
        assert result is not None
        return int(result[0])

    def _statuses_to_dataframe(self, statuses: list[Status]) -> pd.DataFrame:
        """Convert Status objects to a DataFrame for DuckDB."""
        rows = []
        for status in statuses:
            spec = status.spec
            # Get model string - handle both ModelConfig and simple cases
            model_str = None
            if spec.model is not None:
                model_str = getattr(spec.model, "model", None) or str(spec.model)

            rows.append(
                {
                    "scan_id": spec.scan_id,
                    "scan_name": spec.scan_name,
                    "scanners": ",".join(spec.scanners.keys()) if spec.scanners else "",
                    "model": model_str,
                    "location": status.location,
                    "timestamp": spec.timestamp,
                    "complete": status.complete,
                }
            )

        return pd.DataFrame(rows)
