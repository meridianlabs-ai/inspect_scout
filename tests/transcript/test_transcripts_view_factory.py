"""Tests for transcripts_view() and transcripts_db() factory functions."""

from pathlib import Path

import pytest
from inspect_scout._transcript.database.factory import transcripts_db, transcripts_view
from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB
from inspect_scout._transcript.eval_log import EvalLogTranscriptsView
from inspect_scout._transcript.factory import _location_type

# Path to real test eval logs
TEST_EVAL_LOGS_DIR = Path(__file__).parent.parent / "recorder" / "logs"


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
