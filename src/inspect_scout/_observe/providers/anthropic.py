"""Anthropic SDK provider for capturing LLM calls."""

import json
from typing import Any, AsyncIterator, Iterator, cast

from inspect_ai.event import Event, ModelEvent
from inspect_ai.model._generate_config import GenerateConfig
from inspect_ai.tool._tool_choice import ToolChoice
from inspect_ai.tool._tool_info import ToolInfo
from wrapt import ObjectProxy  # type: ignore[import-untyped]

from .provider import ObserveEmit


class AnthropicProvider:
    """Provider for capturing Anthropic SDK calls.

    Patches both the sync and async Messages API methods,
    including streaming variants.
    """

    def install(self, emit: ObserveEmit) -> None:
        """Install patches for Anthropic SDK methods."""
        try:
            import anthropic  # noqa: F401
        except ImportError:
            raise ImportError(
                "The 'anthropic' package is required to use provider='anthropic'. "
                "Install it with: pip install anthropic"
            ) from None

        from wrapt import wrap_function_wrapper

        def is_stream(response: Any) -> bool:
            try:
                from anthropic import Stream
            except ImportError:
                return False
            return isinstance(response, Stream)

        def is_async_stream(response: Any) -> bool:
            try:
                from anthropic import AsyncStream
            except ImportError:
                return False
            return isinstance(response, AsyncStream)

        # Sync wrapper for Messages.create
        def sync_create_wrapper(
            wrapped: Any, instance: Any, args: tuple[Any, ...], kwargs: dict[str, Any]
        ) -> Any:
            response = wrapped(*args, **kwargs)

            if is_stream(response):
                return AnthropicStreamCapture(response, kwargs, emit)

            emit({"request": kwargs, "response": response})
            return response

        # Async wrapper for AsyncMessages.create
        def async_create_wrapper(
            wrapped: Any, instance: Any, args: tuple[Any, ...], kwargs: dict[str, Any]
        ) -> Any:
            async def _async_wrapper() -> Any:
                response = await wrapped(*args, **kwargs)

                if is_async_stream(response):
                    return AnthropicAsyncStreamCapture(response, kwargs, emit)

                emit({"request": kwargs, "response": response})
                return response

            return _async_wrapper()

        # Sync wrapper for Messages.stream (returns MessageStreamManager)
        def sync_stream_wrapper(
            wrapped: Any, instance: Any, args: tuple[Any, ...], kwargs: dict[str, Any]
        ) -> Any:
            stream_manager = wrapped(*args, **kwargs)
            return AnthropicStreamManagerCapture(stream_manager, kwargs, emit)

        # Async wrapper for AsyncMessages.stream
        def async_stream_wrapper(
            wrapped: Any, instance: Any, args: tuple[Any, ...], kwargs: dict[str, Any]
        ) -> Any:
            stream_manager = wrapped(*args, **kwargs)
            return AnthropicAsyncStreamManagerCapture(stream_manager, kwargs, emit)

        # Patch Messages.create
        wrap_function_wrapper(
            "anthropic.resources.messages",
            "Messages.create",
            sync_create_wrapper,
        )
        wrap_function_wrapper(
            "anthropic.resources.messages",
            "AsyncMessages.create",
            async_create_wrapper,
        )

        # Patch Messages.stream
        try:
            wrap_function_wrapper(
                "anthropic.resources.messages",
                "Messages.stream",
                sync_stream_wrapper,
            )
            wrap_function_wrapper(
                "anthropic.resources.messages",
                "AsyncMessages.stream",
                async_stream_wrapper,
            )
        except (ImportError, AttributeError):
            # .stream() may not exist in all versions
            pass

    async def build_event(self, data: dict[str, Any]) -> Event:
        """Build ModelEvent from captured Anthropic request/response."""
        from inspect_ai.agent._bridge.anthropic_api_impl import (
            generate_config_from_anthropic,
            tool_choice_from_anthropic_tool_choice,
            tools_from_anthropic_tools,
        )
        from inspect_ai.model import (
            messages_from_anthropic,
            model_output_from_anthropic,
        )

        request = data["request"]
        response = data["response"]

        # Extract system message if present
        system_message = request.get("system")
        if isinstance(system_message, list):
            # System can be a list of content blocks
            system_message = " ".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in system_message
            )

        input_messages = await messages_from_anthropic(
            request.get("messages", []),
            system_message=system_message,
        )
        output = await model_output_from_anthropic(response)

        tools: list[ToolInfo] = []
        tool_choice: ToolChoice | None = None
        config: GenerateConfig = GenerateConfig()

        try:
            from inspect_ai.tool._tool_util import tool_to_tool_info

            raw_tools = tools_from_anthropic_tools(
                request.get("tools"),
                request.get("mcp_servers"),  # MCP servers if present
                {},  # web_search_providers
                {},  # code_execution_providers
            )
            # Convert Tool to ToolInfo if needed
            for t in raw_tools:
                if isinstance(t, ToolInfo):
                    tools.append(t)
                else:
                    tools.append(tool_to_tool_info(t))
        except Exception:
            pass

        try:
            tool_choice = tool_choice_from_anthropic_tool_choice(
                request.get("tool_choice")
            )
        except Exception:
            pass

        try:
            config = generate_config_from_anthropic(request)
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


