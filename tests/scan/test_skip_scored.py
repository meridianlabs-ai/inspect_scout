"""End-to-end tests for the skip_scored feature."""

import tempfile
from pathlib import Path

from inspect_ai import Task, eval
from inspect_ai.dataset import Sample
from inspect_ai.log._file import write_eval_log
from inspect_ai.scorer import Score
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_scout import Result, Scanner, scan, scanner
from inspect_scout._scanresults import scan_results_db
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript

# ============================================================================
# Helper Functions
# ============================================================================


@solver
def add_score_solver(
    scorer_name: str, scored_sample_ids: set[str] | None = None
) -> Solver:
    async def solve(state: TaskState, _generate: Generate) -> TaskState:
        if scored_sample_ids is None or state.sample_id in scored_sample_ids:
            state.scores = {scorer_name: Score(value=1)}
        return state

    return solve  # type: ignore[return-value]


def verify_scanner_results(
    scan_location: str,
    scanner_name: str,
    expected_task_ids: list[str],
) -> None:
    """Verify scanner results match expected transcript task IDs."""
    db = scan_results_db(scan_location)
    try:
        tables = db.conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]

        if scanner_name not in table_names:
            raise AssertionError(
                f"Scanner table '{scanner_name}' not found! "
                f"Available tables: {table_names}"
            )

        # Verify count first for clearer error messages
        count_result = db.conn.execute(
            f'SELECT COUNT(*) FROM "{scanner_name}"'
        ).fetchone()
        assert count_result is not None
        count = count_result[0]
        assert count == len(expected_task_ids), (
            f"Scanner '{scanner_name}' has {count} results, "
            f"expected {len(expected_task_ids)}"
        )

        # Verify exact IDs match
        df = db.conn.execute(
            f'SELECT transcript_task_id FROM "{scanner_name}"'
        ).fetchdf()
        actual_ids = sorted(df["transcript_task_id"].tolist())
        expected_ids = sorted(expected_task_ids)

        assert actual_ids == expected_ids, (
            f"Scanner '{scanner_name}' results mismatch.\n"
            f"Expected: {expected_ids}\n"
            f"Actual: {actual_ids}"
        )
    finally:
        db.conn.close()


# ============================================================================
# Test Scanners
# ============================================================================


@scanner(name="skip_test_scanner", messages="all")
def skip_test_scanner_factory() -> Scanner[Transcript]:
    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(value=1)

    return scan_transcript


@scanner(name="labeled_scanner", messages="all")
def labeled_scanner_factory() -> Scanner[Transcript]:
    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(value=1, label="finding")

    return scan_transcript


# ============================================================================
# Basic Tests
# ============================================================================


def test_skip_scored_all_scored() -> None:
    """Verify that all samples are skipped when they all have existing scores."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        eval_file = tmppath / "test.eval"
        scans_dir = tmppath / "scans"

        # Create eval log where all samples have scores for "skip_test_scanner"
        task = Task(
            dataset=[Sample(input=f"{i}", id=f"sample_{i}") for i in range(3)],
            solver=add_score_solver("skip_test_scanner"),
        )
        log = eval(tasks=task, model="mockllm/model", log_dir=str(tmppath))[0]
        write_eval_log(log, str(eval_file))

        # Run scan with skip_scored=True
        result = scan(
            scanners=[skip_test_scanner_factory()],
            transcripts=transcripts_from(str(eval_file)),
            scans=str(scans_dir),
            skip_scored=True,
        )

        # Verify no samples were scanned (0 results expected)
        db = scan_results_db(result.location)
        try:
            tables = db.conn.execute("SHOW TABLES").fetchall()
            table_names = [t[0] for t in tables]
            if "skip_test_scanner" in table_names:
                count = db.conn.execute(
                    "SELECT COUNT(*) FROM skip_test_scanner"
                ).fetchone()
                assert count is not None
                assert count[0] == 0, f"Expected 0 results, got {count[0]}"
        finally:
            db.conn.close()


def test_skip_scored_partial() -> None:
    """Verify that only unscored samples are processed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        eval_file = tmppath / "test.eval"
        scans_dir = tmppath / "scans"

        # Create eval log where only samples 0 and 2 have scores
        task = Task(
            dataset=[Sample(input=f"{i}", id=f"sample_{i}") for i in range(5)],
            solver=add_score_solver("skip_test_scanner", {"sample_0", "sample_2"}),
        )
        log = eval(tasks=task, model="mockllm/model", log_dir=str(tmppath))[0]
        write_eval_log(log, str(eval_file))

        # Run scan with skip_scored=True
        result = scan(
            scanners=[skip_test_scanner_factory()],
            transcripts=transcripts_from(str(eval_file)),
            scans=str(scans_dir),
            skip_scored=True,
        )

        # Verify only unscored samples (1, 3, 4) were processed
        verify_scanner_results(
            result.location, "skip_test_scanner", ["sample_1", "sample_3", "sample_4"]
        )


