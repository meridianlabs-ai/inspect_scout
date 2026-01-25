"""OpenAI SDK provider for capturing LLM calls."""

from typing import Any, AsyncIterator, Iterator

from inspect_ai.event import Event, ModelEvent
from inspect_ai.model._generate_config import GenerateConfig
from inspect_ai.tool._tool_choice import ToolChoice
from inspect_ai.tool._tool_info import ToolInfo
from wrapt import ObjectProxy  # type: ignore[import-untyped]

from .provider import ObserveEmit


class OpenAIProvider:
    """Provider for capturing OpenAI SDK calls.

    Patches both the Completions API and Responses API methods
    to capture LLM calls.
    """

    def install(self, emit: ObserveEmit) -> None:
        """Install patches for OpenAI SDK methods."""
        try:
            import openai  # noqa: F401
        except ImportError:
            raise ImportError(
                "The 'openai' package is required to use provider='openai'. "
                "Install it with: pip install openai"
            ) from None

        from wrapt import wrap_function_wrapper

        # Check if response is a stream
        def is_chat_stream(response: Any) -> bool:
            try:
                from openai import Stream
            except ImportError:
                return False
            return isinstance(response, Stream)

        def is_chat_async_stream(response: Any) -> bool:
            try:
                from openai import AsyncStream
            except ImportError:
                return False
            return isinstance(response, AsyncStream)

        def is_responses_stream(response: Any) -> bool:
            try:
                from openai.lib.streaming.responses import ResponseStream
            except ImportError:
                return False
            return isinstance(response, ResponseStream)

        def is_responses_async_stream(response: Any) -> bool:
            try:
                from openai.lib.streaming.responses import AsyncResponseStream
            except ImportError:
                return False
            return isinstance(response, AsyncResponseStream)

        # Sync wrapper for Chat Completions
        def sync_chat_wrapper(
            wrapped: Any, instance: Any, args: tuple[Any, ...], kwargs: dict[str, Any]
        ) -> Any:
            response = wrapped(*args, **kwargs)

            if is_chat_stream(response):
                return OpenAIChatStreamCapture(response, kwargs, emit)

            emit({"request": kwargs, "response": response, "api": "completions"})
            return response

        # Async wrapper for Chat Completions
        def async_chat_wrapper(
            wrapped: Any, instance: Any, args: tuple[Any, ...], kwargs: dict[str, Any]
        ) -> Any:
            async def _async_wrapper() -> Any:
                response = await wrapped(*args, **kwargs)

                if is_chat_async_stream(response):
                    return OpenAIChatAsyncStreamCapture(response, kwargs, emit)

                emit({"request": kwargs, "response": response, "api": "completions"})
                return response

            return _async_wrapper()

        # Sync wrapper for Responses API
        def sync_responses_wrapper(
            wrapped: Any, instance: Any, args: tuple[Any, ...], kwargs: dict[str, Any]
        ) -> Any:
            response = wrapped(*args, **kwargs)

            if is_responses_stream(response):
                return OpenAIResponsesStreamCapture(response, kwargs, emit)

            emit({"request": kwargs, "response": response, "api": "responses"})
            return response

        # Async wrapper for Responses API
        def async_responses_wrapper(
            wrapped: Any, instance: Any, args: tuple[Any, ...], kwargs: dict[str, Any]
        ) -> Any:
            async def _async_wrapper() -> Any:
                response = await wrapped(*args, **kwargs)

                if is_responses_async_stream(response):
                    return OpenAIResponsesAsyncStreamCapture(response, kwargs, emit)

                emit({"request": kwargs, "response": response, "api": "responses"})
                return response

            return _async_wrapper()

        # Patch Chat Completions
        wrap_function_wrapper(
            "openai.resources.chat.completions",
            "Completions.create",
            sync_chat_wrapper,
        )
        wrap_function_wrapper(
            "openai.resources.chat.completions",
            "AsyncCompletions.create",
            async_chat_wrapper,
        )

        # Patch Responses API
        try:
            wrap_function_wrapper(
                "openai.resources.responses",
                "Responses.create",
                sync_responses_wrapper,
            )
            wrap_function_wrapper(
                "openai.resources.responses",
                "AsyncResponses.create",
                async_responses_wrapper,
            )
        except (ImportError, AttributeError):
            # Responses API may not exist in older versions
            pass

    async def build_event(self, data: dict[str, Any]) -> Event:
        """Build ModelEvent from captured OpenAI request/response."""
        request = data["request"]
        response = data["response"]
        api = data.get("api", "completions")

        if api == "responses":
            return await self._build_responses_event(request, response)
        else:
            return await self._build_completions_event(request, response)

    async def _build_completions_event(
        self, request: dict[str, Any], response: Any
    ) -> ModelEvent:
        """Build ModelEvent from Chat Completions API response."""
        from inspect_ai.agent._bridge.completions import (
            generate_config_from_openai_completions,
            tool_choice_from_openai_tool_choice,
            tools_from_openai_tools,
        )
        from inspect_ai.model import messages_from_openai, model_output_from_openai

        input_messages = await messages_from_openai(
            request.get("messages", []),
            model=request.get("model"),
        )
        output = await model_output_from_openai(response)

        tools: list[ToolInfo] = []
        tool_choice: ToolChoice | None = None
        config: GenerateConfig = GenerateConfig()

        try:
            tools = tools_from_openai_tools(request.get("tools", []))
        except Exception:
            pass

        try:
            tool_choice = tool_choice_from_openai_tool_choice(
                request.get("tool_choice")
            )
        except Exception:
            pass

        try:
            config = generate_config_from_openai_completions(request)
        except Exception:
            pass

        return ModelEvent(
            model=request.get("model", "unknown"),
            input=input_messages,
            tools=tools,
            tool_choice=tool_choice if tool_choice else "auto",
            config=config,
            output=output,
        )

    async def _build_responses_event(
        self, request: dict[str, Any], response: Any
    ) -> ModelEvent:
        """Build ModelEvent from Responses API response."""
        from inspect_ai.agent._bridge.responses_impl import (
            generate_config_from_openai_responses,
            tool_choice_from_responses_tool_choice,
            tool_from_responses_tool,
        )
        from inspect_ai.model import (
            messages_from_openai_responses,
            model_output_from_openai_responses,
        )

        input_param = request.get("input", [])
        if isinstance(input_param, str):
            input_param = [{"role": "user", "content": input_param}]

        input_messages = await messages_from_openai_responses(
            input_param,
            model=request.get("model"),
        )
        output = await model_output_from_openai_responses(response)

        tools: list[ToolInfo] = []
        tool_choice: ToolChoice | None = None
        config: GenerateConfig = GenerateConfig()

        try:
            from inspect_ai.tool._tool_util import tool_to_tool_info

            for tool in request.get("tools", []):
                tool_or_info = tool_from_responses_tool(tool, {}, {})
                # Convert Tool to ToolInfo if needed
                if isinstance(tool_or_info, ToolInfo):
                    tools.append(tool_or_info)
                else:
                    tools.append(tool_to_tool_info(tool_or_info))
        except Exception:
            pass

        try:
            tool_choice = tool_choice_from_responses_tool_choice(
                request.get("tool_choice")
            )
        except Exception:
            pass

        try:
            config = generate_config_from_openai_responses(request)
        except Exception:
            pass

        return ModelEvent(
            model=request.get("model", "unknown"),
            input=input_messages,
            tools=tools,
            tool_choice=tool_choice if tool_choice else "auto",
            config=config,
            output=output,
        )


