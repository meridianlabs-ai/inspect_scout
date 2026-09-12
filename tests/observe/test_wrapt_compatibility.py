"""SDK-backed runtime and static contracts, run against both wrapt majors in CI."""

import inspect
import json
from types import FunctionType
from typing import TYPE_CHECKING, Any, Literal

import anthropic
import httpx2
import openai
import pytest
from anthropic.lib.streaming import ParsedMessageStreamEvent
from anthropic.resources.messages import AsyncMessages, Messages
from anthropic.types import Message, RawMessageStreamEvent
from inspect_scout._observe.providers._wrapt import (
    TypedObjectProxy,
    wrap_function_wrapper,
)
from inspect_scout._observe.providers.anthropic import (
    AnthropicAsyncStreamCapture,
    AnthropicAsyncStreamManagerCapture,
    AnthropicStreamCapture,
    AnthropicStreamManagerCapture,
)
from inspect_scout._observe.providers.openai import (
    OpenAIChatAsyncStreamCapture,
    OpenAIChatStreamCapture,
    OpenAIResponsesAsyncStreamCapture,
    OpenAIResponsesStreamCapture,
)
from openai.resources.chat.completions import AsyncCompletions, Completions
from openai.resources.responses import AsyncResponses, Responses
from openai.types.chat import ChatCompletionChunk
from openai.types.responses import ResponseStreamEvent
from typing_extensions import assert_type


@pytest.fixture(autouse=True)
def _unpatched_sdk_methods(monkeypatch: pytest.MonkeyPatch) -> None:
    # Other observe tests leave process-wide capture hooks installed. Keep the
    # SDK's own function decorators, and restore the existing hooks afterward.
    for resource, name in (
        (Completions, "create"),
        (AsyncCompletions, "create"),
        (Responses, "create"),
        (AsyncResponses, "create"),
        (Messages, "create"),
        (AsyncMessages, "create"),
        (Messages, "stream"),
        (AsyncMessages, "stream"),
    ):
        method = getattr(resource, name)
        monkeypatch.setattr(
            resource,
            name,
            inspect.unwrap(method, stop=lambda fn: type(fn) is FunctionType),
        )


def _sse(*events: dict[str, Any]) -> bytes:
    return "".join(
        f"event: {event.get('type', 'message')}\ndata: {json.dumps(event)}\n\n"
        for event in events
    ).encode()


def _response(body: bytes) -> httpx2.Response:
    return httpx2.Response(
        200,
        headers={"content-type": "text/event-stream"},
        stream=httpx2.ByteStream(body),
    )


def _transport(response: httpx2.Response) -> httpx2.MockTransport:
    return httpx2.MockTransport(lambda _request: response)


def _openai_response(api: Literal["chat", "responses"]) -> httpx2.Response:
    if api == "chat":
        return _response(
            _sse(
                {
                    "id": "chat-test",
                    "object": "chat.completion.chunk",
                    "created": 0,
                    "model": "test",
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": "hello"},
                            "finish_reason": "stop",
                        }
                    ],
                }
            )
        )
    return _response(
        _sse(
            {
                "type": "response.completed",
                "sequence_number": 0,
                "response": {
                    "id": "response-test",
                    "object": "response",
                    "created_at": 0,
                    "model": "test",
                    "output": [],
                    "parallel_tool_calls": False,
                    "tool_choice": "auto",
                    "tools": [],
                    "status": "completed",
                },
            }
        )
    )


@pytest.mark.parametrize("api", ["chat", "responses"])
def test_openai_sync_sdk_stream(api: Literal["chat", "responses"]) -> None:
    response = _openai_response(api)
    captures: list[dict[str, Any]] = []
    with openai.OpenAI(
        api_key="test", http_client=httpx2.Client(transport=_transport(response))
    ) as client:
        if api == "chat":
            stream = client.chat.completions.create(
                model="test", messages=[], stream=True
            )
            proxy = OpenAIChatStreamCapture[ChatCompletionChunk](
                stream, {}, captures.append
            )
            assert proxy.__wrapped__ is stream
            assert isinstance(proxy, openai.Stream)
            assert not hasattr(stream, "_self_accumulator")
            chunks = list(proxy)
            assert_type(chunks, list[ChatCompletionChunk])
            assert chunks[0].choices[0].delta.content == "hello"
        else:
            events = list(
                OpenAIResponsesStreamCapture(
                    client.responses.create(model="test", input="hi", stream=True),
                    {},
                    captures.append,
                )
            )
            assert_type(events, list[ResponseStreamEvent])
            assert events[0].type == "response.completed"
    assert len(captures) == 1
    assert captures[0]["api"] == ("completions" if api == "chat" else "responses")
    assert response.is_closed


