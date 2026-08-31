"""Shared ``TimelineSpan``/``ModelEvent`` test builders.

Also duplicated verbatim in ``tests/transcript/test_timeline_interleave.py``
(its local helpers) -- that file intentionally keeps its own copies rather
than importing from here, so an edit in either place does not propagate.
"""

from __future__ import annotations

from inspect_ai.event import Event, ModelEvent, TimelineEvent, TimelineSpan
from inspect_ai.model import ChatMessage, GenerateConfig, ModelOutput


def _model_event(input_msgs: list[ChatMessage], output: ModelOutput) -> ModelEvent:
    return ModelEvent.model_construct(
        event="model",
        model="mockllm",
        input=list(input_msgs),
        output=output,
        role="assistant",
        config=GenerateConfig(),
    )


def _span(span_id: str, name: str, events: list[Event]) -> TimelineSpan:
    return TimelineSpan(
        id=span_id,
        name=name,
        span_type="agent",
        content=[TimelineEvent.model_construct(type="event", event=e) for e in events],
    )


def _span_of(
    span_id: str,
    name: str,
    content: list[Event | TimelineSpan],
    *,
    span_type: str | None = "agent",
) -> TimelineSpan:
    """Like ``_span`` but accepts a mix of events and nested spans, and a span_type."""
    items: list[TimelineEvent | TimelineSpan] = [
        item
        if isinstance(item, TimelineSpan)
        else TimelineEvent.model_construct(type="event", event=item)
        for item in content
    ]
    return TimelineSpan(id=span_id, name=name, span_type=span_type, content=items)
