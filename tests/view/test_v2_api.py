"""Tests for the view server and API endpoints."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pyarrow as pa
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from inspect_scout._recorder.recorder import ScanResultsArrow, ScanResultsDF, Status
from inspect_scout._recorder.summary import Summary
from inspect_scout._scanner.result import Error
from inspect_scout._scanspec import ScanSpec
from inspect_scout._view._api_v2 import v2_api_app
from inspect_scout._view.server import (
    AuthorizationMiddleware,
)
from starlette.status import (
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)


def _base64url(s: str) -> str:
    """Encode string as base64url (URL-safe base64 without padding)."""
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


if TYPE_CHECKING:
    from inspect_scout._transcript.types import Transcript


def base64url(s: str) -> str:
    """Encode string as base64url (URL-safe base64 without padding)."""
    import base64

    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


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
    return TestClient(v2_api_app(results_dir=results_dir))


class TestViewServerAppScansEndpoint:
    """Tests for the /scanjobs endpoint."""

    @pytest.mark.asyncio
    async def test_scans_endpoint_success(
        self, app_with_results_dir: TestClient
    ) -> None:
        """Test successful retrieval of scans list."""
        mock_view = AsyncMock()
        mock_view.count = AsyncMock(return_value=1)

        async def mock_select(query: Any) -> Any:
            yield Status(
                complete=True,
                spec=ScanSpec(scan_name="test_scan", scanners={}, transcripts=None),
                location="/test/scan1",
                summary=Summary(scanners={}),
                errors=[],
            )

        mock_view.select = mock_select

        with patch(
            "inspect_scout._view._api_v2.scan_jobs_view",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_view)),
        ):
            response = app_with_results_dir.post("/scanjobs", json={})

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 1

    @pytest.mark.asyncio
    async def test_scans_endpoint_no_results_dir(self) -> None:
        """Test scans endpoint without results_dir."""
        client = TestClient(v2_api_app(results_dir=None))

        response = client.post("/scanjobs", json={})

        assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR


class TestViewServerAppScanDfEndpoint:
    """Tests for the /scanjobs/{scan}/{scanner} endpoint."""

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
            "inspect_scout._view._api_v2.scan_results_arrow_async",
            return_value=mock_results,
        ):
            response = app_with_results_dir.get(
                f"/scanjobs/{base64url('test_scan')}/scanner1"
            )

        assert response.status_code == 200
        assert (
            response.headers["content-type"]
            == "application/vnd.apache.arrow.stream; codecs=lz4"
        )

    @pytest.mark.asyncio
    async def test_scanner_df_endpoint_scanner_not_found(
        self, app_with_results_dir: TestClient
    ) -> None:
        """Test scanner_df endpoint with non-existent scanner."""
        mock_results = MagicMock(spec=ScanResultsArrow)
        mock_results.scanners = ["scanner1"]

        with patch(
            "inspect_scout._view._api_v2.scan_results_arrow_async",
            return_value=mock_results,
        ):
            response = app_with_results_dir.get(
                f"/scanjobs/{base64url('test_scan')}/nonexistent"
            )

        assert response.status_code == HTTP_404_NOT_FOUND


class TestViewServerAppScanEndpoint:
    """Tests for the /scanjobs/{scan} endpoint."""

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
            "inspect_scout._view._api_v2.scan_results_df_async",
            return_value=mock_results,
        ):
            response = app_with_results_dir.get(f"/scanjobs/{base64url('test_scan')}")

        assert response.status_code == 200
        data = response.json()
        assert data["complete"] is True
        assert data["location"] == "/test/scan"


class TestAuthorizationMiddleware:
    """Tests for the AuthorizationMiddleware."""

    def test_authorization_middleware_success(self) -> None:
        """Test successful authorization."""
        test_auth = "Bearer test-token"

        v2_api = v2_api_app(results_dir="/test")
        v2_api.add_middleware(AuthorizationMiddleware, authorization=test_auth)

        main_app = FastAPI()
        main_app.mount("/api/v2", v2_api)

        client = TestClient(main_app)

        mock_view = AsyncMock()
        mock_view.count = AsyncMock(return_value=0)

        async def mock_select(query: Any) -> Any:
            return
            yield  # make it a generator

        mock_view.select = mock_select

        with patch(
            "inspect_scout._view._api_v2.scan_jobs_view",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_view)),
        ):
            response = client.post(
                "/api/v2/scanjobs",
                json={},
                headers={"Authorization": test_auth},
            )

        assert response.status_code == 200

    def test_authorization_middleware_failure(self) -> None:
        """Test failed authorization."""
        test_auth = "Bearer test-token"

        v2_api = v2_api_app(results_dir="/test")
        v2_api.add_middleware(AuthorizationMiddleware, authorization=test_auth)

        main_app = FastAPI()
        main_app.mount("/api/v2", v2_api)

        client = TestClient(main_app)

        response = client.post(
            "/api/v2/scanjobs",
            json={},
            headers={"Authorization": "Bearer wrong-token"},
        )

        assert response.status_code == 401

    def test_authorization_middleware_missing_header(self) -> None:
        """Test missing authorization header."""
        test_auth = "Bearer test-token"

        v2_api = v2_api_app(results_dir="/test")
        v2_api.add_middleware(AuthorizationMiddleware, authorization=test_auth)

        main_app = FastAPI()
        main_app.mount("/api/v2", v2_api)

        client = TestClient(main_app)

        response = client.post("/api/v2/scanjobs", json={})

        assert response.status_code == 401


class TestAccessPolicy:
    """Tests for access policy enforcement."""

    @pytest.mark.asyncio
    async def test_access_policy_read_forbidden(self) -> None:
        """Test that access policy blocks unauthorized reads."""
        mock_access_policy = MagicMock()
        mock_access_policy.can_read = AsyncMock(return_value=False)

        client = TestClient(
            v2_api_app(access_policy=mock_access_policy, results_dir="/test")
        )

        with patch("inspect_scout._view._api_v2.scan_results_df_async") as mock_scan:
            response = client.get(f"/scanjobs/{base64url('test_scan')}")

        assert response.status_code == HTTP_403_FORBIDDEN
        mock_scan.assert_not_called()

    @pytest.mark.asyncio
    async def test_access_policy_list_forbidden(self) -> None:
        """Test that access policy blocks unauthorized lists."""
        mock_access_policy = MagicMock()
        mock_access_policy.can_list = AsyncMock(return_value=False)

        client = TestClient(
            v2_api_app(access_policy=mock_access_policy, results_dir="/test")
        )

        with patch("inspect_scout._view._api_v2.scan_jobs_view") as mock_view:
            response = client.post("/scanjobs", json={})

        assert response.status_code == HTTP_403_FORBIDDEN
        mock_view.assert_not_called()


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
            "inspect_scout._view._api_v2.scan_results_df_async",
            return_value=mock_results,
        ):
            # Use relative path (base64url encoded)
            response = app_with_results_dir.get(
                f"/scanjobs/{base64url('relative/path/scan')}"
            )

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
            "inspect_scout._view._api_v2.scan_results_df_async",
            return_value=mock_results,
        ):
            response = app_with_results_dir.get(f"/scanjobs/{base64url('test_scan')}")

        assert response.status_code == 200
        data = response.json()
        assert data["complete"] is False
        assert len(data["errors"]) == 1
        assert data["errors"][0]["error"] == "Test error"


def _create_test_transcripts_for_api(count: int) -> list[Transcript]:
    """Create transcripts with varied metadata for API pagination tests."""
    from inspect_ai.model._chat_message import ChatMessageUser
    from inspect_scout._transcript.types import Transcript

    transcripts: list[Transcript] = []
    for i in range(count):
        transcripts.append(
            Transcript(
                transcript_id=f"t{i:03d}",
                source_type="test",
                source_id=f"src-{i}",
                source_uri=f"test://uri/{i}",
                model=["gpt-4", "claude"][i % 2],
                task_set=["math", "code"][i % 2],
                score=float(i) * 0.1,
                metadata={"index": i},
                messages=[ChatMessageUser(content=f"Q{i}")],
                events=[],
            )
        )
    return transcripts


async def _populate_transcripts(location: Path, transcripts: list[Transcript]) -> None:
    """Populate transcript database for testing."""
    from inspect_scout import transcripts_db

    async with transcripts_db(str(location)) as db:
        await db.insert(transcripts)


class TestTranscriptsPagination:
    """Tests for /transcripts endpoint pagination."""

    def test_transcripts_response_structure(self, tmp_path: Path) -> None:
        """Verify response has items, next_cursor, and count fields."""
        # Create test client
        client = TestClient(v2_api_app(results_dir=str(tmp_path)))

        # Make request (empty dir)
        response = client.post(f"/transcripts/{_base64url(str(tmp_path))}", json={})

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "next_cursor" in data
        assert "total_count" in data
        assert isinstance(data["items"], list)
        assert data["next_cursor"] is None
        assert data["total_count"] == 0

    @pytest.mark.asyncio
    async def test_transcripts_count_no_filter(self, tmp_path: Path) -> None:
        """Count equals total items when no filter."""
        transcripts = _create_test_transcripts_for_api(10)
        await _populate_transcripts(tmp_path, transcripts)

        client = TestClient(v2_api_app(results_dir=str(tmp_path)))
        response = client.post(f"/transcripts/{_base64url(str(tmp_path))}", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 10
        assert len(data["items"]) == 10

    @pytest.mark.asyncio
    async def test_transcripts_count_with_filter(self, tmp_path: Path) -> None:
        """Count reflects filtered total."""
        transcripts = _create_test_transcripts_for_api(10)
        await _populate_transcripts(tmp_path, transcripts)

        client = TestClient(v2_api_app(results_dir=str(tmp_path)))
        # Filter to gpt-4 only (every other one = 5)
        response = client.post(
            f"/transcripts/{_base64url(str(tmp_path))}",
            json={"filter": {"left": "model", "operator": "=", "right": "gpt-4"}},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 5
        assert len(data["items"]) == 5

    @pytest.mark.asyncio
    async def test_transcripts_count_with_pagination(self, tmp_path: Path) -> None:
        """Count reflects total matching filter, not pagination limit."""
        transcripts = _create_test_transcripts_for_api(10)
        await _populate_transcripts(tmp_path, transcripts)

        client = TestClient(v2_api_app(results_dir=str(tmp_path)))
        response = client.post(
            f"/transcripts/{_base64url(str(tmp_path))}",
            json={"pagination": {"limit": 3, "cursor": None, "direction": "forward"}},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 10  # Total, not limit
        assert len(data["items"]) == 3  # Pagination limit

    @pytest.mark.asyncio
    async def test_transcripts_no_pagination(self, tmp_path: Path) -> None:
        """Returns all results with next_cursor=None when no pagination specified."""
        # Populate with 10 transcripts
        transcripts = _create_test_transcripts_for_api(10)
        await _populate_transcripts(tmp_path, transcripts)

        # Make request without pagination
        client = TestClient(v2_api_app(results_dir=str(tmp_path)))
        response = client.post(f"/transcripts/{_base64url(str(tmp_path))}", json={})

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        assert data["next_cursor"] is None

    @pytest.mark.asyncio
    async def test_pagination_first_page_forward(self, tmp_path: Path) -> None:
        """First page without cursor."""
        # Populate with 10 transcripts
        transcripts = _create_test_transcripts_for_api(10)
        await _populate_transcripts(tmp_path, transcripts)

        # Request first 3 items
        client = TestClient(v2_api_app(results_dir=str(tmp_path)))
        response = client.post(
            f"/transcripts/{_base64url(str(tmp_path))}",
            json={
                "pagination": {"limit": 3, "cursor": None, "direction": "forward"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        # Default sort is transcript_id ASC when pagination without order_by
        assert data["items"][0]["transcript_id"] == "t000"
        assert data["items"][1]["transcript_id"] == "t001"
        assert data["items"][2]["transcript_id"] == "t002"
        assert data["next_cursor"] is not None
        assert data["next_cursor"]["transcript_id"] == "t002"

    @pytest.mark.asyncio
    async def test_pagination_next_page_forward(self, tmp_path: Path) -> None:
        """Next page with cursor."""
        # Populate with 10 transcripts
        transcripts = _create_test_transcripts_for_api(10)
        await _populate_transcripts(tmp_path, transcripts)

        client = TestClient(v2_api_app(results_dir=str(tmp_path)))

        # Get first page
        response1 = client.post(
            f"/transcripts/{_base64url(str(tmp_path))}",
            json={
                "pagination": {"limit": 3, "cursor": None, "direction": "forward"},
            },
        )
        data1 = response1.json()
        cursor = data1["next_cursor"]

        # Get second page using cursor
        response2 = client.post(
            f"/transcripts/{_base64url(str(tmp_path))}",
            json={
                "pagination": {"limit": 3, "cursor": cursor, "direction": "forward"},
            },
        )

        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2["items"]) == 3
        assert data2["items"][0]["transcript_id"] == "t003"
        assert data2["items"][1]["transcript_id"] == "t004"
        assert data2["items"][2]["transcript_id"] == "t005"
        assert data2["next_cursor"] is not None

    @pytest.mark.asyncio
    async def test_pagination_backward(self, tmp_path: Path) -> None:
        """Backward pagination."""
        # Populate with 10 transcripts
        transcripts = _create_test_transcripts_for_api(10)
        await _populate_transcripts(tmp_path, transcripts)

        client = TestClient(v2_api_app(results_dir=str(tmp_path)))

        # Get last 3 items (backward from end)
        response = client.post(
            f"/transcripts/{_base64url(str(tmp_path))}",
            json={
                "pagination": {"limit": 3, "cursor": None, "direction": "backward"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        # Backward without cursor returns last N items
        assert data["items"][0]["transcript_id"] == "t007"
        assert data["items"][1]["transcript_id"] == "t008"
        assert data["items"][2]["transcript_id"] == "t009"
        assert data["next_cursor"] is not None

    def test_pagination_empty_results(self, tmp_path: Path) -> None:
        """Empty dataset."""
        client = TestClient(v2_api_app(results_dir=str(tmp_path)))

        response = client.post(
            f"/transcripts/{_base64url(str(tmp_path))}",
            json={"pagination": {"limit": 10, "cursor": None, "direction": "forward"}},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["next_cursor"] is None

    @pytest.mark.asyncio
    async def test_pagination_single_column_sort(self, tmp_path: Path) -> None:
        """Single column sort with pagination."""
        # Populate with 10 transcripts (alternating gpt-4, claude)
        transcripts = _create_test_transcripts_for_api(10)
        await _populate_transcripts(tmp_path, transcripts)

        client = TestClient(v2_api_app(results_dir=str(tmp_path)))

        # Sort by model ASC, paginate
        response = client.post(
            f"/transcripts/{_base64url(str(tmp_path))}",
            json={
                "order_by": {"column": "model", "direction": "ASC"},
                "pagination": {"limit": 3, "cursor": None, "direction": "forward"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        # Should get claude items first (alphabetically)
        assert all(item["model"] == "claude" for item in data["items"])
        assert data["next_cursor"] is not None
        assert "model" in data["next_cursor"]
        assert "transcript_id" in data["next_cursor"]  # tiebreaker added

    @pytest.mark.asyncio
    async def test_pagination_multi_column_sort(self, tmp_path: Path) -> None:
        """Multi-column sort with pagination."""
        # Populate with 10 transcripts
        transcripts = _create_test_transcripts_for_api(10)
        await _populate_transcripts(tmp_path, transcripts)

        client = TestClient(v2_api_app(results_dir=str(tmp_path)))

        # Sort by model ASC, then score DESC
        response = client.post(
            f"/transcripts/{_base64url(str(tmp_path))}",
            json={
                "order_by": [
                    {"column": "model", "direction": "ASC"},
                    {"column": "score", "direction": "DESC"},
                ],
                "pagination": {"limit": 3, "cursor": None, "direction": "forward"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        # Within same model, scores should descend
        assert data["items"][0]["model"] == "claude"
        assert data["next_cursor"] is not None
        assert "model" in data["next_cursor"]
        assert "score" in data["next_cursor"]
        assert "transcript_id" in data["next_cursor"]

    @pytest.mark.asyncio
    async def test_pagination_explicit_transcript_id_sort(self, tmp_path: Path) -> None:
        """User sorts by transcript_id (no duplicate tiebreaker)."""
        # Populate with 10 transcripts
        transcripts = _create_test_transcripts_for_api(10)
        await _populate_transcripts(tmp_path, transcripts)

        client = TestClient(v2_api_app(results_dir=str(tmp_path)))

        # Sort explicitly by transcript_id
        response = client.post(
            f"/transcripts/{_base64url(str(tmp_path))}",
            json={
                "order_by": {"column": "transcript_id", "direction": "DESC"},
                "pagination": {"limit": 3, "cursor": None, "direction": "forward"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        # Should be descending
        assert data["items"][0]["transcript_id"] == "t009"
        assert data["items"][1]["transcript_id"] == "t008"
        assert data["items"][2]["transcript_id"] == "t007"
        # Cursor should only have transcript_id (no duplicate)
        assert data["next_cursor"] == {"transcript_id": "t007"}

    @pytest.mark.asyncio
    async def test_pagination_default_sort(self, tmp_path: Path) -> None:
        """No order_by with pagination (defaults to transcript_id ASC)."""
        # Populate with 10 transcripts
        transcripts = _create_test_transcripts_for_api(10)
        await _populate_transcripts(tmp_path, transcripts)

        client = TestClient(v2_api_app(results_dir=str(tmp_path)))

        # Paginate without order_by
        response = client.post(
            f"/transcripts/{_base64url(str(tmp_path))}",
            json={
                "pagination": {"limit": 3, "cursor": None, "direction": "forward"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        # Should default to transcript_id ASC
        assert data["items"][0]["transcript_id"] == "t000"
        assert data["items"][1]["transcript_id"] == "t001"
        assert data["items"][2]["transcript_id"] == "t002"
        assert data["next_cursor"] == {"transcript_id": "t002"}

    @pytest.mark.asyncio
    async def test_pagination_none_values(self, tmp_path: Path) -> None:
        """None values in sort columns."""
        from inspect_ai.model._chat_message import ChatMessageUser
        from inspect_scout._transcript.types import Transcript

        # Create transcripts with None scores
        transcripts = [
            Transcript(
                transcript_id="t000",
                source_type="test",
                source_id="src",
                source_uri="test://uri",
                model="gpt-4",
                score=None,
                metadata={},
                messages=[ChatMessageUser(content="Q")],
                events=[],
            ),
            Transcript(
                transcript_id="t001",
                source_type="test",
                source_id="src",
                source_uri="test://uri",
                model="gpt-4",
                score=0.5,
                metadata={},
                messages=[ChatMessageUser(content="Q")],
                events=[],
            ),
            Transcript(
                transcript_id="t002",
                source_type="test",
                source_id="src",
                source_uri="test://uri",
                model="gpt-4",
                score=None,
                metadata={},
                messages=[ChatMessageUser(content="Q")],
                events=[],
            ),
        ]
        await _populate_transcripts(tmp_path, transcripts)

        client = TestClient(v2_api_app(results_dir=str(tmp_path)))

        # Sort by score (None values treated as empty string)
        response = client.post(
            f"/transcripts/{_base64url(str(tmp_path))}",
            json={
                "order_by": {"column": "score", "direction": "ASC"},
                "pagination": {"limit": 2, "cursor": None, "direction": "forward"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        # Database sorts None values last (SQL NULL behavior)
        # First two results should be non-None scores
        assert data["items"][0]["score"] is not None
        assert data["next_cursor"] is not None

    @pytest.mark.asyncio
    async def test_pagination_last_page(self, tmp_path: Path) -> None:
        """Cursor is None at end."""
        # Populate with 5 transcripts
        transcripts = _create_test_transcripts_for_api(5)
        await _populate_transcripts(tmp_path, transcripts)

        client = TestClient(v2_api_app(results_dir=str(tmp_path)))

        # Get first page of 3
        response1 = client.post(
            f"/transcripts/{_base64url(str(tmp_path))}",
            json={
                "pagination": {"limit": 3, "cursor": None, "direction": "forward"},
            },
        )
        data1 = response1.json()
        cursor = data1["next_cursor"]

        # Get second (last) page - should have 2 items and no next_cursor
        response2 = client.post(
            f"/transcripts/{_base64url(str(tmp_path))}",
            json={
                "pagination": {"limit": 3, "cursor": cursor, "direction": "forward"},
            },
        )

        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2["items"]) == 2
        assert data2["items"][0]["transcript_id"] == "t003"
        assert data2["items"][1]["transcript_id"] == "t004"
        assert data2["next_cursor"] is None  # Last page

    @pytest.mark.asyncio
    async def test_pagination_limit_larger_than_results(self, tmp_path: Path) -> None:
        """Limit exceeds available results."""
        # Populate with 5 transcripts
        transcripts = _create_test_transcripts_for_api(5)
        await _populate_transcripts(tmp_path, transcripts)

        client = TestClient(v2_api_app(results_dir=str(tmp_path)))

        # Request 100 items when only 5 exist
        response = client.post(
            f"/transcripts/{_base64url(str(tmp_path))}",
            json={
                "pagination": {"limit": 100, "cursor": None, "direction": "forward"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
        assert data["next_cursor"] is None

    @pytest.mark.asyncio
    async def test_pagination_cursor_mismatch(self, tmp_path: Path) -> None:
        """Mismatched cursor keys handled gracefully."""
        # Populate with 10 transcripts
        transcripts = _create_test_transcripts_for_api(10)
        await _populate_transcripts(tmp_path, transcripts)

        client = TestClient(v2_api_app(results_dir=str(tmp_path)))

        # Provide cursor with extra keys and missing expected keys
        fake_cursor = {"transcript_id": "t005", "extra_key": "ignored"}

        response = client.post(
            f"/transcripts/{_base64url(str(tmp_path))}",
            json={
                "pagination": {
                    "limit": 3,
                    "cursor": fake_cursor,
                    "direction": "forward",
                },
            },
        )

        assert response.status_code == 200
        data = response.json()
        # Should continue from t005 (extra keys ignored, missing keys treated as None)
        assert len(data["items"]) == 3
        assert data["items"][0]["transcript_id"] == "t006"
