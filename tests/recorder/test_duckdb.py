"""Tests for DuckDB results_db() and to_file() functionality."""

import tempfile
from pathlib import Path

import duckdb
import pytest
from inspect_scout._scanresults import scan_status


@pytest.fixture
def test_scans_path():
    """Path to test scans."""
    return Path(__file__).parent / "scans"


@pytest.fixture
def test_scan_results(test_scans_path):
    return scan_status((test_scans_path / "scan_id=JzvEPBFB4aVpCU93FFbiFT").as_posix())


class TestResultsDB:
    """Tests for the results_db() function."""

    def test_results_db_creates_connection(self, test_scan_results):
        """Test that results_db creates a valid DuckDB connection."""
        from inspect_scout._scanresults import scan_results_db

        db = scan_results_db(test_scan_results.location)

        assert db.conn is not None
        assert isinstance(db.conn, duckdb.DuckDBPyConnection)

        # Clean up
        db.conn.close()

    def test_results_db_has_transcripts_table(self, test_scan_results):
        """Test that the transcripts table exists and has data."""
        from inspect_scout._scanresults import scan_results_db

        db = scan_results_db(test_scan_results.location)

        try:
            # Check table exists
            tables = db.conn.execute("SHOW TABLES").fetchall()
            table_names = [t[0] for t in tables]
            assert "transcripts" in table_names

            # Check it has data
            count = db.conn.execute("SELECT COUNT(*) FROM transcripts").fetchone()[0]
            assert count > 0

            # Check renamed columns exist
            columns = db.conn.execute("DESCRIBE transcripts").fetchdf()
            column_names = columns["column_name"].tolist()
            assert "id" in column_names
            assert "source_id" in column_names
            assert "source_uri" in column_names
            # Original names should NOT exist
            assert "sample_id" not in column_names
            assert "eval_id" not in column_names
            assert "log" not in column_names

        finally:
            db.conn.close()

    def test_results_db_has_scanner_views(self, test_scan_results):
        """Test that scanner views are created."""
        from inspect_scout._scanresults import scan_results_db

        db = scan_results_db(test_scan_results.location)

        try:
            tables = db.conn.execute("SHOW TABLES").fetchall()
            table_names = [t[0] for t in tables]

            # Check for scanner views
            assert "word_counter" in table_names
            assert "message_length" in table_names

        finally:
            db.conn.close()

    def test_results_db_can_query_scanners(self, test_scan_results):
        """Test that we can query scanner results."""
        from inspect_scout._scanresults import scan_results_db

        db = scan_results_db(test_scan_results.location)

        try:
            # Query a scanner
            results = db.conn.execute("SELECT * FROM word_counter LIMIT 5").fetchdf()

            assert len(results) > 0
            assert "value" in results.columns
            assert "explanation" in results.columns

        finally:
            db.conn.close()

    def test_results_db_can_join_tables(self, test_scan_results):
        """Test joining transcripts with scanner results."""
        from inspect_scout._scanresults import scan_results_db

        db = scan_results_db(test_scan_results.location)

        try:
            # Join transcripts with scanner results using the renamed columns
            results = db.conn.execute("""
                SELECT t.id, s.value, s.explanation
                FROM transcripts t
                JOIN word_counter s ON t.id = s.transcript_id
                LIMIT 5
            """).fetchdf()

            assert len(results) > 0
            assert "id" in results.columns
            assert "value" in results.columns
            assert "explanation" in results.columns

        finally:
            db.conn.close()

    def test_results_db_can_join_multiple_scanners(self, test_scan_results):
        """Test joining multiple scanner results together."""
        from inspect_scout._scanresults import scan_results_db

        db = scan_results_db(test_scan_results.location)

        try:
            # Join multiple scanners using the renamed columns
            results = db.conn.execute("""
                SELECT
                    t.id,
                    wc.value as word_count,
                    ml.value as message_length
                FROM transcripts t
                JOIN word_counter wc ON t.id = wc.transcript_id
                JOIN message_length ml ON t.id = ml.transcript_id
                LIMIT 5
            """).fetchdf()

            assert len(results) > 0
            assert "word_count" in results.columns
            assert "message_length" in results.columns

        finally:
            db.conn.close()

    def test_results_db_context_manager(self, test_scan_results):
        """Test that the context manager works correctly."""
        from inspect_scout._scanresults import scan_results_db

        db = scan_results_db(test_scan_results.location)

        with db:
            # Should be able to use the connection
            count = db.conn.execute("SELECT COUNT(*) FROM transcripts").fetchone()[0]
            assert count > 0

        # Connection should be closed after context exit
        with pytest.raises(duckdb.ConnectionException):
            db.conn.execute("SELECT 1")


