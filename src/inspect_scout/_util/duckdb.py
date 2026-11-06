from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import duckdb

from .._query.sql import quote_identifier


def generated_identifier(prefix: str) -> str:
    """Create an internal DuckDB identifier independent of artifact names."""
    return f"_scout_{prefix}_{uuid4().hex}"


def escape_duckdb_glob(path: str) -> str:
    """Make a discovered path literal in DuckDB's glob-aware file readers."""
    replacements = {
        "*": "[*]",
        "?": "[?]",
        "[": "[[]",
        "{": "[{]",
    }
    return "".join(replacements.get(char, char) for char in path)


def parquet_paths(paths: str | Sequence[str]) -> str | list[str]:
    """Normalize explicit Parquet paths for DuckDB's Python relation API."""
    values = [paths] if isinstance(paths, str) else list(paths)
    if not values:
        raise ValueError("At least one Parquet path is required")
    escaped = [escape_duckdb_glob(path) for path in values]
    return escaped[0] if len(escaped) == 1 else escaped


def create_parquet_view(
    conn: duckdb.DuckDBPyConnection,
    paths: str | Sequence[str],
    *,
    union_by_name: bool = False,
    filename: bool = False,
) -> str:
    """Register explicit Parquet sources under an internal DuckDB view."""
    name = generated_identifier("parquet")
    paths_variable = f"{name}_paths"
    conn.execute(
        f"SET VARIABLE {quote_identifier(paths_variable)} = ?",
        [parquet_paths(paths)],
    )
    options = []
    if union_by_name:
        options.append("union_by_name = true")
    if filename:
        options.append("filename = true")
    option_sql = f", {', '.join(options)}" if options else ""
    try:
        conn.execute(
            f"CREATE VIEW {quote_identifier(name)} AS "
            f"SELECT * FROM read_parquet("
            f"getvariable('{paths_variable}'){option_sql})"
        )
    except Exception:
        conn.execute(f"RESET VARIABLE {quote_identifier(paths_variable)}")
        raise
    return name


def drop_view(conn: duckdb.DuckDBPyConnection, view_name: str) -> None:
    """Drop a generated DuckDB view."""
    conn.execute(f"DROP VIEW IF EXISTS {quote_identifier(view_name)}")
    if view_name.startswith("_scout_parquet_"):
        conn.execute(f"RESET VARIABLE {quote_identifier(f'{view_name}_paths')}")


@contextmanager
def parquet_view(
    conn: duckdb.DuckDBPyConnection,
    paths: str | Sequence[str],
    *,
    union_by_name: bool = False,
    filename: bool = False,
) -> Iterator[str]:
    """Temporarily register explicit Parquet sources as a generated view."""
    view_name = create_parquet_view(
        conn,
        paths,
        union_by_name=union_by_name,
        filename=filename,
    )
    try:
        yield view_name
    finally:
        drop_view(conn, view_name)


def relation_columns(
    conn: duckdb.DuckDBPyConnection,
    relation_name: str,
) -> set[str]:
    """Read the top-level columns of a DuckDB table or view."""
    rows = conn.execute(
        f"SELECT column_name FROM (DESCRIBE {quote_identifier(relation_name)})"
    ).fetchall()
    return {str(row[0]) for row in rows}


def restrict_external_access(
    conn: duckdb.DuckDBPyConnection,
    *,
    allowed_paths: Sequence[str] = (),
    allowed_directories: Sequence[str] = (),
) -> None:
    """Lock a read-only DuckDB connection to explicitly intended sources."""
    if allowed_paths:
        path_variants: list[str] = []
        for path in allowed_paths:
            path_variants.append(path)
            if path.startswith("file://"):
                path_variants.append(path[len("file://") :])
            elif "://" not in path:
                absolute_path = Path(path).absolute()
                path_variants.extend([str(absolute_path), absolute_path.as_uri()])
        path_variants.extend(escape_duckdb_glob(path) for path in list(path_variants))
        conn.execute(
            "SET allowed_paths = ?",
            [list(dict.fromkeys(path_variants))],
        )
    if allowed_directories:
        conn.execute(
            "SET allowed_directories = ?",
            [list(dict.fromkeys(allowed_directories))],
        )
    conn.execute("SET autoinstall_known_extensions = false")
    conn.execute("SET autoload_known_extensions = false")
    conn.execute("SET enable_external_access = false")
    conn.execute("SET lock_configuration = true")
