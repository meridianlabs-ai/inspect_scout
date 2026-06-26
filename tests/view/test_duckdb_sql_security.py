import base64
from pathlib import Path
from typing import AsyncIterator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from inspect_ai.model import ChatMessageUser
from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB
from inspect_scout._transcript.types import Transcript
from inspect_scout._view._api_v2 import v2_api_app


def _encode_dir(path: Path) -> str:
    return base64.urlsafe_b64encode(str(path).encode()).decode().rstrip("=")


@pytest_asyncio.fixture
async def transcript_db(tmp_path: Path) -> AsyncIterator[Path]:
    location = tmp_path / "transcripts"
    db = ParquetTranscriptsDB(str(location))
    await db.connect()
    await db.insert(
        [
            Transcript(
                transcript_id="security-test",
                source_type="test",
                source_id="source",
                source_uri="test://source",
                model="model",
                messages=[ChatMessageUser(content="fixture")],
                events=[],
            )
        ]
    )
    await db.disconnect()
    yield location


def test_order_by_sql_injection_is_rejected(
    transcript_db: Path, tmp_path: Path
) -> None:
    marker = tmp_path / "order-by-marker.txt"
    injected_column = (
        f"transcript_id\"; COPY (SELECT 'INJECTED') TO '{marker}' (HEADER false); --"
    )

    with TestClient(v2_api_app(), raise_server_exceptions=False) as client:
        response = client.post(
            f"/transcripts/{_encode_dir(transcript_db)}",
            json={
                "order_by": {
                    "column": injected_column,
                    "direction": "ASC",
                }
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"].startswith("Unknown column:")
    assert not marker.exists()


def test_distinct_sql_injection_is_rejected(
    transcript_db: Path, tmp_path: Path
) -> None:
    marker = tmp_path / "distinct-marker.txt"
    injected_column = (
        f"model\"; COPY (SELECT 'INJECTED') TO E'{marker}' (HEADER false); --"
    )

    with TestClient(v2_api_app(), raise_server_exceptions=False) as client:
        response = client.post(
            f"/transcripts/{_encode_dir(transcript_db)}/distinct",
            json={"column": injected_column},
        )

    assert response.status_code == 400
    assert response.json()["detail"].startswith("Unknown column:")
    assert not marker.exists()


@pytest.mark.parametrize(
    "column",
    [
        '"',
        "--",
        "/* comment */",
        "; SELECT 1",
        "E''",
        "\\x2f",
        "model\\",
    ],
)
def test_identifier_metacharacters_never_reach_sql(
    transcript_db: Path, column: str
) -> None:
    with TestClient(v2_api_app(), raise_server_exceptions=False) as client:
        order_response = client.post(
            f"/transcripts/{_encode_dir(transcript_db)}",
            json={"order_by": {"column": column, "direction": "ASC"}},
        )
        distinct_response = client.post(
            f"/transcripts/{_encode_dir(transcript_db)}/distinct",
            json={"column": column},
        )

    assert order_response.status_code == 400
    assert distinct_response.status_code == 400
