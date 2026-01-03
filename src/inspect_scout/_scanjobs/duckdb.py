"""DuckDB implementation of ScanJobsView."""

from functools import reduce
from typing import AsyncIterator, Literal

import duckdb
import pandas as pd
from typing_extensions import override

from inspect_scout._recorder.recorder import Status
from inspect_scout._transcript.columns import Condition

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
    async def select(
        self,
        where: list[Condition] | None = None,
        limit: int | None = None,
        order_by: list[tuple[str, Literal["ASC", "DESC"]]] | None = None,
    ) -> AsyncIterator[Status]:
        """Select scan jobs matching criteria."""
        assert self._conn is not None, "Not connected"

        # Build SQL query
        where_clause, where_params = self._build_where_clause(where)
        sql = f"SELECT scan_id FROM {SCAN_JOBS_TABLE}{where_clause}"

        # Add ORDER BY
        if order_by:
            order_parts = [f'"{col}" {direction}' for col, direction in order_by]
            sql += " ORDER BY " + ", ".join(order_parts)

        # Add LIMIT
        if limit is not None:
            sql += f" LIMIT {limit}"

        # Execute query
        result = self._conn.execute(sql, where_params).fetchall()

        # Yield Status objects
        for (scan_id,) in result:
            status = self._status_by_scan_id.get(scan_id)
            if status is not None:
                yield status

    @override
    async def count(self, where: list[Condition] | None = None) -> int:
        """Count scan jobs matching criteria."""
        assert self._conn is not None, "Not connected"

        where_clause, where_params = self._build_where_clause(where)
        sql = f"SELECT COUNT(*) FROM {SCAN_JOBS_TABLE}{where_clause}"

        result = self._conn.execute(sql, where_params).fetchone()
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

    def _build_where_clause(
        self, where: list[Condition] | None
    ) -> tuple[str, list[object]]:
        """Build WHERE clause and parameters from conditions.

        Args:
            where: List of conditions to combine with AND.

        Returns:
            Tuple of (where_clause, parameters). where_clause is empty string if no conditions.
        """
        if where and len(where) > 0:
            condition: Condition = (
                where[0] if len(where) == 1 else reduce(lambda a, b: a & b, where)
            )
            where_sql, where_params = condition.to_sql("duckdb")
            return f" WHERE {where_sql}", where_params
        return "", []
