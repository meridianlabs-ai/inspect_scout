"""Message IDs assigned across an imported trace's model calls."""

import time

from inspect_ai.model import ChatMessageUser
from inspect_scout.sources._message_ids import TraceMessageIds


def test_many_equal_messages_in_one_conversation_take_linear_time() -> None:
    # Quadratic matching took over 10 seconds for this many.
    messages = [ChatMessageUser(content="same") for _ in range(50_000)]

    start = time.perf_counter()
    TraceMessageIds().apply_messages(messages, "call")
    elapsed = time.perf_counter() - start

    assert elapsed < 3
    assert len({m.id for m in messages}) == len(messages)
