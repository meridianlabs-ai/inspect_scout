"""Tests for the view server and API endpoints."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pyarrow as pa
import pytest
from fastapi.testclient import TestClient
from inspect_scout._recorder.recorder import ScanResultsArrow, ScanResultsDF, Status
from inspect_scout._recorder.summary import Summary
from inspect_scout._scanner.result import Error
from inspect_scout._scanspec import ScanSpec
from inspect_scout._view._api_v1 import v1_api_app
from inspect_scout._view.server import (
    AuthorizationMiddleware,
)
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)


@pytest.fixture
def mock_fs() -> MagicMock:
    """Create a mock filesystem."""
    fs = MagicMock()
    fs.exists.return_value = True
    info = MagicMock()
    info.name = "/test/results"
    fs.info.return_value = info
    return fs


@pytest.fixture
def sample_scan_spec() -> ScanSpec:
    """Create a sample scan specification."""
    return ScanSpec(
        scan_name="test_scan",
        scanners={},
        transcripts=None,
    )


@pytest.fixture
def sample_status(sample_scan_spec: ScanSpec) -> Status:
    """Create a sample scan status."""
    return Status(
        complete=True,
        spec=sample_scan_spec,
        location="/test/scan",
        summary=Summary(scanners={}),
        errors=[],
    )


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """Create a sample pandas DataFrame."""
    return pd.DataFrame(
        {
            "transcript_id": ["t1", "t2", "t3"],
            "scanner": ["scanner1", "scanner1", "scanner1"],
            "value": [1.0, 2.0, 3.0],
            "explanation": ["test1", "test2", "test3"],
        }
    )


@pytest.fixture
def app_with_results_dir(tmp_path: Path) -> TestClient:
    """Create a test app with a temporary results directory."""
    results_dir = str(tmp_path)
    app = v1_api_app(results_dir=results_dir)
    return TestClient(app)


class TestViewServerAppScansEndpoint:
    """Tests for the /scans endpoint."""

    @pytest.mark.asyncio
    async def test_scans_endpoint_success(
        self, app_with_results_dir: TestClient
    ) -> None:
        """Test successful retrieval of scans list."""
        mock_scans = [
            Status(
                complete=True,
                spec=ScanSpec(scan_name="test_scan", scanners={}, transcripts=None),
                location="/test/scan1",
                summary=Summary(scanners={}),
                errors=[],
            )
        ]

        with patch(
            "inspect_scout._view._api_v1.scan_list_async", return_value=mock_scans
        ):
            response = app_with_results_dir.get("/scans")

        assert response.status_code == 200
        data = response.json()
        assert "scans" in data
        assert "results_dir" in data
        assert len(data["scans"]) == 1

    @pytest.mark.asyncio
    async def test_scans_endpoint_with_query_param(
        self, app_with_results_dir: TestClient
    ) -> None:
        """Test scans endpoint with results_dir query parameter."""
        mock_scans: list[Status] = []

        with patch(
            "inspect_scout._view._api_v1.scan_list_async", return_value=mock_scans
        ):
            response = app_with_results_dir.get("/scans?results_dir=/custom/path")

        assert response.status_code == 200
        data = response.json()
        assert data["results_dir"] == "/custom/path"

    @pytest.mark.asyncio
    async def test_scans_endpoint_no_results_dir(self) -> None:
        """Test scans endpoint without results_dir."""
        app = v1_api_app(results_dir=None)
        client = TestClient(app)

        response = client.get("/scans")

        assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR

    # @pytest.mark.asyncio
    # async def test_scans_endpoint_returns_etag(
    #     self, app_with_results_dir: TestClient
    # ) -> None:
    #     """Test that /scans returns ETag header."""
    #     with (
    #         patch("inspect_scout._view._api_v1.scan_list_async", return_value=[]),
    #         patch(
    #             "inspect_scout._view._api_v1._compute_scans_etag",
    #             return_value="abc123",
    #         ),
    #     ):
    #         response = app_with_results_dir.get("/scans")

    #     assert response.status_code == 200
    #     assert response.headers.get("etag") == '"abc123"'

    # @pytest.mark.asyncio
    # async def test_scans_endpoint_304_on_matching_etag(
    #     self, app_with_results_dir: TestClient
    # ) -> None:
    #     """Test 304 returned when If-None-Match matches ETag."""
    #     with patch(
    #         "inspect_scout._view._api_v1._compute_scans_etag",
    #         return_value="abc123",
    #     ):
    #         response = app_with_results_dir.get(
    #             "/scans", headers={"If-None-Match": '"abc123"'}
    #         )

    #     assert response.status_code == 304
    #     assert response.headers.get("etag") == '"abc123"'

    # @pytest.mark.asyncio
    # async def test_scans_endpoint_200_on_mismatched_etag(
    #     self, app_with_results_dir: TestClient
    # ) -> None:
    #     """Test full response when If-None-Match doesn't match."""
    #     with (
    #         patch("inspect_scout._view._api_v1.scan_list_async", return_value=[]),
    #         patch(
    #             "inspect_scout._view._api_v1._compute_scans_etag",
    #             return_value="abc123",
    #         ),
    #     ):
    #         response = app_with_results_dir.get(
    #             "/scans", headers={"If-None-Match": '"old-etag"'}
    #         )

    #     assert response.status_code == 200
    #     assert response.headers.get("etag") == '"abc123"'


