"""Tests for schema migration utilities."""

from pathlib import Path
from typing import AsyncIterator

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import pytest_asyncio
from inspect_scout import log_columns as c
from inspect_scout import transcripts_from
from inspect_scout._query import Query
from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB
from inspect_scout._transcript.database.parquet.migration import (
    EVAL_LOG_COLUMN_MAP,
    migrate_table,
    migrate_view,
)
from inspect_scout._transcript.transcripts import Transcripts

# Path to test logs
TEST_LOGS_DIR = Path(__file__).parent.parent.parent / "recorder" / "logs"

# Reverse mapping: new column names -> old column names
NEW_TO_OLD_COLUMN_MAP = {v: k for k, v in EVAL_LOG_COLUMN_MAP.items()}

# --- Test Fixtures ---


@pytest.fixture
def conn() -> duckdb.DuckDBPyConnection:
    """Create in-memory DuckDB connection."""
    return duckdb.connect(":memory:")


def get_column_names(conn: duckdb.DuckDBPyConnection, table_name: str) -> set[str]:
    """Get column names for a table or view."""
    result = conn.execute(f"""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = '{table_name}'
    """).fetchall()
    return {row[0] for row in result}


# --- migrate_table Tests ---


class TestMigrateTable:
    """Tests for migrate_table function."""

    def test_migrate_table_adds_generated_columns(
        self, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Table with old columns gets new generated columns."""
        # Create table with old column names
        conn.execute("""
            CREATE TABLE test_table AS
            SELECT
                'transcript_1' AS transcript_id,
                'my_task' AS task_name,
                '2025-01-01' AS eval_created,
                'claude-3' AS solver,
                '{"param": "value"}' AS solver_args,
                '{"temp": 0.7}' AS generate_config
        """)

        # Verify old columns exist, new columns don't
        columns_before = get_column_names(conn, "test_table")
        assert "task_name" in columns_before
        assert "task_set" not in columns_before

        # Run migration
        migrate_table(conn, "test_table")

        # Verify new columns were added
        columns_after = get_column_names(conn, "test_table")
        assert "task_set" in columns_after
        assert "date" in columns_after
        assert "agent" in columns_after
        assert "agent_args" in columns_after
        assert "model_options" in columns_after

    def test_migrate_table_skips_existing_new_columns(
        self, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """No-op if new columns already exist."""
        # Create table with both old and new column names
        conn.execute("""
            CREATE TABLE test_table AS
            SELECT
                'transcript_1' AS transcript_id,
                'old_task' AS task_name,
                'new_task' AS task_set,
                '2025-01-01' AS eval_created,
                '2025-01-02' AS date
        """)

        # Run migration
        migrate_table(conn, "test_table")

        # Verify new columns still have their original values (not overwritten)
        result = conn.execute("SELECT task_set, date FROM test_table").fetchone()
        assert result is not None
        assert result[0] == "new_task"  # Original value preserved
        assert result[1] == "2025-01-02"  # Original value preserved

    def test_migrate_table_partial_columns(
        self, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Only migrates columns that exist."""
        # Create table with only some old columns
        conn.execute("""
            CREATE TABLE test_table AS
            SELECT
                'transcript_1' AS transcript_id,
                'my_task' AS task_name,
                'some_model' AS model
        """)

        # Run migration
        migrate_table(conn, "test_table")

        # Verify only task_set was added (task_name existed)
        columns = get_column_names(conn, "test_table")
        assert "task_set" in columns
        # These should NOT exist since their old columns didn't exist
        assert "date" not in columns
        assert "agent" not in columns
        assert "agent_args" not in columns

    def test_migrate_table_queries_with_new_names(
        self, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Queries using new column names work after migration."""
        # Create table with old column names
        conn.execute("""
            CREATE TABLE test_table AS
            SELECT
                'transcript_1' AS transcript_id,
                'math_task' AS task_name,
                '2025-06-15' AS eval_created,
                'gpt-4' AS solver,
                '{"temp": 0.7}' AS solver_args,
                '{"max_tokens": 1000}' AS generate_config
        """)

        # Run migration
        migrate_table(conn, "test_table")

        # Query using new column names
        result = conn.execute("""
            SELECT task_set, date, agent, agent_args, model_options
            FROM test_table
            WHERE task_set = 'math_task'
        """).fetchone()

        assert result is not None
        assert result[0] == "math_task"
        assert result[1] == "2025-06-15"
        assert result[2] == "gpt-4"
        assert result[3] == '{"temp": 0.7}'
        assert result[4] == '{"max_tokens": 1000}'

    def test_migrate_table_nonexistent_table(
        self, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Migration of non-existent table doesn't raise (no columns found)."""
        # This should not raise - it will just find no columns
        migrate_table(conn, "nonexistent_table")


# --- migrate_view Tests ---


class TestMigrateView:
    """Tests for migrate_view function."""

    def test_migrate_view_adds_aliases(self, conn: duckdb.DuckDBPyConnection) -> None:
        """View with old columns gets aliased columns."""
        # Create source table and view with old column names
        conn.execute("""
            CREATE TABLE source_table AS
            SELECT
                'transcript_1' AS transcript_id,
                'my_task' AS task_name,
                '2025-01-01' AS eval_created,
                'claude-3' AS solver,
                '{"param": "value"}' AS solver_args,
                '{"temp": 0.7}' AS generate_config
        """)
        conn.execute("""
            CREATE VIEW test_view AS
            SELECT * FROM source_table
        """)

        # Verify old columns exist, new columns don't
        columns_before = get_column_names(conn, "test_view")
        assert "task_name" in columns_before
        assert "task_set" not in columns_before

        # Run migration
        migrate_view(conn, "test_view")

        # Verify new columns were added as aliases
        columns_after = get_column_names(conn, "test_view")
        assert "task_set" in columns_after
        assert "date" in columns_after
        assert "agent" in columns_after
        assert "agent_args" in columns_after
        assert "model_options" in columns_after

    def test_migrate_view_skips_existing_new_columns(
        self, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """No-op if new columns already exist in view."""
        # Create source table with both old and new columns
        conn.execute("""
            CREATE TABLE source_table AS
            SELECT
                'transcript_1' AS transcript_id,
                'old_task' AS task_name,
                'new_task' AS task_set
        """)
        conn.execute("""
            CREATE VIEW test_view AS
            SELECT * FROM source_table
        """)

        # Run migration
        migrate_view(conn, "test_view")

        # Verify new column still has original value
        result = conn.execute("SELECT task_set FROM test_view").fetchone()
        assert result is not None
        assert result[0] == "new_task"  # Original value preserved

    def test_migrate_view_partial_columns(
        self, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Only adds aliases for existing old columns."""
        # Create view with only some old columns
        conn.execute("""
            CREATE TABLE source_table AS
            SELECT
                'transcript_1' AS transcript_id,
                'my_task' AS task_name,
                'some_model' AS model
        """)
        conn.execute("""
            CREATE VIEW test_view AS
            SELECT * FROM source_table
        """)

        # Run migration
        migrate_view(conn, "test_view")

        # Verify only task_set was added
        columns = get_column_names(conn, "test_view")
        assert "task_set" in columns
        # These should NOT exist since their old columns didn't exist
        assert "date" not in columns
        assert "agent" not in columns
        assert "agent_args" not in columns

    def test_migrate_view_queries_with_new_names(
        self, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Queries using new column names work after migration."""
        # Create view with old column names
        conn.execute("""
            CREATE TABLE source_table AS
            SELECT
                'transcript_1' AS transcript_id,
                'math_task' AS task_name,
                '2025-06-15' AS eval_created,
                'gpt-4' AS solver,
                '{"temp": 0.7}' AS solver_args,
                '{"max_tokens": 1000}' AS generate_config
        """)
        conn.execute("""
            CREATE VIEW test_view AS
            SELECT * FROM source_table
        """)

        # Run migration
        migrate_view(conn, "test_view")

        # Query using new column names
        result = conn.execute("""
            SELECT task_set, date, agent, agent_args, model_options
            FROM test_view
            WHERE task_set = 'math_task'
        """).fetchone()

        assert result is not None
        assert result[0] == "math_task"
        assert result[1] == "2025-06-15"
        assert result[2] == "gpt-4"
        assert result[3] == '{"temp": 0.7}'
        assert result[4] == '{"max_tokens": 1000}'

    def test_migrate_view_nonexistent_view(
        self, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Migration of non-existent view doesn't raise."""
        # This should not raise - it will find no view definition
        migrate_view(conn, "nonexistent_view")

    def test_migrate_view_preserves_original_data(
        self, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """View migration preserves all original columns and data."""
        # Create view with various columns
        conn.execute("""
            CREATE TABLE source_table AS
            SELECT
                'transcript_1' AS transcript_id,
                'my_task' AS task_name,
                'extra_data' AS extra_column,
                42 AS numeric_column
        """)
        conn.execute("""
            CREATE VIEW test_view AS
            SELECT * FROM source_table
        """)

        # Run migration
        migrate_view(conn, "test_view")

        # Verify all original columns still exist and have correct values
        result = conn.execute("""
            SELECT transcript_id, task_name, extra_column, numeric_column, task_set
            FROM test_view
        """).fetchone()

        assert result is not None
        assert result[0] == "transcript_1"
        assert result[1] == "my_task"
        assert result[2] == "extra_data"
        assert result[3] == 42
        assert result[4] == "my_task"  # Aliased from task_name


# --- Column Map Tests ---


class TestColumnMap:
    """Tests for the EVAL_LOG_COLUMN_MAP configuration."""

    def test_column_map_has_expected_mappings(self) -> None:
        """Verify the column map contains all expected old->new mappings."""
        assert EVAL_LOG_COLUMN_MAP == {
            "task_name": "task_set",
            "eval_created": "date",
            "solver": "agent",
            "solver_args": "agent_args",
            "generate_config": "model_options",
        }

    def test_all_mappings_applied_to_table(
        self, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """All mappings in EVAL_LOG_COLUMN_MAP are applied to table."""
        # Create table with all old column names
        conn.execute("""
            CREATE TABLE test_table AS
            SELECT
                'transcript_1' AS transcript_id,
                'task_value' AS task_name,
                'date_value' AS eval_created,
                'agent_value' AS solver,
                'args_value' AS solver_args,
                'config_value' AS generate_config
        """)

        migrate_table(conn, "test_table")

        # Query using all new column names
        result = conn.execute("""
            SELECT task_set, date, agent, agent_args, model_options
            FROM test_table
        """).fetchone()

        assert result is not None
        assert result[0] == "task_value"
        assert result[1] == "date_value"
        assert result[2] == "agent_value"
        assert result[3] == "args_value"
        assert result[4] == "config_value"

    def test_all_mappings_applied_to_view(
        self, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """All mappings in EVAL_LOG_COLUMN_MAP are applied to view."""
        # Create view with all old column names
        conn.execute("""
            CREATE TABLE source_table AS
            SELECT
                'transcript_1' AS transcript_id,
                'task_value' AS task_name,
                'date_value' AS eval_created,
                'agent_value' AS solver,
                'args_value' AS solver_args,
                'config_value' AS generate_config
        """)
        conn.execute("CREATE VIEW test_view AS SELECT * FROM source_table")

        migrate_view(conn, "test_view")

        # Query using all new column names
        result = conn.execute("""
            SELECT task_set, date, agent, agent_args, model_options
            FROM test_view
        """).fetchone()

        assert result is not None
        assert result[0] == "task_value"
        assert result[1] == "date_value"
        assert result[2] == "agent_value"
        assert result[3] == "args_value"
        assert result[4] == "config_value"


# --- Integration Tests with Parquet Files ---


class TestParquetIntegration:
    """Integration tests using actual Parquet files with old schema."""

    def test_migrate_table_from_parquet_with_old_columns(self, tmp_path: Path) -> None:
        """Migration works on a table loaded from Parquet file with old columns."""
        # Create a Parquet file with old column names
        parquet_path = tmp_path / "old_schema.parquet"
        table = pa.table(
            {
                "transcript_id": ["t1", "t2", "t3"],
                "task_name": ["math", "coding", "qa"],
                "eval_created": ["2025-01-01", "2025-01-02", "2025-01-03"],
                "solver": ["gpt-4", "claude-3", "gpt-4"],
                "solver_args": ['{"temp": 0.7}', '{"temp": 0.5}', '{"temp": 0.9}'],
                "generate_config": [
                    '{"max_tokens": 1000}',
                    '{"max_tokens": 2000}',
                    '{"max_tokens": 3000}',
                ],
                "model": ["gpt-4", "claude-3", "gpt-4"],
                "filename": ["file1.parquet", "file2.parquet", "file3.parquet"],
            }
        )
        pq.write_table(table, str(parquet_path))

        # Load into DuckDB
        conn = duckdb.connect(":memory:")
        conn.execute(f"""
            CREATE TABLE transcript_index AS
            SELECT * FROM read_parquet('{parquet_path}')
        """)

        # Run migration
        migrate_table(conn, "transcript_index")

        # Verify queries with new column names work
        result = conn.execute("""
            SELECT task_set, date, agent, agent_args, model_options
            FROM transcript_index
            WHERE task_set = 'math'
        """).fetchone()

        assert result is not None
        assert result[0] == "math"
        assert result[1] == "2025-01-01"
        assert result[2] == "gpt-4"
        assert result[3] == '{"temp": 0.7}'
        assert result[4] == '{"max_tokens": 1000}'

        # Verify all rows are accessible via new column names
        count = conn.execute("""
            SELECT COUNT(*) FROM transcript_index
            WHERE agent IN ('gpt-4', 'claude-3')
        """).fetchone()
        assert count is not None
        assert count[0] == 3

        conn.close()

    def test_migrate_view_from_parquet_with_old_columns(self, tmp_path: Path) -> None:
        """Migration works on a view over Parquet file with old columns."""
        # Create a Parquet file with old column names
        parquet_path = tmp_path / "old_schema.parquet"
        table = pa.table(
            {
                "transcript_id": ["t1", "t2", "t3"],
                "task_name": ["math", "coding", "qa"],
                "eval_created": ["2025-01-01", "2025-01-02", "2025-01-03"],
                "solver": ["gpt-4", "claude-3", "gpt-4"],
                "solver_args": ['{"temp": 0.7}', '{"temp": 0.5}', '{"temp": 0.9}'],
                "generate_config": [
                    '{"max_tokens": 1000}',
                    '{"max_tokens": 2000}',
                    '{"max_tokens": 3000}',
                ],
                "model": ["gpt-4", "claude-3", "gpt-4"],
                "messages": ["[]", "[]", "[]"],
                "events": ["[]", "[]", "[]"],
            }
        )
        pq.write_table(table, str(parquet_path))

        # Load into DuckDB as a view (simulating transcripts view)
        conn = duckdb.connect(":memory:")
        conn.execute(f"""
            CREATE VIEW transcripts AS
            SELECT * EXCLUDE (messages, events)
            FROM read_parquet('{parquet_path}')
        """)

        # Run migration
        migrate_view(conn, "transcripts")

        # Verify queries with new column names work
        result = conn.execute("""
            SELECT task_set, date, agent, agent_args, model_options
            FROM transcripts
            WHERE task_set = 'coding'
        """).fetchone()

        assert result is not None
        assert result[0] == "coding"
        assert result[1] == "2025-01-02"
        assert result[2] == "claude-3"
        assert result[3] == '{"temp": 0.5}'
        assert result[4] == '{"max_tokens": 2000}'

        conn.close()

    def test_mixed_old_and_new_columns_in_parquet(self, tmp_path: Path) -> None:
        """Migration handles Parquet with some old and some new columns."""
        # Create a Parquet file with mixed columns
        # (e.g., partially migrated or newer format with some old names)
        parquet_path = tmp_path / "mixed_schema.parquet"
        table = pa.table(
            {
                "transcript_id": ["t1", "t2"],
                "task_set": ["math", "coding"],  # New name
                "eval_created": ["2025-01-01", "2025-01-02"],  # Old name
                "agent": ["gpt-4", "claude-3"],  # New name
                "solver_args": ['{"temp": 0.7}', '{"temp": 0.5}'],  # Old name
                "generate_config": [
                    '{"max_tokens": 1000}',
                    '{"max_tokens": 2000}',
                ],  # Old name
                "model": ["gpt-4", "claude-3"],
            }
        )
        pq.write_table(table, str(parquet_path))

        # Load into DuckDB
        conn = duckdb.connect(":memory:")
        conn.execute(f"""
            CREATE TABLE transcript_index AS
            SELECT * FROM read_parquet('{parquet_path}')
        """)

        # Run migration
        migrate_table(conn, "transcript_index")

        # Verify new columns work (task_set, agent already existed)
        # Only date, agent_args, and model_options should be added as aliases
        result = conn.execute("""
            SELECT task_set, date, agent, agent_args, model_options
            FROM transcript_index
            WHERE task_set = 'math'
        """).fetchone()

        assert result is not None
        assert result[0] == "math"
        assert result[1] == "2025-01-01"  # Aliased from eval_created
        assert result[2] == "gpt-4"
        assert result[3] == '{"temp": 0.7}'  # Aliased from solver_args
        assert result[4] == '{"max_tokens": 1000}'  # Aliased from generate_config

        conn.close()

    def test_parquet_with_all_new_columns_no_migration_needed(
        self, tmp_path: Path
    ) -> None:
        """Migration is a no-op for Parquet with all new column names."""
        # Create a Parquet file with all new column names
        parquet_path = tmp_path / "new_schema.parquet"
        table = pa.table(
            {
                "transcript_id": ["t1", "t2"],
                "task_set": ["math", "coding"],
                "date": ["2025-01-01", "2025-01-02"],
                "agent": ["gpt-4", "claude-3"],
                "agent_args": ['{"temp": 0.7}', '{"temp": 0.5}'],
                "model_options": ['{"max_tokens": 1000}', '{"max_tokens": 2000}'],
                "model": ["gpt-4", "claude-3"],
            }
        )
        pq.write_table(table, str(parquet_path))

        # Load into DuckDB
        conn = duckdb.connect(":memory:")
        conn.execute(f"""
            CREATE TABLE transcript_index AS
            SELECT * FROM read_parquet('{parquet_path}')
        """)

        # Get columns before migration
        columns_before = conn.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'transcript_index'
        """).fetchall()

        # Run migration (should be a no-op)
        migrate_table(conn, "transcript_index")

        # Get columns after migration
        columns_after = conn.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'transcript_index'
        """).fetchall()

        # Same columns - no new ones added
        assert set(r[0] for r in columns_before) == set(r[0] for r in columns_after)

        # Queries still work
        result = conn.execute("""
            SELECT task_set, date, agent, model_options FROM transcript_index
        """).fetchall()
        assert len(result) == 2

        conn.close()


# --- End-to-End Integration Tests ---


def rename_parquet_columns_to_old_schema(db_path: Path) -> None:
    """Rename columns in all parquet files to use old schema names.

    This simulates a database created before the column rename migration.
    """
    # Find all parquet files (data files and index files)
    parquet_files = list(db_path.glob("**/*.parquet")) + list(db_path.glob("**/*.idx"))

    for parquet_file in parquet_files:
        # Read the parquet file
        table = pq.read_table(str(parquet_file))

        # Check if any new column names exist and need renaming
        schema = table.schema
        new_names = list(schema.names)
        rename_map = {}

        for new_name, old_name in NEW_TO_OLD_COLUMN_MAP.items():
            if new_name in new_names:
                rename_map[new_name] = old_name

        if rename_map:
            # Rename columns by creating new table with renamed column names
            new_schema_names = [rename_map.get(name, name) for name in schema.names]

            # Create new table with renamed columns
            new_table = pa.table(
                {
                    new_schema_names[i]: table.column(i).to_pylist()
                    for i in range(len(schema))
                }
            )

            # Write back to the same file
            pq.write_table(new_table, str(parquet_file))


async def get_transcript_ids_from_transcripts(
    transcripts: Transcripts,
) -> list[str]:
    """Helper to get transcript IDs from a Transcripts object."""
    async with transcripts.reader() as reader:
        return [info.transcript_id async for info in reader.index()]


class TestEndToEndMigration:
    """End-to-end integration tests using real eval logs and transcripts_from."""

    @pytest_asyncio.fixture
    async def populated_db_with_old_schema(self, tmp_path: Path) -> AsyncIterator[Path]:
        """Create a database from test logs, then rewrite to old schema."""
        db_path = tmp_path / "transcript_db"
        db_path.mkdir(parents=True, exist_ok=True)

        # Step 1: Create database from test eval logs
        db = ParquetTranscriptsDB(str(db_path))
        await db.connect()
        await db.insert(transcripts_from(str(TEST_LOGS_DIR)))
        await db.disconnect()

        # Step 2: Rewrite parquet files to use old column names
        rename_parquet_columns_to_old_schema(db_path)

        yield db_path

    @pytest.mark.asyncio
    async def test_query_with_log_columns_old_names(
        self, populated_db_with_old_schema: Path
    ) -> None:
        """Test that LogColumns API with old field names works on old schema DB.

        LogColumns.task_name returns Column("task_set"), which requires the
        migration to add task_set as an alias to the old task_name column.
        """
        # Open the database with old schema
        transcripts = transcripts_from(str(populated_db_with_old_schema))

        # Query using LogColumns with deprecated property
        # c.task_name returns Column("task_set") - requires migration alias
        filtered = transcripts.where(c.task_name == "popularity")

        # Get transcript IDs
        ids = await get_transcript_ids_from_transcripts(filtered)

        # Verify we got results (popularity task exists in test logs)
        assert len(ids) > 0, "Should find transcripts for popularity task"

    @pytest.mark.asyncio
    async def test_query_with_bracket_notation_old_names(
        self, populated_db_with_old_schema: Path
    ) -> None:
        """Test that bracket notation with old column names works on old schema DB.

        c["task_name"] generates SQL for the actual column name, which exists
        in the old schema database.
        """
        # Open the database with old schema
        transcripts = transcripts_from(str(populated_db_with_old_schema))

        # Query using bracket notation - directly references old column name
        filtered = transcripts.where(c["task_name"] == "popularity")

        # Get transcript IDs
        ids = await get_transcript_ids_from_transcripts(filtered)

        # Verify we got results
        assert len(ids) > 0, "Should find transcripts using bracket notation"

    @pytest.mark.asyncio
    async def test_query_with_new_column_names(
        self, populated_db_with_old_schema: Path
    ) -> None:
        """Test that new column names work on old schema DB via migration aliases.

        The migration should add task_set as an alias to task_name, so
        queries using task_set should work.
        """
        # Open the database with old schema
        transcripts = transcripts_from(str(populated_db_with_old_schema))

        # Query using new column name (via standard property)
        # c.task_set returns Column("task_set") - works via migration alias
        filtered = transcripts.where(c.task_set == "popularity")

        # Get transcript IDs
        ids = await get_transcript_ids_from_transcripts(filtered)

        # Verify we got results
        assert len(ids) > 0, "Should find transcripts using new column name"

    @pytest.mark.asyncio
    async def test_multiple_old_column_names_work(
        self, populated_db_with_old_schema: Path
    ) -> None:
        """Test that multiple deprecated column names work via LogColumns."""
        transcripts = transcripts_from(str(populated_db_with_old_schema))

        # Test multiple old column names through LogColumns
        # These all return the new column name, which requires migration aliases

        # task_name -> task_set (query for popularity)
        filtered = transcripts.where(c.task_name == "popularity")
        ids = await get_transcript_ids_from_transcripts(filtered)
        assert len(ids) > 0, "task_name query should work"

        # eval_created -> date (check it's not None)
        filtered = transcripts.where(c.eval_created.is_not_null())
        ids = await get_transcript_ids_from_transcripts(filtered)
        assert len(ids) > 0, "eval_created query should work"


# --- End-to-End Test for model_options Field ---


class TestModelOptionsEndToEnd:
    """End-to-end tests for model_options field flow."""

    @pytest.mark.asyncio
    async def test_model_options_storage_and_retrieval(self, tmp_path: Path) -> None:
        """Test that model_options flows correctly: insertion → storage → retrieval."""
        from inspect_ai.model._chat_message import ChatMessageUser
        from inspect_scout._transcript.types import Transcript

        db_path = tmp_path / "model_options_test_db"
        db_path.mkdir(parents=True, exist_ok=True)

        # Create transcripts with model_options populated
        model_options_data = {"temperature": 0.7, "max_tokens": 1000, "top_p": 0.9}
        transcripts = [
            Transcript(
                transcript_id="mo-001",
                source_type="test",
                source_id="test-source",
                source_uri="test://uri/1",
                model="gpt-4",
                model_options=model_options_data,
                agent="test-agent",
                agent_args={"param1": "value1"},
                metadata={},
                messages=[ChatMessageUser(content="Test message")],
                events=[],
            ),
            Transcript(
                transcript_id="mo-002",
                source_type="test",
                source_id="test-source",
                source_uri="test://uri/2",
                model="claude-3",
                model_options={"temperature": 0.5},
                agent="other-agent",
                agent_args={"param2": "value2"},
                metadata={},
                messages=[ChatMessageUser(content="Another test")],
                events=[],
            ),
        ]

        # Insert into database
        db = ParquetTranscriptsDB(str(db_path))
        await db.connect()

        try:
            await db.insert(transcripts)

            # Query back and verify model_options is preserved
            results = [info async for info in db.select(Query())]
            assert len(results) == 2

            # Find specific transcript and verify model_options
            mo_001 = next(r for r in results if r.transcript_id == "mo-001")
            assert mo_001.model_options == model_options_data
            assert mo_001.model_options["temperature"] == 0.7
            assert mo_001.model_options["max_tokens"] == 1000
            assert mo_001.model_options["top_p"] == 0.9

            mo_002 = next(r for r in results if r.transcript_id == "mo-002")
            assert mo_002.model_options == {"temperature": 0.5}

            # Verify agent_args is also preserved
            assert mo_001.agent_args == {"param1": "value1"}
            assert mo_002.agent_args == {"param2": "value2"}

        finally:
            await db.disconnect()

    @pytest.mark.asyncio
    async def test_model_options_null_handling(self, tmp_path: Path) -> None:
        """Test that null/empty model_options is handled correctly."""
        from inspect_ai.model._chat_message import ChatMessageUser
        from inspect_scout._transcript.types import Transcript

        db_path = tmp_path / "model_options_null_test_db"
        db_path.mkdir(parents=True, exist_ok=True)

        # Create transcripts with None and empty model_options
        transcripts = [
            Transcript(
                transcript_id="null-001",
                source_type="test",
                source_id="test-source",
                source_uri="test://uri/1",
                model="gpt-4",
                model_options=None,  # Explicitly None
                metadata={},
                messages=[ChatMessageUser(content="Test")],
                events=[],
            ),
            Transcript(
                transcript_id="null-002",
                source_type="test",
                source_id="test-source",
                source_uri="test://uri/2",
                model="claude-3",
                model_options={},  # Empty dict
                metadata={},
                messages=[ChatMessageUser(content="Test")],
                events=[],
            ),
        ]

        db = ParquetTranscriptsDB(str(db_path))
        await db.connect()

        try:
            await db.insert(transcripts)

            results = [info async for info in db.select(Query())]
            assert len(results) == 2

            # Verify null/empty handling
            null_001 = next(r for r in results if r.transcript_id == "null-001")
            null_002 = next(r for r in results if r.transcript_id == "null-002")

            # Both should be handled gracefully
            assert null_001.model_options is None
            assert null_002.model_options == {}

        finally:
            await db.disconnect()

    @pytest.mark.asyncio
    async def test_model_options_via_transcripts_api(self, tmp_path: Path) -> None:
        """Test model_options access via high-level transcripts API."""
        from inspect_ai.model._chat_message import ChatMessageUser
        from inspect_scout._transcript.types import Transcript

        db_path = tmp_path / "model_options_api_test_db"
        db_path.mkdir(parents=True, exist_ok=True)

        # Create test transcripts
        model_options_data = {"temperature": 0.8, "stop": ["\\n\\n"]}
        transcripts_data = [
            Transcript(
                transcript_id="api-001",
                source_type="test",
                source_id="test-source",
                source_uri="test://uri/1",
                model="gpt-4",
                model_options=model_options_data,
                metadata={},
                messages=[ChatMessageUser(content="Test")],
                events=[],
            ),
        ]

        # Insert via DB
        db = ParquetTranscriptsDB(str(db_path))
        await db.connect()
        await db.insert(transcripts_data)
        await db.disconnect()

        # Access via high-level API
        transcripts_obj = transcripts_from(str(db_path))

        async with transcripts_obj.reader() as reader:
            results = [info async for info in reader.index()]

        assert len(results) == 1
        assert results[0].model_options == model_options_data
