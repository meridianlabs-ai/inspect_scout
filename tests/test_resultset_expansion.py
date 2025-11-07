"""Tests for resultset expansion in scan_results_df and scan_results_db."""

import tempfile
from pathlib import Path

from inspect_scout import Result, Scanner, result_set, scan, scanner
from inspect_scout._scanresults import scan_results_db, scan_results_df
from inspect_scout._transcript.database import transcripts_from_logs
from inspect_scout._transcript.types import Transcript

# Test data location
LOGS_DIR = Path(__file__).parent.parent / "examples" / "scanner" / "logs"


@scanner(name="resultset_scanner", messages="all")
def resultset_scanner_factory() -> Scanner[Transcript]:
    """Scanner that returns a resultset with multiple labeled results."""

    async def scan_transcript(transcript: Transcript) -> Result:
        # Create a resultset with multiple results
        results = [
            Result(
                label="deception",
                value=True,
                explanation="Found deceptive pattern",
                metadata={"confidence": 0.9},
            ),
            Result(
                label="deception",
                value=False,
                explanation="No deception in second check",
                metadata={"confidence": 0.7},
            ),
            Result(
                label="misconfiguration",
                value="high",
                answer="HIGH",
                explanation="Configuration issue detected",
            ),
        ]
        return result_set(results)

    return scan_transcript


@scanner(name="simple_scanner", messages="all")
def simple_scanner_factory() -> Scanner[Transcript]:
    """Scanner that returns a simple non-resultset result."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(
            value=42,
            explanation="Simple value",
        )

    return scan_transcript


@scanner(name="empty_resultset_scanner", messages="all")
def empty_resultset_scanner_factory() -> Scanner[Transcript]:
    """Scanner that returns an empty resultset."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return result_set([])

    return scan_transcript


def test_resultset_expansion_basic() -> None:
    """Test that resultsets are expanded into multiple rows."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[resultset_scanner_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
        )

        # Get results with rows="results" (should expand)
        results = scan_results_df(status.location, scanner="resultset_scanner")
        df = results.scanners["resultset_scanner"]

        # Should have 3 rows (one for each result in the resultset)
        assert len(df) == 3

        # Check that labels are present
        assert "label" in df.columns
        assert sorted(df["label"].tolist()) == [
            "deception",
            "deception",
            "misconfiguration",
        ]

        # Check that values are expanded
        assert "value" in df.columns
        deception_values = df[df["label"] == "deception"]["value"].tolist()
        assert sorted(deception_values) == [False, True]

        # Check that explanation is present
        assert "explanation" in df.columns
        assert all(df["explanation"].notna())

        # Check that metadata is present and is JSON string
        assert "metadata" in df.columns
        assert all(df["metadata"].notna())


def test_resultset_expansion_with_type_casting() -> None:
    """Test that value types are properly cast after expansion."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[resultset_scanner_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
        )

        results = scan_results_df(status.location, scanner="resultset_scanner")
        df = results.scanners["resultset_scanner"]

        # Check value types
        assert "value_type" in df.columns

        # Boolean values should be cast to bool
        deception_rows = df[df["label"] == "deception"]
        for _, row in deception_rows.iterrows():
            if row["value_type"] == "boolean":
                assert isinstance(row["value"], bool)

        # String values should remain as strings
        misc_rows = df[df["label"] == "misconfiguration"]
        for _, row in misc_rows.iterrows():
            if row["value_type"] == "string":
                assert isinstance(row["value"], str)


def test_resultset_expansion_preserves_other_columns() -> None:
    """Test that non-result columns are preserved during expansion."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[resultset_scanner_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
        )

        results = scan_results_df(status.location, scanner="resultset_scanner")
        df = results.scanners["resultset_scanner"]

        # All expanded rows should have the same transcript_id
        assert "transcript_id" in df.columns
        assert df["transcript_id"].nunique() == 1

        # Should have scanner metadata
        assert "scanner_name" in df.columns
        assert all(df["scanner_name"] == "resultset_scanner")


def test_mixed_scanners_expansion() -> None:
    """Test that resultset and non-resultset scanners can coexist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[resultset_scanner_factory(), simple_scanner_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
        )

        # Resultset scanner should have 3 rows
        results = scan_results_df(status.location, scanner="resultset_scanner")
        resultset_df = results.scanners["resultset_scanner"]
        assert len(resultset_df) == 3

        # Simple scanner should have 1 row
        results = scan_results_df(status.location, scanner="simple_scanner")
        simple_df = results.scanners["simple_scanner"]
        assert len(simple_df) == 1
        assert simple_df["value"].iloc[0] == 42


