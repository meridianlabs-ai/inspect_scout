"""Shared ``TimelineSpan``/``ModelEvent`` test builders."""

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
    items: list[TimelineEvent | TimelineSpan] = [
        item
        if isinstance(item, TimelineSpan)
        else TimelineEvent.model_construct(type="event", event=item)
        for item in content
    ]
    return TimelineSpan(id=span_id, name=name, span_type=span_type, content=items)
