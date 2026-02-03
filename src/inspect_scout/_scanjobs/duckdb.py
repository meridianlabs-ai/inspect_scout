"""DuckDB implementation of ScanJobsView."""

import json
from typing import AsyncIterator

import duckdb
import pandas as pd
from typing_extensions import override

from inspect_scout._recorder.file import FileRecorder

from .._query import Query, ScalarValue
from .._query.condition import Condition
from .._query.condition_sql import condition_as_sql
from .._recorder.active_scans_store import ActiveScanInfo, active_scans_store
from .._recorder.recorder import Status
from .._view._api_v2_types import ScanRow
from .convert import scan_row_from_status
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
        self._scan_row_by_scan_id: dict[str, ScanRow] = {}
        self._conn: duckdb.DuckDBPyConnection | None = None

    @override
    async def connect(self) -> None:
        """Connect to in-memory DuckDB and load data."""
        if self._conn is not None:
            return

        self._conn = duckdb.connect(":memory:")

        # Get active scans for status enrichment
        with active_scans_store() as store:
            active_scans_map = store.read_all()

        # Convert Status objects to ScanRows and build DataFrame
        df = self._statuses_to_dataframe(self._statuses, active_scans_map)

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
    async def select(self, query: Query | None = None) -> AsyncIterator[ScanRow]:
        """Select scan jobs matching query."""
        assert self._conn is not None, "Not connected"
        query = query or Query()

        # Build SQL suffix using Query (no shuffle for scan jobs)
        suffix, params, _ = query.to_sql_suffix("duckdb")
        sql = f"SELECT scan_id FROM {SCAN_JOBS_TABLE}{suffix}"

        # Execute query
        result = self._conn.execute(sql, params).fetchall()

        # Yield ScanRow objects
        for (scan_id,) in result:
            scan_row = self._scan_row_by_scan_id.get(scan_id)
            if scan_row is not None:
                yield scan_row

    @override
    async def count(self, query: Query | None = None) -> int:
        """Count scan jobs matching query."""
        assert self._conn is not None, "Not connected"
        query = query or Query()

        # For count, only WHERE matters (ignore limit/order_by)
        count_query = Query(where=query.where)
        suffix, params, _ = count_query.to_sql_suffix("duckdb")
        sql = f"SELECT COUNT(*) FROM {SCAN_JOBS_TABLE}{suffix}"

        result = self._conn.execute(sql, params).fetchone()
        assert result is not None
        return int(result[0])

    @override
    async def distinct(
        self, column: str, condition: Condition | None
    ) -> list[ScalarValue]:
        """Get distinct values of a column, sorted ascending."""
        assert self._conn is not None, "Not connected"

        if condition is not None:
            where_sql, params = condition_as_sql(condition, "duckdb")
            sql = f'SELECT DISTINCT "{column}" FROM {SCAN_JOBS_TABLE} WHERE {where_sql} ORDER BY "{column}" ASC'
        else:
            params = []
            sql = f'SELECT DISTINCT "{column}" FROM {SCAN_JOBS_TABLE} ORDER BY "{column}" ASC'

        result = self._conn.execute(sql, params).fetchall()
        return [row[0] for row in result]

    def _statuses_to_dataframe(
        self,
        statuses: list[Status],
        active_scans_map: dict[str, ActiveScanInfo],
    ) -> pd.DataFrame:
        """Convert Status objects to a DataFrame for DuckDB.

        Uses scan_row_from_status() for all transformation logic, then
        converts to DataFrame rows for SQL querying.
        """
        rows = []
        for status in statuses:
            scan_row = scan_row_from_status(
                status,
                active_scan_info=active_scans_map.get(status.spec.scan_id),
            )
            # Cache for lookup in select()
            self._scan_row_by_scan_id[scan_row.scan_id] = scan_row

            # Convert to dict for DataFrame, serializing dicts as JSON for DuckDB
            row_dict = scan_row.model_dump()
            for key in ("packages", "metadata", "scan_args"):
                if row_dict[key] is not None:
                    row_dict[key] = json.dumps(row_dict[key])

            rows.append(row_dict)

        return pd.DataFrame(rows)


async def scan_jobs_view(scans_location: str) -> ScanJobsView:
    """Create a ScanJobsView for the given scans location.

    Args:
        scans_location: Path to directory containing scan jobs.

    Returns:
        ScanJobsView instance for querying scan jobs.
    """
    return DuckDBScanJobsView(await FileRecorder.list(scans_location))
