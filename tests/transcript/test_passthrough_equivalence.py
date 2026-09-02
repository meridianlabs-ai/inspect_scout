"""Passthrough output expands to the same transcript `load()` produces."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest
from inspect_ai.log import expand_events
from inspect_ai.model import ChatMessage
from inspect_scout._transcript.handle import SpooledTranscriptHandle
from inspect_scout._transcript.json.passthrough import pooled_passthrough
from inspect_scout._transcript.json.stream_parse import stream_parse_to_spool
from inspect_scout._transcript.types import Transcript, TranscriptInfo
from pydantic import TypeAdapter

_CHAT_MESSAGE_ADAPTER: TypeAdapter[ChatMessage] = TypeAdapter(ChatMessage)


def _sample_bytes() -> bytes:
    """A sample with pooled model inputs and attachment refs.

    Three pooled messages, but the event references only the last one
    (position [2, 3)) -- pruning must drop positions 0-1 and the surviving
    ref must remap 2 -> 0. Each pooled message has clearly distinct content
    so a wrong remap surfaces as a content mismatch, not just a structural
    one (Task 2's tests already cover the raw-ref-level remap; this checks
    remapped refs expand back to the *right* content).

    The unthinned fields (`metadata`, `target`, `scores`) are here because the
    passthrough splices them with its own `_merged_metadata` rather than
    `handle._merge_unthinned`; `1e-07` renders differently under stdlib json
    and pydantic, so it pins that the difference stays textual.
    """
    att = "b" * 32
    top_att = "c" * 32
    return json.dumps(
        {
            "id": "t1",
            "metadata": {"cost": 1e-07, "note": "sample metadata"},
            "target": "the-target",
            "scores": {"accuracy": {"value": 1.0}},
            "messages": [
                {"id": "m1", "role": "user", "content": f"attachment://{top_att}"}
            ],
            "events": [
                {
                    "event": "model",
                    "timestamp": 1.0,
                    "uuid": "u1",
                    "working_start": 100.0,
                    "model": "test-model",
                    "input": [],
                    "input_refs": [[2, 3]],
                    "tools": [],
                    "tool_choice": "none",
                    "config": {},
                    "output": {},
                }
            ],
            "events_data": {
                "messages": [
                    {"id": "sys0", "role": "system", "content": "pool entry zero"},
                    {"id": "sys1", "role": "system", "content": "pool entry one"},
                    {
                        "id": "sys2",
                        "role": "system",
                        "content": f"attachment://{att}",
                    },
                ],
                "calls": [],
            },
            "attachments": {
                att: "expanded system prompt",
                top_att: "expanded user content",
            },
        }
    ).encode()


def _resolve_attachments(value: Any, attachments: dict[str, str]) -> Any:
    """Mirror the viewer's client-side attachment resolution."""
    if isinstance(value, str):
        for att_id, content in attachments.items():
            value = value.replace(f"attachment://{att_id}", content)
        return value
    if isinstance(value, list):
        return [_resolve_attachments(v, attachments) for v in value]
    if isinstance(value, dict):
        return {k: _resolve_attachments(v, attachments) for k, v in value.items()}
    return value


@pytest.mark.asyncio
async def test_passthrough_expands_to_the_materialized_transcript(
    tmp_path: Path,
) -> None:
    data = _sample_bytes()
    info = TranscriptInfo(transcript_id="t1")

    result = await stream_parse_to_spool(io.BytesIO(data), "all", "all", tmp_path)
    try:
        input_json, input_data_json = pooled_passthrough(info, result)
    finally:
        result.close()

    # Independently produce the materialized transcript for comparison.
    parsed_result = await stream_parse_to_spool(
        io.BytesIO(data), "all", "all", tmp_path
    )

    async def parse() -> Any:
        return parsed_result

    async def fallback() -> Transcript:
        raise AssertionError("fallback should not be called")

    handle = SpooledTranscriptHandle(info, parse, fallback)
    try:
        materialized = await handle.load()
    finally:
        await handle.aclose()

    envelope = json.loads(input_json)
    assert input_data_json is not None
    data_obj = json.loads(input_data_json)

    expanded = expand_events(json.dumps(envelope["events"]), input_data_json.decode())
    resolved = _resolve_attachments(
        [e.model_dump(mode="json") for e in expanded], data_obj["attachments"]
    )

    assert resolved == [e.model_dump(mode="json") for e in materialized.events]

    resolved_messages = _resolve_attachments(
        envelope["messages"], data_obj["attachments"]
    )
    assert [
        _CHAT_MESSAGE_ADAPTER.validate_python(m).model_dump(mode="json")
        for m in resolved_messages
    ] == [m.model_dump(mode="json") for m in materialized.messages]

    assert envelope["metadata"] == materialized.metadata