# =============================================================================
# Stream Capture Wrappers
# =============================================================================


class OpenAIChatStreamCapture(ObjectProxy):  # type: ignore[misc]
    """Capture wrapper for OpenAI Chat Completions sync streams."""

    def __init__(
        self,
        stream: Any,
        request_kwargs: dict[str, Any],
        emit: ObserveEmit,
    ) -> None:
        super().__init__(stream)
        self._self_request_kwargs = request_kwargs
        self._self_emit = emit
        self._self_accumulated: dict[str, Any] = {
            "id": None,
            "object": "chat.completion",
            "created": 0,
            "model": None,
            "choices": [],
            "usage": None,
        }

    def __iter__(self) -> Iterator[Any]:
        for chunk in self.__wrapped__:
            self._accumulate_chunk(chunk)
            yield chunk

        # Stream complete - emit accumulated response
        self._emit_response()

    def _accumulate_chunk(self, chunk: Any) -> None:
        """Accumulate a chunk into the complete response."""
        if chunk.id:
            self._self_accumulated["id"] = chunk.id
        if chunk.model:
            self._self_accumulated["model"] = chunk.model
        if hasattr(chunk, "created") and chunk.created:
            self._self_accumulated["created"] = chunk.created
        if chunk.usage:
            self._self_accumulated["usage"] = chunk.usage

        for choice in chunk.choices:
            # Ensure we have enough choice slots
            while len(self._self_accumulated["choices"]) <= choice.index:
                self._self_accumulated["choices"].append(
                    {
                        "index": len(self._self_accumulated["choices"]),
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [],
                        },
                        "finish_reason": None,
                    }
                )

            acc_choice = self._self_accumulated["choices"][choice.index]

            if choice.finish_reason:
                acc_choice["finish_reason"] = choice.finish_reason

            if choice.delta:
                delta = choice.delta
                if delta.role:
                    acc_choice["message"]["role"] = delta.role
                if delta.content:
                    acc_choice["message"]["content"] += delta.content

                # Handle tool calls
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        tool_calls = acc_choice["message"]["tool_calls"]
                        while len(tool_calls) <= tc.index:
                            tool_calls.append(
                                {
                                    "id": "",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""},
                                }
                            )
                        tc_acc = tool_calls[tc.index]
                        if tc.id:
                            tc_acc["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tc_acc["function"]["name"] += tc.function.name
                            if tc.function.arguments:
                                tc_acc["function"]["arguments"] += tc.function.arguments

    def _emit_response(self) -> None:
        """Emit the accumulated response."""
        # Clean up empty tool_calls lists
        for choice in self._self_accumulated["choices"]:
            if not choice["message"]["tool_calls"]:
                del choice["message"]["tool_calls"]

        self._self_emit(
            {
                "request": self._self_request_kwargs,
                "response": self._self_accumulated,
                "api": "completions",
            }
        )


class OpenAIChatAsyncStreamCapture(ObjectProxy):  # type: ignore[misc]
    """Capture wrapper for OpenAI Chat Completions async streams."""

    def __init__(
        self,
        stream: Any,
        request_kwargs: dict[str, Any],
        emit: ObserveEmit,
    ) -> None:
        super().__init__(stream)
        self._self_request_kwargs = request_kwargs
        self._self_emit = emit
        self._self_accumulated: dict[str, Any] = {
            "id": None,
            "object": "chat.completion",
            "created": 0,
            "model": None,
            "choices": [],
            "usage": None,
        }

    async def __aiter__(self) -> AsyncIterator[Any]:
        async for chunk in self.__wrapped__:
            self._accumulate_chunk(chunk)
            yield chunk

        # Stream complete - emit accumulated response
        self._emit_response()

    def _accumulate_chunk(self, chunk: Any) -> None:
        """Accumulate a chunk into the complete response."""
        if chunk.id:
            self._self_accumulated["id"] = chunk.id
        if chunk.model:
            self._self_accumulated["model"] = chunk.model
        if hasattr(chunk, "created") and chunk.created:
            self._self_accumulated["created"] = chunk.created
        if chunk.usage:
            self._self_accumulated["usage"] = chunk.usage

        for choice in chunk.choices:
            while len(self._self_accumulated["choices"]) <= choice.index:
                self._self_accumulated["choices"].append(
                    {
                        "index": len(self._self_accumulated["choices"]),
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [],
                        },
                        "finish_reason": None,
                    }
                )

            acc_choice = self._self_accumulated["choices"][choice.index]

            if choice.finish_reason:
                acc_choice["finish_reason"] = choice.finish_reason

            if choice.delta:
                delta = choice.delta
                if delta.role:
                    acc_choice["message"]["role"] = delta.role
                if delta.content:
                    acc_choice["message"]["content"] += delta.content

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        tool_calls = acc_choice["message"]["tool_calls"]
                        while len(tool_calls) <= tc.index:
                            tool_calls.append(
                                {
                                    "id": "",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""},
                                }
                            )
                        tc_acc = tool_calls[tc.index]
                        if tc.id:
                            tc_acc["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tc_acc["function"]["name"] += tc.function.name
                            if tc.function.arguments:
                                tc_acc["function"]["arguments"] += tc.function.arguments

    def _emit_response(self) -> None:
        """Emit the accumulated response."""
        for choice in self._self_accumulated["choices"]:
            if not choice["message"]["tool_calls"]:
                del choice["message"]["tool_calls"]

        self._self_emit(
            {
                "request": self._self_request_kwargs,
                "response": self._self_accumulated,
                "api": "completions",
            }
        )


class OpenAIResponsesStreamCapture(ObjectProxy):  # type: ignore[misc]
    """Capture wrapper for OpenAI Responses API sync streams."""

    def __init__(
        self,
        stream: Any,
        request_kwargs: dict[str, Any],
        emit: ObserveEmit,
    ) -> None:
        super().__init__(stream)
        self._self_request_kwargs = request_kwargs
        self._self_emit = emit
        self._self_complete_response: Any = None

    def __iter__(self) -> Iterator[Any]:
        for event in self.__wrapped__:
            # Capture the complete response from response.completed event
            if hasattr(event, "type") and event.type == "response.completed":
                if hasattr(event, "response"):
                    self._self_complete_response = event.response
            yield event

        # Stream complete - emit if we captured a response
        if self._self_complete_response is not None:
            self._self_emit(
                {
                    "request": self._self_request_kwargs,
                    "response": self._self_complete_response,
                    "api": "responses",
                }
            )


class OpenAIResponsesAsyncStreamCapture(ObjectProxy):  # type: ignore[misc]
    """Capture wrapper for OpenAI Responses API async streams."""

    def __init__(
        self,
        stream: Any,
        request_kwargs: dict[str, Any],
        emit: ObserveEmit,
    ) -> None:
        super().__init__(stream)
        self._self_request_kwargs = request_kwargs
        self._self_emit = emit
        self._self_complete_response: Any = None

    async def __aiter__(self) -> AsyncIterator[Any]:
        async for event in self.__wrapped__:
            if hasattr(event, "type") and event.type == "response.completed":
                if hasattr(event, "response"):
                    self._self_complete_response = event.response
            yield event

        if self._self_complete_response is not None:
            self._self_emit(
                {
                    "request": self._self_request_kwargs,
                    "response": self._self_complete_response,
                    "api": "responses",
                }
            )
