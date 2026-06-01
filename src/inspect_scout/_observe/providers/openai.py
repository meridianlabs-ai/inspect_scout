"""OpenAI SDK provider for capturing LLM calls."""

from typing import Any, AsyncIterator, Iterator

from inspect_ai.event import Event, ModelEvent
from inspect_ai.model import StopReason
from inspect_ai.model._generate_config import GenerateConfig
from inspect_ai.tool._tool_choice import ToolChoice
from inspect_ai.tool._tool_info import ToolInfo
from wrapt import ObjectProxy  # type: ignore[import-untyped]

from .provider import ObserveEmit


def _stop_reason_from_openai_error(error: Exception) -> StopReason | None:
    """Map an OpenAI ``APIError`` raised mid-stream to an inspect ``StopReason``.

    Mirrors the error-code detection in
    ``inspect_ai.model._openai.openai_handle_bad_request``.
    """
    code = getattr(error, "code", None)
    if code in (
        "invalid_prompt",
        "content_policy_violation",
        "content_filter",
        "cyber_policy",
    ):
        return "content_filter"
    if code == "context_length_exceeded":
        return "model_length"
    return None


def _error_message(error: Exception) -> str:
    """Extract the human-readable message from an OpenAI error.

    Mirrors ``inspect_ai.model._openai.openai_handle_bad_request``.
    """
    body = getattr(error, "body", None)
    if isinstance(body, dict) and "message" in body:
        return str(body.get("message"))
    return getattr(error, "message", None) or str(error)


