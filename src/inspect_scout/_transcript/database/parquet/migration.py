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
    columns = conn.execute(f"""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = '{table_name}'
    """).fetchall()
    column_names = {row[0] for row in columns}

    # Build list of aliases needed
    aliases = [
        f"{old} AS {new}"
        for old, new in column_map.items()
        if old in column_names and new not in column_names
    ]

    if aliases:
        alias_clause = ", ".join(aliases)
        temp_table = f"{table_name}_migration_temp"

        # Create new table with original columns plus aliases
        conn.execute(f"""
            CREATE TABLE {temp_table} AS
            SELECT *, {alias_clause} FROM {table_name}
        """)

        # Replace original table
        conn.execute(f"DROP TABLE {table_name}")
        conn.execute(f"ALTER TABLE {temp_table} RENAME TO {table_name}")


def migrate_view(
    conn: duckdb.DuckDBPyConnection,
    view_name: str,
    column_map: dict[str, str] = EVAL_LOG_COLUMN_MAP,
) -> None:
    """
    Modify a view in place to add column aliases for backward compatibility.

    column_map: {old_name: new_name, ...}
    """
    columns = conn.execute(f"""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = '{view_name}'
    """).fetchall()
    column_names = {row[0] for row in columns}

    aliases = [
        f"{old} AS {new}"
        for old, new in column_map.items()
        if old in column_names and new not in column_names
    ]

    if aliases:
        result = conn.execute(f"""
            SELECT sql FROM duckdb_views() WHERE view_name = '{view_name}'
        """).fetchone()
        if result is None:
            return
        view_sql = result[0]

        # Extract the SELECT part after "CREATE VIEW name AS "
        # and strip trailing semicolon if present
        select_part = view_sql.split(" AS ", 1)[1].rstrip(";").strip()
        alias_clause = ", ".join(aliases)

        conn.execute(f"""
            CREATE OR REPLACE VIEW {view_name} AS
            SELECT *, {alias_clause} FROM ({select_part}) AS _base
        """)
