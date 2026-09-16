from typing import Any

from inspect_ai._util.json import to_json_safe


def to_json_bytes_compact(x: Any) -> bytes:
    """Serialize to UTF-8 JSON bytes without pretty-print whitespace.

    Wraps ``to_json_safe`` (surrogate-safe) with ``indent=None``. Use for
    machine-read payloads such as stored parquet columns and bytes streamed to
    the viewer, where the default ``indent=2`` only bloats the representation
    without benefit since the data is never human-consumed.

    In extreme cases, this reduces serialized JSON from 700 MiB -> 200 MiB.
    """
    return to_json_safe(x, indent=None)


def to_json_str_compact(x: Any) -> str:
    """``to_json_bytes_compact`` decoded to ``str``.

    Prefer the bytes form for values headed straight into a parquet column:
    pyarrow accepts UTF-8 bytes for string columns and would re-encode a ``str``
    anyway. The decode also costs a second full copy of the payload, at PEP
    393's 1, 2, or 4 bytes per character (set by the widest code point in the
    string).
    """
    return to_json_bytes_compact(x).decode("utf-8")
