"""Arrow conversion of the pre-serialized `input`/`input_data` columns.

`_serialize_input` emits UTF-8 JSON buffers rather than `str`; these pin that
the buffers reach a real string column, and that no other column takes the
passthrough — arbitrary metadata can be bytes pyarrow refuses to decode.
"""

from typing import Any

import pyarrow as pa
import pytest
from inspect_scout._recorder.buffer import _records_to_arrow

BufferType = type[bytes] | type[bytearray]


@pytest.mark.parametrize("buffer_type", [bytes, bytearray], ids=["bytes", "bytearray"])
@pytest.mark.parametrize(
    "template",
    [
        pytest.param([b'{"a":1}', b'{"a":2}'], id="all-buffers"),
        pytest.param([b'{"a":1}', '{"a":2}'], id="buffer-and-str"),
        pytest.param([b'{"a":1}', None], id="buffer-and-null"),
    ],
)
def test_bytes_columns_become_string_columns(
    buffer_type: BufferType, template: list[Any]
) -> None:
    values = [buffer_type(v) if isinstance(v, bytes) else v for v in template]

    table = _records_to_arrow([{"input": value} for value in values])

    assert table.schema.field("input").type == pa.large_string()
    assert table.column("input").to_pylist() == [
        value.decode() if isinstance(value, (bytes, bytearray)) else value
        for value in values
    ]


@pytest.mark.parametrize("buffer_type", [bytes, bytearray], ids=["bytes", "bytearray"])
def test_bytes_column_preserves_non_ascii(buffer_type: BufferType) -> None:
    """The bytes are UTF-8; decoding must happen, not a repr()."""
    encoded = buffer_type('{"text":"héllo 你好"}'.encode())

    table = _records_to_arrow([{"input": encoded}])

    assert table.column("input").to_pylist() == ['{"text":"héllo 你好"}']


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(b'{"a":1}', '"{\\"a\\":1}"', id="utf8-json-encoded"),
        pytest.param(b"\xff", "b'\\xff'", id="non-utf8-stringified"),
    ],
)
def test_other_columns_keep_the_json_encode_fallback(
    value: bytes, expected: str
) -> None:
    """Metadata columns hold arbitrary eval-log bytes, not pre-serialized JSON.

    Passing those through would turn a non-UTF-8 value into an `ArrowInvalid`
    that aborts the whole recording.
    """
    table = _records_to_arrow([{"transcript_date": value}])

    assert table.column("transcript_date").to_pylist() == [expected]


def test_mixed_column_decodes_buffers_instead_of_repring_them() -> None:
    """Latent today: `input` is uniformly bytes-or-None per recorded batch.

    `str()` in the mixed-column fallback would put a b'...' repr in a public
    results column.
    """
    table = _records_to_arrow([{"input": b'{"a":1}'}, {"input": 3}])

    assert table.column("input").to_pylist() == ['{"a":1}', "3"]
