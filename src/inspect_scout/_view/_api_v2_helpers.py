from collections.abc import Callable
from typing import Any, Literal

from .._transcript.types import TranscriptInfo
from ._api_v2_types import OrderBy, Pagination


def _make_sort_key(
    column: str,
) -> Callable[[TranscriptInfo], str | int | float | bool]:
    """Create a sort key function for the given column name.

    Args:
        column: Name of the attribute to sort by

    Returns:
        A function that extracts the sort key from a TranscriptInfo
    """

    def sort_key(t: TranscriptInfo) -> str | int | float | bool:
        val = getattr(t, column, "")
        return val if val is not None else ""

    return sort_key


def _sort_transcripts(
    transcripts: list[TranscriptInfo], order_by: OrderBy | list[OrderBy]
) -> None:
    """Sort transcripts in-place by one or more columns.

    Uses stable sort with reverse column order to handle multi-column sorting.
    Missing/None values are treated as empty strings for sorting.

    Args:
        transcripts: List of transcripts to sort in-place
        order_by: Single OrderBy or list of OrderBy specifications
    """
    order_bys = order_by if isinstance(order_by, list) else [order_by]

    # Sort in reverse order of columns to handle multi-column sorting. Python's
    # sort is stable, so sorting by secondary keys first, then primary keys last
    # produces correct multi-column ordering. E.g., for [model ASC, score DESC]:
    # first sort by score DESC, then sort by model ASC (stable sort preserves score
    # order within each model group).
    for order_by_spec in reversed(order_bys):
        transcripts.sort(
            key=_make_sort_key(order_by_spec.column),
            reverse=(order_by_spec.direction == "desc"),
        )


def _ensure_tiebreaker(
    order_by: OrderBy | list[OrderBy] | None,
) -> list[tuple[str, Literal["asc", "desc"]]]:
    """Ensure sort order has transcript_id as final tiebreaker.

    Returns list of (column, direction) tuples.
    If order_by is None, returns [("transcript_id", "asc")].
    If transcript_id already in sort, don't add duplicate.
    """
    if order_by is None:
        return [("transcript_id", "asc")]

    order_bys = order_by if isinstance(order_by, list) else [order_by]
    columns = [(ob.column, ob.direction) for ob in order_bys]

    if any(col == "transcript_id" for col, _ in columns):
        return columns

    return columns + [("transcript_id", "asc")]


def _compare_to_cursor(
    transcript: TranscriptInfo,
    cursor: dict[str, Any],
    order_columns: list[tuple[str, Literal["asc", "desc"]]],
    direction: Literal["forward", "backward"],
) -> bool:
    """Check if transcript should be included based on cursor comparison.

    Uses lexicographic comparison on sort columns.
    Returns True if transcript comes after cursor (forward) or before (backward).
    """
    for column, sort_dir in order_columns:
        cursor_val = cursor.get(column)
        transcript_val = getattr(transcript, column, None)

        # Normalize None to empty string (matches sort behavior)
        cursor_val = "" if cursor_val is None else cursor_val
        transcript_val = "" if transcript_val is None else transcript_val

        if transcript_val == cursor_val:
            continue

        is_greater = transcript_val > cursor_val
        want_greater = (direction == "forward" and sort_dir == "asc") or (
            direction == "backward" and sort_dir == "desc"
        )

        return is_greater if want_greater else not is_greater

    # All columns equal - same row as cursor, exclude
    return False


def _apply_cursor_pagination(
    transcripts: list[TranscriptInfo],
    pagination: Pagination,
    order_columns: list[tuple[str, Literal["asc", "desc"]]],
) -> list[TranscriptInfo]:
    """Apply cursor-based pagination to sorted transcripts.

    Args:
        transcripts: Already sorted list
        pagination: Contains cursor, limit, direction
        order_columns: Sort order as (column, direction) tuples

    Returns:
        Paginated slice of transcripts
    """
    if not pagination.cursor:
        # First page
        if pagination.direction == "forward":
            return transcripts[: pagination.limit]
        else:
            return transcripts[-pagination.limit :]

    # Find rows matching cursor condition
    filtered: list[TranscriptInfo] = []
    for transcript in transcripts:
        if _compare_to_cursor(
            transcript, pagination.cursor, order_columns, pagination.direction
        ):
            filtered.append(transcript)
            if len(filtered) >= pagination.limit:
                break

    return filtered


def _build_cursor(
    transcript: TranscriptInfo,
    order_columns: list[tuple[str, Literal["asc", "desc"]]],
) -> dict[str, Any]:
    """Build cursor from transcript using sort columns."""
    cursor: dict[str, Any] = {}
    for column, _ in order_columns:
        cursor[column] = getattr(transcript, column, None)
    return cursor


def _has_more_results(
    all_results: list[TranscriptInfo],
    paginated: list[TranscriptInfo],
    pagination: Pagination,
) -> bool:
    """Check if more results exist beyond current page."""
    if not paginated or len(paginated) < pagination.limit:
        return False

    if pagination.direction == "forward":
        last_item = paginated[-1]
        last_idx = all_results.index(last_item)
        return last_idx < len(all_results) - 1
    else:
        first_item = paginated[0]
        first_idx = all_results.index(first_item)
        return first_idx > 0