def test_rows_parameter_transcripts_mode() -> None:
    """Test that rows='transcripts' does NOT expand resultsets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[resultset_scanner_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
        )

        # Get results with rows="transcripts" (should NOT expand)
        results = scan_results_df(
            status.location, scanner="resultset_scanner", rows="transcripts"
        )
        df = results.scanners["resultset_scanner"]

        # Should have 1 row (unexpanded)
        assert len(df) == 1

        # Value should be a JSON string
        assert "value" in df.columns
        assert isinstance(df["value"].iloc[0], str)

        # Value type should be "resultset"
        assert df["value_type"].iloc[0] == "resultset"


def test_empty_resultset_expansion() -> None:
    """Test that empty resultsets are handled correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[empty_resultset_scanner_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
        )

        results = scan_results_df(status.location, scanner="empty_resultset_scanner")
        df = results.scanners["empty_resultset_scanner"]

        # Empty resultset should result in 0 rows after expansion
        assert len(df) == 0


def test_resultset_with_optional_fields() -> None:
    """Test that optional fields (answer, metadata) are handled correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[resultset_scanner_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
        )

        results = scan_results_df(status.location, scanner="resultset_scanner")
        df = results.scanners["resultset_scanner"]

        # Some rows have answer, some don't
        assert "answer" in df.columns
        misc_row = df[df["label"] == "misconfiguration"].iloc[0]
        assert misc_row["answer"] == "HIGH"

        # Deception rows may not have answer
        deception_rows = df[df["label"] == "deception"]
        # Check that answer column exists but may be None
        assert "answer" in deception_rows.columns


def test_multiple_transcripts_with_resultsets() -> None:
    """Test resultset expansion across multiple transcripts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[resultset_scanner_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=2,  # Scan 2 transcripts
            max_processes=1,
        )

        results = scan_results_df(status.location, scanner="resultset_scanner")
        df = results.scanners["resultset_scanner"]

        # Should have 6 rows (3 results × 2 transcripts)
        assert len(df) == 6

        # Should have 2 unique transcript IDs
        assert df["transcript_id"].nunique() == 2

        # Each transcript should contribute 3 rows
        for transcript_id in df["transcript_id"].unique():
            transcript_rows = df[df["transcript_id"] == transcript_id]
            assert len(transcript_rows) == 3


# DuckDB-specific tests


def test_duckdb_resultset_expansion_basic() -> None:
    """Test that resultsets are expanded into multiple rows in DuckDB views."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[resultset_scanner_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
        )

        # Get results with rows="results" (should expand)
        results_db = scan_results_db(status.location)

        # Query the view
        df = results_db.conn.execute("SELECT * FROM resultset_scanner").fetchdf()

        # Should have 3 rows (one for each result in the resultset)
        assert len(df) == 3

        # Check that labels are present
        assert "label" in df.columns
        assert sorted(df["label"].tolist()) == [
            "deception",
            "deception",
            "misconfiguration",
        ]

        # Check that values are expanded
        assert "value" in df.columns
        deception_values = df[df["label"] == "deception"]["value"].tolist()
        # DuckDB may return different types, so sort as strings (case-insensitive)
        assert sorted([str(v).lower() for v in deception_values]) == ["false", "true"]

        results_db.conn.close()


def test_duckdb_resultset_type_casting() -> None:
    """Test that value types are properly cast after expansion in DuckDB."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[resultset_scanner_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
        )

        results_db = scan_results_db(status.location)
        df = results_db.conn.execute("SELECT * FROM resultset_scanner").fetchdf()

        # Check value types
        assert "value_type" in df.columns

        # Boolean rows should have boolean value_type
        deception_rows = df[df["label"] == "deception"]
        for _, row in deception_rows.iterrows():
            if row["value_type"] == "boolean":
                # Value should be boolean type
                assert isinstance(row["value"], (bool, type(None)))

        # String rows should have string value_type
        misc_rows = df[df["label"] == "misconfiguration"]
        for _, row in misc_rows.iterrows():
            if row["value_type"] == "string":
                assert isinstance(row["value"], (str, type(None)))

        results_db.conn.close()


def test_duckdb_rows_transcripts_mode() -> None:
    """Test that rows='transcripts' does NOT expand resultsets in DuckDB."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[resultset_scanner_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
        )

        # Get results with rows="transcripts" (should NOT expand)
        results_db = scan_results_db(status.location, rows="transcripts")
        df = results_db.conn.execute("SELECT * FROM resultset_scanner").fetchdf()

        # Should have 1 row (unexpanded)
        assert len(df) == 1

        # Value type should be "resultset"
        assert df["value_type"].iloc[0] == "resultset"

        # Value should be a JSON string
        assert isinstance(df["value"].iloc[0], str)

        results_db.conn.close()


def test_duckdb_mixed_scanners() -> None:
    """Test that resultset and non-resultset scanners work together in DuckDB."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[resultset_scanner_factory(), simple_scanner_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
        )

        results_db = scan_results_db(status.location)

        # Resultset scanner should have 3 rows
        resultset_df = results_db.conn.execute(
            "SELECT * FROM resultset_scanner"
        ).fetchdf()
        assert len(resultset_df) == 3

        # Simple scanner should have 1 row
        simple_df = results_db.conn.execute("SELECT * FROM simple_scanner").fetchdf()
        assert len(simple_df) == 1
        assert simple_df["value"].iloc[0] == 42

        results_db.conn.close()


