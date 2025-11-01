import json
from pathlib import Path

import pytest
import yaml
from inspect_scout._scan import _worklist_from
from inspect_scout._scanspec import ScannerWork


def test_worklist_from_json(tmp_path: Path) -> None:
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
    result = _worklist_from(json_file)

    assert len(result) == 2
    assert isinstance(result[0], ScannerWork)
    assert result[0].scanner == "scanner_a"
    assert result[0].transcripts == ["transcript_1", "transcript_2"]
    assert isinstance(result[1], ScannerWork)
    assert result[1].scanner == "scanner_b"
    assert result[1].transcripts == ["transcript_3", "transcript_4"]


def test_worklist_from_yaml(tmp_path: Path) -> None:
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
    result = _worklist_from(yaml_file)

    assert len(result) == 2
    assert isinstance(result[0], ScannerWork)
    assert result[0].scanner == "scanner_a"
    assert result[0].transcripts == ["transcript_1", "transcript_2"]
    assert isinstance(result[1], ScannerWork)
    assert result[1].scanner == "scanner_b"
    assert result[1].transcripts == ["transcript_3", "transcript_4"]


def test_worklist_from_accepts_str_path(tmp_path: Path) -> None:
    """Test that _worklist_from accepts both str and Path."""
    # Create test data
    worklist_data = [
        {"scanner": "scanner_a", "transcripts": ["transcript_1"]},
    ]

    # Write JSON file
    json_file = tmp_path / "worklist.json"
    json_file.write_text(json.dumps(worklist_data))

    # Load using str path
    result = _worklist_from(str(json_file))

    assert len(result) == 1
    assert result[0].scanner == "scanner_a"


def test_worklist_from_non_list_raises_error(tmp_path: Path) -> None:
    """Test that non-list data raises PrerequisiteError."""
    from inspect_ai._util.error import PrerequisiteError

    # Create invalid test data (dict instead of list)
    invalid_data = {"scanner": "scanner_a", "transcripts": ["transcript_1"]}

    # Write JSON file
    json_file = tmp_path / "worklist.json"
    json_file.write_text(json.dumps(invalid_data))

    # Verify it raises PrerequisiteError
    with pytest.raises(PrerequisiteError, match="must be a list"):
        _worklist_from(json_file)
