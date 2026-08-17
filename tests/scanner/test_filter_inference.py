"""Tests for automatic filter inference from type annotations."""

from collections.abc import AsyncIterator, Callable
from typing import Any

import pytest
from inspect_ai._util.registry import registry_info
from inspect_ai.event._event import Event
from inspect_ai.event._model import ModelEvent
from inspect_ai.event._tool import ToolEvent
from inspect_ai.model._chat_message import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageUser,
)
from inspect_scout import Result, Scanner, Transcript, scanner
from inspect_scout._scanner.scanner import SCANNER_CONFIG
from inspect_scout._scanner.validate import infer_filters_from_type


def test_infer_single_message_type() -> None:
    """Scanner with specific message type should infer filter."""

    @scanner()  # No explicit messages filter
    def user_scanner() -> Scanner[ChatMessageUser]:
        async def scan(message: ChatMessageUser) -> Result:
            return Result(value={"text": message.text})

        return scan

    instance: Any = user_scanner()
    assert registry_info(instance).metadata[SCANNER_CONFIG].content.messages == ["user"]


def test_infer_union_message_types() -> None:
    """Scanner with union of message types should infer filters."""

    @scanner()  # No explicit filters
    def multi_scanner() -> Scanner[ChatMessageSystem | ChatMessageUser]:
        async def scan(message: ChatMessageSystem | ChatMessageUser) -> Result:
            return Result(value={"role": message.role})

        return scan

    instance: Any = multi_scanner()
    assert set(registry_info(instance).metadata[SCANNER_CONFIG].content.messages) == {
        "system",
        "user",
    }


def test_infer_assistant_type() -> None:
    """Scanner with assistant type should infer filter."""

    @scanner()
    def assistant_scanner() -> Scanner[ChatMessageAssistant]:
        async def scan(message: ChatMessageAssistant) -> Result:
            return Result(value={"model": message.model})

        return scan

    instance: Any = assistant_scanner()
    assert registry_info(instance).metadata[SCANNER_CONFIG].content.messages == [
        "assistant"
    ]


def test_infer_list_message_type() -> None:
    """Scanner with list of specific message type should infer filter."""

    @scanner()
    def batch_scanner() -> Scanner[list[ChatMessageAssistant]]:
        async def scan(messages: list[ChatMessageAssistant]) -> Result:
            return Result(value={"count": len(messages)})

        return scan

    instance: Any = batch_scanner()
    assert registry_info(instance).metadata[SCANNER_CONFIG].content.messages == [
        "assistant"
    ]


def test_infer_event_type() -> None:
    """Scanner with specific event type should infer filter."""

    @scanner()
    def model_scanner() -> Scanner[ModelEvent]:
        async def scan(event: ModelEvent) -> Result:
            return Result(value={"model": event.model})

        return scan

    instance: Any = model_scanner()
    assert registry_info(instance).metadata[SCANNER_CONFIG].content.events == ["model"]


def test_infer_union_event_types() -> None:
    """Scanner with union of event types should infer filters."""

    @scanner()
    def event_scanner() -> Scanner[ModelEvent | ToolEvent]:
        async def scan(event: ModelEvent | ToolEvent) -> Result:
            return Result(value={"event": event.event})

        return scan

    instance: Any = event_scanner()
    assert set(registry_info(instance).metadata[SCANNER_CONFIG].content.events) == {
        "model",
        "tool",
    }


def test_no_inference_for_base_message_type() -> None:
    """Scanner with base ChatMessage type should require explicit filter."""
    with pytest.raises(ValueError, match="requires at least one of"):

        @scanner()  # No filter, can't infer from base type
        def base_scanner() -> Scanner[ChatMessage]:
            async def scan(message: ChatMessage) -> Result:
                return Result(value={"role": message.role})

            return scan

        base_scanner()


def test_no_inference_for_transcript() -> None:
    """Scanner with Transcript type should require explicit filters."""
    with pytest.raises(ValueError, match="requires at least one of"):

        @scanner()  # No filters, can't infer for Transcript
        def transcript_scanner() -> Scanner[Transcript]:
            async def scan(transcript: Transcript) -> Result:
                return Result(value={"id": transcript.transcript_id})

            return scan

        transcript_scanner()


def test_explicit_filter_overrides_inference() -> None:
    """Explicit filter should take precedence over type inference."""

    @scanner(messages=["system"])  # Explicit filter
    def explicit_scanner() -> Scanner[ChatMessageSystem]:  # Must match filter
        async def scan(message: ChatMessageSystem) -> Result:
            return Result(value={"text": message.text})

        return scan

    instance: Any = explicit_scanner()
    # Should use explicit filter (no inference needed)
    assert registry_info(instance).metadata[SCANNER_CONFIG].content.messages == [
        "system"
    ]