def _response_is_empty(response: Any) -> bool:
    """True if the captured response carries no usable data.

    Happens when an error fires before any chunk/event is accumulated, or
    when a non-streaming call raised before returning a response. Handles
    both the Chat Completions accumulator-dict shape and the Responses API
    Response-object shape.
    """
    if response is None:
        return True
    if isinstance(response, dict):
        return not response.get("id") and not response.get("choices")
    return not getattr(response, "id", None) and not getattr(response, "output", None)


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

        def _is_stream_type(response: Any, module: str, class_name: str) -> bool:
            """Check if response is an instance of a stream class.

            Args:
                response: The response object to check.
                module: Module path (e.g., "openai" or "openai.lib.streaming.responses").
                class_name: Class name (e.g., "Stream", "AsyncStream").

            Returns:
                True if response is an instance of the specified class.
            """
            try:
                import importlib

                mod = importlib.import_module(module)
                cls = getattr(mod, class_name)
                return isinstance(response, cls)
            except (ImportError, AttributeError):
                return False

        def sync_chat_wrapper(
            wrapped: Any, instance: Any, args: tuple[Any, ...], kwargs: dict[str, Any]
        ) -> Any:
            from openai import APIStatusError

            try:
                response = wrapped(*args, **kwargs)
            except APIStatusError as e:
                emit(
                    {
                        "request": kwargs,
                        "response": None,
                        "api": "completions",
                        "error": e,
                    }
                )
                raise

            if _is_stream_type(response, "openai", "Stream"):
                return OpenAIChatStreamCapture(response, kwargs, emit)

            emit({"request": kwargs, "response": response, "api": "completions"})
            return response

        def async_chat_wrapper(
            wrapped: Any, instance: Any, args: tuple[Any, ...], kwargs: dict[str, Any]
        ) -> Any:
            from openai import APIStatusError

            async def _async_wrapper() -> Any:
                try:
                    response = await wrapped(*args, **kwargs)
                except APIStatusError as e:
                    emit(
                        {
                            "request": kwargs,
                            "response": None,
                            "api": "completions",
                            "error": e,
                        }
                    )
                    raise

                if _is_stream_type(response, "openai", "AsyncStream"):
                    return OpenAIChatAsyncStreamCapture(response, kwargs, emit)

                emit({"request": kwargs, "response": response, "api": "completions"})
                return response

            return _async_wrapper()

        def sync_responses_wrapper(
            wrapped: Any, instance: Any, args: tuple[Any, ...], kwargs: dict[str, Any]
        ) -> Any:
            from openai import APIStatusError

            try:
                response = wrapped(*args, **kwargs)
            except APIStatusError as e:
                emit(
                    {
                        "request": kwargs,
                        "response": None,
                        "api": "responses",
                        "error": e,
                    }
                )
                raise

            # Check for ResponseStream (high-level) or Stream (with stream=True)
            if _is_stream_type(
                response, "openai.lib.streaming.responses", "ResponseStream"
            ) or _is_stream_type(response, "openai", "Stream"):
                return OpenAIResponsesStreamCapture(response, kwargs, emit)

            emit({"request": kwargs, "response": response, "api": "responses"})
            return response

        def async_responses_wrapper(
            wrapped: Any, instance: Any, args: tuple[Any, ...], kwargs: dict[str, Any]
        ) -> Any:
            from openai import APIStatusError

            async def _async_wrapper() -> Any:
                try:
                    response = await wrapped(*args, **kwargs)
                except APIStatusError as e:
                    emit(
                        {
                            "request": kwargs,
                            "response": None,
                            "api": "responses",
                            "error": e,
                        }
                    )
                    raise

                # Check for AsyncResponseStream (high-level) or AsyncStream (with stream=True)
                if _is_stream_type(
                    response, "openai.lib.streaming.responses", "AsyncResponseStream"
                ) or _is_stream_type(response, "openai", "AsyncStream"):
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
        error = data.get("error")

        if error is not None and _response_is_empty(response):
            # Error fired before any usable response data — e.g. content-policy
            # 400 (non-streaming) or an SSE error event before the first chunk
            # (streaming). Synthesize the event from request + error rather than
            # validating an empty response payload.
            event = await self._build_error_event(request, error, api)
        elif api == "responses":
            event = await self._build_responses_event(request, response)
        else:
            event = await self._build_completions_event(request, response)

        if error is not None:
            event.error = repr(error)
            stop_reason = _stop_reason_from_openai_error(error)
            if stop_reason is not None:
                for choice in event.output.choices:
                    if choice.stop_reason == "unknown":
                        choice.stop_reason = stop_reason
        return event

    async def _build_error_event(
        self, request: dict[str, Any], error: Exception, api: str
    ) -> ModelEvent:
        """Build a ModelEvent from a call that produced no response payload.

        Triggered by a non-streaming content-policy 400 or an SSE error event
        before the first chunk/event. Mirrors
        ``inspect_ai.model._openai.openai_handle_bad_request``: a synthetic
        single-choice output carrying the error message as content, with
        stop_reason inferred from the error code. Caller sets ``event.error``.
        """
        from inspect_ai.model import (
            ModelOutput,
            messages_from_openai,
            messages_from_openai_responses,
        )

        model = request.get("model", "unknown")
        if api == "responses":
            input_param = request.get("input", [])
            if isinstance(input_param, str):
                input_param = [{"role": "user", "content": input_param}]
            input_messages = await messages_from_openai_responses(
                input_param, model=model
            )
        else:
            input_messages = await messages_from_openai(
                request.get("messages", []), model=model
            )
        stop_reason = _stop_reason_from_openai_error(error) or "unknown"
        output = ModelOutput.from_content(
            model=model,
            content=_error_message(error),
            stop_reason=stop_reason,
        )
        return ModelEvent(
            model=model,
            input=input_messages,
            tools=[],
            tool_choice="auto",
            config=GenerateConfig(),
            output=output,
        )

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

        # A stream that errored mid-way has choices with finish_reason=None,
        # which ChatCompletion.model_validate rejects. Fill a placeholder so the
        # converter runs, then mark the resulting stop_reason as 'unknown'.
        unfinished: set[int] = set()
        if isinstance(response, dict):
            for choice in response.get("choices", []):
                if choice.get("finish_reason") is None:
                    unfinished.add(choice.get("index", 0))
                    choice["finish_reason"] = "stop"

        output = await model_output_from_openai(response)
        for i in unfinished:
            if i < len(output.choices):
                output.choices[i].stop_reason = "unknown"

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
                elif tool_or_info is not None:
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


