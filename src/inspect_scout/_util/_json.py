from typing import Any

from inspect_ai._util.json import to_json_safe


def to_json_str_compact(x: Any) -> str:
    """Serialize to JSON without pretty-print whitespace.

    Wraps ``to_json_safe`` (surrogate-safe) with ``indent=None`` and decodes to
    ``str``. Use for machine-read payloads such as stored parquet  columns and
    bytes streamed to the viewer, where the default ``indent=2`` only bloats the
    representation without benefit since the data is never human-consumed.

    In extreme cases, this reduces serialized JSON from 700 MiB -> 200 MiB.
    """
    return to_json_safe(x, indent=None).decode("utf-8")


def to_json_bytes_compact(x: Any) -> bytes:
    """``to_json_str_compact`` without decoding to ``str``.

    Prefer this for values headed straight into a parquet column: pyarrow
    accepts UTF-8 bytes for string columns and would re-encode a ``str``
    anyway. Skipping the decode also avoids a second full copy of the payload,
    at PEP 393's 1, 2, or 4 bytes per character (set by the widest code point
    in the string).
    """
    return to_json_safe(x, indent=None)
