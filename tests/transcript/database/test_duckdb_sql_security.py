from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from inspect_ai.model import ChatMessageUser
from inspect_scout._query import Query
from inspect_scout._query.order_by import OrderBy
from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB
from inspect_scout._transcript.types import Transcript


def _minimal_transcript_table(transcript_id: str) -> pa.Table:
    return pa.table(
        {
            "transcript_id": [transcript_id],
            "messages": ["[]"],
            "events": ["[]"],
        }
    )


@pytest.mark.asyncio
async def test_malicious_transcript_filename_is_data(tmp_path: Path) -> None:
    location = tmp_path / "transcripts"
    location.mkdir()
    marker = tmp_path / "transcript-marker.txt"

    pq.write_table(_minimal_transcript_table("normal"), location / "a.parquet")
    pq.write_table(_minimal_transcript_table("companion"), location / "z")

    escaped_marker = str(marker).replace("\\", "\\\\").replace("/", "\\x2f")
    malicious_name = (
        "z']); "
        f"COPY (SELECT 'INJECTED') TO E'{escaped_marker}' "
        "(HEADER false); --.parquet"
    )
    pq.write_table(
        _minimal_transcript_table("malicious-name"),
        location / malicious_name,
    )

    db = ParquetTranscriptsDB(str(location), read_only=True)
    await db.connect()
    try:
        assert await db.count(Query()) == 2
        assert {item.transcript_id async for item in db.select()} == {
            "normal",
            "malicious-name",
        }
        assert len([item async for item in db.select(Query(shuffle=7))]) == 2
        assert db._conn is not None
        with pytest.raises(duckdb.PermissionException):
            db._conn.execute("COPY (SELECT 1) TO ?", [str(marker)])
    finally:
        await db.disconnect()

    assert not marker.exists()


@pytest.mark.asyncio
async def test_metacharacter_database_path_and_index_round_trip(
    tmp_path: Path,
) -> None:
    location = tmp_path / "db'; --"
    db = ParquetTranscriptsDB(str(location))
    await db.connect()
    await db.insert(
        [
            Transcript(
                transcript_id="indexed",
                source_type="test",
                source_id="source",
                source_uri="test://source",
                metadata={'custom"; column': "value"},
                messages=[ChatMessageUser(content="fixture")],
                events=[],
            )
        ]
    )
    await db.disconnect()

    read_db = ParquetTranscriptsDB(str(location), read_only=True)
    await read_db.connect()
    try:
        assert await read_db.count(Query()) == 1
        assert await read_db.distinct('custom"; column', None) == ["value"]
        assert (
            len(
                [
                    item
                    async for item in read_db.select(
                        Query(order_by=[OrderBy('custom"; column', "ASC")])
                    )
                ]
            )
            == 1
        )
    finally:
        await read_db.disconnect()