def test_duckdb_preserves_columns() -> None:
    """Test that all columns are preserved during expansion in DuckDB."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[resultset_scanner_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
        )

        results_db = scan_results_db(status.location)
        df = results_db.conn.execute("SELECT * FROM resultset_scanner").fetchdf()

        # All expanded rows should have the same transcript_id
        assert "transcript_id" in df.columns
        assert df["transcript_id"].nunique() == 1

        # Should have scanner metadata
        assert "scanner_name" in df.columns
        assert all(df["scanner_name"] == "resultset_scanner")

        # Should have scan metadata
        assert "scan_id" in df.columns
        assert df["scan_id"].nunique() == 1

        results_db.conn.close()


def test_duckdb_multiple_transcripts() -> None:
    """Test resultset expansion across multiple transcripts in DuckDB."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[resultset_scanner_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=2,  # Scan 2 transcripts
            max_processes=1,
        )

        results_db = scan_results_db(status.location)
        df = results_db.conn.execute("SELECT * FROM resultset_scanner").fetchdf()

        # Should have 6 rows (3 results × 2 transcripts)
        assert len(df) == 6

        # Should have 2 unique transcript IDs
        assert df["transcript_id"].nunique() == 2

        # Each transcript should contribute 3 rows
        for transcript_id in df["transcript_id"].unique():
            count = results_db.conn.execute(
                f"SELECT COUNT(*) FROM resultset_scanner WHERE transcript_id = '{transcript_id}'"
            ).fetchone()
            assert count is not None
            assert count[0] == 3

        results_db.conn.close()


def test_duckdb_empty_resultset() -> None:
    """Test that empty resultsets are handled correctly in DuckDB."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[empty_resultset_scanner_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
        )

        results_db = scan_results_db(status.location)
        df = results_db.conn.execute("SELECT * FROM empty_resultset_scanner").fetchdf()

        # Empty resultset should result in 0 rows after expansion
        assert len(df) == 0

        results_db.conn.close()


def test_duckdb_query_expanded_results() -> None:
    """Test that we can query expanded results with SQL in DuckDB."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[resultset_scanner_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
        )

        results_db = scan_results_db(status.location)

        # Query for deception results only
        deception_df = results_db.conn.execute(
            "SELECT * FROM resultset_scanner WHERE label = 'deception'"
        ).fetchdf()
        assert len(deception_df) == 2
        assert all(deception_df["label"] == "deception")

        # Query for true deception values
        true_deception = results_db.conn.execute(
            "SELECT * FROM resultset_scanner WHERE label = 'deception' AND value = TRUE"
        ).fetchdf()
        assert len(true_deception) == 1

        # Aggregate queries should work
        label_counts = results_db.conn.execute(
            "SELECT label, COUNT(*) as count FROM resultset_scanner GROUP BY label ORDER BY label"
        ).fetchdf()
        assert len(label_counts) == 2
        assert label_counts[label_counts["label"] == "deception"]["count"].iloc[0] == 2
        assert (
            label_counts[label_counts["label"] == "misconfiguration"]["count"].iloc[0]
            == 1
        )

        results_db.conn.close()


def test_resultset_expansion_nulls_scan_execution_fields() -> None:
    """Test that scan execution fields are NULL in expanded rows to avoid incorrect aggregation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[resultset_scanner_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
        )

        results = scan_results_df(status.location, scanner="resultset_scanner")
        df = results.scanners["resultset_scanner"]

        # All expanded rows should have NULL scan_total_tokens and scan_model_usage
        assert "scan_total_tokens" in df.columns
        assert "scan_model_usage" in df.columns

        # All values should be None/null since these are expanded resultset rows
        assert df["scan_total_tokens"].isna().all()
        assert df["scan_model_usage"].isna().all()


def test_duckdb_resultset_expansion_nulls_scan_execution_fields() -> None:
    """Test that scan execution fields are NULL in expanded DuckDB rows."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[resultset_scanner_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
        )

        results_db = scan_results_db(status.location)
        df = results_db.conn.execute("SELECT * FROM resultset_scanner").fetchdf()

        # All expanded rows should have NULL scan_total_tokens and scan_model_usage
        assert "scan_total_tokens" in df.columns
        assert "scan_model_usage" in df.columns

        # All values should be None/null
        assert df["scan_total_tokens"].isna().all()
        assert df["scan_model_usage"].isna().all()

        results_db.conn.close()


