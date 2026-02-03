"""DuckDB implementation of ScanJobsView."""

import json
from typing import Any, AsyncIterator

import duckdb
import pandas as pd
from typing_extensions import override

from .._query import Query, ScalarValue
from .._query.condition import Condition
from .._query.condition_sql import condition_as_sql
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
        suffix, params, _ = query.to_sql_suffix("duckdb")
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

    def _statuses_to_dataframe(self, statuses: list[Status]) -> pd.DataFrame:
        """Convert Status objects to a DataFrame for DuckDB.

        Creates flat columns matching ScanRow fields for filtering/sorting.
        In addition to direct field mappings, this method computes several
        aggregate/derived columns to support client display and filtering needs:

        - status: Computed from errors/complete state (without active_scan_info;
          the endpoint overrides to "active" for scans with active_scan_info)
        - total_results: Sum of results across all scanners
        - total_errors: Sum of errors across all scanners
        - total_tokens: Sum of tokens across all scanners
        - scanners: Comma-separated list of scanner names
        - tags: Comma-separated list of tags
        - revision_*: Flattened revision fields (version, commit, origin)
        """
        rows = []
        for status in statuses:
            spec = status.spec
            summary = status.summary

            # Compute status string (without active_scan_info)
            if len(status.errors) > 0:
                status_str = "error"
            elif status.complete:
                status_str = "complete"
            else:
                status_str = "incomplete"

            # Extract model string
            model_str = None
            if spec.model is not None:
                model_str = getattr(spec.model, "model", None) or str(spec.model)

            # Aggregate summary fields
            total_results = 0
            total_errors = 0
            total_tokens = 0
            for scanner_summary in summary.scanners.values():
                total_results += scanner_summary.results
                total_errors += scanner_summary.errors
                total_tokens += scanner_summary.tokens

            rows.append(
                {
                    # Fields from source types
                    "scan_id": spec.scan_id,
                    "scan_name": spec.scan_name,
                    "scan_file": spec.scan_file,
                    "timestamp": spec.timestamp,
                    "packages": _serialize_dict(spec.packages),
                    "metadata": _serialize_dict(spec.metadata),
                    "scan_args": _serialize_dict(spec.scan_args),
                    "location": status.location,
                    # Transformed/flattened fields
                    "status": status_str,
                    "scanners": ",".join(spec.scanners.keys()) if spec.scanners else "",
                    "model": model_str,
                    "tags": ",".join(spec.tags) if spec.tags else "",
                    "revision_version": spec.revision.version
                    if spec.revision
                    else None,
                    "revision_commit": spec.revision.commit if spec.revision else None,
                    "revision_origin": spec.revision.origin if spec.revision else None,
                    # Aggregate fields
                    "total_results": total_results,
                    "total_errors": total_errors,
                    "total_tokens": total_tokens,
                }
            )

        return pd.DataFrame(rows)


def _serialize_dict(d: dict[str, Any] | None) -> str | None:
    """Serialize dict to JSON string for DuckDB storage."""
    if d is None:
        return None
    return json.dumps(d)