class TestToFile:
    """Tests for the to_file() method."""

    def test_to_file_creates_database_file(self, test_scan_results, tmp_path):
        """Test that to_file creates a valid database file."""
        from inspect_scout._scanresults import scan_results_db

        db = scan_results_db(test_scan_results.location)
        db_file = tmp_path / "test_results.duckdb"

        try:
            db.to_file(str(db_file))

            # Check file was created
            assert db_file.exists()

            # Verify it's a valid DuckDB file
            verify_conn = duckdb.connect(str(db_file))
            tables = verify_conn.execute("SHOW TABLES").fetchall()
            assert len(tables) > 0
            verify_conn.close()

        finally:
            db.conn.close()

    def test_to_file_materializes_all_tables(self, test_scan_results, tmp_path):
        """Test that all tables/views are materialized."""
        from inspect_scout._scanresults import scan_results_db

        db = scan_results_db(test_scan_results.location)
        db_file = tmp_path / "test_results.duckdb"

        try:
            db.to_file(str(db_file))

            # Open the file and check tables
            verify_conn = duckdb.connect(str(db_file))
            tables = verify_conn.execute("SHOW TABLES").fetchall()
            table_names = [t[0] for t in tables]

            assert "transcripts" in table_names
            assert "word_counter" in table_names
            assert "message_length" in table_names

            verify_conn.close()

        finally:
            db.conn.close()

    def test_to_file_preserves_data(self, test_scan_results, tmp_path):
        """Test that data is preserved when writing to file."""
        from inspect_scout._scanresults import scan_results_db

        db = scan_results_db(test_scan_results.location)
        db_file = tmp_path / "test_results.duckdb"

        try:
            # Get original count
            original_count = db.conn.execute(
                "SELECT COUNT(*) FROM word_counter"
            ).fetchone()[0]

            db.to_file(str(db_file))

            # Check count in file
            verify_conn = duckdb.connect(str(db_file))
            file_count = verify_conn.execute(
                "SELECT COUNT(*) FROM word_counter"
            ).fetchone()[0]

            assert file_count == original_count

            verify_conn.close()

        finally:
            db.conn.close()

    def test_to_file_file_exists_error(self, test_scan_results, tmp_path):
        """Test that FileExistsError is raised when file exists."""
        from inspect_scout._scanresults import scan_results_db

        db = scan_results_db(test_scan_results.location)
        db_file = tmp_path / "test_results.duckdb"

        try:
            # Create the file first
            db.to_file(str(db_file))

            # Try to create it again without overwrite
            with pytest.raises(FileExistsError) as exc_info:
                db.to_file(str(db_file))

            assert "already exists" in str(exc_info.value)
            assert "overwrite=True" in str(exc_info.value)

        finally:
            db.conn.close()

    def test_to_file_overwrite_works(self, test_scan_results, tmp_path):
        """Test that overwrite parameter works correctly."""
        from inspect_scout._scanresults import scan_results_db

        db = scan_results_db(test_scan_results.location)
        db_file = tmp_path / "test_results.duckdb"

        try:
            # Create the file first
            db.to_file(str(db_file))

            # Overwrite should succeed
            db.to_file(str(db_file), overwrite=True)

            # Verify file still exists and is valid
            assert db_file.exists()
            verify_conn = duckdb.connect(str(db_file))
            tables = verify_conn.execute("SHOW TABLES").fetchall()
            assert len(tables) > 0
            verify_conn.close()

        finally:
            db.conn.close()

    def test_to_file_relative_path(self, test_scan_results):
        """Test that relative paths work correctly."""
        from inspect_scout._scanresults import scan_results_db

        db = scan_results_db(test_scan_results.location)

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                db_file = Path(tmpdir) / "test_results.duckdb"

                # Use relative path
                db.to_file(str(db_file))

                # Check file was created
                assert db_file.exists()

        finally:
            db.conn.close()

    def test_to_file_queries_work_after_materialization(
        self, test_scan_results, tmp_path
    ):
        """Test that joins work on the materialized database file."""
        from inspect_scout._scanresults import scan_results_db

        db = scan_results_db(test_scan_results.location)
        db_file = tmp_path / "test_results.duckdb"

        try:
            db.to_file(str(db_file))

            # Open file and run complex query using the renamed columns
            verify_conn = duckdb.connect(str(db_file))
            results = verify_conn.execute("""
                SELECT
                    t.id,
                    wc.value as word_count,
                    ml.value as message_length
                FROM transcripts t
                JOIN word_counter wc ON t.id = wc.transcript_id
                JOIN message_length ml ON t.id = ml.transcript_id
                LIMIT 5
            """).fetchdf()

            assert len(results) > 0
            assert "word_count" in results.columns
            assert "message_length" in results.columns

            verify_conn.close()

        finally:
            db.conn.close()


class TestResults:
    """Tests for the results() function (DataFrame-based results)."""

    @pytest.mark.asyncio
    async def test_results_has_renamed_columns(self, test_scan_results):
        """Test that results() also has the renamed transcript columns."""
        from inspect_scout._scanresults import scan_results_async

        results = await scan_results_async(test_scan_results.location)

        # Check that transcripts DataFrame has renamed columns
        transcripts_df = results.data["transcripts"]
        assert "id" in transcripts_df.columns
        assert "source_id" in transcripts_df.columns
        assert "source_uri" in transcripts_df.columns

        # Original names should NOT exist
        assert "sample_id" not in transcripts_df.columns
        assert "eval_id" not in transcripts_df.columns
        assert "log" not in transcripts_df.columns