@pytest.mark.asyncio
@pytest.mark.parametrize("api", ["chat", "responses"])
async def test_openai_async_sdk_stream(api: Literal["chat", "responses"]) -> None:
    response = _openai_response(api)
    captures: list[dict[str, Any]] = []
    async with openai.AsyncOpenAI(
        api_key="test", http_client=httpx2.AsyncClient(transport=_transport(response))
    ) as client:
        if api == "chat":
            stream = await client.chat.completions.create(
                model="test", messages=[], stream=True
            )
            proxy = OpenAIChatAsyncStreamCapture[ChatCompletionChunk](
                stream, {}, captures.append
            )
            assert proxy.__wrapped__ is stream
            assert isinstance(proxy, openai.AsyncStream)
            chunks = [chunk async for chunk in proxy]
            assert_type(chunks, list[ChatCompletionChunk])
            assert chunks[0].choices[0].delta.content == "hello"
        else:
            events = [
                event
                async for event in OpenAIResponsesAsyncStreamCapture(
                    await client.responses.create(
                        model="test", input="hi", stream=True
                    ),
                    {},
                    captures.append,
                )
            ]
            assert_type(events, list[ResponseStreamEvent])
            assert events[0].type == "response.completed"
    assert len(captures) == 1
    assert response.is_closed


def _anthropic_response(*, fail: bool = False) -> httpx2.Response:
    body = _sse(
        {
            "type": "message_start",
            "message": {
                "id": "msg-test",
                "type": "message",
                "role": "assistant",
                "model": "test",
                "content": [],
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {"input_tokens": 1, "output_tokens": 0},
            },
        },
        {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "text", "text": ""},
        },
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": "hello"},
        },
    )
    body += (
        _sse(
            {
                "type": "error",
                "error": {"type": "overloaded_error", "message": "overloaded"},
            }
        )
        if fail
        else _sse(
            {"type": "content_block_stop", "index": 0},
            {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                "usage": {"output_tokens": 1},
            },
            {"type": "message_stop"},
        )
    )
    return _response(body)


def test_anthropic_sync_sdk_stream() -> None:
    response = _anthropic_response()
    captures: list[dict[str, Any]] = []
    with anthropic.Anthropic(
        api_key="test", http_client=httpx2.Client(transport=_transport(response))
    ) as client:
        stream = client.messages.create(
            model="test", max_tokens=5, messages=[], stream=True
        )
        proxy = AnthropicStreamCapture(stream, {}, captures.append)
        assert proxy.__wrapped__ is stream
        events = list(proxy)
        assert_type(events, list[RawMessageStreamEvent])
        assert events[-1].type == "message_stop"
    assert len(captures) == 1
    assert captures[0]["response"]["content"][0]["text"] == "hello"
    assert response.is_closed


@pytest.mark.asyncio
async def test_anthropic_async_sdk_stream() -> None:
    response = _anthropic_response()
    captures: list[dict[str, Any]] = []
    async with anthropic.AsyncAnthropic(
        api_key="test", http_client=httpx2.AsyncClient(transport=_transport(response))
    ) as client:
        stream = await client.messages.create(
            model="test", max_tokens=5, messages=[], stream=True
        )
        proxy = AnthropicAsyncStreamCapture(stream, {}, captures.append)
        assert proxy.__wrapped__ is stream
        events = [event async for event in proxy]
        assert_type(events, list[RawMessageStreamEvent])
        assert events[-1].type == "message_stop"
    assert len(captures) == 1
    assert response.is_closed


