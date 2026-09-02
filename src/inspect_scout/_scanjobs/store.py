"""Persistent SQLite store for the scan-jobs index.

One row per scan (the ScanRow columns) plus a change_token used by the
lazy refresh in refresh.py. Queries run via the existing "sqlite" SQL
dialect, the same path EvalLogTranscriptsView uses.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .._query import Query, ScalarValue
from .._query.condition import Condition
from .._query.condition_sql import condition_as_sql
from .._query.sql import quote_identifier, validate_column
from .._view._api_v2_types import ScanRow

SCAN_JOBS_TABLE = "scan_jobs"
JSON_COLUMNS = ("packages", "metadata", "scan_args")


# DDL: scan_id is the natural key for upsert; timestamp stored as ISO text
# (sorts correctly); JSON columns as TEXT; integer aggregates as INTEGER.
# DDL column order is documentation only; reads/writes are keyed positionally
# by _SCAN_ROW_COLUMNS, so DDL order need not match ScanRow field order.
_CREATE_TABLE = f"""
CREATE TABLE IF NOT EXISTS {SCAN_JOBS_TABLE} (
    scan_id TEXT PRIMARY KEY,
    scan_name TEXT,
    scan_file TEXT,
    timestamp TEXT,
    packages TEXT,
    metadata TEXT,
    scan_args TEXT,
    location TEXT,
    status TEXT,
    scanners TEXT,
    model TEXT,
    tags TEXT,
    revision_version TEXT,
    revision_commit TEXT,
    revision_origin TEXT,
    total_results INTEGER,
    total_errors INTEGER,
    total_tokens INTEGER,
    active_completion_pct INTEGER,
    transcript_count INTEGER,
    change_token TEXT
)
"""

_SCAN_ROW_COLUMNS = tuple(ScanRow.model_fields.keys())
_ALL_COLUMNS = (*_SCAN_ROW_COLUMNS, "change_token")


class ScanIndexStore:
    def __init__(self, db_path: str | Path) -> None:
        self._conn = sqlite3.connect(str(db_path))
        # WAL: concurrent readers + single writer with retry (view server + CLI).
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.execute(_CREATE_TABLE)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def upsert(self, rows: list[tuple[ScanRow, str]]) -> None:
        placeholders = ", ".join(["?"] * len(_ALL_COLUMNS))
        cols = ", ".join(quote_identifier(column) for column in _ALL_COLUMNS)
        sql = (
            f"INSERT OR REPLACE INTO {quote_identifier(SCAN_JOBS_TABLE)} "
            f"({cols}) VALUES ({placeholders})"
        )
        self._conn.executemany(
            sql, [self._row_to_tuple(row, token) for row, token in rows]
        )
        self._conn.commit()

    def delete(self, scan_ids: list[str]) -> None:
        if not scan_ids:
            return
        self._conn.executemany(
            f"DELETE FROM {quote_identifier(SCAN_JOBS_TABLE)} WHERE scan_id = ?",
            [(sid,) for sid in scan_ids],
        )
        self._conn.commit()

    def stored_tokens(self) -> dict[str, str]:
        cursor = self._conn.execute(
            f"SELECT scan_id, change_token FROM {quote_identifier(SCAN_JOBS_TABLE)}"
        )
        return {scan_id: token for scan_id, token in cursor.fetchall()}

    def select(self, query: Query | None = None) -> list[ScanRow]:
        query = query or Query()
        suffix, params, _ = query.to_sql_suffix(
            "sqlite", available_columns=_SCAN_ROW_COLUMNS
        )
        cols = ", ".join(quote_identifier(column) for column in _SCAN_ROW_COLUMNS)
        cursor = self._conn.execute(
            f"SELECT {cols} FROM {quote_identifier(SCAN_JOBS_TABLE)}{suffix}",
            params,
        )
        return [self._tuple_to_row(row) for row in cursor.fetchall()]

    def count(self, query: Query | None = None) -> int:
        query = query or Query()
        count_query = Query(where=query.where)
        suffix, params, _ = count_query.to_sql_suffix("sqlite")
        result = self._conn.execute(
            f"SELECT COUNT(*) FROM {quote_identifier(SCAN_JOBS_TABLE)}{suffix}",
            params,
        ).fetchone()
        return int(result[0])

    def distinct(self, column: str, condition: Condition | None) -> list[ScalarValue]:
        column = validate_column(column, _SCAN_ROW_COLUMNS)
        quoted_column = quote_identifier(column)
        quoted_table = quote_identifier(SCAN_JOBS_TABLE)
        if condition is not None:
            where_sql, params = condition_as_sql(condition, "sqlite")
            sql = (
                f"SELECT DISTINCT {quoted_column} FROM {quoted_table} "
                f"WHERE {where_sql} ORDER BY {quoted_column} ASC"
            )
        else:
            params = []
            sql = (
                f"SELECT DISTINCT {quoted_column} FROM {quoted_table} "
                f"ORDER BY {quoted_column} ASC"
            )
        return [row[0] for row in self._conn.execute(sql, params).fetchall()]

    def _row_to_tuple(self, row: ScanRow, token: str) -> tuple[Any, ...]:
        data = row.model_dump()
        values: list[Any] = []
        for col in _SCAN_ROW_COLUMNS:
            value = data[col]
            if col in JSON_COLUMNS:
                values.append(None if value is None else json.dumps(value))
            elif col == "timestamp":
                values.append(value.isoformat() if value is not None else None)
            else:
                values.append(value)
        values.append(token)
        return tuple(values)

    def _tuple_to_row(self, row: tuple[Any, ...]) -> ScanRow:
        data = dict(zip(_SCAN_ROW_COLUMNS, row, strict=True))
        for col in JSON_COLUMNS:
            if data[col] is not None:
                data[col] = json.loads(data[col])
        if data["timestamp"] is not None:
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return ScanRow(**data)