def test_inference_with_custom_name() -> None:
    """Filter inference should work with custom scanner name."""

    @scanner(name="custom_inferred")
    def named_scanner() -> Scanner[ChatMessageAssistant]:
        async def scan(message: ChatMessageAssistant) -> Result:
            return Result(value={"model": message.model})

        return scan

    instance: Any = named_scanner()
    assert registry_info(instance).name == "custom_inferred"
    assert registry_info(instance).metadata[SCANNER_CONFIG].content.messages == [
        "assistant"
    ]


def test_inference_with_factory_pattern() -> None:
    """Filter inference should work with factory pattern."""

    @scanner()
    def parameterized_scanner(threshold: int = 10) -> Scanner[ChatMessageAssistant]:
        async def scan(message: ChatMessageAssistant) -> Result:
            if len(message.text) > threshold:
                return Result(value={"long": True})
            return Result(value={"short": True})

        return scan

    instance: Any = parameterized_scanner(threshold=5)
    assert registry_info(instance).metadata[SCANNER_CONFIG].content.messages == [
        "assistant"
    ]


def test_no_inference_with_loader() -> None:
    """No filter inference when loader is provided."""
    from inspect_scout import loader

    @loader(name="test_loader", messages="all")  # type: ignore[arg-type]
    def test_loader() -> Callable[[Transcript], AsyncIterator[Transcript]]:
        async def load(transcripts: Transcript) -> AsyncIterator[Transcript]:
            yield transcripts

        return load

    loader_instance: Any = test_loader()

    # Should work without filters when loader is provided
    @scanner(loader=loader_instance)
    def loader_scanner() -> Scanner[Transcript]:
        async def scan(transcript: Transcript) -> Result:
            return Result(value={"id": transcript.transcript_id})

        return scan

    instance: Any = loader_scanner()
    assert registry_info(instance).metadata[SCANNER_CONFIG].loader
    # No messages or events should be inferred
    assert registry_info(instance).metadata[SCANNER_CONFIG].content.messages is None
    assert registry_info(instance).metadata[SCANNER_CONFIG].content.messages is None


def test_no_inference_with_mixed_message_event_union() -> None:
    """Scanner with union of messages and events should require explicit filters or Transcript."""
    with pytest.raises(ValueError, match="requires at least one of"):

        @scanner()  # Can't infer when mixing messages and events
        def mixed_scanner() -> Scanner[ChatMessageUser | ModelEvent]:
            async def scan(item: ChatMessageUser | ModelEvent) -> Result:
                if isinstance(item, ChatMessageUser):
                    return Result(value={"type": "message", "content": item.text})
                else:
                    return Result(value={"type": "event", "model": item.model})

            return scan

        mixed_scanner()


def test_no_inference_without_type_hints() -> None:
    """Scanner without type hints should require explicit filters."""
    with pytest.raises(ValueError, match="requires at least one of"):

        @scanner()
        def untyped_scanner() -> Callable[[Any], Any]:
            async def scan(message):  # type: ignore[no-untyped-def]  # No type annotation
                return Result(value={"ok": True})

            return scan

        untyped_scanner()


def test_decorator_without_parentheses() -> None:
    """Scanner decorator can be used without parentheses when types can be inferred."""

    @scanner  # No parentheses!
    def user_scanner() -> Scanner[ChatMessageUser]:
        async def scan(message: ChatMessageUser) -> Result:
            return Result(value={"text": message.text})

        return scan

    instance: Any = user_scanner()
    assert registry_info(instance).metadata[SCANNER_CONFIG].content.messages == ["user"]


def test_decorator_without_parentheses_with_union() -> None:
    """Scanner decorator without parentheses works with union types."""

    @scanner  # No parentheses!
    def multi_scanner() -> Scanner[ChatMessageSystem | ChatMessageUser]:
        async def scan(message: ChatMessageSystem | ChatMessageUser) -> Result:
            return Result(value={"role": message.role})

        return scan

    instance: Any = multi_scanner()
    assert set(registry_info(instance).metadata[SCANNER_CONFIG].content.messages) == {
        "system",
        "user",
    }


