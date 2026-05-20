"""Tests for stream-capture wrappers when the underlying stream errors mid-way.

When an SDK stream raises after yielding some chunks (overloaded, connection
reset, server-sent ``error`` event), the capture wrapper should still emit
whatever was accumulated, tagged with the exception, so the partial generation
is recorded as a ``ModelEvent`` with ``error`` set rather than dropped.

These are unit tests over the wrapper classes themselves (the narrowest public
surface for this behaviour) using real SDK event/chunk/exception types. The
end-to-end happy path is covered by ``test_observe_providers.py``.
"""

from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable, Iterator

import httpx
import pytest


def _record_emit() -> tuple[list[dict[str, Any]], Callable[[dict[str, Any]], None]]:
    """Return a (captures, emit) pair where emit appends to captures."""
    captures: list[dict[str, Any]] = []
    return captures, captures.append


@dataclass
class StreamErrorCase:
    """One stream-wrapper variant under test."""

    id: str
    wrapper_cls: type
    chunks: list[Any]
    error: Exception
    request: dict[str, Any]
    verify_partial: Callable[[dict[str, Any]], None]


# --------------------------------------------------------------------------- #
# Anthropic — create(stream=True) wrappers
# --------------------------------------------------------------------------- #


def _anthropic_text_chunks() -> list[Any]:
    from anthropic.types import (
        ContentBlockDeltaEvent,
        ContentBlockStartEvent,
        Message,
        MessageStartEvent,
        TextBlock,
        TextDelta,
        Usage,
    )

    return [
        MessageStartEvent(
            type="message_start",
            message=Message(
                id="msg_test",
                type="message",
                role="assistant",
                model="claude-test",
                content=[],
                stop_reason=None,
                stop_sequence=None,
                usage=Usage(input_tokens=12, output_tokens=0),
            ),
        ),
        ContentBlockStartEvent(
            type="content_block_start",
            index=0,
            content_block=TextBlock(type="text", text=""),
        ),
        ContentBlockDeltaEvent(
            type="content_block_delta",
            index=0,
            delta=TextDelta(type="text_delta", text="Hello "),
        ),
        ContentBlockDeltaEvent(
            type="content_block_delta",
            index=0,
            delta=TextDelta(type="text_delta", text="wor"),
        ),
    ]


def _anthropic_error() -> Exception:
    import anthropic

    return anthropic.APIConnectionError(
        message="overloaded_error", request=httpx.Request("POST", "http://test")
    )


def _verify_anthropic_partial(data: dict[str, Any]) -> None:
    response = data["response"]
    assert response["id"] == "msg_test"
    assert response["model"] == "claude-test"
    assert response["content"][0]["type"] == "text"
    assert response["content"][0]["text"] == "Hello wor"
    assert response["usage"]["input_tokens"] == 12


# --------------------------------------------------------------------------- #
# OpenAI — Chat Completions wrappers
# --------------------------------------------------------------------------- #


def _openai_chat_chunks() -> list[Any]:
    from openai.types.chat import ChatCompletionChunk
    from openai.types.chat.chat_completion_chunk import Choice, ChoiceDelta

    return [
        ChatCompletionChunk(
            id="cmpl_test",
            object="chat.completion.chunk",
            created=0,
            model="gpt-test",
            choices=[
                Choice(index=0, delta=ChoiceDelta(role="assistant", content="Hello "))
            ],
        ),
        ChatCompletionChunk(
            id="cmpl_test",
            object="chat.completion.chunk",
            created=0,
            model="gpt-test",
            choices=[Choice(index=0, delta=ChoiceDelta(content="wor"))],
        ),
    ]


def _openai_error() -> Exception:
    import openai

    return openai.APIConnectionError(
        message="connection reset", request=httpx.Request("POST", "http://test")
    )


def _verify_openai_chat_partial(data: dict[str, Any]) -> None:
    assert data["api"] == "completions"
    response = data["response"]
    assert response["id"] == "cmpl_test"
    assert response["model"] == "gpt-test"
    assert response["choices"][0]["message"]["content"] == "Hello wor"


# --------------------------------------------------------------------------- #
# OpenAI — Responses API wrappers
# --------------------------------------------------------------------------- #