@pytest.mark.parametrize("via", ["iter", "text", "final"])
@pytest.mark.parametrize("fail", [False, True])
def test_anthropic_sync_sdk_manager(via: str, fail: bool) -> None:
    response = _anthropic_response(fail=fail)
    captures: list[dict[str, Any]] = []
    with anthropic.Anthropic(
        api_key="test", http_client=httpx2.Client(transport=_transport(response))
    ) as client:
        manager = AnthropicStreamManagerCapture(
            client.messages.stream(model="test", max_tokens=5, messages=[]),
            {},
            captures.append,
        )
        error: anthropic.APIError | None = None
        try:
            with manager as stream:
                if via == "iter":
                    events = list(stream)
                    if TYPE_CHECKING:
                        assert_type(events, list[ParsedMessageStreamEvent[None]])
                elif via == "text":
                    assert "".join(stream.text_stream) == "hello"
                else:
                    assert isinstance(stream.get_final_message(), Message)
                assert stream.get_final_text() == "hello"
        except anthropic.APIError as exc:
            error = exc
        assert response.is_closed
    assert len(captures) == 1
    if fail:
        assert error is not None
        assert captures[0]["error"] is error
    else:
        assert error is None
        assert "error" not in captures[0]
    message = captures[0]["response"]
    assert isinstance(message, Message)
    assert message.content[0].type == "text"
    assert message.content[0].text == "hello"


@pytest.mark.asyncio
@pytest.mark.parametrize("via", ["iter", "text", "final"])
@pytest.mark.parametrize("fail", [False, True])
async def test_anthropic_async_sdk_manager(via: str, fail: bool) -> None:
    response = _anthropic_response(fail=fail)
    captures: list[dict[str, Any]] = []
    async with anthropic.AsyncAnthropic(
        api_key="test", http_client=httpx2.AsyncClient(transport=_transport(response))
    ) as client:
        manager = AnthropicAsyncStreamManagerCapture(
            client.messages.stream(model="test", max_tokens=5, messages=[]),
            {},
            captures.append,
        )
        error: anthropic.APIError | None = None
        try:
            async with manager as stream:
                if via == "iter":
                    events = [event async for event in stream]
                    if TYPE_CHECKING:
                        assert_type(events, list[ParsedMessageStreamEvent[None]])
                elif via == "text":
                    assert (
                        "".join([text async for text in stream.text_stream]) == "hello"
                    )
                else:
                    assert isinstance(await stream.get_final_message(), Message)
                assert await stream.get_final_text() == "hello"
        except anthropic.APIError as exc:
            error = exc
        assert response.is_closed
    assert len(captures) == 1
    if fail:
        assert error is not None
        assert captures[0]["error"] is error
    else:
        assert error is None
        assert "error" not in captures[0]
    message = captures[0]["response"]
    assert isinstance(message, Message)
    assert message.content[0].type == "text"
    assert message.content[0].text == "hello"


class _Counter:
    value = 0

    def increment(self, amount: int = 1) -> int:
        self.value += amount
        return self.value


class _CounterProxy(TypedObjectProxy[_Counter]):
    value: int
    _self_marker: str


def test_proxy_attribute_isolation_and_unwrapping() -> None:
    counter = _Counter()
    proxy = _CounterProxy(counter)
    assert_type(proxy.__wrapped__, _Counter)
    proxy.value = 5
    proxy._self_marker = "private"
    assert counter.value == 5
    assert proxy.value == 5
    assert proxy._self_marker == "private"
    assert not hasattr(counter, "_self_marker")
    assert proxy.__wrapped__ is counter
    assert isinstance(proxy, _Counter)


def test_function_wrapper_preserves_binding_and_signature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = _Counter.increment
    monkeypatch.setattr(_Counter, "increment", original)
    instances: list[object] = []

    def wrapper(
        wrapped: Any, instance: Any, args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> Any:
        instances.append(instance)
        return wrapped(*args, **kwargs)

    wrap_function_wrapper(__name__, "_Counter.increment", wrapper)
    counter = _Counter()
    assert counter.increment(amount=3) == 3
    assert _Counter.increment(counter, 2) == 5
    assert instances == [counter, counter]
    assert inspect.unwrap(_Counter.increment) is original
    assert inspect.signature(_Counter.increment) == inspect.signature(original)
