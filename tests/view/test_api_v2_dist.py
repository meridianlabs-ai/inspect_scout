"""Tests for GET /dist endpoint."""

from pathlib import Path

from fastapi.testclient import TestClient
from inspect_scout._view._api_v2 import v2_api_app


class TestDistEndpoint:
    """Tests for GET /dist endpoint."""

    def test_returns_path_when_provided(self) -> None:
        """Returns the pre-resolved dist path."""
        fake_path = Path("/resolved/dist")
        client = TestClient(v2_api_app(dist_path=fake_path))

        response = client.get("/dist")

        assert response.status_code == 200
        assert response.json()["path"] == "/resolved/dist"

    def test_returns_404_when_path_is_none(self) -> None:
        """Returns 404 when no dist path was provided."""
        client = TestClient(v2_api_app(dist_path=None))

        response = client.get("/dist")

        assert response.status_code == 404
