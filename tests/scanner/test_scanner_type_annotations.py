"""Tests for scanner decorator type annotation handling."""

from __future__ import annotations

import inspect
from functools import partial
from typing import Optional, get_type_hints

import pytest
from inspect_ai.model import ChatMessageAssistant
from inspect_ai.model._chat_message import ChatMessage
from inspect_scout import Result, Scanner, Transcript, scanner

from tests.scanner.wrappers import wrap_async


@pytest.mark.asyncio
async def test_scanner_instantiates_with_postponed_transcript_annotation() -> None:
    @scanner(messages="all")
    def transcript_scanner() -> Scanner[Transcript]:
        async def scan(transcript: Transcript) -> Result:
            return Result(value=len(transcript.messages))

        return scan

    instance = transcript_scanner()
    transcript = Transcript(
        transcript_id="postponed",
        source_type="test",
        source_id="test",
        source_uri="test://postponed",
        messages=[ChatMessageAssistant(content="hello")],
    )
    result = await instance(transcript)
    assert isinstance(result, Result)
    assert result.value == 1


@pytest.mark.asyncio
async def test_scanner_instantiates_with_postponed_message_list_annotation() -> None:
    @scanner
    def message_scanner() -> Scanner[list[ChatMessageAssistant]]:
        async def scan(messages: list[ChatMessageAssistant]) -> Result:
            return Result(value=len(messages))

        return scan

    instance: Scanner[list[ChatMessageAssistant]] = message_scanner()
    result = await instance([ChatMessageAssistant(content="hello")])
    assert isinstance(result, Result)
    assert result.value == 1


@pytest.mark.asyncio
async def test_scanner_registers_with_unresolvable_return_annotation() -> None:
    """Scanner registration resolves its input annotation without its return type."""

    def create_scanner() -> Scanner[Transcript]:
        from inspect_scout._scanner.result import Result as LocalResult

        @scanner(messages="all")
        def local_result_scanner() -> Scanner[Transcript]:
            async def scan(transcript: Transcript) -> LocalResult:
                return LocalResult(value=len(transcript.messages))

            return scan

        return local_result_scanner()

    instance = create_scanner()
    transcript = Transcript(
        transcript_id="local-result",
        source_type="test",
        source_id="test",
        source_uri="test://local-result",
    )
    result = await instance(transcript)
    assert isinstance(result, Result)
    assert result.value == 0


@pytest.mark.asyncio
async def test_scanner_registers_partial_with_postponed_input_annotation() -> None:
    """Partial scanners retain their postponed input annotation resolution."""

    @scanner(messages="all")
    def partial_scanner() -> Scanner[Transcript]:
        async def scan(transcript: Transcript) -> Result:
            return Result(value=transcript.transcript_id)

        return partial(scan)

    instance = partial_scanner()
    transcript = Transcript(
        transcript_id="partial",
        source_type="test",
        source_id="test",
        source_uri="test://partial",
    )
    result = await instance(transcript)
    assert isinstance(result, Result)
    assert result.value == "partial"


@pytest.mark.asyncio
async def test_scanner_registers_wrapped_with_postponed_input_annotation() -> None:
    """Wrapped scanners resolve annotations in the wrapped function's globals."""

    @scanner(messages="all")
    def wrapped_scanner() -> Scanner[Transcript]:
        async def scan(transcript: Transcript) -> Result:
            return Result(value=transcript.transcript_id)

        return wrap_async(scan)

    instance = wrapped_scanner()
    transcript = Transcript(
        transcript_id="wrapped",
        source_type="test",
        source_id="test",
        source_uri="test://wrapped",
    )
    result = await instance(transcript)
    assert isinstance(result, Result)
    assert result.value == "wrapped"


def test_scanner_preserves_type_annotations_with_future_annotations() -> None:
    """Scanner decorator preserves type hints with PEP 563 stringified annotations."""

    @scanner(messages=["system"])
    def my_scanner(threshold: int, name: str = "default") -> Scanner[ChatMessage]:
        async def scan(message: ChatMessage) -> Result:
            return Result(value={"ok": True})

        return scan

    # get_type_hints should work (not return strings)
    hints = get_type_hints(my_scanner)
    assert hints["threshold"] is int
    assert hints["name"] is str
    # Return type should be Scanner[ChatMessage]
    assert "return" in hints


def test_scanner_preserves_signature() -> None:
    """Scanner decorator preserves the original function signature."""

    @scanner(messages=["user"])
    def parameterized_scanner(
        threshold: int,
        prefix: str = "test",
        enabled: bool = True,
    ) -> Scanner[ChatMessage]:
        async def scan(message: ChatMessage) -> Result:
            return Result(value={"threshold": threshold})

        return scan

    sig = inspect.signature(parameterized_scanner)
    params = list(sig.parameters.keys())

    assert params == ["threshold", "prefix", "enabled"]
    assert sig.parameters["threshold"].default is inspect.Parameter.empty
    assert sig.parameters["prefix"].default == "test"
    assert sig.parameters["enabled"].default is True


def test_scanner_annotations_accessible_via_dunder() -> None:
    """Scanner __annotations__ dict contains resolved types, not strings."""

    @scanner(messages=["assistant"])
    def annotated_scanner(count: int) -> Scanner[ChatMessage]:
        async def scan(message: ChatMessage) -> Result:
            return Result(value={"count": count})

        return scan

    annotations = annotated_scanner.__annotations__

    # Should be actual types, not strings like 'int'
    assert annotations["count"] is int
    assert not isinstance(annotations["count"], str)


def test_scanner_with_complex_type_annotations() -> None:
    """Scanner handles complex type annotations like Optional, list, etc."""

    @scanner(messages=["system"])
    def complex_scanner(
        items: list[str],
        mapping: dict[str, int],
        optional_val: Optional[float] = None,
    ) -> Scanner[ChatMessage]:
        async def scan(message: ChatMessage) -> Result:
            return Result(value={})

        return scan

    hints = get_type_hints(complex_scanner)

    # These should be resolved types
    assert hints["items"] == list[str]
    assert hints["mapping"] == dict[str, int]


def test_scanner_signature_with_no_parameters() -> None:
    """Scanner with no parameters has empty signature."""

    @scanner(messages=["system"])
    def no_param_scanner() -> Scanner[ChatMessage]:
        async def scan(message: ChatMessage) -> Result:
            return Result(value={})

        return scan

    sig = inspect.signature(no_param_scanner)
    assert len(sig.parameters) == 0


def test_scanner_signature_with_args_kwargs() -> None:
    """Scanner preserves *args and **kwargs in signature."""

    @scanner(messages=["user"])
    def flexible_scanner(
        required: str, *args: str, **kwargs: int
    ) -> Scanner[ChatMessage]:
        async def scan(message: ChatMessage) -> Result:
            return Result(value={})

        return scan

    sig = inspect.signature(flexible_scanner)
    assert "required" in sig.parameters
    assert sig.parameters["args"].kind == inspect.Parameter.VAR_POSITIONAL
    assert sig.parameters["kwargs"].kind == inspect.Parameter.VAR_KEYWORD
