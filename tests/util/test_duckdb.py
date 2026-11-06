from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from inspect_scout._query.sql import quote_identifier
from inspect_scout._util.duckdb import (
    create_parquet_view,
    restrict_external_access,
)


def test_discovered_parquet_paths_are_not_globs(tmp_path: Path) -> None:
    literal = tmp_path / "literal*[x]?.parquet"
    matching = tmp_path / "literal-otherx1.parquet"
    pq.write_table(pa.table({"value": ["literal"]}), literal)
    pq.write_table(pa.table({"value": ["other"]}), matching)

    conn = duckdb.connect(":memory:")
    try:
        source_view = create_parquet_view(conn, str(literal))
        restrict_external_access(conn, allowed_paths=[str(literal)])
        assert conn.execute(
            f"SELECT value FROM {quote_identifier(source_view)}"
        ).fetchall() == [("literal",)]
        with pytest.raises(duckdb.PermissionException):
            conn.execute(
                "SELECT value FROM read_parquet(?)",
                [str(literal)],
            ).fetchall()
    finally:
        conn.close()