class TestViewServerAppScanDfEndpoint:
    """Tests for the /scanner_df endpoint."""

    @pytest.mark.asyncio
    async def test_scanner_df_endpoint_success(
        self, app_with_results_dir: TestClient, sample_dataframe: pd.DataFrame
    ) -> None:
        """Test successful retrieval of scanner dataframe."""
        # Create a mock ScanResultsArrow
        mock_results = MagicMock(spec=ScanResultsArrow)
        mock_results.scanners = ["scanner1"]

        # Create mock record batch reader
        table = pa.Table.from_pandas(sample_dataframe, preserve_index=False)
        mock_reader = MagicMock()
        mock_reader.__enter__ = MagicMock(return_value=mock_reader)
        mock_reader.__exit__ = MagicMock(return_value=None)
        mock_reader.__iter__ = MagicMock(return_value=iter([table.to_batches()[0]]))
        mock_reader.schema = table.schema

        mock_results.reader.return_value = mock_reader

        with patch(
            "inspect_scout._view._api_v1.scan_results_arrow_async",
            return_value=mock_results,
        ):
            response = app_with_results_dir.get(
                "/scanner_df/test_scan?scanner=scanner1"
            )

        assert response.status_code == 200
        assert (
            response.headers["content-type"]
            == "application/vnd.apache.arrow.stream; codecs=lz4"
        )

    @pytest.mark.asyncio
    async def test_scanner_df_endpoint_missing_scanner_param(
        self, app_with_results_dir: TestClient
    ) -> None:
        """Test scanner_df endpoint without scanner parameter."""
        response = app_with_results_dir.get("/scanner_df/test_scan")

        assert response.status_code == HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_scanner_df_endpoint_scanner_not_found(
        self, app_with_results_dir: TestClient
    ) -> None:
        """Test scanner_df endpoint with non-existent scanner."""
        mock_results = MagicMock(spec=ScanResultsArrow)
        mock_results.scanners = ["scanner1"]

        with patch(
            "inspect_scout._view._api_v1.scan_results_arrow_async",
            return_value=mock_results,
        ):
            response = app_with_results_dir.get(
                "/scanner_df/test_scan?scanner=nonexistent"
            )

        assert response.status_code == HTTP_404_NOT_FOUND