def test_infer_timeline_type() -> None:
    """Scanner with Timeline type should infer timeline filter."""
    from inspect_scout._transcript.timeline import Timeline

    @scanner()
    def timeline_scanner() -> Scanner[Timeline]:
        async def scan(timeline: Timeline) -> Result:
            return Result(value={"name": timeline.name})

        return scan

    instance: Any = timeline_scanner()
    config = registry_info(instance).metadata[SCANNER_CONFIG]
    assert config.content.timeline == "all"
    assert config.content.events == "all"


def test_infer_list_timeline_type() -> None:
    """Scanner with list[Timeline] type should infer timeline filter."""
    from inspect_scout._transcript.timeline import Timeline

    @scanner()
    def timeline_list_scanner() -> Scanner[list[Timeline]]:
        async def scan(timelines: list[Timeline]) -> Result:
            return Result(value={"count": len(timelines)})

        return scan

    instance: Any = timeline_list_scanner()
    config = registry_info(instance).metadata[SCANNER_CONFIG]
    assert config.content.timeline == "all"
    assert config.content.events == "all"


def test_decorator_without_parentheses_fails_for_base_type() -> None:
    """Scanner decorator without parentheses should fail for base ChatMessage type."""
    with pytest.raises(ValueError, match="requires at least one of"):

        @scanner  # No parentheses, but base type needs explicit filter
        def base_scanner() -> Scanner[ChatMessage]:
            async def scan(message: ChatMessage) -> Result:
                return Result(value={"role": message.role})

            return scan

        base_scanner()


def test_infer_newly_filterable_event_types() -> None:
    """Event types added to the filter enum should infer like any other."""
    from inspect_ai.event._score_edit import ScoreEditEvent

    @scanner()
    def score_edit_scanner() -> Scanner[ScoreEditEvent]:
        async def scan(event: ScoreEditEvent) -> Result:
            return Result(value={"name": event.score_name})

        return scan

    instance: Any = score_edit_scanner()
    assert registry_info(instance).metadata[SCANNER_CONFIG].content.events == [
        "score_edit"
    ]


def test_unmapped_event_type_raises() -> None:
    """An Event with no filter mapping must fail loudly, not scan zero events."""
    from inspect_ai.event._subtask import SubtaskEvent

    with pytest.raises(TypeError, match="no corresponding events filter"):

        @scanner()
        def subtask_scanner() -> Scanner[SubtaskEvent]:
            async def scan(event: SubtaskEvent) -> Result:
                return Result(value={"name": event.name})

            return scan

        subtask_scanner()


@pytest.mark.parametrize(
    "annotation",
    [
        pytest.param(Event, id="bare-event"),
        pytest.param(Event | None, id="optional-event"),
        pytest.param(ChatMessageUser | Event, id="message-or-event"),
    ],
)
def test_full_event_union_infers_no_filter(annotation: Any) -> None:
    """`Event` is a Union alias, so these flatten to every concrete event type.

    They name the base type rather than a selection, and inference declines
    base types. Without this, their deprecated StepEvent/SubtaskEvent members
    trip the unmapped-type check, replacing the loader's own diagnostic with a
    misleading one. See `test_full_event_union_still_rejected_by_loader` for
    what these annotations actually do end to end.
    """

    def scan(value: Any) -> None: ...

    scan.__annotations__ = {"value": annotation}
    assert infer_filters_from_type(scan, globals()) == (None, None, False)


@pytest.mark.parametrize(
    "annotation",
    [
        pytest.param(Event | None, id="optional-event"),
        pytest.param(ChatMessageUser | Event, id="message-or-event"),
    ],
)
def test_full_event_union_still_rejected_by_loader(annotation: Any) -> None:
    """Declining inference is not the same as supporting the annotation.

    These were rejected before the EventType widening too. The loader cannot
    route a union spanning both input kinds (or one including None), and that
    is the error the author should see -- not a complaint about the deprecated
    event types the alias happens to contain.
    """

    def factory() -> Any:
        async def scan(value: Any) -> Result:
            return Result(value={})

        scan.__annotations__ = {"value": annotation, "return": Result}
        return scan

    factory.__annotations__ = {"return": Scanner[annotation]}

    # With an explicit events= filter, inference is bypassed entirely and the
    # loader rejects the union either way -- that path cannot tell a working
    # _spans_event_union from a broken one. Without a filter it can: declining
    # inference yields the "requires at least one of" error, while the
    # unmapped-type check would raise about StepEvent/SubtaskEvent instead.
    with pytest.raises(ValueError, match="requires at least one of"):
        scanner()(factory)()
    with pytest.raises(RuntimeError, match="must conform to ChatMessage or Event"):
        scanner(events="all")(factory)()
