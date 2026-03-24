"""Tests for GET /dist endpoint."""

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from inspect_ai._lfs import LFSError
from inspect_scout._view._api_v2 import v2_api_app


class TestDistEndpoint:
    """Tests for GET /dist endpoint."""

    def test_returns_path_when_resolved(self) -> None:
        """Successful resolution returns path string."""
        fake_path = Path("/resolved/dist")
        client = TestClient(v2_api_app())

        with patch(
            "inspect_scout._view._api_v2_dist.resolve_lfs_directory",
            return_value=fake_path,
        ):
            response = client.get("/dist")

        assert response.status_code == 200
        data = response.json()
        assert data["path"] == "/resolved/dist"

    def test_returns_503_on_lfs_error(self) -> None:
        """LFS failure returns 503 with guidance."""
        client = TestClient(v2_api_app())

        with patch(
            "inspect_scout._view._api_v2_dist.resolve_lfs_directory",
            side_effect=LFSError("LFS not installed"),
        ):
            response = client.get("/dist")

        assert response.status_code == 503
        detail = response.json()["detail"]
        assert "Failed to resolve dist directory" in detail
        assert "git-lfs" in detail

    def test_passes_correct_args(self) -> None:
        """Verifies correct arguments passed to resolve_lfs_directory."""
        fake_path = Path("/some/path")
        client = TestClient(v2_api_app())

        with patch(
            "inspect_scout._view._api_v2_dist.resolve_lfs_directory",
            return_value=fake_path,
        ) as mock_resolve:
            client.get("/dist")

        mock_resolve.assert_called_once()
        args, kwargs = mock_resolve.call_args
        assert str(args[0]).endswith("/dist")
        assert "cache_dir" in kwargs
        assert (
            kwargs["repo_url"] == "https://github.com/meridianlabs-ai/inspect_scout.git"
        )