def test_skip_scored_false() -> None:
    """Verify that all samples are processed when skip_scored=False."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        eval_file = tmppath / "test.eval"
        scans_dir = tmppath / "scans"

        # Create eval log where all samples have scores
        task = Task(
            dataset=[Sample(input=f"{i}", id=f"sample_{i}") for i in range(3)],
            solver=add_score_solver("skip_test_scanner"),
        )
        log = eval(tasks=task, model="mockllm/model", log_dir=str(tmppath))[0]
        write_eval_log(log, str(eval_file))

        # Run scan with skip_scored=False (default)
        result = scan(
            scanners=[skip_test_scanner_factory()],
            transcripts=transcripts_from(str(eval_file)),
            scans=str(scans_dir),
            skip_scored=False,
        )

        # Verify all samples were scanned
        verify_scanner_results(
            result.location, "skip_test_scanner", ["sample_0", "sample_1", "sample_2"]
        )


# ============================================================================
# Prefix Matching Tests
# ============================================================================


def test_skip_scored_prefix_match() -> None:
    """Verify that scores named 'scanner_label' also trigger skip."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        eval_file = tmppath / "test.eval"
        scans_dir = tmppath / "scans"

        # Create eval log with scores named "labeled_scanner_finding"
        # (scanner name + underscore + label)
        task = Task(
            dataset=[Sample(input=f"{i}", id=f"sample_{i}") for i in range(3)],
            solver=add_score_solver("labeled_scanner_finding"),
        )
        log = eval(tasks=task, model="mockllm/model", log_dir=str(tmppath))[0]
        write_eval_log(log, str(eval_file))

        # Run scan with skip_scored=True using "labeled_scanner"
        result = scan(
            scanners=[labeled_scanner_factory()],
            transcripts=transcripts_from(str(eval_file)),
            scans=str(scans_dir),
            skip_scored=True,
        )

        # Verify all samples were skipped (prefix match should work, 0 results expected)
        db = scan_results_db(result.location)
        try:
            tables = db.conn.execute("SHOW TABLES").fetchall()
            table_names = [t[0] for t in tables]
            if "labeled_scanner" in table_names:
                count = db.conn.execute(
                    "SELECT COUNT(*) FROM labeled_scanner"
                ).fetchone()
                assert count is not None
                assert count[0] == 0, f"Expected 0 results, got {count[0]}"
        finally:
            db.conn.close()


# ============================================================================
# Edge Case Tests
# ============================================================================


def test_skip_scored_no_scores() -> None:
    """Verify all samples are processed when none have scores."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        eval_file = tmppath / "test.eval"
        scans_dir = tmppath / "scans"

        # Create eval log with no scores for our scanner
        task = Task(
            dataset=[Sample(input=f"{i}", id=f"sample_{i}") for i in range(3)],
        )
        log = eval(tasks=task, model="mockllm/model", log_dir=str(tmppath))[0]
        write_eval_log(log, str(eval_file))

        # Run scan with skip_scored=True
        result = scan(
            scanners=[skip_test_scanner_factory()],
            transcripts=transcripts_from(str(eval_file)),
            scans=str(scans_dir),
            skip_scored=True,
        )

        # Verify all samples were processed
        verify_scanner_results(
            result.location, "skip_test_scanner", ["sample_0", "sample_1", "sample_2"]
        )


def test_skip_scored_different_scanner() -> None:
    """Verify samples are processed if scores are from a different scanner."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        eval_file = tmppath / "test.eval"
        scans_dir = tmppath / "scans"

        # Create eval log with scores from "other_scanner", not "skip_test_scanner"
        task = Task(
            dataset=[Sample(input=f"{i}", id=f"sample_{i}") for i in range(3)],
            solver=add_score_solver("other_scanner"),
        )
        log = eval(tasks=task, model="mockllm/model", log_dir=str(tmppath))[0]
        write_eval_log(log, str(eval_file))

        # Run scan with skip_scored=True using "skip_test_scanner"
        result = scan(
            scanners=[skip_test_scanner_factory()],
            transcripts=transcripts_from(str(eval_file)),
            scans=str(scans_dir),
            skip_scored=True,
        )

        # Verify all samples were processed (different scanner name)
        verify_scanner_results(
            result.location, "skip_test_scanner", ["sample_0", "sample_1", "sample_2"]
        )