class TestViewServerAppScanEndpoint:
    """Tests for the /scan endpoint."""

    @pytest.mark.asyncio
    async def test_scan_endpoint_success(
        self, app_with_results_dir: TestClient, sample_dataframe: pd.DataFrame
    ) -> None:
        """Test successful retrieval of scan results."""
        mock_results = ScanResultsDF(
            complete=True,
            spec=ScanSpec(scan_name="test_scan", scanners={}, transcripts=None),
            location="/test/scan",
            summary=Summary(scanners={}),
            errors=[],
            scanners={"scanner1": sample_dataframe},
        )

        with patch(
            "inspect_scout._view._api_v1.scan_results_df_async",
            return_value=mock_results,
        ):
            response = app_with_results_dir.get("/scan/test_scan")

        assert response.status_code == 200
        data = response.json()
        assert data["complete"] is True
        assert data["location"] == "/test/scan"

    @pytest.mark.asyncio
    async def test_scan_endpoint_status_only(
        self, app_with_results_dir: TestClient, sample_dataframe: pd.DataFrame
    ) -> None:
        """Test scan endpoint with status_only parameter."""
        mock_results = ScanResultsDF(
            complete=True,
            spec=ScanSpec(scan_name="test_scan", scanners={}, transcripts=None),
            location="/test/scan",
            summary=Summary(scanners={}),
            errors=[],
            scanners={"scanner1": sample_dataframe},
        )

        with patch(
            "inspect_scout._view._api_v1.scan_results_df_async",
            return_value=mock_results,
        ):
            response = app_with_results_dir.get("/scan/test_scan?status_only=true")

        assert response.status_code == 200
        data = response.json()
        print(data)
        assert data["complete"] is True


class TestViewServerAppScanDeleteEndpoint:
    """Tests for the /scan-delete endpoint."""

    @pytest.mark.asyncio
    async def test_scan_delete_endpoint_success(
        self, app_with_results_dir: TestClient
    ) -> None:
        """Test successful deletion of scan results."""
        with patch("inspect_scout._view._api_v1.remove_scan_results") as mock_remove:
            response = app_with_results_dir.get("/scan-delete/test_scan")

        assert response.status_code == 200
        assert response.json() is True
        mock_remove.assert_called_once()


class TestAuthorizationMiddleware:
    """Tests for the AuthorizationMiddleware."""

    def test_authorization_middleware_success(self) -> None:
        """Test successful authorization."""
        app = v1_api_app(results_dir="/test")
        test_auth = "Bearer test-token"

        # Add authorization middleware
        from fastapi import FastAPI

        main_app = FastAPI()
        main_app.add_middleware(AuthorizationMiddleware, authorization=test_auth)
        main_app.mount("/api", app)

        client = TestClient(main_app)

        with patch("inspect_scout._view._api_v1.scan_list_async", return_value=[]):
            response = client.get(
                "/api/scans?results_dir=/test",
                headers={"Authorization": test_auth},
            )

        assert response.status_code == 200

    def test_authorization_middleware_failure(self) -> None:
        """Test failed authorization."""
        app = v1_api_app(results_dir="/test")
        test_auth = "Bearer test-token"

        # Add authorization middleware
        from fastapi import FastAPI

        main_app = FastAPI()
        main_app.add_middleware(AuthorizationMiddleware, authorization=test_auth)
        main_app.mount("/api", app)

        client = TestClient(main_app)

        response = client.get(
            "/api/scans?results_dir=/test",
            headers={"Authorization": "Bearer wrong-token"},
        )

        assert response.status_code == 401

    def test_authorization_middleware_missing_header(self) -> None:
        """Test missing authorization header."""
        app = v1_api_app(results_dir="/test")
        test_auth = "Bearer test-token"

        # Add authorization middleware
        from fastapi import FastAPI

        main_app = FastAPI()
        main_app.add_middleware(AuthorizationMiddleware, authorization=test_auth)
        main_app.mount("/api", app)

        client = TestClient(main_app)

        response = client.get("/api/scans?results_dir=/test")

        assert response.status_code == 401