class AnthropicStreamCapture(ObjectProxy):  # type: ignore[misc]
    """Capture wrapper for Anthropic sync streams (with stream=True)."""

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
            "type": "message",
            "role": "assistant",
            "model": None,
            "content": [],
            "stop_reason": None,
            "stop_sequence": None,
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }
        self._self_current_block_idx = -1
        self._self_current_block: dict[str, Any] | None = None

    def __iter__(self) -> Iterator[Any]:
        for event in self.__wrapped__:
            self._accumulate_event(event)
            yield event

        self._emit_response()

    def _accumulate_event(self, event: Any) -> None:
        """Accumulate a streaming event into the complete response."""
        event_type = getattr(event, "type", None)

        if event_type == "message_start":
            message = event.message
            self._self_accumulated["id"] = message.id
            self._self_accumulated["model"] = message.model
            if message.usage:
                self._self_accumulated["usage"]["input_tokens"] = (
                    message.usage.input_tokens
                )

        elif event_type == "content_block_start":
            self._self_current_block_idx = event.index
            block = event.content_block
            if block.type == "text":
                self._self_current_block = {"type": "text", "text": ""}
            elif block.type == "thinking":
                self._self_current_block = {"type": "thinking", "thinking": ""}
            elif block.type in ("tool_use", "server_tool_use", "mcp_tool_use"):
                # server_tool_use is for server-side tools like web search/fetch
                # mcp_tool_use is for MCP connector tools
                self._self_current_block = {
                    "type": block.type,
                    "id": block.id,
                    "name": block.name,
                    "input": "",
                }
                # mcp_tool_use also has server_name
                if block.type == "mcp_tool_use":
                    self._self_current_block["server_name"] = getattr(
                        block, "server_name", None
                    )
            elif block.type in ("web_search_tool_result", "web_fetch_tool_result"):
                # Server-side tool results come complete in content_block_start
                self._self_current_block = {
                    "type": block.type,
                    "tool_use_id": getattr(block, "tool_use_id", None),
                    "content": getattr(block, "content", []),
                }
            elif block.type == "mcp_tool_result":
                # MCP tool results
                self._self_current_block = {
                    "type": "mcp_tool_result",
                    "tool_use_id": getattr(block, "tool_use_id", None),
                    "is_error": getattr(block, "is_error", False),
                    "content": getattr(block, "content", []),
                }
            else:
                self._self_current_block = {"type": block.type}
            self._self_accumulated["content"].append(self._self_current_block)

        elif event_type == "content_block_delta":
            if self._self_current_block is not None:
                delta = event.delta
                if delta.type == "text_delta":
                    self._self_current_block["text"] += delta.text
                elif delta.type == "thinking_delta":
                    self._self_current_block["thinking"] += delta.thinking
                elif delta.type == "signature_delta":
                    # Signature for thinking block integrity verification
                    self._self_current_block["signature"] = delta.signature
                elif delta.type == "input_json_delta":
                    self._self_current_block["input"] += delta.partial_json

        elif event_type == "content_block_stop":
            # Finalize current block
            if self._self_current_block and "input" in self._self_current_block:
                # Parse the accumulated JSON string
                try:
                    self._self_current_block["input"] = json.loads(
                        self._self_current_block["input"]
                    )
                except json.JSONDecodeError:
                    self._self_current_block["input"] = {}
            self._self_current_block = None

        elif event_type == "message_delta":
            if event.delta:
                if hasattr(event.delta, "stop_reason"):
                    self._self_accumulated["stop_reason"] = event.delta.stop_reason
                if hasattr(event.delta, "stop_sequence"):
                    self._self_accumulated["stop_sequence"] = event.delta.stop_sequence
            if event.usage:
                self._self_accumulated["usage"]["output_tokens"] = (
                    event.usage.output_tokens
                )

    def _emit_response(self) -> None:
        """Emit the accumulated response."""
        self._self_emit(
            {
                "request": self._self_request_kwargs,
                "response": self._self_accumulated,
            }
        )


