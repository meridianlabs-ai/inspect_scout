"""Tests for the scanner decorator functionality."""

import functools
import types
from collections.abc import AsyncIterator, Callable
from typing import Any

import pytest
from inspect_ai._util.registry import registry_info
from inspect_ai.model._chat_message import ChatMessage
from inspect_scout import llm_scanner
from inspect_scout._scanner.result import Result
from inspect_scout._scanner.scanner import (
    SCANNER_CONFIG,
    Scanner,
    mark_streaming_support,
    scanner,
    scanner_supports_streaming,
)
from inspect_scout._transcript.handle import TranscriptHandle
from inspect_scout._transcript.types import Transcript

# Scanner decorator tests


def test_scanner_creates_config() -> None:
    @scanner(messages=["system"])
    def test_scanner() -> Scanner[ChatMessage]:
        async def scan(message: ChatMessage) -> Result:
            return Result(value={"ok": True})

        return scan

    instance = test_scanner()
    config = registry_info(instance).metadata[SCANNER_CONFIG]
    assert registry_info(instance).name == "test_scanner"
    assert config.content.messages == ["system"]


def test_scanner_with_custom_name() -> None:
    """Scanner decorator should accept custom name."""

    @scanner(messages=["user"], name="custom_scanner")
    def test_scanner() -> Scanner[ChatMessage]:
        async def scan(message: ChatMessage) -> Result:
            return Result(value={"ok": True})

        return scan

    instance = test_scanner()
    assert registry_info(instance).name == "custom_scanner"


def test_scanner_with_events() -> None:
    """Scanner decorator should handle event filters."""
    from inspect_ai.event._event import Event

    @scanner(events=["model", "tool"])
    def test_scanner() -> Scanner[Event]:
        async def scan(event: Event) -> Result:
            return Result(value={"event": event.event})

        return scan

    instance = test_scanner()
    assert registry_info(instance).metadata[SCANNER_CONFIG].content.events == [
        "model",
        "tool",
    ]


def test_scanner_with_both_filters() -> None:
    """Scanner decorator should handle both message and event filters."""
    from inspect_scout._transcript.types import Transcript

    @scanner(messages=["user"], events=["model"])
    def test_scanner() -> Scanner[Transcript]:
        async def scan(transcript: Transcript) -> Result:
            return Result(value={"id": transcript.transcript_id})

        return scan

    instance = test_scanner()
    config = registry_info(instance).metadata[SCANNER_CONFIG]
    assert config.content.messages == ["user"]
    assert config.content.events == ["model"]


def test_scanner_requires_async() -> None:
    """Scanner must be async."""
    with pytest.raises(TypeError, match="not declared as an async callable"):

        @scanner(messages=["system"])
        def test_scanner() -> Scanner[ChatMessage]:
            def scan(message: ChatMessage) -> Result:  # Not async!
                return Result(value={"bad": True})

            return scan  # type: ignore[return-value]

        test_scanner()


def test_scanner_requires_at_least_one_filter_or_loader() -> None:
    """Scanner decorator requires at least one filter or loader."""
    with pytest.raises(ValueError, match="requires at least one of"):

        @scanner()  # No filters or loader!
        def test_scanner() -> Scanner[ChatMessage]:
            async def scan(message: ChatMessage) -> Result:
                return Result(value={"bad": True})

            return scan

        test_scanner()


def test_scanner_factory_with_parameters() -> None:
    """Scanner factory can accept parameters."""

    @scanner(messages=["assistant"])
    def parameterized_scanner(threshold: int = 10) -> Scanner[ChatMessage]:
        async def scan(message: ChatMessage) -> Result:
            if len(message.text) > threshold:
                return Result(value={"long": True})
            return Result(value={"short": True})

        return scan

    # Create instances with different parameters
    scanner1 = parameterized_scanner(threshold=5)
    scanner2 = parameterized_scanner(threshold=20)

    # Both should have the same config
    assert registry_info(scanner1).name == registry_info(scanner2).name


def test_scanner_with_loader() -> None:
    """Scanner can use a custom loader."""
    from inspect_scout._scanner.loader import loader
    from inspect_scout._transcript.types import Transcript

    @loader(name="test_loader", messages="all")  # type: ignore[arg-type]
    def test_loader() -> Callable[[Transcript], AsyncIterator[Transcript]]:
        async def load(transcripts: Transcript) -> AsyncIterator[Transcript]:
            yield transcripts

        return load

    loader_instance: Any = test_loader()

    @scanner(loader=loader_instance)
    def test_scanner() -> Scanner[Transcript]:
        async def scan(transcript: Transcript) -> Result:
            return Result(value={"id": transcript.transcript_id})

        return scan

    instance = test_scanner()
    assert registry_info(instance).metadata[SCANNER_CONFIG].loader
    assert registry_info(instance).metadata[SCANNER_CONFIG].loader == loader_instance