def _openai_responses_chunks() -> list[Any]:
    from openai.types.responses import (
        Response,
        ResponseCreatedEvent,
        ResponseTextDeltaEvent,
    )

    response_snapshot = Response(
        id="resp_test",
        object="response",
        created_at=0,
        model="gpt-test",
        output=[],
        parallel_tool_calls=False,
        tool_choice="auto",
        tools=[],
        status="in_progress",
    )
    return [
        ResponseCreatedEvent(
            type="response.created", sequence_number=0, response=response_snapshot
        ),
        ResponseTextDeltaEvent(
            type="response.output_text.delta",
            sequence_number=1,
            content_index=0,
            output_index=0,
            item_id="item_0",
            logprobs=[],
            delta="Hello ",
        ),
    ]


def _verify_openai_responses_partial(data: dict[str, Any]) -> None:
    assert data["api"] == "responses"
    # The Responses wrapper tracks the latest event-carried response snapshot,
    # so on mid-stream error we should at least get the response.created one.
    assert data["response"].id == "resp_test"
    assert data["response"].status == "in_progress"


# --------------------------------------------------------------------------- #
# Google — generate_content_stream wrappers
# --------------------------------------------------------------------------- #


def _google_chunks() -> list[Any]:
    from google.genai.types import Candidate, Content, GenerateContentResponse, Part

    def chunk(text: str) -> GenerateContentResponse:
        return GenerateContentResponse(
            candidates=[
                Candidate(
                    index=0, content=Content(role="model", parts=[Part(text=text)])
                )
            ]
        )

    return [chunk("Hello "), chunk("wor")]


def _google_error() -> Exception:
    from google.genai.errors import ServerError

    return ServerError(503, {"error": {"message": "overloaded"}})


def _verify_google_partial(data: dict[str, Any]) -> None:
    parts = data["accumulated_parts"][0]
    assert "".join(p.text for p in parts) == "Hello wor"
    assert data["response"] is not None  # last_chunk


# --------------------------------------------------------------------------- #
# Test tables
# --------------------------------------------------------------------------- #


def _sync_cases() -> list[StreamErrorCase]:
    from inspect_scout._observe.providers.anthropic import AnthropicStreamCapture
    from inspect_scout._observe.providers.google import GoogleStreamCapture
    from inspect_scout._observe.providers.openai import (
        OpenAIChatStreamCapture,
        OpenAIResponsesStreamCapture,
    )

    return [
        StreamErrorCase(
            id="anthropic-create",
            wrapper_cls=AnthropicStreamCapture,
            chunks=_anthropic_text_chunks(),
            error=_anthropic_error(),
            request={"model": "claude-test", "messages": []},
            verify_partial=_verify_anthropic_partial,
        ),
        StreamErrorCase(
            id="openai-chat",
            wrapper_cls=OpenAIChatStreamCapture,
            chunks=_openai_chat_chunks(),
            error=_openai_error(),
            request={"model": "gpt-test", "messages": []},
            verify_partial=_verify_openai_chat_partial,
        ),
        StreamErrorCase(
            id="openai-responses",
            wrapper_cls=OpenAIResponsesStreamCapture,
            chunks=_openai_responses_chunks(),
            error=_openai_error(),
            request={"model": "gpt-test", "input": "hi"},
            verify_partial=_verify_openai_responses_partial,
        ),
        StreamErrorCase(
            id="google",
            wrapper_cls=GoogleStreamCapture,
            chunks=_google_chunks(),
            error=_google_error(),
            request={"model": "gemini-test", "contents": []},
            verify_partial=_verify_google_partial,
        ),
    ]


def _async_cases() -> list[StreamErrorCase]:
    from inspect_scout._observe.providers.anthropic import AnthropicAsyncStreamCapture
    from inspect_scout._observe.providers.google import GoogleAsyncStreamCapture
    from inspect_scout._observe.providers.openai import (
        OpenAIChatAsyncStreamCapture,
        OpenAIResponsesAsyncStreamCapture,
    )

    return [
        StreamErrorCase(
            id="anthropic-create",
            wrapper_cls=AnthropicAsyncStreamCapture,
            chunks=_anthropic_text_chunks(),
            error=_anthropic_error(),
            request={"model": "claude-test", "messages": []},
            verify_partial=_verify_anthropic_partial,
        ),
        StreamErrorCase(
            id="openai-chat",
            wrapper_cls=OpenAIChatAsyncStreamCapture,
            chunks=_openai_chat_chunks(),
            error=_openai_error(),
            request={"model": "gpt-test", "messages": []},
            verify_partial=_verify_openai_chat_partial,
        ),
        StreamErrorCase(
            id="openai-responses",
            wrapper_cls=OpenAIResponsesAsyncStreamCapture,
            chunks=_openai_responses_chunks(),
            error=_openai_error(),
            request={"model": "gpt-test", "input": "hi"},
            verify_partial=_verify_openai_responses_partial,
        ),
        StreamErrorCase(
            id="google",
            wrapper_cls=GoogleAsyncStreamCapture,
            chunks=_google_chunks(),
            error=_google_error(),
            request={"model": "gemini-test", "contents": []},
            verify_partial=_verify_google_partial,
        ),
    ]


