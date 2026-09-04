"""`JsonTextWriter` re-serializes ijson events exactly as json.dumps would.

This sits under every spooled transcript's metadata, so a divergence here
silently changes recorded data. The contract asserted is byte equality with
`json.dumps(value, ensure_ascii=False, separators=(",", ":"))`.
"""

from __future__ import annotations

import io
import json
from typing import Any

import ijson  # type: ignore[import-untyped]  # no published stubs
import pytest
from inspect_scout._transcript.json.reducer import JsonTextWriter

VALUES: list[Any] = [
    pytest.param({"nested": {"deep": {"deeper": [1, 2, {"x": None}]}}}, id="nested"),
    pytest.param({"t": True, "f": False, "n": None}, id="literals"),
    pytest.param({"i": 0, "neg": -17, "big": 2**53 + 1}, id="integers"),
    pytest.param({"f": 1.5, "e": 1e-7, "neg": -0.0}, id="floats"),
    pytest.param({"unicode": "héllo 你好 🎉"}, id="unicode"),
    pytest.param({"escapes": 'quote" back\\slash\nnewline\ttab'}, id="escapes"),
    pytest.param({"control": "\x00\x1f"}, id="control-chars"),
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