class OpenAIChatStreamAccumulator:
    """Helper class to accumulate OpenAI Chat Completions stream chunks.

    This class contains the shared accumulation logic used by both sync and async
    stream capture wrappers, avoiding code duplication.
    """

    def __init__(self) -> None:
        self.accumulated: dict[str, Any] = {
            "id": None,
            "object": "chat.completion",
            "created": 0,
            "model": None,
            "choices": [],
            "usage": None,
        }

    def accumulate_chunk(self, chunk: Any) -> None:
        """Accumulate a chunk into the complete response."""
        if chunk.id:
            self.accumulated["id"] = chunk.id
        if chunk.model:
            self.accumulated["model"] = chunk.model
        if hasattr(chunk, "created") and chunk.created:
            self.accumulated["created"] = chunk.created
        if chunk.usage:
            self.accumulated["usage"] = chunk.usage

        for choice in chunk.choices:
            # Ensure we have enough choice slots
            while len(self.accumulated["choices"]) <= choice.index:
                self.accumulated["choices"].append(
                    {
                        "index": len(self.accumulated["choices"]),
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [],
                        },
                        "finish_reason": None,
                    }
                )

            acc_choice = self.accumulated["choices"][choice.index]

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

    def get_response(self) -> dict[str, Any]:
        """Get the accumulated response, cleaning up empty tool_calls."""
        for choice in self.accumulated["choices"]:
            if not choice["message"]["tool_calls"]:
                del choice["message"]["tool_calls"]
        return self.accumulated


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
        self._self_accumulator = OpenAIChatStreamAccumulator()

    def __iter__(self) -> Iterator[Any]:
        error: Exception | None = None
        try:
            for chunk in self.__wrapped__:
                self._self_accumulator.accumulate_chunk(chunk)
                yield chunk
        except Exception as e:
            error = e
            raise
        finally:
            data: dict[str, Any] = {
                "request": self._self_request_kwargs,
                "response": self._self_accumulator.get_response(),
                "api": "completions",
            }
            if error is not None:
                data["error"] = error
            self._self_emit(data)


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
        self._self_accumulator = OpenAIChatStreamAccumulator()

    async def __aiter__(self) -> AsyncIterator[Any]:
        error: Exception | None = None
        try:
            async for chunk in self.__wrapped__:
                self._self_accumulator.accumulate_chunk(chunk)
                yield chunk
        except Exception as e:
            error = e
            raise
        finally:
            data: dict[str, Any] = {
                "request": self._self_request_kwargs,
                "response": self._self_accumulator.get_response(),
                "api": "completions",
            }
            if error is not None:
                data["error"] = error
            self._self_emit(data)


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
        self._self_response_snapshot: Any = None

    def __iter__(self) -> Iterator[Any]:
        error: Exception | None = None
        try:
            for event in self.__wrapped__:
                # Track the latest Response snapshot from any lifecycle event
                # (created/queued/in_progress/completed/incomplete/failed) so a
                # mid-stream error still has something to emit.
                if hasattr(event, "response"):
                    self._self_response_snapshot = event.response
                yield event
        except Exception as e:
            error = e
            raise
        finally:
            # Emit when we have a snapshot, OR when an error fired before any
            # event arrived (so build_event can synthesize a content-filter
            # event from request + error). A clean iteration with no events
            # and no error stays silent.
            if self._self_response_snapshot is not None or error is not None:
                data: dict[str, Any] = {
                    "request": self._self_request_kwargs,
                    "response": self._self_response_snapshot,
                    "api": "responses",
                }
                if error is not None:
                    data["error"] = error
                self._self_emit(data)


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
        self._self_response_snapshot: Any = None

    async def __aiter__(self) -> AsyncIterator[Any]:
        error: Exception | None = None
        try:
            async for event in self.__wrapped__:
                # Track the latest Response snapshot from any lifecycle event
                # (created/queued/in_progress/completed/incomplete/failed) so a
                # mid-stream error still has something to emit.
                if hasattr(event, "response"):
                    self._self_response_snapshot = event.response
                yield event
        except Exception as e:
            error = e
            raise
        finally:
            # Emit when we have a snapshot, OR when an error fired before any
            # event arrived (so build_event can synthesize a content-filter
            # event from request + error). A clean iteration with no events
            # and no error stays silent.
            if self._self_response_snapshot is not None or error is not None:
                data: dict[str, Any] = {
                    "request": self._self_request_kwargs,
                    "response": self._self_response_snapshot,
                    "api": "responses",
                }
                if error is not None:
                    data["error"] = error
                self._self_emit(data)
