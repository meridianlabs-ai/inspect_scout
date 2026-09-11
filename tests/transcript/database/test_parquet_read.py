from pathlib import Path

import pytest
from inspect_ai.model import ChatMessageUser
from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB
from inspect_scout._transcript.types import (
    Transcript,
    TranscriptContent,
    TranscriptInfo,
)

EXPLANATION = "graded C because the tests failed"


def _info_fields(t: TranscriptInfo) -> dict[str, object]:
    return {name: getattr(t, name) for name in TranscriptInfo.model_fields}


@pytest.mark.asyncio
async def test_read_carries_every_info_field_the_index_holds(tmp_path: Path) -> None:
    """A read must return the same `TranscriptInfo` fields `select()` yielded.

    The no-content path builds its `Transcript` from the info field by field,
    so a field added to the model is silently dropped there until it is added
    to that copy too. `score_explanation` is the value the index holds today
    that the copy lost.
    """
    location = tmp_path / "db"
    db = ParquetTranscriptsDB(str(location))
    await db.connect()
    await db.insert(
        [
            Transcript(
                transcript_id="t1",
                source_type="test",
                source_id="source",
                source_uri="test://source",
                score="C",
                score_explanation=EXPLANATION,
                messages=[ChatMessageUser(content="hi")],
                events=[],
            )
        ]
    )
    await db.disconnect()

    read_db = ParquetTranscriptsDB(str(location), read_only=True)
    await read_db.connect()
    try:
        infos = [info async for info in read_db.select()]
        assert len(infos) == 1
        info = infos[0]
        assert info.score_explanation == EXPLANATION

        without_content = await read_db.read(info, TranscriptContent())
        assert _info_fields(without_content) == _info_fields(info)
        assert without_content.messages == []

        with_content = await read_db.read(info, TranscriptContent(messages="all"))
        assert _info_fields(with_content) == _info_fields(info)
        assert len(with_content.messages) == 1
    finally:
        await read_db.disconnect()
