"""Arrow conversion of the pre-serialized (bytes/bytearray) `input` columns.

`_serialize_input` emits UTF-8 buffers rather than `str`; these pin that the
buffers survive into a real string column, for both buffer types.
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
