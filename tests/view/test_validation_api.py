"""Tests for the validation sets REST API endpoints."""

from __future__ import annotations

import base64
import json
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from inspect_scout._view._api_v2 import v2_api_app
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)


def _base64url(s: str) -> str:
    """Encode string as base64url (URL-safe base64 without padding)."""
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


@pytest.fixture
def client(tmp_path: Path) -> Generator[TestClient, None, None]:
    """Create a test client with the current working directory set to tmp_path."""
    import os

    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        yield TestClient(v2_api_app())
    finally:
        os.chdir(original_cwd)


@pytest.fixture
def validation_csv(tmp_path: Path) -> Path:
    """Create a sample CSV validation file."""
    csv_path = tmp_path / "validations" / "test.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.write_text("id,target\nt1,true\nt2,false\n")
    return csv_path


@pytest.fixture
def validation_yaml(tmp_path: Path) -> Path:
    """Create a sample YAML validation file."""
    yaml_path = tmp_path / "validations" / "test.yaml"
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text(
        """- id: t1
  target: true
- id: t2
  target: false
"""
    )
    return yaml_path


@pytest.fixture
def validation_yaml_nested(tmp_path: Path) -> Path:
    """Create a YAML validation file with nested split format."""
    yaml_path = tmp_path / "validations" / "nested.yaml"
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text(
        """- split: dev
  cases:
    - id: t1
      target: true
- split: test
  cases:
    - id: t2
      target: false
"""
    )
    return yaml_path