class AnthropicAsyncStreamCapture(ObjectProxy):  # type: ignore[misc]
    """Capture wrapper for Anthropic async streams (with stream=True)."""

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
            "type": "message",
            "role": "assistant",
            "model": None,
            "content": [],
            "stop_reason": None,
            "stop_sequence": None,
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }
        self._self_current_block_idx = -1
        self._self_current_block: dict[str, Any] | None = None

    async def __aiter__(self) -> AsyncIterator[Any]:
        async for event in self.__wrapped__:
            self._accumulate_event(event)
            yield event

        self._emit_response()

    def _accumulate_event(self, event: Any) -> None:
        """Accumulate a streaming event into the complete response."""
        event_type = getattr(event, "type", None)

        if event_type == "message_start":
            message = event.message
            self._self_accumulated["id"] = message.id
            self._self_accumulated["model"] = message.model
            if message.usage:
                self._self_accumulated["usage"]["input_tokens"] = (
                    message.usage.input_tokens
                )

        elif event_type == "content_block_start":
            self._self_current_block_idx = event.index
            block = event.content_block
            if block.type == "text":
                self._self_current_block = {"type": "text", "text": ""}
            elif block.type == "thinking":
                self._self_current_block = {"type": "thinking", "thinking": ""}
            elif block.type in ("tool_use", "server_tool_use", "mcp_tool_use"):
                # server_tool_use is for server-side tools like web search/fetch
                # mcp_tool_use is for MCP connector tools
                self._self_current_block = {
                    "type": block.type,
                    "id": block.id,
                    "name": block.name,
                    "input": "",
                }
                # mcp_tool_use also has server_name
                if block.type == "mcp_tool_use":
                    self._self_current_block["server_name"] = getattr(
                        block, "server_name", None
                    )
            elif block.type in ("web_search_tool_result", "web_fetch_tool_result"):
                # Server-side tool results come complete in content_block_start
                self._self_current_block = {
                    "type": block.type,
                    "tool_use_id": getattr(block, "tool_use_id", None),
                    "content": getattr(block, "content", []),
                }
            elif block.type == "mcp_tool_result":
                # MCP tool results
                self._self_current_block = {
                    "type": "mcp_tool_result",
                    "tool_use_id": getattr(block, "tool_use_id", None),
                    "is_error": getattr(block, "is_error", False),
                    "content": getattr(block, "content", []),
                }
            else:
                self._self_current_block = {"type": block.type}
            self._self_accumulated["content"].append(self._self_current_block)

        elif event_type == "content_block_delta":
            if self._self_current_block is not None:
                delta = event.delta
                if delta.type == "text_delta":
                    self._self_current_block["text"] += delta.text
                elif delta.type == "thinking_delta":
                    self._self_current_block["thinking"] += delta.thinking
                elif delta.type == "signature_delta":
                    # Signature for thinking block integrity verification
                    self._self_current_block["signature"] = delta.signature
                elif delta.type == "input_json_delta":
                    self._self_current_block["input"] += delta.partial_json

        elif event_type == "content_block_stop":
            if self._self_current_block and "input" in self._self_current_block:
                try:
                    self._self_current_block["input"] = json.loads(
                        self._self_current_block["input"]
                    )
                except json.JSONDecodeError:
                    self._self_current_block["input"] = {}
            self._self_current_block = None

        elif event_type == "message_delta":
            if event.delta:
                if hasattr(event.delta, "stop_reason"):
                    self._self_accumulated["stop_reason"] = event.delta.stop_reason
                if hasattr(event.delta, "stop_sequence"):
                    self._self_accumulated["stop_sequence"] = event.delta.stop_sequence
            if event.usage:
                self._self_accumulated["usage"]["output_tokens"] = (
                    event.usage.output_tokens
                )

    def _emit_response(self) -> None:
        """Emit the accumulated response."""
        self._self_emit(
            {
                "request": self._self_request_kwargs,
                "response": self._self_accumulated,
            }
        )


class AnthropicStreamManagerCapture(ObjectProxy):  # type: ignore[misc]
    """Capture wrapper for Anthropic MessageStreamManager (sync .stream())."""

    def __init__(
        self,
        stream_manager: Any,
        request_kwargs: dict[str, Any],
        emit: ObserveEmit,
    ) -> None:
        super().__init__(stream_manager)
        self._self_request_kwargs = request_kwargs
        self._self_emit = emit

    def __enter__(self) -> "AnthropicStreamManagerCaptureContext":
        stream = self.__wrapped__.__enter__()
        return AnthropicStreamManagerCaptureContext(
            stream, self._self_request_kwargs, self._self_emit
        )

    def __exit__(self, *args: Any) -> Any:
        return self.__wrapped__.__exit__(*args)


