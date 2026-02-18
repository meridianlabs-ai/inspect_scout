"""Tests for scanner input endpoint (GET /scans/{dir}/{scan}/{scanner}/{uuid}/input)."""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from inspect_scout._view._api_v2 import v2_api_app


def _base64url(s: str) -> str:
    """Encode string as base64url (URL-safe base64 without padding)."""
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


_SCANS_DIR = _base64url("/tmp/scans")
_SCAN_PATH = _base64url("scan_id=test123")


def _url(scanner: str, uuid: str) -> str:
    return f"/scans/{_SCANS_DIR}/{_SCAN_PATH}/{scanner}/{uuid}/input"


def _make_mock_result(scanners: list[str]) -> MagicMock:
    """Create a mock ScanResultsArrow."""
    result = MagicMock()
    result.scanners = scanners
    return result


class TestScannerInputEndpoint:
    """Tests for the scanner_input endpoint."""

    def test_returns_404_for_unknown_uuid(self) -> None:
        """When get_field raises KeyError for a missing UUID, return 404."""
        mock_result = _make_mock_result(scanners=["refusal"])
        mock_result.get_field.side_effect = KeyError("'abc123' not found in uuid")

        client = TestClient(v2_api_app())
        with patch(
            "inspect_scout._view._api_v2_scans.scan_results_arrow_async",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = client.get(_url("refusal", "nonexistent-uuid"))

        assert response.status_code == 404
        assert "nonexistent-uuid" in response.json()["detail"]

    def test_returns_404_for_unknown_scanner(self) -> None:
        """When scanner is not in results, return 404."""
        mock_result = _make_mock_result(scanners=["refusal"])

        client = TestClient(v2_api_app())
        with patch(
            "inspect_scout._view._api_v2_scans.scan_results_arrow_async",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = client.get(_url("nonexistent", "some-uuid"))

        assert response.status_code == 404
        assert "nonexistent" in response.json()["detail"]

    def test_returns_input_for_valid_uuid(self) -> None:
        """When UUID exists, return the input content with input type header."""
        mock_result = _make_mock_result(scanners=["refusal"])

        input_scalar = MagicMock()
        input_scalar.as_py.return_value = "the input text"
        type_scalar = MagicMock()
        type_scalar.as_py.return_value = "text"
        mock_result.get_field.side_effect = [input_scalar, type_scalar]

        client = TestClient(v2_api_app())
        with patch(
            "inspect_scout._view._api_v2_scans.scan_results_arrow_async",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = client.get(_url("refusal", "valid-uuid"))

        assert response.status_code == 200
        assert response.text == "the input text"
        assert response.headers["X-Input-Type"] == "text"