class TestListValidations:
    """Tests for GET /validations endpoint."""

    def test_list_validations_empty(self, client: TestClient) -> None:
        """Test listing validations in empty directory."""
        response = client.get("/validations")
        assert response.status_code == 200
        paths = response.json()
        assert paths == []

    def test_list_validations_with_files(
        self, client: TestClient, validation_csv: Path, validation_yaml: Path
    ) -> None:
        """Test listing validations with CSV and YAML files."""
        response = client.get("/validations")
        assert response.status_code == 200
        paths = response.json()
        assert len(paths) == 2

        # Check that both files are listed
        assert any("test.csv" in p for p in paths)
        assert any("test.yaml" in p for p in paths)

    def test_list_validations_excludes_invalid(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """Test that invalid files are excluded from listing."""
        # Create an invalid CSV (no id column)
        invalid_csv = tmp_path / "invalid.csv"
        invalid_csv.write_text("name,value\nfoo,1\n")

        # Create a valid CSV
        valid_csv = tmp_path / "valid.csv"
        valid_csv.write_text("id,target\nt1,true\n")

        response = client.get("/validations")
        assert response.status_code == 200
        paths = response.json()
        # Only valid file should be listed
        assert len(paths) == 1
        assert "valid.csv" in paths[0]


class TestCreateValidation:
    """Tests for POST /validations endpoint."""

    def test_create_validation_csv(self, client: TestClient, tmp_path: Path) -> None:
        """Test creating a new CSV validation file."""
        file_path = tmp_path / "new_validation.csv"
        file_uri = f"file://{file_path}"

        response = client.post(
            "/validations",
            json={
                "path": file_uri,
                "cases": [
                    {"id": "t1", "target": True},
                    {"id": "t2", "target": False},
                ],
            },
        )

        assert response.status_code == 200
        result_uri = response.json()
        assert result_uri.endswith("new_validation.csv")
        assert file_path.exists()

    def test_create_validation_yaml(self, client: TestClient, tmp_path: Path) -> None:
        """Test creating a new YAML validation file."""
        file_path = tmp_path / "new_validation.yaml"
        file_uri = f"file://{file_path}"

        response = client.post(
            "/validations",
            json={
                "path": file_uri,
                "cases": [{"id": "t1", "target": True, "split": "dev"}],
            },
        )

        assert response.status_code == 200
        result_uri = response.json()
        assert result_uri.endswith("new_validation.yaml")

    def test_create_validation_with_labels(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """Test creating a validation file with label-based cases."""
        file_path = tmp_path / "labels.yaml"
        file_uri = f"file://{file_path}"

        response = client.post(
            "/validations",
            json={
                "path": file_uri,
                "cases": [
                    {"id": "t1", "labels": {"deception": True, "jailbreak": False}}
                ],
            },
        )

        assert response.status_code == 200
        assert file_path.exists()

    def test_create_validation_conflict(
        self, client: TestClient, validation_csv: Path
    ) -> None:
        """Test creating a file that already exists."""
        file_uri = f"file://{validation_csv}"

        response = client.post(
            "/validations",
            json={
                "path": file_uri,
                "cases": [{"id": "t1", "target": True}],
            },
        )

        assert response.status_code == HTTP_409_CONFLICT

    def test_create_validation_invalid_case(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """Test creating with invalid case (both target and labels)."""
        file_path = tmp_path / "invalid.csv"
        file_uri = f"file://{file_path}"

        response = client.post(
            "/validations",
            json={
                "path": file_uri,
                "cases": [{"id": "t1", "target": True, "labels": {"foo": True}}],
            },
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

    def test_create_validation_neither_target_nor_labels(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """Test creating with invalid case (neither target nor labels)."""
        file_path = tmp_path / "invalid.csv"
        file_uri = f"file://{file_path}"

        response = client.post(
            "/validations",
            json={
                "path": file_uri,
                "cases": [{"id": "t1", "split": "dev"}],
            },
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

    def test_create_validation_missing_id(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """Test creating with missing case id."""
        file_path = tmp_path / "invalid.csv"
        file_uri = f"file://{file_path}"

        response = client.post(
            "/validations",
            json={
                "path": file_uri,
                "cases": [{"target": True}],
            },
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

    def test_create_validation_path_traversal(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """Test that path traversal is rejected."""
        # Try to escape project directory
        file_uri = "file:///etc/passwd"

        response = client.post(
            "/validations",
            json={
                "path": file_uri,
                "cases": [{"id": "t1", "target": True}],
            },
        )

        assert response.status_code == HTTP_400_BAD_REQUEST


class TestGetValidationCases:
    """Tests for GET /validations/{uri} endpoint."""

    def test_get_cases_csv(self, client: TestClient, validation_csv: Path) -> None:
        """Test getting cases from a CSV file."""
        file_uri = f"file://{validation_csv}"
        encoded_uri = _base64url(file_uri)

        response = client.get(f"/validations/{encoded_uri}")

        assert response.status_code == 200
        cases = response.json()
        assert len(cases) == 2
        assert cases[0]["id"] == "t1"
        assert cases[0]["target"] is True
        assert cases[1]["id"] == "t2"
        assert cases[1]["target"] is False

    def test_get_cases_yaml(self, client: TestClient, validation_yaml: Path) -> None:
        """Test getting cases from a YAML file."""
        file_uri = f"file://{validation_yaml}"
        encoded_uri = _base64url(file_uri)

        response = client.get(f"/validations/{encoded_uri}")

        assert response.status_code == 200
        cases = response.json()
        assert len(cases) == 2

    def test_get_cases_yaml_nested(
        self, client: TestClient, validation_yaml_nested: Path
    ) -> None:
        """Test getting cases from a YAML file with nested splits."""
        file_uri = f"file://{validation_yaml_nested}"
        encoded_uri = _base64url(file_uri)

        response = client.get(f"/validations/{encoded_uri}")

        assert response.status_code == 200
        cases = response.json()
        assert len(cases) == 2
        # Cases should have split field from flattening
        assert cases[0]["split"] == "dev"
        assert cases[1]["split"] == "test"

    def test_get_cases_not_found(self, client: TestClient, tmp_path: Path) -> None:
        """Test getting cases from non-existent file."""
        file_uri = f"file://{tmp_path}/nonexistent.csv"
        encoded_uri = _base64url(file_uri)

        response = client.get(f"/validations/{encoded_uri}")

        assert response.status_code == HTTP_404_NOT_FOUND

    def test_get_cases_path_traversal(self, client: TestClient) -> None:
        """Test that path traversal is rejected."""
        file_uri = "file:///etc/passwd"
        encoded_uri = _base64url(file_uri)

        response = client.get(f"/validations/{encoded_uri}")

        assert response.status_code == HTTP_400_BAD_REQUEST


class TestDeleteValidation:
    """Tests for DELETE /validations/{uri} endpoint."""

    def test_delete_validation(self, client: TestClient, validation_csv: Path) -> None:
        """Test deleting a validation file."""
        file_uri = f"file://{validation_csv}"
        encoded_uri = _base64url(file_uri)

        assert validation_csv.exists()

        response = client.delete(f"/validations/{encoded_uri}")

        assert response.status_code == 200
        assert response.json() == {"deleted": True}
        assert not validation_csv.exists()

    def test_delete_validation_not_found(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """Test deleting a non-existent file."""
        file_uri = f"file://{tmp_path}/nonexistent.csv"
        encoded_uri = _base64url(file_uri)

        response = client.delete(f"/validations/{encoded_uri}")

        assert response.status_code == HTTP_404_NOT_FOUND

    def test_delete_validation_path_traversal(self, client: TestClient) -> None:
        """Test that path traversal is rejected."""
        file_uri = "file:///etc/passwd"
        encoded_uri = _base64url(file_uri)

        response = client.delete(f"/validations/{encoded_uri}")

        assert response.status_code == HTTP_400_BAD_REQUEST


class TestGetValidationCase:
    """Tests for GET /validations/{uri}/{case_id} endpoint."""

    def test_get_case(self, client: TestClient, validation_csv: Path) -> None:
        """Test getting a specific case by ID."""
        file_uri = f"file://{validation_csv}"
        encoded_uri = _base64url(file_uri)
        encoded_case_id = _base64url("t1")

        response = client.get(f"/validations/{encoded_uri}/{encoded_case_id}")

        assert response.status_code == 200
        case = response.json()
        assert case["id"] == "t1"
        assert case["target"] is True

    def test_get_case_not_found(self, client: TestClient, validation_csv: Path) -> None:
        """Test getting a non-existent case."""
        file_uri = f"file://{validation_csv}"
        encoded_uri = _base64url(file_uri)
        encoded_case_id = _base64url("nonexistent")

        response = client.get(f"/validations/{encoded_uri}/{encoded_case_id}")

        assert response.status_code == HTTP_404_NOT_FOUND

    def test_get_case_list_id(self, client: TestClient, tmp_path: Path) -> None:
        """Test getting a case with a list ID."""
        # Create a YAML file with list IDs
        yaml_path = tmp_path / "list_ids.yaml"
        yaml_path.write_text(
            """- id: ["a", "b"]
  target: true
"""
        )

        file_uri = f"file://{yaml_path}"
        encoded_uri = _base64url(file_uri)
        # Encode the list ID as JSON
        encoded_case_id = _base64url(json.dumps(["a", "b"]))

        response = client.get(f"/validations/{encoded_uri}/{encoded_case_id}")

        assert response.status_code == 200
        case = response.json()
        assert case["id"] == ["a", "b"]


class TestUpsertValidationCase:
    """Tests for POST /validations/{uri}/{case_id} endpoint."""

    def test_create_case(self, client: TestClient, validation_csv: Path) -> None:
        """Test creating a new case."""
        file_uri = f"file://{validation_csv}"
        encoded_uri = _base64url(file_uri)
        encoded_case_id = _base64url("t3")

        response = client.post(
            f"/validations/{encoded_uri}/{encoded_case_id}",
            json={"target": True},
        )

        assert response.status_code == 200
        case = response.json()
        assert case["id"] == "t3"
        assert case["target"] is True

        # Verify the case was added
        get_response = client.get(f"/validations/{encoded_uri}")
        cases = get_response.json()
        assert len(cases) == 3

    def test_update_case(self, client: TestClient, validation_csv: Path) -> None:
        """Test updating an existing case."""
        file_uri = f"file://{validation_csv}"
        encoded_uri = _base64url(file_uri)
        encoded_case_id = _base64url("t1")

        response = client.post(
            f"/validations/{encoded_uri}/{encoded_case_id}",
            json={"target": False},  # Change from true to false
        )

        assert response.status_code == 200
        case = response.json()
        assert case["id"] == "t1"
        assert case["target"] is False

        # Verify the case was updated (count unchanged)
        get_response = client.get(f"/validations/{encoded_uri}")
        cases = get_response.json()
        assert len(cases) == 2
        t1_case = next(c for c in cases if c["id"] == "t1")
        assert t1_case["target"] is False

    def test_upsert_with_labels(
        self, client: TestClient, validation_yaml: Path
    ) -> None:
        """Test upserting a case with labels."""
        file_uri = f"file://{validation_yaml}"
        encoded_uri = _base64url(file_uri)
        encoded_case_id = _base64url("t3")

        response = client.post(
            f"/validations/{encoded_uri}/{encoded_case_id}",
            json={"labels": {"deception": True, "jailbreak": False}},
        )

        assert response.status_code == 200
        case = response.json()
        assert case["labels"] == {"deception": True, "jailbreak": False}

    def test_upsert_with_split_and_predicate(
        self, client: TestClient, validation_csv: Path
    ) -> None:
        """Test upserting a case with split and predicate."""
        file_uri = f"file://{validation_csv}"
        encoded_uri = _base64url(file_uri)
        encoded_case_id = _base64url("t3")

        response = client.post(
            f"/validations/{encoded_uri}/{encoded_case_id}",
            json={"target": 0.5, "split": "dev", "predicate": "gte"},
        )

        assert response.status_code == 200
        case = response.json()
        assert case["target"] == 0.5
        assert case["split"] == "dev"
        assert case["predicate"] == "gte"

    def test_upsert_invalid_both_target_and_labels(
        self, client: TestClient, validation_csv: Path
    ) -> None:
        """Test that providing both target and labels is rejected."""
        file_uri = f"file://{validation_csv}"
        encoded_uri = _base64url(file_uri)
        encoded_case_id = _base64url("t1")

        response = client.post(
            f"/validations/{encoded_uri}/{encoded_case_id}",
            json={"target": True, "labels": {"foo": True}},
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

    def test_upsert_invalid_neither_target_nor_labels(
        self, client: TestClient, validation_csv: Path
    ) -> None:
        """Test that providing neither target nor labels is rejected."""
        file_uri = f"file://{validation_csv}"
        encoded_uri = _base64url(file_uri)
        encoded_case_id = _base64url("t1")

        response = client.post(
            f"/validations/{encoded_uri}/{encoded_case_id}",
            json={"split": "dev"},
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

    def test_upsert_file_not_found(self, client: TestClient, tmp_path: Path) -> None:
        """Test upserting to a non-existent file."""
        file_uri = f"file://{tmp_path}/nonexistent.csv"
        encoded_uri = _base64url(file_uri)
        encoded_case_id = _base64url("t1")

        response = client.post(
            f"/validations/{encoded_uri}/{encoded_case_id}",
            json={"target": True},
        )

        assert response.status_code == HTTP_404_NOT_FOUND


class TestDeleteValidationCase:
    """Tests for DELETE /validations/{uri}/{case_id} endpoint."""

    def test_delete_case(self, client: TestClient, validation_csv: Path) -> None:
        """Test deleting a case."""
        file_uri = f"file://{validation_csv}"
        encoded_uri = _base64url(file_uri)
        encoded_case_id = _base64url("t1")

        response = client.delete(f"/validations/{encoded_uri}/{encoded_case_id}")

        assert response.status_code == 200
        assert response.json() == {"deleted": True}

        # Verify the case was deleted
        get_response = client.get(f"/validations/{encoded_uri}")
        cases = get_response.json()
        assert len(cases) == 1
        assert cases[0]["id"] == "t2"

    def test_delete_case_not_found(
        self, client: TestClient, validation_csv: Path
    ) -> None:
        """Test deleting a non-existent case."""
        file_uri = f"file://{validation_csv}"
        encoded_uri = _base64url(file_uri)
        encoded_case_id = _base64url("nonexistent")

        response = client.delete(f"/validations/{encoded_uri}/{encoded_case_id}")

        assert response.status_code == HTTP_404_NOT_FOUND

    def test_delete_case_file_not_found(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """Test deleting from a non-existent file."""
        file_uri = f"file://{tmp_path}/nonexistent.csv"
        encoded_uri = _base64url(file_uri)
        encoded_case_id = _base64url("t1")

        response = client.delete(f"/validations/{encoded_uri}/{encoded_case_id}")

        assert response.status_code == HTTP_404_NOT_FOUND


class TestValidationFileWriter:
    """Tests for ValidationFileWriter."""

    def test_write_preserves_nested_splits(self, tmp_path: Path) -> None:
        """Test that writing to a file with nested splits preserves the structure."""
        from inspect_scout._validation.writer import ValidationFileWriter

        # Create a YAML file with nested splits
        yaml_path = tmp_path / "nested.yaml"
        yaml_path.write_text(
            """- split: dev
  cases:
    - id: t1
      target: true
"""
        )

        writer = ValidationFileWriter(yaml_path)
        cases = writer.read_cases()

        # Add a new case
        cases.append({"id": "t2", "target": False, "split": "dev"})
        writer.write_cases(cases)

        # Read back and verify structure preserved
        import yaml

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        # Should still be nested
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["split"] == "dev"
        assert len(data[0]["cases"]) == 2

    def test_find_case_index_with_list_id(self, tmp_path: Path) -> None:
        """Test finding a case by list ID."""
        from inspect_scout._validation.writer import ValidationFileWriter

        yaml_path = tmp_path / "list_ids.yaml"
        yaml_path.write_text(
            """- id: ["a", "b"]
  target: true
- id: c
  target: false
"""
        )

        writer = ValidationFileWriter(yaml_path)
        cases = writer.read_cases()

        # Find by list ID
        index = writer.find_case_index(cases, ["a", "b"])
        assert index == 0

        # Find by string ID
        index = writer.find_case_index(cases, "c")
        assert index == 1

        # Not found
        index = writer.find_case_index(cases, "nonexistent")
        assert index is None


class TestFileScannerFunctions:
    """Tests for file scanner helper functions."""

    def test_is_venv_directory(self, tmp_path: Path) -> None:
        """Test venv directory detection."""
        from inspect_scout._util.venv import is_venv_directory

        # Create a venv-like directory
        venv_dir = tmp_path / ".venv"
        venv_dir.mkdir()
        (venv_dir / "pyvenv.cfg").write_text("home = /usr/bin")

        assert is_venv_directory(venv_dir) is True

        # Regular directory
        regular_dir = tmp_path / "src"
        regular_dir.mkdir()
        assert is_venv_directory(regular_dir) is False

    def test_is_validation_file(self, tmp_path: Path) -> None:
        """Test validation file detection."""
        from inspect_scout._validation.file_scanner import is_validation_file

        # Valid CSV
        valid_csv = tmp_path / "valid.csv"
        valid_csv.write_text("id,target\nt1,true\n")
        assert is_validation_file(valid_csv) is True

        # Invalid CSV (no id column)
        invalid_csv = tmp_path / "invalid.csv"
        invalid_csv.write_text("name,value\nfoo,1\n")
        assert is_validation_file(invalid_csv) is False

        # Valid YAML
        valid_yaml = tmp_path / "valid.yaml"
        valid_yaml.write_text("- id: t1\n  target: true\n")
        assert is_validation_file(valid_yaml) is True

        # Non-validation file
        txt_file = tmp_path / "readme.txt"
        txt_file.write_text("hello")
        assert is_validation_file(txt_file) is False

    def test_scan_excludes_hidden_dirs(self, tmp_path: Path) -> None:
        """Test that hidden directories are excluded."""
        from inspect_scout._validation.file_scanner import scan_validation_files

        # Create validation file in hidden directory
        hidden_dir = tmp_path / ".hidden"
        hidden_dir.mkdir()
        hidden_file = hidden_dir / "valid.csv"
        hidden_file.write_text("id,target\nt1,true\n")

        # Create validation file in normal directory
        normal_file = tmp_path / "valid.csv"
        normal_file.write_text("id,target\nt1,true\n")

        files = list(scan_validation_files(tmp_path))

        assert len(files) == 1
        assert files[0] == normal_file

    def test_scan_excludes_node_modules(self, tmp_path: Path) -> None:
        """Test that node_modules is excluded."""
        from inspect_scout._validation.file_scanner import scan_validation_files

        # Create validation file in node_modules
        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        node_file = node_modules / "valid.csv"
        node_file.write_text("id,target\nt1,true\n")

        # Create validation file in normal directory
        normal_file = tmp_path / "valid.csv"
        normal_file.write_text("id,target\nt1,true\n")

        files = list(scan_validation_files(tmp_path))

        assert len(files) == 1
        assert files[0] == normal_file