def test_scanner_preserves_function_metadata() -> None:
    """Scanner decorator should preserve function metadata."""

    @scanner(messages=["system"])
    def test_scanner_with_doc() -> Scanner[ChatMessage]:
        """This is a test scanner."""

        async def scan(message: ChatMessage) -> Result:
            return Result(value={"ok": True})

        return scan

    # Check that metadata is preserved
    assert test_scanner_with_doc.__name__ == "test_scanner_with_doc"
    assert test_scanner_with_doc.__doc__ == "This is a test scanner."


# Scanner registry tests


def test_scanner_added_to_registry() -> None:
    """Scanner should be added to registry."""

    @scanner(messages=["system"], name="registry_test_scanner")
    def test_scanner() -> Scanner[ChatMessage]:
        async def scan(message: ChatMessage) -> Result:
            return Result(value={"ok": True})

        return scan

    # Create an instance to trigger registration
    scanner_instance = test_scanner()
    assert registry_info(scanner_instance).name == "registry_test_scanner"


def test_scanner_with_timeline() -> None:
    """Scanner decorator should handle timeline filter."""
    from inspect_scout._transcript.timeline import Timeline

    @scanner(timeline="all")
    def test_scanner() -> Scanner[Timeline]:
        async def scan(timeline: Timeline) -> Result:
            return Result(value={"name": timeline.name})

        return scan

    instance: Any = test_scanner()
    config = registry_info(instance).metadata[SCANNER_CONFIG]
    assert config.content.timeline == "all"
    # timeline implies events="all"
    assert config.content.events == "all"


def test_scanner_with_timeline_true() -> None:
    """Scanner with timeline=True should use default event set."""
    from inspect_scout._scanner.filter import TIMELINE_DEFAULT_EVENTS
    from inspect_scout._transcript.timeline import Timeline

    @scanner(timeline=True)
    def test_scanner() -> Scanner[Timeline]:
        async def scan(timeline: Timeline) -> Result:
            return Result(value={"name": timeline.name})

        return scan

    instance: Any = test_scanner()
    config = registry_info(instance).metadata[SCANNER_CONFIG]
    assert config.content.timeline == TIMELINE_DEFAULT_EVENTS
    # Events derived from timeline types + structural events
    events = config.content.events
    assert isinstance(events, list)
    for event_type in TIMELINE_DEFAULT_EVENTS:
        assert event_type in events


def test_scanner_with_named_timeline() -> None:
    """Scanner decorator should handle event-type timeline filter."""
    from inspect_scout._transcript.timeline import Timeline

    @scanner(timeline=["model"])
    def test_scanner() -> Scanner[list[Timeline]]:
        async def scan(timelines: list[Timeline]) -> Result:
            return Result(value={"count": len(timelines)})

        return scan

    instance: Any = test_scanner()
    config = registry_info(instance).metadata[SCANNER_CONFIG]
    assert config.content.timeline == ["model"]
    # Events derived from timeline types + structural events
    events = config.content.events
    assert isinstance(events, list)
    assert "model" in events
    assert "span_begin" in events
    assert "span_end" in events


def test_scanner_timeline_with_explicit_events() -> None:
    """Scanner with timeline and explicit events should preserve explicit events."""
    from inspect_scout._transcript.types import Transcript

    @scanner(timeline="all", events=["model"])
    def test_scanner() -> Scanner[Transcript]:
        async def scan(transcript: Transcript) -> Result:
            return Result(value={"id": transcript.transcript_id})

        return scan

    instance: Any = test_scanner()
    config = registry_info(instance).metadata[SCANNER_CONFIG]
    assert config.content.timeline == "all"
    # Explicit events are preserved, but span events are added for tree building
    events = config.content.events
    assert isinstance(events, list)
    assert "model" in events
    assert "span_begin" in events
    assert "span_end" in events


def test_multiple_scanners_different_names() -> None:
    """Multiple scanners can be registered with different names."""

    @scanner(messages=["system"], name="scanner_one")
    def scanner1() -> Scanner[ChatMessage]:
        async def scan(message: ChatMessage) -> Result:
            return Result(value={"scanner": 1})

        return scan

    @scanner(messages=["user"], name="scanner_two")
    def scanner2() -> Scanner[ChatMessage]:
        async def scan(message: ChatMessage) -> Result:
            return Result(value={"scanner": 2})

        return scan

    instance1 = scanner1()
    instance2 = scanner2()

    assert registry_info(instance1).name == "scanner_one"
    assert registry_info(instance2).name == "scanner_two"


def test_streaming_vouch_does_not_leak_through_functools_wraps() -> None:
    """A wrapper that adds its own transcript access must not inherit the inner vouch.

    `functools.wraps` copies `__dict__`. If the vouch lived there, this wrapper
    would receive a handle and `not transcript.messages` -- a bound method on a
    handle -- would be a silent wrong answer.
    """

    @scanner(messages="all")
    def wrapping() -> Scanner[Transcript]:
        inner = llm_scanner(question="q?", answer="boolean")

        @functools.wraps(inner)
        async def scan(transcript: Transcript) -> Result | list[Result]:
            if not transcript.messages:
                return Result(value=False)
            return await inner(transcript)

        return scan

    assert scanner_supports_streaming(wrapping()) is False


