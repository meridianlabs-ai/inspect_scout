"""Message IDs assigned across an imported trace's model calls."""

import time

import pytest
from inspect_ai.model import ChatMessageUser
from inspect_scout.sources._message_ids import TraceMessageIds


@pytest.mark.slow
def test_many_equal_messages_in_one_conversation_take_linear_time() -> None:
    # A gross-regression budget, not a benchmark: this takes about 0.3s on a
    # laptop, while the quadratic matching it replaced took over 10s.
    messages = [ChatMessageUser(content="same") for _ in range(50_000)]

    start = time.perf_counter()
    TraceMessageIds().apply_messages(messages, "call")
    elapsed = time.perf_counter() - start

    assert elapsed < 3
    assert len({m.id for m in messages}) == len(messages)
