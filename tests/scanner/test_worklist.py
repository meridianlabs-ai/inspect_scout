"""End-to-end tests for the worklist feature."""

import tempfile
from pathlib import Path

import pytest
from inspect_scout import Result, Scanner, ScannerWork, scan, scanner
from inspect_scout._scanresults import scan_results_db, scan_status
from inspect_scout._transcript.eval_log import transcripts_from_logs
from inspect_scout._transcript.types import Transcript

# Test data location
LOGS_DIR = Path(__file__).parent.parent / "recorder" / "logs"


# ============================================================================
# Helper Functions
# ============================================================================


async def get_n_transcript_ids(n: int) -> list[str]:
    """Get first n transcript IDs from test logs."""
    transcripts = transcripts_from_logs(LOGS_DIR)
    async with transcripts.reader() as tr:
        index_list = [info async for info in tr.index()]
        return [info.id for info in index_list[:n]]


# Define scanner factories that can be used in tests
# Note: Names have _scanner suffix to avoid DuckDB namespace conflicts
@scanner(name="counter_a", messages="all")
def counter_a_scanner() -> Scanner[Transcript]:
    """Scanner A - returns value 1."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(
            value=1,
            explanation=f"Scanner counter_a processed transcript {transcript.id}",
        )

    return scan_transcript


@scanner(name="counter_b", messages="all")
def counter_b_scanner() -> Scanner[Transcript]:
    """Scanner B - returns value 2."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(
            value=2,
            explanation=f"Scanner counter_b processed transcript {transcript.id}",
        )

    return scan_transcript


@scanner(name="scanner_a", messages="all")
def scanner_a_factory() -> Scanner[Transcript]:
    """Scanner A - generic."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(
            value=1, explanation=f"Scanner A processed transcript {transcript.id}"
        )

    return scan_transcript


@scanner(name="scanner_b", messages="all")
def scanner_b_factory() -> Scanner[Transcript]:
    """Scanner B - generic."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(
            value=2, explanation=f"Scanner B processed transcript {transcript.id}"
        )

    return scan_transcript


@scanner(name="scanner_1", messages="all")
def scanner_1_factory() -> Scanner[Transcript]:
    """Scanner 1."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(value=1, explanation=f"Scanner 1 processed {transcript.id}")

    return scan_transcript


@scanner(name="scanner_2", messages="all")
def scanner_2_factory() -> Scanner[Transcript]:
    """Scanner 2."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(value=2, explanation=f"Scanner 2 processed {transcript.id}")

    return scan_transcript


@scanner(name="scanner_3", messages="all")
def scanner_3_factory() -> Scanner[Transcript]:
    """Scanner 3."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(value=3, explanation=f"Scanner 3 processed {transcript.id}")

    return scan_transcript


@scanner(name="scanner_4", messages="all")
def scanner_4_factory() -> Scanner[Transcript]:
    """Scanner 4."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(value=4, explanation=f"Scanner 4 processed {transcript.id}")

    return scan_transcript


@scanner(name="default_a", messages="all")
def default_a_factory() -> Scanner[Transcript]:
    """Default scanner A."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(value=1, explanation="default_a processed transcript")

    return scan_transcript


@scanner(name="default_b", messages="all")
def default_b_factory() -> Scanner[Transcript]:
    """Default scanner B."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(value=2, explanation="default_b processed transcript")

    return scan_transcript


@scanner(name="spec_scanner", messages="all")
def spec_scanner_factory() -> Scanner[Transcript]:
    """Scanner for spec persistence test."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(value=1, explanation="spec_scanner processed transcript")

    return scan_transcript


@scanner(name="resume_scanner", messages="all")
def resume_scanner_factory() -> Scanner[Transcript]:
    """Scanner for resume test."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(value=1, explanation="resume_scanner processed transcript")

    return scan_transcript


@scanner(name="subset_scanner", messages="all")
def subset_scanner_factory() -> Scanner[Transcript]:
    """Scanner for subset test."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(value=1, explanation="subset_scanner processed transcript")

    return scan_transcript


@scanner(name="resilient_scanner", messages="all")
def resilient_scanner_factory() -> Scanner[Transcript]:
    """Scanner for resilient test."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(value=1, explanation="resilient_scanner processed transcript")

    return scan_transcript


@scanner(name="db_scanner_a", messages="all")
def db_scanner_a_factory() -> Scanner[Transcript]:
    """DB Scanner A."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(value=1, explanation="db_scanner_a processed transcript")

    return scan_transcript


@scanner(name="db_scanner_b", messages="all")
def db_scanner_b_factory() -> Scanner[Transcript]:
    """DB Scanner B."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(value=2, explanation="db_scanner_b processed transcript")

    return scan_transcript


