"""Values used to restore metrics retain their types across buffer storage."""

from pathlib import Path

import pytest
from inspect_ai.model import ChatMessageUser
from inspect_scout import Result
from inspect_scout._recorder.file import FileRecorder
from inspect_scout._scanner.result import ResultReport
from inspect_scout._scanspec import ScannerSpec, ScanSpec
from inspect_scout._transcript.types import TranscriptInfo
from pydantic import JsonValue


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "values",
    [
        [0, 1],
        [True, False],
        [None, 1, True, "1", "true", [0, 1], {"score": 0.5}],
    ],
)
async def test_recorded_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, values: list[JsonValue]
) -> None:
    monkeypatch.setenv("SCOUT_SCANBUFFER_DIR", str(tmp_path / "buffer"))
    recorder = FileRecorder()
    await recorder.init(
        ScanSpec(scan_name="values", scanners={"test": ScannerSpec(name="test")}),
        str(tmp_path / "scans"),
    )
    await recorder.record(
        TranscriptInfo(
            transcript_id="t1",
            source_type="test",
            source_id="src",
            source_uri="test://t1",
        ),
        "test",
        [
            ResultReport(
                input_type="message",
                input_ids=[],
                input=ChatMessageUser(content=""),
                result=Result(value=value),
                validation=None,
                error=None,
                events=[],
                model_usage={},
            )
            for value in values
        ],
        None,
    )
    # Reopen without syncing: an interrupted scan may only have buffered results.
    resumed = FileRecorder()
    await resumed.resume(await recorder.location())
    assert await resumed.is_recorded("t1", "test")
    restored = await resumed.recorded_values("t1", "test")
    assert restored == values
    assert [type(value) for value in restored] == [type(value) for value in values]