@scanner(name="resultset_with_references_scanner", messages="all")
def resultset_with_references_scanner_factory() -> Scanner[Transcript]:
    """Scanner that returns a resultset with Results containing references."""
    from inspect_scout._scanner.result import Reference

    async def scan_transcript(transcript: Transcript) -> Result:
        # Create results with different reference types
        results = [
            Result(
                label="finding1",
                value=True,
                explanation="Found issue in message 1",
                references=[
                    Reference(type="message", cite="[M1]", id="msg-1"),
                    Reference(type="message", cite="[M2]", id="msg-2"),
                ],
            ),
            Result(
                label="finding2",
                value=False,
                explanation="No issue in event 1",
                references=[
                    Reference(type="event", cite="[E1]", id="event-1"),
                ],
            ),
            Result(
                label="finding3",
                value="mixed",
                explanation="Mixed references",
                references=[
                    Reference(type="message", cite="[M3]", id="msg-3"),
                    Reference(type="event", cite="[E2]", id="event-2"),
                    Reference(type="event", cite="[E3]", id="event-3"),
                ],
            ),
        ]
        return result_set(results)

    return scan_transcript


def test_resultset_expansion_with_references() -> None:
    """Test that references are properly split by type in expanded rows."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[resultset_with_references_scanner_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
        )

        results = scan_results_df(
            status.location, scanner="resultset_with_references_scanner"
        )
        df = results.scanners["resultset_with_references_scanner"]

        # Should have 3 rows (one for each result in the resultset)
        assert len(df) == 3

        # Check that reference columns exist
        assert "message_references" in df.columns
        assert "event_references" in df.columns

        # Check first row (2 message refs, 0 event refs)
        row1 = df[df["label"] == "finding1"].iloc[0]
        import json

        msg_refs_1 = json.loads(row1["message_references"])
        event_refs_1 = json.loads(row1["event_references"])
        assert len(msg_refs_1) == 2
        assert len(event_refs_1) == 0
        assert msg_refs_1[0]["type"] == "message"
        assert msg_refs_1[0]["cite"] == "[M1]"

        # Check second row (0 message refs, 1 event ref)
        row2 = df[df["label"] == "finding2"].iloc[0]
        msg_refs_2 = json.loads(row2["message_references"])
        event_refs_2 = json.loads(row2["event_references"])
        assert len(msg_refs_2) == 0
        assert len(event_refs_2) == 1
        assert event_refs_2[0]["type"] == "event"
        assert event_refs_2[0]["cite"] == "[E1]"

        # Check third row (1 message ref, 2 event refs)
        row3 = df[df["label"] == "finding3"].iloc[0]
        msg_refs_3 = json.loads(row3["message_references"])
        event_refs_3 = json.loads(row3["event_references"])
        assert len(msg_refs_3) == 1
        assert len(event_refs_3) == 2
        assert msg_refs_3[0]["cite"] == "[M3]"
        assert event_refs_3[0]["cite"] == "[E2]"
        assert event_refs_3[1]["cite"] == "[E3]"


def test_duckdb_resultset_expansion_with_references() -> None:
    """Test that references are properly split by type in expanded DuckDB rows."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[resultset_with_references_scanner_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
        )

        results_db = scan_results_db(status.location)
        df = results_db.conn.execute(
            "SELECT * FROM resultset_with_references_scanner"
        ).fetchdf()

        # Should have 3 rows
        assert len(df) == 3

        # Check that reference columns exist
        assert "message_references" in df.columns
        assert "event_references" in df.columns

        import json

        # Check first row (2 message refs, 0 event refs)
        row1 = df[df["label"] == "finding1"].iloc[0]
        msg_refs_1 = json.loads(row1["message_references"])
        event_refs_1 = json.loads(row1["event_references"])
        assert len(msg_refs_1) == 2
        assert len(event_refs_1) == 0

        # Check second row (0 message refs, 1 event ref)
        row2 = df[df["label"] == "finding2"].iloc[0]
        msg_refs_2 = json.loads(row2["message_references"])
        event_refs_2 = json.loads(row2["event_references"])
        assert len(msg_refs_2) == 0
        assert len(event_refs_2) == 1

        # Check third row (1 message ref, 2 event refs)
        row3 = df[df["label"] == "finding3"].iloc[0]
        msg_refs_3 = json.loads(row3["message_references"])
        event_refs_3 = json.loads(row3["event_references"])
        assert len(msg_refs_3) == 1
        assert len(event_refs_3) == 2

        results_db.conn.close()