@scanner(name="original_name_a", messages="all")
def original_name_a_factory() -> Scanner[Transcript]:
    """Original name scanner A."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(value=1, explanation="original_name_a processed transcript")

    return scan_transcript


@scanner(name="original_name_b", messages="all")
def original_name_b_factory() -> Scanner[Transcript]:
    """Original name scanner B."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(value=2, explanation="original_name_b processed transcript")

    return scan_transcript


def verify_scanner_results(
    scan_location: str, scanner_name: str, expected_transcript_ids: list[str]
) -> None:
    """Verify a scanner's results match expected transcript IDs."""
    db = scan_results_db(scan_location)
    try:
        # Check if table exists
        tables = db.conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]

        if scanner_name not in table_names:
            raise AssertionError(
                f"Scanner table '{scanner_name}' not found! "
                f"Available tables: {table_names}"
            )

        # Query the scanner's results
        query = f'SELECT transcript_id FROM "{scanner_name}" ORDER BY transcript_id'
        results_df = db.conn.execute(query).fetchdf()
        actual_ids = sorted(results_df["transcript_id"].tolist())
        expected_ids = sorted(expected_transcript_ids)

        assert actual_ids == expected_ids, (
            f"Scanner '{scanner_name}' processed incorrect transcripts.\n"
            f"Expected: {expected_ids}\n"
            f"Actual: {actual_ids}"
        )

        # Verify count
        count_query = f'SELECT COUNT(*) as count FROM "{scanner_name}"'
        _result = db.conn.execute(count_query).fetchone()
        assert _result is not None
        count = _result[0]
        assert count == len(expected_transcript_ids), (
            f"Scanner '{scanner_name}' has {count} results, "
            f"expected {len(expected_transcript_ids)}"
        )
    finally:
        db.conn.close()


# ============================================================================
# Basic Worklist Tests
# ============================================================================


