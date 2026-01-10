"""Tests for POST /code endpoint."""

import pytest
from fastapi.testclient import TestClient
from inspect_scout._project import init_project
from inspect_scout._view._api_v2 import v2_api_app


@pytest.fixture
def client(tmp_path: str) -> TestClient:
    """Create test client with initialized project."""
    init_project(transcripts=str(tmp_path))
    return TestClient(v2_api_app(results_dir=str(tmp_path)))


class TestCodeEndpoint:
    """Tests for POST /code endpoint."""

    def test_code_simple_condition(self, client: TestClient) -> None:
        """Simple condition returns python and filter code."""
        response = client.post(
            "/code",
            json={
                "is_compound": False,
                "left": "total_tokens",
                "operator": "<",
                "right": 75,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "python" in data
        assert "filter" in data
        assert "total_tokens < 75" in data["filter"]
        assert "transcripts_from" in data["python"]
        assert "total_tokens < 75" in data["python"]

    def test_code_compound_condition(self, client: TestClient) -> None:
        """Compound AND condition returns python and filter code."""
        response = client.post(
            "/code",
            json={
                "is_compound": True,
                "left": {
                    "is_compound": False,
                    "left": "model",
                    "operator": "=",
                    "right": "gpt-4",
                },
                "operator": "AND",
                "right": {
                    "is_compound": False,
                    "left": "total_tokens",
                    "operator": ">",
                    "right": 100,
                },
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "python" in data
        assert "filter" in data
        assert "AND" in data["filter"]
        assert "model = 'gpt-4'" in data["filter"]
        assert "total_tokens > 100" in data["filter"]

    def test_code_string_equality(self, client: TestClient) -> None:
        """String equality condition."""
        response = client.post(
            "/code",
            json={
                "is_compound": False,
                "left": "status",
                "operator": "=",
                "right": "complete",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "status = 'complete'" in data["filter"]

    def test_code_in_operator(self, client: TestClient) -> None:
        """IN operator with list of values."""
        response = client.post(
            "/code",
            json={
                "is_compound": False,
                "left": "model",
                "operator": "IN",
                "right": ["gpt-4", "gpt-3.5", "claude"],
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "IN ('gpt-4', 'gpt-3.5', 'claude')" in data["filter"]

    def test_code_condition_list(self, client: TestClient) -> None:
        """List of conditions ANDed together."""
        response = client.post(
            "/code",
            json=[
                {
                    "is_compound": False,
                    "left": "model",
                    "operator": "=",
                    "right": "gpt-4",
                },
                {
                    "is_compound": False,
                    "left": "total_tokens",
                    "operator": "<",
                    "right": 100,
                },
            ],
        )

        assert response.status_code == 200
        data = response.json()

        assert "AND" in data["filter"]
        assert "model = 'gpt-4'" in data["filter"]
        assert "total_tokens < 100" in data["filter"]

    def test_code_condition_list_single(self, client: TestClient) -> None:
        """Single-item list returns just that condition."""
        response = client.post(
            "/code",
            json=[{"is_compound": False, "left": "x", "operator": "=", "right": 1}],
        )

        assert response.status_code == 200
        data = response.json()

        assert data["filter"] == "x = 1"