class AnthropicStreamManagerCaptureContext(ObjectProxy):  # type: ignore[misc]
    """Context returned by AnthropicStreamManagerCapture.__enter__."""

    def __init__(
        self,
        stream: Any,
        request_kwargs: dict[str, Any],
        emit: ObserveEmit,
    ) -> None:
        super().__init__(stream)
        self._self_request_kwargs = request_kwargs
        self._self_emit = emit
        self._self_final_message: Any = None

    def __iter__(self) -> Iterator[Any]:
        for event in self.__wrapped__:
            yield event

        # Get final message from stream
        if hasattr(self.__wrapped__, "get_final_message"):
            self._self_final_message = self.__wrapped__.get_final_message()
            self._self_emit(
                {
                    "request": self._self_request_kwargs,
                    "response": self._self_final_message,
                }
            )

    @property
    def text_stream(self) -> Iterator[str]:
        """Pass through text_stream property."""
        for text in self.__wrapped__.text_stream:
            yield text

        if hasattr(self.__wrapped__, "get_final_message"):
            self._self_final_message = self.__wrapped__.get_final_message()
            self._self_emit(
                {
                    "request": self._self_request_kwargs,
                    "response": self._self_final_message,
                }
            )

    def get_final_message(self) -> Any:
        """Get final message and ensure emission."""
        message = self.__wrapped__.get_final_message()
        if self._self_final_message is None:
            self._self_final_message = message
            self._self_emit(
                {
                    "request": self._self_request_kwargs,
                    "response": message,
                }
            )
        return message

    def get_final_text(self) -> str:
        """Get final text."""
        return cast(str, self.__wrapped__.get_final_text())

    def until_done(self) -> None:
        """Consume stream to completion."""
        for _ in self:
            pass


class AnthropicAsyncStreamManagerCapture(ObjectProxy):  # type: ignore[misc]
    """Capture wrapper for Anthropic AsyncMessageStreamManager."""

    def __init__(
        self,
        stream_manager: Any,
        request_kwargs: dict[str, Any],
        emit: ObserveEmit,
    ) -> None:
        super().__init__(stream_manager)
        self._self_request_kwargs = request_kwargs
        self._self_emit = emit

    async def __aenter__(self) -> "AnthropicAsyncStreamManagerCaptureContext":
        stream = await self.__wrapped__.__aenter__()
        return AnthropicAsyncStreamManagerCaptureContext(
            stream, self._self_request_kwargs, self._self_emit
        )

    async def __aexit__(self, *args: Any) -> Any:
        return await self.__wrapped__.__aexit__(*args)


class AnthropicAsyncStreamManagerCaptureContext(ObjectProxy):  # type: ignore[misc]
    """Context returned by AnthropicAsyncStreamManagerCapture.__aenter__."""

    def __init__(
        self,
        stream: Any,
        request_kwargs: dict[str, Any],
        emit: ObserveEmit,
    ) -> None:
        super().__init__(stream)
        self._self_request_kwargs = request_kwargs
        self._self_emit = emit
        self._self_final_message: Any = None

    async def __aiter__(self) -> AsyncIterator[Any]:
        async for event in self.__wrapped__:
            yield event

        if hasattr(self.__wrapped__, "get_final_message"):
            self._self_final_message = await self.__wrapped__.get_final_message()
            self._self_emit(
                {
                    "request": self._self_request_kwargs,
                    "response": self._self_final_message,
                }
            )

    @property
    def text_stream(self) -> AsyncIterator[str]:
        """Pass through async text_stream property."""

        async def _text_stream() -> AsyncIterator[str]:
            async for text in self.__wrapped__.text_stream:
                yield text

            if hasattr(self.__wrapped__, "get_final_message"):
                self._self_final_message = await self.__wrapped__.get_final_message()
                self._self_emit(
                    {
                        "request": self._self_request_kwargs,
                        "response": self._self_final_message,
                    }
                )

        return _text_stream()

    async def get_final_message(self) -> Any:
        """Get final message and ensure emission."""
        message = await self.__wrapped__.get_final_message()
        if self._self_final_message is None:
            self._self_final_message = message
            self._self_emit(
                {
                    "request": self._self_request_kwargs,
                    "response": message,
                }
            )
        return message

    async def get_final_text(self) -> str:
        """Get final text."""
        return cast(str, await self.__wrapped__.get_final_text())

    async def until_done(self) -> None:
        """Consume stream to completion."""
        async for _ in self:
            pass
