"""Tests for transcripts_view() and transcripts_db() factory functions."""

from pathlib import Path

import pytest
from inspect_scout._transcript.database.factory import transcripts_db, transcripts_view
from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB
from inspect_scout._transcript.eval_log import (
    EvalLogTranscripts,
    EvalLogTranscriptsView,
)
from inspect_scout._transcript.factory import _location_type, transcripts_from

# Path to real test eval logs
TEST_EVAL_LOGS_DIR = Path(__file__).parent.parent / "recorder" / "logs"


def _eval_log_files() -> list[Path]:
    return sorted(TEST_EVAL_LOGS_DIR.glob("*.eval"))


@pytest.fixture
def parquet_db_location(tmp_path: Path) -> Path:
    """Create a location that looks like a parquet database (empty dir)."""
    db_path = tmp_path / "parquet_db"
    db_path.mkdir()
    return db_path


def test_transcripts_view_returns_parquet_for_database(
    parquet_db_location: Path,
) -> None:
    """transcripts_view() returns ParquetTranscriptsDB for parquet location."""
    view = transcripts_view(str(parquet_db_location))
    assert isinstance(view, ParquetTranscriptsDB)


def test_transcripts_view_returns_eval_log_for_logs() -> None:
    """transcripts_view() returns EvalLogTranscriptsView for eval log location."""
    view = transcripts_view(str(TEST_EVAL_LOGS_DIR))
    assert isinstance(view, EvalLogTranscriptsView)


def test_transcripts_db_returns_parquet_for_database(
    parquet_db_location: Path,
) -> None:
    """transcripts_db() returns ParquetTranscriptsDB for parquet location."""
    db = transcripts_db(str(parquet_db_location))
    assert isinstance(db, ParquetTranscriptsDB)


def test_transcripts_db_raises_for_eval_log() -> None:
    """transcripts_db() raises ValueError for eval log location."""
    with pytest.raises(
        ValueError, match="Mutable database not supported for eval logs"
    ):
        transcripts_db(str(TEST_EVAL_LOGS_DIR))


def test_location_type_detects_database(parquet_db_location: Path) -> None:
    """_location_type() returns 'database' for empty directory."""
    assert _location_type(str(parquet_db_location)) == "database"


def test_location_type_detects_eval_log() -> None:
    """_location_type() returns 'eval_log' for directory with .eval files."""
    assert _location_type(str(TEST_EVAL_LOGS_DIR)) == "eval_log"


def test_location_type_detects_eval_log_file() -> None:
    """_location_type() returns 'eval_log' for a path to a single .eval file."""
    eval_files = _eval_log_files()
    assert eval_files, "expected fixture .eval files to exist"
    assert _location_type(str(eval_files[0])) == "eval_log"


def test_location_type_detects_database_for_non_eval_file(tmp_path: Path) -> None:
    """_location_type() returns 'database' for a non-.eval file path."""
    db_file = tmp_path / "transcripts.parquet"
    db_file.write_bytes(b"")
    assert _location_type(str(db_file)) == "database"


def test_location_type_detects_eval_log_for_s3_uri() -> None:
    """_location_type() returns 'eval_log' for an s3:// URI ending in .eval.

    The check must be purely path-based (no filesystem access), so an
    unreachable bucket is fine.
    """
    assert _location_type("s3://nonexistent-bucket/path/to/log.eval") == "eval_log"


def test_transcripts_from_multiple_eval_log_files() -> None:
    """transcripts_from() accepts a list of .eval file paths.

    Reproduces the bug where individual .eval file paths were misclassified
    as 'database', causing 'Only one transcript database location may be
    specified.' to be raised.
    """
    eval_files = _eval_log_files()
    assert len(eval_files) >= 2, "need multiple .eval fixture files"
    transcripts = transcripts_from([str(p) for p in eval_files])
    assert isinstance(transcripts, EvalLogTranscripts)


def test_transcripts_from_single_eval_log_file() -> None:
    """transcripts_from() with a single .eval file path returns eval log transcripts."""
    eval_files = _eval_log_files()
    assert eval_files, "expected fixture .eval files to exist"
    transcripts = transcripts_from(str(eval_files[0]))
    assert isinstance(transcripts, EvalLogTranscripts)