def test_direct_llm_scanner_wrapper_streams() -> None:
    """Returning llm_scanner's own scan passes its vouch through: nothing else reads the transcript."""

    @scanner(messages="all")
    def direct() -> Scanner[Transcript]:
        return llm_scanner(question="q?", answer="boolean")

    assert scanner_supports_streaming(direct()) is True


def test_callable_question_is_vouched_against() -> None:
    """A callable question needs the whole transcript, so llm_scanner vouches against streaming."""

    async def question(t: Transcript) -> str:
        return "q?"

    @scanner(messages="all")
    def dynamic() -> Scanner[Transcript]:
        return llm_scanner(question=question, answer="boolean")

    assert scanner_supports_streaming(dynamic()) is False


@pytest.mark.parametrize(
    ("declared", "vouched", "expected"),
    [
        (None, None, False),
        (None, True, True),
        (None, False, False),
        (False, None, False),
        (False, True, False),
        (True, None, True),
        (True, True, True),
        (True, False, False),
    ],
    ids=[
        "undeclared-unvouched",
        "undeclared-vouched-for",
        "undeclared-vouched-against",
        "declared-off-unvouched",
        "declared-off-vouched-for",
        "declared-on-unvouched",
        "declared-on-vouched-for",
        "declared-on-vouched-against",
    ],
)
def test_streaming_support_combines_declaration_and_vouch(
    declared: bool | None, vouched: bool | None, expected: bool
) -> None:
    """Undeclared defers to the vouch; declared is a conjunction -- neither False is overridden."""
    kwargs: dict[str, Any] = {"messages": "all"}
    if declared is not None:
        kwargs["supports_streaming"] = declared

    @scanner(**kwargs)
    def s() -> Scanner[Transcript]:
        async def scan(transcript: Transcript | TranscriptHandle) -> Result:
            return Result(value=True)

        if vouched is not None:
            mark_streaming_support(scan, vouched)
        return scan

    assert scanner_supports_streaming(s()) is expected


def test_streaming_declaration_requires_a_handle_capable_signature() -> None:
    """`supports_streaming=True` on a Transcript-only scan function raises when the factory runs."""

    @scanner(messages="all", supports_streaming=True)
    def s() -> Scanner[Transcript]:
        async def scan(transcript: Transcript) -> Result:
            return Result(value=True)

        return scan

    with pytest.raises(TypeError, match="supports_streaming=True"):
        s()


def test_streaming_declaration_resolves_string_annotations() -> None:
    """A literal string annotation (simulating `from __future__ import annotations`) resolves."""

    @scanner(messages="all", supports_streaming=True)
    def string_annotated() -> Scanner[Transcript]:
        async def scan(transcript: "Transcript | TranscriptHandle") -> Result:
            return Result(value=True)

        return scan

    instance = string_annotated()
    assert scanner_supports_streaming(instance) is True


def test_streaming_declaration_resolves_hints_in_the_scan_functions_module() -> None:
    """A scan function from another module resolves against its own globals.

    `from __future__ import annotations` there makes the annotation a string only
    that module's namespace can resolve; the factory's namespace need not carry
    `Transcript` or `TranscriptHandle` at all.
    """
    lib = types.ModuleType("streaming_lib")
    exec(
        "from __future__ import annotations\n"
        "from inspect_scout import Result, Transcript, TranscriptHandle\n"
        "async def scan(transcript: Transcript | TranscriptHandle) -> Result:\n"
        "    return Result(value=True)\n",
        lib.__dict__,
    )
    ns: dict[str, Any] = {"scanner": scanner, "lib": lib}
    exec(
        "@scanner(messages='all', supports_streaming=True)\n"
        "def cross():\n"
        "    return lib.scan\n",
        ns,
    )

    assert scanner_supports_streaming(ns["cross"]()) is True


def test_streaming_declaration_refuses_a_functools_wraps_wrapper() -> None:
    """`wraps` copies the wrapped function's annotations, so nothing is verifiable.

    The wrapper below is `Transcript`-only but carries `llm_scanner`'s
    `Transcript | TranscriptHandle` annotation, which would let an untruthful
    declaration through.
    """

    @scanner(messages="all", supports_streaming=True)
    def wrapping() -> Scanner[Transcript]:
        inner = llm_scanner(question="q?", answer="boolean")

        @functools.wraps(inner)
        async def scan(transcript: Transcript) -> Result | list[Result]:
            if not transcript.messages:
                return Result(value=False)
            return await inner(transcript)

        return scan

    with pytest.raises(TypeError, match="__wrapped__"):
        wrapping()
