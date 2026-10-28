"""Pool repeated model event inputs and calls without merging message IDs."""

from collections.abc import Sequence

import mmh3
from inspect_ai.event import Event, ModelEvent
from inspect_ai.event._pool import _compress_refs, condense_model_event_calls
from inspect_ai.log import EventsData
from inspect_ai.model import ChatMessage


def condense_events(events: Sequence[Event]) -> tuple[list[Event], EventsData]:
    """De-duplicate repeated model event inputs and calls into shared pools.

    The same as `inspect_ai.log.condense_events`, except that two input
    messages are pooled together only if their IDs match as well as their
    content. Imported transcripts give equal-content messages distinct IDs
    (a message sent twice, a reply given twice), and inspect_ai's pool
    ignores IDs before inspect_ai#6143, so each copy would read back with
    the first one's ID. The result reads back with `expand_events`.

    TODO: use `inspect_ai.log.condense_events` once the inspect_ai floor
    includes inspect_ai#6143.

    Args:
        events: Events to condense.

    Returns:
        The condensed events, and the message and call pools.
    """
    message_pool: list[ChatMessage] = []
    index: dict[str, int] = {}
    by_object: dict[int, int] = {}
    condensed: list[Event] = []
    for event in events:
        if isinstance(event, ModelEvent) and event.input:
            refs: list[int] = []
            for message in event.input:
                position = by_object.get(id(message))
                if position is None:
                    key = mmh3.hash_bytes(message.model_dump_json().encode()).hex()
                    position = index.setdefault(key, len(message_pool))
                    if position == len(message_pool):
                        message_pool.append(message)
                    by_object[id(message)] = position
                refs.append(position)
            event = event.model_copy(
                update={"input": [], "input_refs": _compress_refs(refs)}
            )
        condensed.append(event)
    condensed, _, calls = condense_model_event_calls(condensed, 0, {})
    return condensed, EventsData(
        messages=message_pool, calls=[call for _, call in calls]
    )
