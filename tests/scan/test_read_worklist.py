"""Tests for the _resolve_worklist function."""

import json
from pathlib import Path

import pytest
import yaml
from inspect_scout import log_columns as c
from inspect_scout._scan import _resolve_worklist
from inspect_scout._scanspec import Worklist
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.transcripts import ScannerWork

# Test data location
LOGS_DIR = Path(__file__).parent.parent / "recorder" / "logs"


# ============================================================================
# Tests for loading worklist from files (JSON/YAML)
# ============================================================================


@pytest.mark.asyncio
async def test_worklist_from_json(tmp_path: Path) -> None:
    """Test loading worklist from JSON file."""
    # Create test data
    worklist_data = [
        {"scanner": "scanner_a", "transcripts": ["transcript_1", "transcript_2"]},
        {"scanner": "scanner_b", "transcripts": ["transcript_3", "transcript_4"]},
    ]

    # Write JSON file
    json_file = tmp_path / "worklist.json"
    json_file.write_text(json.dumps(worklist_data))

    # Load and verify
    result = await _resolve_worklist(json_file)

    assert result is not None
    assert len(result) == 2
    assert isinstance(result[0], Worklist)
    assert result[0].scanner == "scanner_a"
    assert result[0].transcripts == ["transcript_1", "transcript_2"]
    assert isinstance(result[1], Worklist)
    assert result[1].scanner == "scanner_b"
    assert result[1].transcripts == ["transcript_3", "transcript_4"]


@pytest.mark.asyncio
async def test_worklist_from_yaml(tmp_path: Path) -> None:
    """Test loading worklist from YAML file."""
    # Create test data
    worklist_data = [
        {"scanner": "scanner_a", "transcripts": ["transcript_1", "transcript_2"]},
        {"scanner": "scanner_b", "transcripts": ["transcript_3", "transcript_4"]},
    ]

    # Write YAML file
    yaml_file = tmp_path / "worklist.yaml"
    yaml_file.write_text(yaml.dump(worklist_data))

    # Load and verify
    result = await _resolve_worklist(yaml_file)

    assert result is not None
    assert len(result) == 2
    assert isinstance(result[0], Worklist)
    assert result[0].scanner == "scanner_a"
    assert result[0].transcripts == ["transcript_1", "transcript_2"]
    assert isinstance(result[1], Worklist)
    assert result[1].scanner == "scanner_b"
    assert result[1].transcripts == ["transcript_3", "transcript_4"]


@pytest.mark.asyncio
async def test_worklist_from_accepts_str_path(tmp_path: Path) -> None:
    """Test that _resolve_worklist accepts both str and Path."""
    # Create test data
    worklist_data = [
        {"scanner": "scanner_a", "transcripts": ["transcript_1"]},
    ]

    # Write JSON file
    json_file = tmp_path / "worklist.json"
    json_file.write_text(json.dumps(worklist_data))

    # Load using str path
    result = await _resolve_worklist(str(json_file))

    assert result is not None
    assert len(result) == 1
    assert result[0].scanner == "scanner_a"


@pytest.mark.asyncio
async def test_worklist_from_non_list_raises_error(tmp_path: Path) -> None:
    """Test that non-list data raises PrerequisiteError."""
    from inspect_ai._util.error import PrerequisiteError

    # Create invalid test data (dict instead of list)
    invalid_data = {"scanner": "scanner_a", "transcripts": ["transcript_1"]}

    # Write JSON file
    json_file = tmp_path / "worklist.json"
    json_file.write_text(json.dumps(invalid_data))

    # Verify it raises PrerequisiteError
    with pytest.raises(PrerequisiteError, match="must be a list"):
        await _resolve_worklist(json_file)


# ============================================================================
# Tests for resolving ScannerWork with Transcripts queries
# ============================================================================


@pytest.mark.asyncio
async def test_resolve_worklist_none() -> None:
    """Test that None input returns None."""
    result = await _resolve_worklist(None)
    assert result is None


@pytest.mark.asyncio
async def test_resolve_worklist_with_explicit_ids() -> None:
    """Test that ScannerWork with explicit list[str] IDs gets converted to Worklist."""
    transcript_ids = ["id_1", "id_2", "id_3"]
    worklist = [
        ScannerWork(scanner="scanner_a", transcripts=transcript_ids),
    ]

    result = await _resolve_worklist(worklist)

    assert result is not None
    assert len(result) == 1
    assert isinstance(result[0], Worklist)
    assert result[0].scanner == "scanner_a"
    assert result[0].transcripts == transcript_ids


@pytest.mark.asyncio
async def test_resolve_worklist_with_transcripts_query() -> None:
    """Test that ScannerWork with a Transcripts query resolves to actual IDs."""
    # Create a Transcripts query that filters by task_name
    transcripts = transcripts_from(LOGS_DIR)
    filtered = transcripts.where(c.task == "popularity")

    worklist = [
        ScannerWork(scanner="scanner_a", transcripts=filtered),
    ]

    result = await _resolve_worklist(worklist)

    assert result is not None
    assert len(result) == 1
    assert isinstance(result[0], Worklist)
    assert result[0].scanner == "scanner_a"
    # Verify we got actual transcript IDs (strings), not a Transcripts object
    assert isinstance(result[0].transcripts, list)
    assert len(result[0].transcripts) > 0
    assert all(isinstance(tid, str) for tid in result[0].transcripts)


@pytest.mark.asyncio
async def test_resolve_worklist_mixed() -> None:
    """Test worklist with both Transcripts queries and explicit ID lists."""
    # Create a Transcripts query
    transcripts = transcripts_from(LOGS_DIR)
    filtered = transcripts.where(c.task == "popularity")

    # Create worklist with mixed types
    explicit_ids = ["explicit_id_1", "explicit_id_2"]
    worklist = [
        ScannerWork(scanner="scanner_a", transcripts=filtered),
        ScannerWork(scanner="scanner_b", transcripts=explicit_ids),
    ]

    result = await _resolve_worklist(worklist)

    assert result is not None
    assert len(result) == 2

    # First entry should have resolved transcript IDs
    assert isinstance(result[0], Worklist)
    assert result[0].scanner == "scanner_a"
    assert len(result[0].transcripts) > 0

    # Second entry should have the explicit IDs unchanged
    assert isinstance(result[1], Worklist)
    assert result[1].scanner == "scanner_b"
    assert result[1].transcripts == explicit_ids


@pytest.mark.asyncio
async def test_resolve_worklist_multiple_transcripts_queries() -> None:
    """Test the builder pattern with multiple independent Transcripts queries.

    This tests the use case where the same base Transcripts is used with
    different .where() filters for different scanners.
    """
    # Create base transcripts and filter independently
    transcripts = transcripts_from(LOGS_DIR)
    popularity_transcripts = transcripts.where(c.task == "popularity")
    security_transcripts = transcripts.where(c.task == "security_guide")

    worklist = [
        ScannerWork(scanner="scanner_a", transcripts=popularity_transcripts),
        ScannerWork(scanner="scanner_b", transcripts=security_transcripts),
    ]

    result = await _resolve_worklist(worklist)

    assert result is not None
    assert len(result) == 2

    # Both should be resolved to Worklist with actual IDs
    assert isinstance(result[0], Worklist)
    assert isinstance(result[1], Worklist)

    # Verify they have different transcript IDs (different task_names)
    popularity_ids = set(result[0].transcripts)
    security_ids = set(result[1].transcripts)

    # The sets should not overlap since they're from different tasks
    assert len(popularity_ids & security_ids) == 0

    # Both should have some transcripts
    assert len(popularity_ids) > 0
    assert len(security_ids) > 0
