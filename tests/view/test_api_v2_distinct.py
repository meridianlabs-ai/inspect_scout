"""Tests for POST /transcripts/{dir}/distinct endpoint."""

import base64
from pathlib import Path
from typing import AsyncIterator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from inspect_ai.model._chat_message import ChatMessageUser
from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB
from inspect_scout._transcript.types import Transcript
from inspect_scout._view._api_v2 import v2_api_app


def _encode_dir(path: str) -> str:
    """Base64url encode a directory path."""
    return base64.urlsafe_b64encode(path.encode()).decode().rstrip("=")


def _create_transcript(
    id: str,
    model: str,
    task_set: str,
) -> Transcript:
    """Create a test transcript."""
    return Transcript(
        transcript_id=id,
        source_type="test",
        source_id="source-001",
        source_uri="test://uri",
        task_set=task_set,
        model=model,
        score=None,
        metadata={},
        messages=[ChatMessageUser(content="Test")],
        events=[],
    )


@pytest.fixture
def test_location(tmp_path: Path) -> Path:
    """Create temporary directory for Parquet files."""
    location = tmp_path / "transcript_db"
    location.mkdir(parents=True, exist_ok=True)
    return location


@pytest_asyncio.fixture
async def populated_db(test_location: Path) -> AsyncIterator[ParquetTranscriptsDB]:
    """Create and populate a parquet database."""
    db = ParquetTranscriptsDB(str(test_location))
    await db.connect()
    await db.insert(
        [
            _create_transcript("t1", "gpt-4", "math"),
            _create_transcript("t2", "gpt-4", "coding"),
            _create_transcript("t3", "claude", "math"),
            _create_transcript("t4", "claude", "qa"),
            _create_transcript("t5", "gpt-3.5", "math"),
        ]
    )
    yield db
    await db.disconnect()


@pytest.fixture
def client(test_location: Path, populated_db: ParquetTranscriptsDB) -> TestClient:
    """Create test client."""
    return TestClient(v2_api_app(results_dir=str(test_location)))


class TestDistinctEndpoint:
    """Tests for POST /transcripts/{dir}/distinct endpoint."""

    def test_distinct_no_filter(self, client: TestClient, test_location: Path) -> None:
        """Get distinct values without filter."""
        response = client.post(
            f"/transcripts/{_encode_dir(str(test_location))}/distinct",
            json={"column": "model"},
        )

        assert response.status_code == 200
        values = response.json()
        assert set(values) == {"claude", "gpt-3.5", "gpt-4"}
        # Verify sorted ascending
        assert values == sorted(values)

    def test_distinct_with_filter(
        self, client: TestClient, test_location: Path
    ) -> None:
        """Get distinct values with filter condition."""
        response = client.post(
            f"/transcripts/{_encode_dir(str(test_location))}/distinct",
            json={
                "column": "model",
                "filter": {
                    "is_compound": False,
                    "left": "task_set",
                    "operator": "=",
                    "right": "math",
                },
            },
        )

        assert response.status_code == 200
        values = response.json()
        assert set(values) == {"claude", "gpt-3.5", "gpt-4"}

    def test_distinct_empty_result(
        self, client: TestClient, test_location: Path
    ) -> None:
        """Get distinct values with no matching results."""
        response = client.post(
            f"/transcripts/{_encode_dir(str(test_location))}/distinct",
            json={
                "column": "task_set",
                "filter": {
                    "is_compound": False,
                    "left": "model",
                    "operator": "=",
                    "right": "nonexistent",
                },
            },
        )

        assert response.status_code == 200
        assert response.json() == []

    def test_distinct_no_body(self, client: TestClient, test_location: Path) -> None:
        """Request with no body returns empty list."""
        response = client.post(
            f"/transcripts/{_encode_dir(str(test_location))}/distinct",
        )

        assert response.status_code == 200
        assert response.json() == []

    def test_distinct_different_column(
        self, client: TestClient, test_location: Path
    ) -> None:
        """Get distinct values for different column."""
        response = client.post(
            f"/transcripts/{_encode_dir(str(test_location))}/distinct",
            json={"column": "task_set"},
        )

        assert response.status_code == 200
        values = response.json()
        assert set(values) == {"coding", "math", "qa"}
        assert values == sorted(values)
