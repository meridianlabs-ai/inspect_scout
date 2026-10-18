"""V3 message/call pool helpers for spool-backed readers.

The materialized load (load_filtered.py) expands pool refs with inspect_ai's
`expand_events` after validation, so events share validated pool entries.
"""

from __future__ import annotations


def slice_positions(start: int, end: int, pool_len: int) -> range:
    """Positions that ``pool[start:end]`` selects from a pool of ``pool_len``.

    Spool-backed callers index by position rather than holding the list, so
    they must enumerate. A bare ``range(start, end)`` is not slicing: it
    addresses the wrong entries for a negative bound and walks the full span
    for a huge one.
    """
    start_index, stop_index, _ = slice(start, end).indices(pool_len)
    return range(start_index, stop_index)