SYNC_CASES = _sync_cases()
ASYNC_CASES = _async_cases()


# --------------------------------------------------------------------------- #
# Sync stream wrappers
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("case", SYNC_CASES, ids=lambda c: c.id)
def test_sync_stream_emits_partial_on_error(case: StreamErrorCase) -> None:
    """A mid-stream exception still emits the accumulated partial response."""
    captures, emit = _record_emit()

    def failing_stream() -> Iterator[Any]:
        yield from case.chunks
        raise case.error

    wrapper = case.wrapper_cls(failing_stream(), case.request, emit)

    seen: list[Any] = []
    with pytest.raises(type(case.error)):
        for chunk in wrapper:
            seen.append(chunk)

    # Caller saw all pre-error chunks unchanged.
    assert seen == case.chunks

    # Exactly one capture, carrying request + partial response + error.
    assert len(captures) == 1
    data = captures[0]
    assert data["request"] is case.request
    assert data["error"] is case.error
    case.verify_partial(data)


@pytest.mark.parametrize("case", SYNC_CASES, ids=lambda c: c.id)
def test_sync_stream_emits_once_on_success(case: StreamErrorCase) -> None:
    """Clean completion still emits exactly once with no error key (regression)."""
    captures, emit = _record_emit()

    wrapper = case.wrapper_cls(iter(case.chunks), case.request, emit)
    for _ in wrapper:
        pass

    assert len(captures) == 1
    assert "error" not in captures[0]
    assert captures[0]["request"] is case.request


@pytest.mark.parametrize("case", SYNC_CASES, ids=lambda c: c.id)
def test_sync_stream_emits_partial_on_consumer_break(case: StreamErrorCase) -> None:
    """If the caller stops consuming early, the partial is still captured."""
    captures, emit = _record_emit()

    wrapper = case.wrapper_cls(iter(case.chunks), case.request, emit)
    gen = iter(wrapper)
    next(gen)
    gen.close()

    assert len(captures) == 1
    assert "error" not in captures[0]


# --------------------------------------------------------------------------- #
# Async stream wrappers
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ASYNC_CASES, ids=lambda c: c.id)
async def test_async_stream_emits_partial_on_error(case: StreamErrorCase) -> None:
    """A mid-stream exception still emits the accumulated partial response."""
    captures, emit = _record_emit()

    async def failing_stream() -> AsyncIterator[Any]:
        for chunk in case.chunks:
            yield chunk
        raise case.error

    wrapper = case.wrapper_cls(failing_stream(), case.request, emit)

    seen: list[Any] = []
    with pytest.raises(type(case.error)):
        async for chunk in wrapper:
            seen.append(chunk)

    assert seen == case.chunks
    assert len(captures) == 1
    data = captures[0]
    assert data["request"] is case.request
    assert data["error"] is case.error
    case.verify_partial(data)


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ASYNC_CASES, ids=lambda c: c.id)
async def test_async_stream_emits_once_on_success(case: StreamErrorCase) -> None:
    """Clean completion still emits exactly once with no error key (regression)."""
    captures, emit = _record_emit()

    async def stream() -> AsyncIterator[Any]:
        for chunk in case.chunks:
            yield chunk

    wrapper = case.wrapper_cls(stream(), case.request, emit)
    async for _ in wrapper:
        pass

    assert len(captures) == 1
    assert "error" not in captures[0]


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ASYNC_CASES, ids=lambda c: c.id)
async def test_async_stream_emits_partial_on_consumer_break(
    case: StreamErrorCase,
) -> None:
    """If the caller stops consuming early, the partial is still captured."""
    captures, emit = _record_emit()

    async def stream() -> AsyncIterator[Any]:
        for chunk in case.chunks:
            yield chunk

    wrapper = case.wrapper_cls(stream(), case.request, emit)
    agen = wrapper.__aiter__()
    await agen.__anext__()
    await agen.aclose()

    assert len(captures) == 1
    assert "error" not in captures[0]


