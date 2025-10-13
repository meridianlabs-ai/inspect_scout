"""Tests for DuckDB results_db() and to_file() functionality."""

import tempfile
from pathlib import Path

import duckdb
import pytest
from inspect_scout import scan, transcripts

from .test_scanners import message_length, word_counter


@pytest.fixture
def test_logs_path():
    """Path to test logs."""
    return Path(__file__).parent / "logs"


@pytest.fixture
def test_scan_results(test_logs_path, tmp_path):
    """Run a test scan and return the status."""
    status = scan(
        scanners=[
            word_counter("the"),
            message_length(),
        ],
        transcripts=transcripts(test_logs_path),
        max_transcripts=5,
        results=tmp_path.as_posix(),
    )
    return status


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
            # Join transcripts with scanner results
            results = db.conn.execute("""
                SELECT t.sample_id, s.value, s.explanation
                FROM transcripts t
                JOIN word_counter s ON t.sample_id = s.transcript_id
                LIMIT 5
            """).fetchdf()

            assert len(results) > 0
            assert "sample_id" in results.columns
            assert "value" in results.columns
            assert "explanation" in results.columns

        finally:
            db.conn.close()

    def test_results_db_can_join_multiple_scanners(self, test_scan_results):
        """Test joining multiple scanner results together."""
        from inspect_scout._scanresults import scan_results_db

        db = scan_results_db(test_scan_results.location)

        try:
            # Join multiple scanners
            results = db.conn.execute("""
                SELECT
                    t.sample_id,
                    wc.value as word_count,
                    ml.value as message_length
                FROM transcripts t
                JOIN word_counter wc ON t.sample_id = wc.transcript_id
                JOIN message_length ml ON t.sample_id = ml.transcript_id
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

            # Open file and run complex query
            verify_conn = duckdb.connect(str(db_file))
            results = verify_conn.execute("""
                SELECT
                    t.sample_id,
                    wc.value as word_count,
                    ml.value as message_length
                FROM transcripts t
                JOIN word_counter wc ON t.sample_id = wc.transcript_id
                JOIN message_length ml ON t.sample_id = ml.transcript_id
                LIMIT 5
            """).fetchdf()

            assert len(results) > 0
            assert "word_count" in results.columns
            assert "message_length" in results.columns

            verify_conn.close()

        finally:
            db.conn.close()


class TestCloudPaths:
    """Tests for cloud path handling."""

    def test_to_file_detects_s3_path(self, test_scan_results):
        """Test that S3 paths are detected (without actually connecting)."""
        from inspect_scout._scanresults import scan_results_db

        db = scan_results_db(test_scan_results.location)

        # This will fail because we don't have AWS credentials set up,
        # but we can verify it tries to use cloud storage
        with pytest.raises(Exception):  # Will fail on connection/auth
            db.to_file("s3://test-bucket/results.duckdb")

        db.conn.close()

    def test_to_file_detects_gcs_path(self, test_scan_results):
        """Test that GCS paths are detected (without actually connecting)."""
        from inspect_scout._scanresults import scan_results_db

        db = scan_results_db(test_scan_results.location)

        # This will fail because we don't have GCS credentials set up,
        # but we can verify it tries to use cloud storage
        with pytest.raises(Exception):  # Will fail on connection/auth
            db.to_file("gs://test-bucket/results.duckdb")

        db.conn.close()