@pytest.mark.asyncio
async def test_worklist_basic_filtering() -> None:
    """Verify that a worklist correctly restricts which transcripts are processed."""
    # Get 5 transcript IDs
    transcript_ids = await get_n_transcript_ids(5)

    # Create worklist with overlap
    # counter_a processes transcripts [0, 1, 2]
    # counter_b processes transcripts [2, 3, 4]
    worklist = [
        ScannerWork(scanner="counter_a", transcripts=transcript_ids[0:3]),
        ScannerWork(scanner="counter_b", transcripts=transcript_ids[2:5]),
    ]

    # Run scan
    with tempfile.TemporaryDirectory() as tmpdir:
        result = scan(
            scanners=[counter_a_scanner(), counter_b_scanner()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            worklist=worklist,
            results=tmpdir,
        )

        # Verify results
        verify_scanner_results(result.location, "counter_a", transcript_ids[0:3])
        verify_scanner_results(result.location, "counter_b", transcript_ids[2:5])


@pytest.mark.asyncio
async def test_worklist_no_overlap() -> None:
    """Verify scanners with completely disjoint worklists."""
    # Get 4 transcript IDs
    transcript_ids = await get_n_transcript_ids(4)

    # Create worklist with no overlap
    worklist = [
        ScannerWork(scanner="scanner_a", transcripts=transcript_ids[0:2]),
        ScannerWork(scanner="scanner_b", transcripts=transcript_ids[2:4]),
    ]

    # Run scan
    with tempfile.TemporaryDirectory() as tmpdir:
        result = scan(
            scanners=[scanner_a_factory(), scanner_b_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            worklist=worklist,
            results=tmpdir,
        )

        # Verify results - no overlap
        verify_scanner_results(result.location, "scanner_a", transcript_ids[0:2])
        verify_scanner_results(result.location, "scanner_b", transcript_ids[2:4])


@pytest.mark.asyncio
async def test_worklist_empty_transcript_list() -> None:
    """Verify scanner with empty transcript list processes nothing."""
    # Get 3 transcript IDs
    transcript_ids = await get_n_transcript_ids(3)

    # Create worklist with one empty list
    worklist = [
        ScannerWork(scanner="scanner_a", transcripts=transcript_ids),
        ScannerWork(scanner="scanner_b", transcripts=[]),  # Empty list
    ]

    # Run scan
    with tempfile.TemporaryDirectory() as tmpdir:
        result = scan(
            scanners=[scanner_a_factory(), scanner_b_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            worklist=worklist,
            results=tmpdir,
        )

        # Verify scanner_a has results
        verify_scanner_results(result.location, "scanner_a", transcript_ids)

        # Verify scanner_b has no results (no table created when no transcripts processed)
        db = scan_results_db(result.location)
        try:
            tables = db.conn.execute("SHOW TABLES").fetchall()
            table_names = [t[0] for t in tables]
            assert "scanner_b" not in table_names, (
                "scanner_b should not have a table when processing no transcripts"
            )
        finally:
            db.conn.close()


@pytest.mark.asyncio
async def test_worklist_single_scanner_subset() -> None:
    """Verify a single scanner can process a subset of transcripts."""
    # Get 5 transcript IDs from available transcripts
    transcript_ids = await get_n_transcript_ids(5)

    # Create worklist with subset
    worklist = [ScannerWork(scanner="subset_scanner", transcripts=transcript_ids)]

    # Run scan with all transcripts available but worklist limiting to 5
    with tempfile.TemporaryDirectory() as tmpdir:
        result = scan(
            scanners=[subset_scanner_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            worklist=worklist,
            results=tmpdir,
        )

        # Verify exactly 5 results
        verify_scanner_results(result.location, "subset_scanner", transcript_ids)


# ============================================================================
# Edge Case Tests
# ============================================================================


@pytest.mark.asyncio
async def test_worklist_nonexistent_transcript_ids() -> None:
    """Verify system handles gracefully when worklist contains non-existent IDs."""
    # Get 2 valid transcript IDs
    valid_ids = await get_n_transcript_ids(2)

    # Add non-existent IDs
    transcript_ids = [
        valid_ids[0],
        "nonexistent_id_12345",
        valid_ids[1],
        "another_fake_id_67890",
    ]

    # Create worklist with mix of valid and invalid IDs
    worklist = [ScannerWork(scanner="resilient_scanner", transcripts=transcript_ids)]

    # Run scan - should not error, just process valid IDs
    with tempfile.TemporaryDirectory() as tmpdir:
        result = scan(
            scanners=[resilient_scanner_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            worklist=worklist,
            results=tmpdir,
        )

        # Verify only valid IDs were processed (non-existent IDs silently skipped)
        verify_scanner_results(result.location, "resilient_scanner", valid_ids)


@pytest.mark.asyncio
async def test_worklist_default_behavior_without_worklist() -> None:
    """Verify omitting worklist results in all scanners processing all transcripts."""
    # Get 10 transcript IDs
    transcript_ids = await get_n_transcript_ids(10)

    # Run scan WITHOUT worklist (default behavior)
    with tempfile.TemporaryDirectory() as tmpdir:
        result = scan(
            scanners=[default_a_factory(), default_b_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            # Note: No worklist parameter - should process all transcripts
            results=tmpdir,
            limit=10,  # Limit to 10 to match our transcript_ids
        )

        # Verify both scanners processed all 10 transcripts
        verify_scanner_results(result.location, "default_a", transcript_ids)
        verify_scanner_results(result.location, "default_b", transcript_ids)


# ============================================================================
# Persistence Tests
# ============================================================================


@pytest.mark.asyncio
async def test_worklist_spec_persistence() -> None:
    """Verify worklist is correctly stored in scan spec."""
    # Get transcript IDs
    transcript_ids = await get_n_transcript_ids(3)

    # Create worklist
    original_worklist = [
        ScannerWork(scanner="spec_scanner", transcripts=transcript_ids)
    ]

    # Run scan
    with tempfile.TemporaryDirectory() as tmpdir:
        result = scan(
            scanners=[spec_scanner_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            worklist=original_worklist,
            results=tmpdir,
        )

        # Load scan status and check spec
        status = scan_status(result.location)
        spec = status.spec

        # Verify worklist is in spec
        assert spec.worklist is not None, "Worklist should be stored in spec"
        assert len(spec.worklist) == 1, "Should have 1 worklist entry"

        # Verify worklist content
        stored_work = spec.worklist[0]
        assert stored_work.scanner == "spec_scanner"
        assert sorted(stored_work.transcripts) == sorted(transcript_ids)


# ============================================================================
# Complex Scenario Tests
# ============================================================================


@pytest.mark.asyncio
async def test_worklist_partial_overlap_many_scanners() -> None:
    """Test complex scenario with many scanners and various overlaps."""
    # Get 8 transcript IDs (A, B, C, D, E, F, G, H)
    transcript_ids = await get_n_transcript_ids(8)
    A, B, C, D, E, F, G, H = transcript_ids

    # Create worklist with various overlaps:
    # Scanner 1: [A, B, C, D]
    # Scanner 2: [B, C, E]
    # Scanner 3: [D, E, F]
    # Scanner 4: [F, G, H]
    worklist = [
        ScannerWork(scanner="scanner_1", transcripts=[A, B, C, D]),
        ScannerWork(scanner="scanner_2", transcripts=[B, C, E]),
        ScannerWork(scanner="scanner_3", transcripts=[D, E, F]),
        ScannerWork(scanner="scanner_4", transcripts=[F, G, H]),
    ]

    # Run scan
    with tempfile.TemporaryDirectory() as tmpdir:
        result = scan(
            scanners=[
                scanner_1_factory(),
                scanner_2_factory(),
                scanner_3_factory(),
                scanner_4_factory(),
            ],
            transcripts=transcripts_from_logs(LOGS_DIR),
            worklist=worklist,
            results=tmpdir,
        )

        # Verify each scanner processed exactly its assigned transcripts
        verify_scanner_results(result.location, "scanner_1", [A, B, C, D])
        verify_scanner_results(result.location, "scanner_2", [B, C, E])
        verify_scanner_results(result.location, "scanner_3", [D, E, F])
        verify_scanner_results(result.location, "scanner_4", [F, G, H])

        # Verify total scan operations count
        # Should be 4 + 3 + 3 + 3 = 13 total results
        db = scan_results_db(result.location)
        counts = []
        for name in ["scanner_1", "scanner_2", "scanner_3", "scanner_4"]:
            _res = db.conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()
            assert _res is not None
            counts.append(_res[0])
        total_count = sum(counts)
        db.conn.close()
        assert total_count == 13, f"Expected 13 total results, got {total_count}"


@pytest.mark.asyncio
async def test_worklist_results_database_filtering() -> None:
    """Verify scan results database correctly reflects worklist filtering."""
    # Get transcript IDs
    transcript_ids = await get_n_transcript_ids(5)

    # Create worklist
    worklist = [
        ScannerWork(scanner="db_scanner_a", transcripts=transcript_ids[0:3]),
        ScannerWork(scanner="db_scanner_b", transcripts=transcript_ids[2:5]),
    ]

    # Run scan
    with tempfile.TemporaryDirectory() as tmpdir:
        result = scan(
            scanners=[db_scanner_a_factory(), db_scanner_b_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            worklist=worklist,
            results=tmpdir,
        )

        # Use scan_results_db to verify
        db = scan_results_db(result.location)
        try:
            # Check scanner_a table
            df_a = db.conn.execute("SELECT * FROM db_scanner_a").fetchdf()
            assert len(df_a) == 3, f"db_scanner_a should have 3 rows, got {len(df_a)}"
            assert set(df_a["transcript_id"]) == set(transcript_ids[0:3]), (
                "db_scanner_a has wrong transcript IDs"
            )

            # Check scanner_b table
            df_b = db.conn.execute("SELECT * FROM db_scanner_b").fetchdf()
            assert len(df_b) == 3, f"db_scanner_b should have 3 rows, got {len(df_b)}"
            assert set(df_b["transcript_id"]) == set(transcript_ids[2:5]), (
                "db_scanner_b has wrong transcript IDs"
            )

            # Verify values are correct
            assert all(df_a["value"] == 1), (
                "db_scanner_a should have value=1 for all rows"
            )
            assert all(df_b["value"] == 2), (
                "db_scanner_b should have value=2 for all rows"
            )

        finally:
            db.conn.close()


# ============================================================================
# Integration with Named Scanners (dict)
# ============================================================================


@pytest.mark.asyncio
async def test_worklist_with_named_scanners_dict() -> None:
    """Verify worklist works with scanners passed as a dict with explicit names."""
    # Get transcript IDs
    transcript_ids = await get_n_transcript_ids(4)

    # Pass scanners as dict with custom names
    scanners_dict = {
        "custom_a": original_name_a_factory(),
        "custom_b": original_name_b_factory(),
    }

    # Create worklist using the dict keys (custom names)
    worklist = [
        ScannerWork(scanner="custom_a", transcripts=transcript_ids[0:2]),
        ScannerWork(scanner="custom_b", transcripts=transcript_ids[2:4]),
    ]

    # Run scan
    with tempfile.TemporaryDirectory() as tmpdir:
        result = scan(
            scanners=scanners_dict,
            transcripts=transcripts_from_logs(LOGS_DIR),
            worklist=worklist,
            results=tmpdir,
        )

        # Verify results using custom names
        verify_scanner_results(result.location, "custom_a", transcript_ids[0:2])
        verify_scanner_results(result.location, "custom_b", transcript_ids[2:4])