# --------------------------------------------------------------------------- #
# Anthropic .stream() manager wrappers
# --------------------------------------------------------------------------- #


class _FakeAnthropicMessageStream:
    """Minimal stand-in for ``anthropic.lib.streaming.MessageStream``.

    Only implements what ``AnthropicStreamManagerCaptureContext`` reads:
    iteration, ``text_stream``, ``get_final_message()`` and the
    ``current_message_snapshot`` property the SDK exposes for partial state.
    """

    def __init__(self, events: list[Any], error: Exception | None) -> None:
        self._events = events
        self._error = error
        from anthropic.types import Message, Usage

        self._snapshot = Message(
            id="msg_test",
            type="message",
            role="assistant",
            model="claude-test",
            content=[],
            stop_reason=None,
            stop_sequence=None,
            usage=Usage(input_tokens=12, output_tokens=0),
        )

    @property
    def current_message_snapshot(self) -> Any:
        return self._snapshot

    def __iter__(self) -> Iterator[Any]:
        for ev in self._events:
            self._apply(ev)
            yield ev
        if self._error is not None:
            raise self._error

    @property
    def text_stream(self) -> Iterator[str]:
        for ev in self:
            if getattr(ev, "type", None) == "content_block_delta":
                yield ev.delta.text

    def get_final_message(self) -> Any:
        for _ in self:
            pass
        return self._snapshot

    def _apply(self, ev: Any) -> None:
        from anthropic.types import TextBlock

        if getattr(ev, "type", None) == "content_block_start":
            self._snapshot = self._snapshot.model_copy(
                update={"content": [TextBlock(type="text", text="")]}
            )
        elif getattr(ev, "type", None) == "content_block_delta":
            block = self._snapshot.content[0]
            assert block.type == "text"
            self._snapshot = self._snapshot.model_copy(
                update={
                    "content": [TextBlock(type="text", text=block.text + ev.delta.text)]
                }
            )


class _FakeAnthropicAsyncMessageStream:
    """Async variant of :class:`_FakeAnthropicMessageStream`."""

    def __init__(self, events: list[Any], error: Exception | None) -> None:
        self._sync = _FakeAnthropicMessageStream(events, error)

    @property
    def current_message_snapshot(self) -> Any:
        return self._sync.current_message_snapshot

    async def __aiter__(self) -> AsyncIterator[Any]:
        for ev in self._sync:
            yield ev

    @property
    def text_stream(self) -> AsyncIterator[str]:
        async def _gen() -> AsyncIterator[str]:
            for text in self._sync.text_stream:
                yield text

        return _gen()

    async def get_final_message(self) -> Any:
        async for _ in self:
            pass
        return self._sync.current_message_snapshot


def _anthropic_manager_partial_text(data: dict[str, Any]) -> str:
    msg = data["response"]
    return "".join(b.text for b in msg.content if b.type == "text")


@pytest.mark.parametrize("via", ["iter", "text_stream", "get_final_message"])
def test_anthropic_sync_stream_manager_emits_partial_on_error(via: str) -> None:
    """``messages.stream()`` (sync) emits the SDK snapshot on mid-stream error."""
    from inspect_scout._observe.providers.anthropic import (
        AnthropicStreamManagerCaptureContext,
    )

    captures, emit = _record_emit()
    error = _anthropic_error()
    inner = _FakeAnthropicMessageStream(_anthropic_text_chunks(), error)
    ctx = AnthropicStreamManagerCaptureContext(inner, {"model": "claude-test"}, emit)

    with pytest.raises(type(error)):
        if via == "iter":
            for _ in ctx:
                pass
        elif via == "text_stream":
            for _ in ctx.text_stream:
                pass
        else:
            ctx.get_final_message()

    assert len(captures) == 1
    assert captures[0]["error"] is error
    assert _anthropic_manager_partial_text(captures[0]) == "Hello wor"


