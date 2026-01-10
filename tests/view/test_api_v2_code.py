"""Tests for POST /code endpoint."""

from fastapi.testclient import TestClient
from inspect_scout._view._api_v2 import v2_api_app


class TestCodeEndpoint:
    """Tests for POST /code endpoint."""

    def test_code_simple_condition(self) -> None:
        """Simple condition returns code for all langs."""
        client = TestClient(v2_api_app(results_dir="/tmp"))

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
        assert "sqlite" in data
        assert "duckdb" in data
        assert "postgres" in data

        # SQL dialects should have actual SQL
        assert '"total_tokens" < ?' in data["sqlite"]
        assert '"total_tokens" < ?' in data["duckdb"]
        assert '"total_tokens" < $1' in data["postgres"]

    def test_code_compound_condition(self) -> None:
        """Compound AND condition returns code for all langs."""
        client = TestClient(v2_api_app(results_dir="/tmp"))

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
        assert "sqlite" in data
        assert "duckdb" in data
        assert "postgres" in data

        # Check compound SQL structure
        assert "AND" in data["sqlite"]
        assert '"model"' in data["sqlite"]
        assert '"total_tokens"' in data["sqlite"]

    def test_code_string_equality(self) -> None:
        """String equality condition."""
        client = TestClient(v2_api_app(results_dir="/tmp"))

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

        assert '"status" = ?' in data["sqlite"]
        assert '"status" = $1' in data["postgres"]

    def test_code_in_operator(self) -> None:
        """IN operator with list of values."""
        client = TestClient(v2_api_app(results_dir="/tmp"))

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

        assert "IN" in data["sqlite"]

    def test_code_python_not_yet_implemented(self) -> None:
        """Python code generation NYI."""
        client = TestClient(v2_api_app(results_dir="/tmp"))

        response = client.post(
            "/code",
            json={
                "is_compound": False,
                "left": "x",
                "operator": "=",
                "right": 1,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["python"] == "Not Yet Implemented"
