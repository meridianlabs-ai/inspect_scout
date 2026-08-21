"""`JsonTextWriter` re-serializes ijson events exactly as json.dumps would.

This sits under every spooled transcript's metadata, so a divergence here
silently changes recorded data. The contract asserted is byte equality with
`json.dumps(value, ensure_ascii=False, separators=(",", ":"))`.
"""

from __future__ import annotations

import io
import json
from typing import Any

import ijson  # type: ignore
import pytest
from inspect_scout._transcript.json.reducer import JsonTextWriter

VALUES: list[Any] = [
    pytest.param({}, id="empty-object"),
    pytest.param([], id="empty-array"),
    pytest.param({"k": "v"}, id="flat"),
    pytest.param({"a": 1, "b": 2, "c": 3}, id="several-keys"),
    pytest.param({"nested": {"deep": {"deeper": [1, 2, {"x": None}]}}}, id="nested"),
    pytest.param({"list": [[], {}, [[]], [{}]]}, id="empty-containers-nested"),
    pytest.param({"t": True, "f": False, "n": None}, id="literals"),
    pytest.param({"i": 0, "neg": -17, "big": 2**53 + 1}, id="integers"),
    pytest.param({"f": 1.5, "e": 1e-7, "neg": -0.0}, id="floats"),
    pytest.param({"unicode": "héllo 你好 🎉"}, id="unicode"),
    pytest.param({"escapes": 'quote" back\\slash\nnewline\ttab'}, id="escapes"),
    pytest.param({"control": "\x00\x1f"}, id="control-chars"),
    pytest.param({"empty-key": "", "": "empty"}, id="empty-strings"),
    pytest.param({"attachment": "attachment://" + "a" * 32}, id="attachment-ref"),
    pytest.param({"arr": [{"a": [1, [2, [3]]]}, "x"]}, id="mixed-depth"),
]


def _rewrite(value: Any) -> bytes:
    """Round-trip `value` through ijson events and back out as JSON text."""
    out = io.BytesIO()
    writer = JsonTextWriter(out.write)
    source = json.dumps(value).encode()
    for _prefix, event, event_value in ijson.parse(io.BytesIO(source), use_float=True):
        writer.event(event, event_value)
    return out.getvalue()


@pytest.mark.parametrize("value", VALUES)
def test_matches_json_dumps_byte_for_byte(value: Any) -> None:
    expected = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    assert _rewrite(value).decode() == expected


@pytest.mark.parametrize("value", VALUES)
def test_round_trips_to_an_equal_value(value: Any) -> None:
    assert json.loads(_rewrite(value)) == value


def test_duplicate_keys_resolve_as_json_does() -> None:
    """Both are reported by ijson; last one wins on reparse, as in json."""
    out = io.BytesIO()
    writer = JsonTextWriter(out.write)
    for _prefix, event, value in ijson.parse(
        io.BytesIO(b'{"k":1,"k":2}'), use_float=True
    ):
        writer.event(event, value)
    assert json.loads(out.getvalue()) == {"k": 2}
