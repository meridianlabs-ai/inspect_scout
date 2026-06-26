"""
Schema Migration Utilities for DuckDB

Requirements:
1. If the new field exists in the table/view, do nothing
2. If the old field exists, alias it to the new name so queries using the new name work
3. If neither field exists, do nothing

Approach:
- For tables: Recreate the table with aliased columns added via SELECT.
  DuckDB doesn't support adding generated columns after table creation.
- For views: Wrap the existing view definition in a subquery and add aliases.
  DuckDB's optimizer flattens this, so there's no performance penalty.

Note: Both approaches are read-only compatible. Writes must use the original column names.
"""

import duckdb

from ...._query.sql import quote_identifier
from ...._util.duckdb import generated_identifier

EVAL_LOG_COLUMN_MAP = {
    "task_name": "task_set",
    "eval_created": "date",
    "solver": "agent",
    "solver_args": "agent_args",
    "generate_config": "model_options",
}


def migrate_table(
    conn: duckdb.DuckDBPyConnection,
    table_name: str,
    column_map: dict[str, str] = EVAL_LOG_COLUMN_MAP,
) -> None:
    """
    Recreate a table with aliased columns for backward compatibility.

    DuckDB doesn't support adding generated columns after table creation,
    so we recreate the table with the new columns added via SELECT.

    column_map: {old_name: new_name, ...}
    """
    columns = conn.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = ?
        """,
        [table_name],
    ).fetchall()
    column_names = {row[0] for row in columns}

    # Build list of aliases needed
    aliases = [
        f"{quote_identifier(old)} AS {quote_identifier(new)}"
        for old, new in column_map.items()
        if old in column_names and new not in column_names
    ]

    if aliases:
        alias_clause = ", ".join(aliases)
        temp_table = generated_identifier("migration_table")

        # Create new table with original columns plus aliases
        conn.execute(f"""
            CREATE TABLE {quote_identifier(temp_table)} AS
            SELECT *, {alias_clause} FROM {quote_identifier(table_name)}
        """)

        # Replace original table
        conn.execute(f"DROP TABLE {quote_identifier(table_name)}")
        conn.execute(
            f"ALTER TABLE {quote_identifier(temp_table)} "
            f"RENAME TO {quote_identifier(table_name)}"
        )


def migrate_view(
    conn: duckdb.DuckDBPyConnection,
    view_name: str,
    column_map: dict[str, str] = EVAL_LOG_COLUMN_MAP,
) -> str | None:
    """
    Modify a view in place to add column aliases for backward compatibility.

    column_map: {old_name: new_name, ...}
    """
    columns = conn.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = ?
        """,
        [view_name],
    ).fetchall()
    column_names = {row[0] for row in columns}

    aliases = [
        f"{quote_identifier(old)} AS {quote_identifier(new)}"
        for old, new in column_map.items()
        if old in column_names and new not in column_names
    ]

    if aliases:
        base_view = generated_identifier("migration_view")
        alias_clause = ", ".join(aliases)

        conn.execute(
            f"ALTER VIEW {quote_identifier(view_name)} "
            f"RENAME TO {quote_identifier(base_view)}"
        )
        try:
            conn.execute(f"""
                CREATE VIEW {quote_identifier(view_name)} AS
                SELECT *, {alias_clause} FROM {quote_identifier(base_view)}
            """)
        except Exception:
            conn.execute(
                f"ALTER VIEW {quote_identifier(base_view)} "
                f"RENAME TO {quote_identifier(view_name)}"
            )
            raise
        return base_view

    return None
