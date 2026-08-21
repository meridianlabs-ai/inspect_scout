"""Arrow conversion of pre-serialized (bytes) column values.

`_serialize_input` emits the `input`/`input_data` columns as UTF-8 bytes to
avoid materializing a second, wider copy of a large transcript as `str`.
These assert the bytes survive into a real string column.
"""

from __future__ import annotations

from typing import Any

import pyarrow as pa
import pytest
from inspect_scout._recorder.buffer import _records_to_arrow


@pytest.mark.parametrize(
    "values",
    [
        pytest.param([b'{"a":1}', b'{"a":2}'], id="all-bytes"),
        pytest.param([b'{"a":1}', '{"a":2}'], id="bytes-and-str"),
        pytest.param([b'{"a":1}', None], id="bytes-and-null"),
    ],
)
def test_bytes_columns_become_string_columns(values: list[Any]) -> None:
    table = _records_to_arrow([{"input": value} for value in values])

    assert table.schema.field("input").type == pa.large_string()
    assert table.column("input").to_pylist() == [
        value.decode() if isinstance(value, bytes) else value for value in values
    ]


def test_bytes_column_preserves_non_ascii() -> None:
    """The bytes are UTF-8; decoding must happen, not a repr()."""
    payload = {"text": "héllo 你好"}
    encoded = '{"text":"héllo 你好"}'.encode()

    table = _records_to_arrow([{"input": encoded}])

    assert table.column("input").to_pylist() == [encoded.decode()]
    assert table.column("input")[0].as_py() == '{"text":"héllo 你好"}'
    assert payload["text"] in table.column("input")[0].as_py()