@pytest.mark.asyncio
@pytest.mark.parametrize("via", ["aiter", "text_stream", "get_final_message"])
async def test_anthropic_async_stream_manager_emits_partial_on_error(via: str) -> None:
    """``messages.stream()`` (async) emits the SDK snapshot on mid-stream error."""
    from inspect_scout._observe.providers.anthropic import (
        AnthropicAsyncStreamManagerCaptureContext,
    )

    captures, emit = _record_emit()
    error = _anthropic_error()
    inner = _FakeAnthropicAsyncMessageStream(_anthropic_text_chunks(), error)
    ctx = AnthropicAsyncStreamManagerCaptureContext(
        inner, {"model": "claude-test"}, emit
    )

    with pytest.raises(type(error)):
        if via == "aiter":
            async for _ in ctx:
                pass
        elif via == "text_stream":
            async for _ in ctx.text_stream:
                pass
        else:
            await ctx.get_final_message()

    assert len(captures) == 1
    assert captures[0]["error"] is error
    assert _anthropic_manager_partial_text(captures[0]) == "Hello wor"


def test_anthropic_sync_stream_manager_no_double_emit() -> None:
    """Iterating then calling ``get_final_message()`` still emits once."""
    from inspect_scout._observe.providers.anthropic import (
        AnthropicStreamManagerCaptureContext,
    )

    captures, emit = _record_emit()
    inner = _FakeAnthropicMessageStream(_anthropic_text_chunks(), error=None)
    ctx = AnthropicStreamManagerCaptureContext(inner, {"model": "claude-test"}, emit)

    for _ in ctx:
        pass
    ctx.get_final_message()

    assert len(captures) == 1
    assert "error" not in captures[0]


# --------------------------------------------------------------------------- #
# build_event propagates the error key onto ModelEvent.error
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_anthropic_build_event_carries_error() -> None:
    from inspect_ai.event import ModelEvent
    from inspect_scout._observe.providers.anthropic import (
        AnthropicProvider,
        AnthropicStreamAccumulator,
    )

    acc = AnthropicStreamAccumulator()
    for ev in _anthropic_text_chunks():
        acc.accumulate_event(ev)

    error = _anthropic_error()
    event = await AnthropicProvider().build_event(
        {
            "request": {"model": "claude-test", "messages": []},
            "response": acc.accumulated,
            "error": error,
        }
    )
    assert isinstance(event, ModelEvent)
    assert event.error == repr(error)
    assert event.output is not None


def _openai_moderation_error() -> Exception:
    """An ``APIError`` matching what the SDK raises for an SSE ``error`` event.

    Mirrors the shape OpenAI sends when the streaming safety classifier fires
    after content has already been emitted (``code='invalid_prompt'``).
    """
    import openai

    err = openai.APIError(
        "limited access for safety reasons",
        request=httpx.Request("POST", "http://test"),
        body={
            "type": "invalid_request_error",
            "code": "invalid_prompt",
            "message": "limited access for safety reasons",
            "param": None,
        },
    )
    err.code = "invalid_prompt"
    err.type = "invalid_request_error"
    return err


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error_factory, expected_stop",
    [
        (_openai_moderation_error, "content_filter"),
        (_openai_error, "unknown"),
    ],
    ids=["content_filter", "connection_error"],
)
async def test_openai_build_event_carries_error(
    error_factory: Callable[[], Exception], expected_stop: str
) -> None:
    from inspect_ai.event import ModelEvent
    from inspect_scout._observe.providers.openai import (
        OpenAIChatStreamAccumulator,
        OpenAIProvider,
    )

    acc = OpenAIChatStreamAccumulator()
    for chunk in _openai_chat_chunks():
        acc.accumulate_chunk(chunk)

    error = error_factory()
    event = await OpenAIProvider().build_event(
        {
            "request": {"model": "gpt-test", "messages": []},
            "response": acc.get_response(),
            "api": "completions",
            "error": error,
        }
    )
    assert isinstance(event, ModelEvent)
    assert event.error == repr(error)
    # Partial response (no finish_reason chunk arrived) is still converted,
    # with stop_reason inferred from the error where possible.
    assert event.output.choices[0].message.text == "Hello wor"
    assert event.output.choices[0].stop_reason == expected_stop


