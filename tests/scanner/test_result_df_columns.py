"""`ResultReport.to_df_columns` emits the input columns as UTF-8 JSON buffers.

The recorder hands these straight to pyarrow, so the producer must not decode
them to `str` — every branch of `_serialize_input` is covered here, since the
`input_data` split makes it easy to fix one and miss another.
"""

import json
from datetime import datetime
from typing import Any

import pytest
from inspect_ai.event import InfoEvent
from inspect_ai.model._chat_message import ChatMessageUser
from inspect_scout._scanner.result import Result, ResultReport
from inspect_scout._scanner.types import ScannerInput, ScannerInputNames
from inspect_scout._transcript.types import Transcript


def _transcript() -> Transcript:
    return Transcript(
        transcript_id="t1",
        source_type="test",
        source_id="s1",
        source_uri="test://uri",
        messages=[ChatMessageUser(content="héllo")],
        events=[InfoEvent(event="info", timestamp=datetime.now(), data={"a": 1})],
    )


@pytest.mark.parametrize(
    ("input", "input_type", "pool_dedup", "expect_input_data"),
    [
        pytest.param(_transcript(), "transcript", True, True, id="transcript-pooled"),
        pytest.param(
            _transcript(), "transcript", False, False, id="transcript-unpooled"
        ),
        pytest.param(
            [InfoEvent(event="info", timestamp=datetime.now(), data={"a": 1})],
            "events",
            True,
            True,
            id="events-pooled",
        ),
        pytest.param(
            [ChatMessageUser(content="héllo")],
            "messages",
            True,
            False,
            id="messages-never-pooled",
        ),
    ],
)
def test_input_columns_are_utf8_json_buffers(
    input: ScannerInput,
    input_type: ScannerInputNames,
    pool_dedup: bool,
    expect_input_data: bool,
) -> None:
    report = ResultReport(
        input_type=input_type,
        input_ids=["i1"],
        input=input,
        result=Result(value="yes"),
        validation=None,
        error=None,
        events=[],
        model_usage={},
    )

    columns: dict[str, Any] = report.to_df_columns(pool_dedup=pool_dedup)

    assert isinstance(columns["input"], (bytes, bytearray))
    assert json.loads(bytes(columns["input"]))
    if expect_input_data:
        assert isinstance(columns["input_data"], (bytes, bytearray))
        assert json.loads(bytes(columns["input_data"])) is not None
    else:
        assert columns["input_data"] is None