class TestAccessPolicy:
    """Tests for access policy enforcement."""

    @pytest.mark.asyncio
    async def test_access_policy_read_forbidden(self) -> None:
        """Test that access policy blocks unauthorized reads."""
        mock_access_policy = MagicMock()
        mock_access_policy.can_read = AsyncMock(return_value=False)

        app = v1_api_app(access_policy=mock_access_policy, results_dir="/test")
        client = TestClient(app)

        with patch("inspect_scout._view._api_v1.scan_results_df_async") as mock_scan:
            response = client.get("/scan/test_scan")

        assert response.status_code == HTTP_403_FORBIDDEN
        mock_scan.assert_not_called()

    @pytest.mark.asyncio
    async def test_access_policy_delete_forbidden(self) -> None:
        """Test that access policy blocks unauthorized deletes."""
        mock_access_policy = MagicMock()
        mock_access_policy.can_delete = AsyncMock(return_value=False)

        app = v1_api_app(access_policy=mock_access_policy, results_dir="/test")
        client = TestClient(app)

        with patch("inspect_scout._view._api_v1.remove_scan_results") as mock_remove:
            response = client.get("/scan-delete/test_scan")

        assert response.status_code == HTTP_403_FORBIDDEN
        mock_remove.assert_not_called()

    @pytest.mark.asyncio
    async def test_access_policy_list_forbidden(self) -> None:
        """Test that access policy blocks unauthorized lists."""
        mock_access_policy = MagicMock()
        mock_access_policy.can_list = AsyncMock(return_value=False)

        app = v1_api_app(access_policy=mock_access_policy, results_dir="/test")
        client = TestClient(app)

        with patch("inspect_scout._view._api_v1.scan_list_async") as mock_list:
            response = client.get("/scans?results_dir=/test")

        assert response.status_code == HTTP_403_FORBIDDEN
        mock_list.assert_not_called()


class TestMappingPolicy:
    """Tests for file mapping policy."""

    @pytest.mark.asyncio
    async def test_mapping_policy_map_and_unmap(self) -> None:
        """Test that mapping policy transforms file paths."""
        mock_mapping_policy = MagicMock()
        mock_mapping_policy.map = AsyncMock(
            side_effect=lambda req, file: f"/mapped{file}"
        )
        mock_mapping_policy.unmap = AsyncMock(
            side_effect=lambda req, file: file.replace("/mapped", "")
        )

        app = v1_api_app(mapping_policy=mock_mapping_policy, results_dir="/test")
        client = TestClient(app)

        mock_scans = [
            Status(
                complete=True,
                spec=ScanSpec(scan_name="test_scan", scanners={}, transcripts=None),
                location="/mapped/test/scan1",
                summary=Summary(scanners={}),
                errors=[],
            )
        ]

        with patch(
            "inspect_scout._view._api_v1.scan_list_async", return_value=mock_scans
        ):
            response = client.get("/scans?results_dir=/test")

        assert response.status_code == 200
        data = response.json()
        # Location should be unmapped in response
        assert data["scans"][0]["location"] == "/test/scan1"


class TestViewServerAppEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_relative_path_conversion(
        self, app_with_results_dir: TestClient, sample_dataframe: pd.DataFrame
    ) -> None:
        """Test that relative paths are converted to absolute."""
        mock_results = ScanResultsDF(
            complete=True,
            spec=ScanSpec(scan_name="test_scan", scanners={}, transcripts=None),
            location="/test/scan",
            summary=Summary(scanners={}),
            errors=[],
            scanners={"scanner1": sample_dataframe},
        )

        with patch(
            "inspect_scout._view._api_v1.scan_results_df_async",
            return_value=mock_results,
        ):
            # Use relative path
            response = app_with_results_dir.get("/scan/relative/path/scan")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_scan_with_errors(self, app_with_results_dir: TestClient) -> None:
        """Test scan results with errors."""
        mock_results = ScanResultsDF(
            complete=False,
            spec=ScanSpec(scan_name="test_scan", scanners={}, transcripts=None),
            location="/test/scan",
            summary=Summary(scanners={}),
            errors=[
                Error(
                    transcript_id="t1",
                    scanner="scanner1",
                    error="Test error",
                    traceback="",
                    refusal=False,
                )
            ],
            scanners={},
        )

        with patch(
            "inspect_scout._view._api_v1.scan_results_df_async",
            return_value=mock_results,
        ):
            response = app_with_results_dir.get("/scan/test_scan?status_only=true")

        assert response.status_code == 200
        data = response.json()
        assert data["complete"] is False
        assert len(data["errors"]) == 1
        assert data["errors"][0]["error"] == "Test error"