@pytest.mark.asyncio
async def test_google_build_event_carries_error() -> None:
    from inspect_ai.event import ModelEvent
    from inspect_scout._observe.providers.google import (
        GoogleProvider,
        GoogleStreamAccumulator,
    )

    acc = GoogleStreamAccumulator()
    for chunk in _google_chunks():
        acc.accumulate_chunk(chunk)

    error = _google_error()
    event = await GoogleProvider().build_event(
        {
            **acc.get_response_data({"model": "gemini-test", "contents": []}),
            "error": error,
        }
    )
    assert isinstance(event, ModelEvent)
    assert event.error == repr(error)
    assert event.output is not None


# --------------------------------------------------------------------------- #
# OpenAI — empty-response errors (no chunk ever arrived, or non-streaming 400)
# --------------------------------------------------------------------------- #


def _openai_bad_request_error() -> Exception:
    """Shape of ``BadRequestError`` for a content-policy 400 with no body.

    The HTTP response body is ``{"error": {...}}`` only — no id, no model,
    no choices — so a downstream ``ChatCompletion.model_validate`` would
    reject it. We need the event built from request + error alone.
    """
    import openai

    err = openai.BadRequestError(
        message="blocked by content policy",
        response=httpx.Response(400, request=httpx.Request("POST", "http://test")),
        body={
            "type": "invalid_request_error",
            "code": "content_policy_violation",
            "message": "blocked by content policy",
            "param": None,
        },
    )
    err.code = "content_policy_violation"
    err.type = "invalid_request_error"
    return err


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        None,
        {"id": None, "object": "chat.completion", "model": None, "choices": []},
    ],
    ids=["response_none", "empty_accumulator_dict"],
)
async def test_openai_build_event_synthesizes_from_error_when_empty(
    response: Any,
) -> None:
    """Error fires before any usable response — build event from request+error.

    Two shapes hit this path: a non-streaming wrapper that caught the
    exception before getting a response (``response=None``), and a streaming
    wrapper whose accumulator never saw a chunk (``id=None``, no choices).
    Both should produce a ``ModelEvent`` with the error message as content
    and stop_reason mapped from the error code.
    """
    from inspect_ai.event import ModelEvent
    from inspect_scout._observe.providers.openai import OpenAIProvider

    error = _openai_bad_request_error()
    event = await OpenAIProvider().build_event(
        {
            "request": {
                "model": "gpt-test",
                "messages": [{"role": "user", "content": "hi"}],
            },
            "response": response,
            "api": "completions",
            "error": error,
        }
    )
    assert isinstance(event, ModelEvent)
    assert event.error == repr(error)
    assert event.model == "gpt-test"
    assert len(event.output.choices) == 1
    assert event.output.choices[0].stop_reason == "content_filter"
    assert "blocked by content policy" in event.output.choices[0].message.text


@pytest.mark.asyncio
async def test_async_chat_wrapper_emits_on_bad_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-streaming chat wrapper records an event when the SDK raises."""
    import openai
    from inspect_scout._observe.providers.openai import OpenAIProvider

    captures, emit = _record_emit()
    error = _openai_bad_request_error()

    async def raising_create(self: Any, *args: Any, **kwargs: Any) -> Any:
        raise error

    monkeypatch.setattr(
        "openai.resources.chat.completions.AsyncCompletions.create",
        raising_create,
    )
    OpenAIProvider().install(emit)

    client = openai.AsyncOpenAI(api_key="test", base_url="http://test")
    with pytest.raises(type(error)):
        await client.chat.completions.create(
            model="gpt-test", messages=[{"role": "user", "content": "hi"}]
        )

    assert len(captures) == 1
    data = captures[0]
    assert data["api"] == "completions"
    assert data["response"] is None
    assert data["error"] is error


def test_sync_chat_wrapper_emits_on_bad_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sync non-streaming chat wrapper records an event when the SDK raises."""
    import openai
    from inspect_scout._observe.providers.openai import OpenAIProvider

    captures, emit = _record_emit()
    error = _openai_bad_request_error()

    def raising_create(self: Any, *args: Any, **kwargs: Any) -> Any:
        raise error

    monkeypatch.setattr(
        "openai.resources.chat.completions.Completions.create",
        raising_create,
    )
    OpenAIProvider().install(emit)

    client = openai.OpenAI(api_key="test", base_url="http://test")
    with pytest.raises(type(error)):
        client.chat.completions.create(
            model="gpt-test", messages=[{"role": "user", "content": "hi"}]
        )

    assert len(captures) == 1
    data = captures[0]
    assert data["api"] == "completions"
    assert data["response"] is None
    assert data["error"] is error
