"""Google GenAI SDK provider for capturing LLM calls."""

from typing import Any, AsyncIterator, Iterator

from inspect_ai.event import Event, ModelEvent
from inspect_ai.model._generate_config import GenerateConfig
from inspect_ai.tool import Tool
from inspect_ai.tool._tool_choice import ToolChoice, ToolFunction
from inspect_ai.tool._tool_info import ToolInfo
from inspect_ai.tool._tool_params import ToolParams
from inspect_ai.tool._tool_util import tool_to_tool_info
from inspect_ai.tool._tools._code_execution import (
    CodeExecutionProviders,
    code_execution,
)
from inspect_ai.tool._tools._web_search._web_search import (
    WebSearchProviders,
    web_search,
)

from .provider import ObserveEmit


class GoogleProvider:
    """Provider for capturing Google GenAI SDK calls.

    Patches both sync and async generate_content methods,
    including streaming variants.
    """

    def install(self, emit: ObserveEmit) -> None:
        """Install patches for Google GenAI SDK methods."""
        try:
            import google.genai  # noqa: F401
        except ImportError:
            raise ImportError(
                "The 'google-genai' package is required to use provider='google'. "
                "Install it with: pip install google-genai"
            ) from None

        from wrapt import wrap_function_wrapper  # type: ignore[import-untyped]

        # Check if response is a stream (generator)
        def is_sync_stream(response: Any) -> bool:
            import types

            return isinstance(response, types.GeneratorType)

        def is_async_stream(response: Any) -> bool:
            import types

            return isinstance(response, types.AsyncGeneratorType)

        def _extract_model(instance: Any, kwargs: dict[str, Any]) -> str:
            """Extract model identifier from kwargs or instance."""
            if model := kwargs.get("model"):
                return str(model)
            if hasattr(instance, "_model"):
                return str(instance._model)
            return "unknown"

        # Sync wrapper for Models.generate_content
        def sync_generate_wrapper(
            wrapped: Any, instance: Any, args: tuple[Any, ...], kwargs: dict[str, Any]
        ) -> Any:
            response = wrapped(*args, **kwargs)
            model = _extract_model(instance, kwargs)

            # Check if streaming
            if is_sync_stream(response):
                return GoogleStreamCapture(
                    response,
                    {
                        "model": model,
                        **kwargs,
                        "contents": args[0] if args else [],
                    },
                    emit,
                )

            emit(
                {
                    "request": {
                        "model": model,
                        **kwargs,
                        "contents": args[0] if args else [],
                    },
                    "response": response,
                }
            )
            return response

        # Async wrapper for AsyncModels.generate_content
        def async_generate_wrapper(
            wrapped: Any, instance: Any, args: tuple[Any, ...], kwargs: dict[str, Any]
        ) -> Any:
            model = _extract_model(instance, kwargs)

            async def _async_wrapper() -> Any:
                response = await wrapped(*args, **kwargs)

                # Check if streaming
                if is_async_stream(response):
                    return GoogleAsyncStreamCapture(
                        response,
                        {
                            "model": model,
                            **kwargs,
                            "contents": args[0] if args else [],
                        },
                        emit,
                    )

                emit(
                    {
                        "request": {
                            "model": model,
                            **kwargs,
                            "contents": args[0] if args else [],
                        },
                        "response": response,
                    }
                )
                return response

            return _async_wrapper()

        # Sync wrapper for streaming
        def sync_stream_wrapper(
            wrapped: Any, instance: Any, args: tuple[Any, ...], kwargs: dict[str, Any]
        ) -> Any:
            response = wrapped(*args, **kwargs)
            model = _extract_model(instance, kwargs)

            return GoogleStreamCapture(
                response,
                {"model": model, **kwargs, "contents": args[0] if args else []},
                emit,
            )

        # Async wrapper for streaming
        def async_stream_wrapper(
            wrapped: Any, instance: Any, args: tuple[Any, ...], kwargs: dict[str, Any]
        ) -> Any:
            model = _extract_model(instance, kwargs)

            async def _async_wrapper() -> Any:
                response = await wrapped(*args, **kwargs)
                return GoogleAsyncStreamCapture(
                    response,
                    {
                        "model": model,
                        **kwargs,
                        "contents": args[0] if args else [],
                    },
                    emit,
                )

            return _async_wrapper()

        # Patch Models.generate_content
        try:
            wrap_function_wrapper(
                "google.genai.models",
                "Models.generate_content",
                sync_generate_wrapper,
            )
            wrap_function_wrapper(
                "google.genai.models",
                "AsyncModels.generate_content",
                async_generate_wrapper,
            )
        except (ImportError, AttributeError):
            pass

        # Patch streaming methods if they exist separately
        try:
            wrap_function_wrapper(
                "google.genai.models",
                "Models.generate_content_stream",
                sync_stream_wrapper,
            )
            wrap_function_wrapper(
                "google.genai.models",
                "AsyncModels.generate_content_stream",
                async_stream_wrapper,
            )
        except (ImportError, AttributeError):
            pass

    def _merge_streaming_response(
        self, last_chunk: Any, accumulated_parts: dict[int, list[Any]]
    ) -> Any:
        """Merge accumulated streaming parts into a response structure.

        Follows the pattern from inspect_ai's _stream_generate_content:
        - Merges consecutive text parts
        - Handles thinking blocks (thought=True)
        - Preserves tool calls (function_call, executable_code)
        - Handles thought signatures
        """
        try:
            from google.genai.types import Candidate, Content, GenerateContentResponse
        except ImportError:
            return last_chunk

        if not accumulated_parts:
            return last_chunk

        final_candidates = []
        for idx in sorted(accumulated_parts.keys()):
            parts = accumulated_parts[idx]
            merged_parts = self._merge_candidate_parts(parts)
            last_candidate = self._find_candidate(last_chunk, idx)

            candidate = Candidate(
                index=idx,
                content=Content(parts=merged_parts, role="model"),
                finish_reason=getattr(last_candidate, "finish_reason", None)
                if last_candidate
                else None,
                safety_ratings=getattr(last_candidate, "safety_ratings", None)
                if last_candidate
                else None,
            )
            final_candidates.append(candidate)

        return GenerateContentResponse(
            candidates=final_candidates,
            usage_metadata=getattr(last_chunk, "usage_metadata", None),
            model_version=getattr(last_chunk, "model_version", None),
        )

    def _merge_candidate_parts(self, parts: list[Any]) -> list[Any]:
        """Merge streaming parts for a single candidate.

        Handles thinking blocks, text accumulation, and tool calls.
        """
        from google.genai.types import Part

        merged: list[Part] = []
        thinking_texts: list[str] = []
        output_texts: list[str] = []

        def flush_thinking() -> None:
            if thinking_texts:
                merged.append(Part(thought=True, text="".join(thinking_texts)))
                thinking_texts.clear()

        def flush_output() -> None:
            if output_texts:
                merged.append(Part(text="".join(output_texts)))
                output_texts.clear()

        for part in parts:
            # Handle thought signature (encrypted reasoning)
            if hasattr(part, "thought_signature") and part.thought_signature:
                flush_thinking()
                self._handle_signed_part(part, merged, output_texts)

            # Handle thinking block (unencrypted reasoning)
            elif self._is_thinking_part(part):
                flush_output()
                thinking_texts.append(part.text)

            # Handle regular text
            elif hasattr(part, "text") and part.text:
                flush_thinking()
                output_texts.append(part.text)

            # Handle other parts (function calls, code, etc.)
            else:
                flush_thinking()
                flush_output()
                merged.append(part)

        # Flush remaining
        flush_thinking()
        flush_output()
        return merged

    def _handle_signed_part(
        self, part: Any, merged: list[Any], output_texts: list[str]
    ) -> None:
        """Handle a part with thought_signature."""
        from google.genai.types import Part

        if hasattr(part, "text") and part.text:
            combined = "".join(output_texts) + part.text
            merged.append(Part(thought_signature=part.thought_signature, text=combined))
            output_texts.clear()
        elif hasattr(part, "function_call") and part.function_call:
            if output_texts:
                merged.append(Part(text="".join(output_texts)))
                output_texts.clear()
            merged.append(
                Part(
                    thought_signature=part.thought_signature,
                    function_call=part.function_call,
                )
            )
        elif hasattr(part, "executable_code") and part.executable_code:
            if output_texts:
                merged.append(Part(text="".join(output_texts)))
                output_texts.clear()
            merged.append(
                Part(
                    thought_signature=part.thought_signature,
                    executable_code=part.executable_code,
                )
            )
        elif output_texts:
            merged.append(
                Part(
                    thought_signature=part.thought_signature,
                    text="".join(output_texts),
                )
            )
            output_texts.clear()

    def _is_thinking_part(self, part: Any) -> bool:
        """Check if part is a thinking block (unencrypted reasoning)."""
        return (
            hasattr(part, "thought")
            and part.thought is True
            and hasattr(part, "text")
            and part.text
        )

    def _find_candidate(self, chunk: Any, idx: int) -> Any:
        """Find candidate by index in a chunk."""
        if hasattr(chunk, "candidates") and chunk.candidates:
            for c in chunk.candidates:
                if getattr(c, "index", 0) == idx:
                    return c
        return None

    async def build_event(self, data: dict[str, Any]) -> Event:
        """Build ModelEvent from captured Google GenAI request/response."""
        from inspect_ai.model import messages_from_google, model_output_from_google

        request = data["request"]
        response = data["response"]
        # For streaming, we accumulate parts across chunks
        accumulated_parts = data.get("accumulated_parts")

        # Extract system instruction if present
        system_instruction = request.get("system_instruction")
        if system_instruction and hasattr(system_instruction, "parts"):
            system_instruction = " ".join(
                part.text for part in system_instruction.parts if hasattr(part, "text")
            )

        contents = request.get("contents", [])
        model_name = request.get("model", "unknown")

        input_messages = await messages_from_google(
            contents,
            system_instruction=system_instruction,
            model=model_name,
        )

        # For streaming, we need to construct a response with merged parts
        # following the pattern from inspect_ai's _stream_generate_content
        if accumulated_parts:
            response = self._merge_streaming_response(response, accumulated_parts)

        output = await model_output_from_google(response, model=model_name)

        tools: list[ToolInfo] = []
        tool_choice: ToolChoice | None = None
        config: GenerateConfig = GenerateConfig()

        # Extract tools
        try:
            google_tools = request.get("tools", [])
            if google_tools:
                # Convert tool objects to dicts if needed
                tool_dicts: list[dict[str, Any]] = []
                for tool in google_tools:
                    if hasattr(tool, "model_dump"):
                        tool_dicts.append(tool.model_dump())
                    elif hasattr(tool, "to_dict"):
                        tool_dicts.append(tool.to_dict())
                    elif isinstance(tool, dict):
                        tool_dicts.append(tool)
                raw_tools = tools_from_google_tools(tool_dicts)
                # Convert Tool to ToolInfo if needed
                for t in raw_tools:
                    if isinstance(t, ToolInfo):
                        tools.append(t)
                    else:
                        tools.append(tool_to_tool_info(t))
        except Exception:
            pass

        # Extract tool choice
        try:
            tool_config = request.get("tool_config")
            if tool_config:
                if hasattr(tool_config, "model_dump"):
                    tool_config = tool_config.model_dump()
                elif hasattr(tool_config, "to_dict"):
                    tool_config = tool_config.to_dict()
                tool_choice = tool_choice_from_google_tool_config(tool_config)
        except Exception:
            pass

        # Extract generation config
        try:
            gen_config = request.get("generation_config", {})
            if gen_config:
                if hasattr(gen_config, "model_dump"):
                    gen_config = gen_config.model_dump()
                elif hasattr(gen_config, "to_dict"):
                    gen_config = gen_config.to_dict()
                elif not isinstance(gen_config, dict):
                    gen_config = {}
                config = generate_config_from_google(gen_config)
        except Exception:
            pass

        return ModelEvent(
            model=model_name,
            input=input_messages,
            tools=tools,
            tool_choice=tool_choice if tool_choice else "auto",
            config=config,
            output=output,
        )


"""Google GenAI extraction utilities.

These functions extract Inspect AI types from Google GenAI API parameters.
Copied from pending Inspect AI PR #3055 (not yet merged).

TODO: Once PR #3055 is merged, replace this with imports from
inspect_ai.agent._bridge.google_api_impl
"""


def generate_config_from_google(generation_config: dict[str, Any]) -> GenerateConfig:
    """Extract GenerateConfig from Google API parameters."""
    config = GenerateConfig()

    # From generationConfig
    # Note: Some models don't allow both temperature and top_p
    # If temperature is specified, prefer it over top_p
    has_temperature = "temperature" in generation_config
    if has_temperature:
        config.temperature = generation_config["temperature"]
    if "maxOutputTokens" in generation_config:
        config.max_tokens = generation_config["maxOutputTokens"]
    if "max_output_tokens" in generation_config:
        config.max_tokens = generation_config["max_output_tokens"]
    # Only set top_p if temperature wasn't set (they're often mutually exclusive)
    # Check both camelCase (Gemini) and snake_case variants
    if (
        "topP" in generation_config or "top_p" in generation_config
    ) and not has_temperature:
        config.top_p = generation_config.get("topP", generation_config.get("top_p"))
    if "topK" in generation_config or "top_k" in generation_config:
        config.top_k = generation_config.get("topK", generation_config.get("top_k"))
    if "stopSequences" in generation_config or "stop_sequences" in generation_config:
        config.stop_seqs = generation_config.get(
            "stopSequences", generation_config.get("stop_sequences")
        )

    return config


def tools_from_google_tools(
    google_tools: list[dict[str, Any]] | None,
    web_search_providers: WebSearchProviders | None = None,
    code_execution_providers: CodeExecutionProviders | None = None,
) -> list[ToolInfo | Tool]:
    """Translate Google tools format to Inspect tools."""
    tools: list[ToolInfo | Tool] = []

    for tool in google_tools or []:
        if "functionDeclarations" in tool:
            for func_decl in tool["functionDeclarations"]:
                parameters = func_decl.get(
                    "parameters", func_decl.get("parametersJsonSchema", {})
                )
                tools.append(
                    ToolInfo(
                        name=func_decl.get("name", ""),
                        description=func_decl.get("description", ""),
                        parameters=ToolParams.model_validate(parameters)
                        if parameters
                        else ToolParams(),
                    )
                )
        elif "function_declarations" in tool:
            # snake_case variant
            for func_decl in tool["function_declarations"]:
                parameters = func_decl.get(
                    "parameters", func_decl.get("parameters_json_schema", {})
                )
                tools.append(
                    ToolInfo(
                        name=func_decl.get("name", ""),
                        description=func_decl.get("description", ""),
                        parameters=ToolParams.model_validate(parameters)
                        if parameters
                        else ToolParams(),
                    )
                )
        elif "googleSearch" in tool or "google_search" in tool:
            tools.append(web_search(web_search_providers or {}))
        elif "codeExecution" in tool or "code_execution" in tool:
            tools.append(code_execution(providers=code_execution_providers or {}))
        elif "googleSearchRetrieval" in tool or "google_search_retrieval" in tool:
            tools.append(web_search(web_search_providers or {}))

    return tools


def tool_choice_from_google_tool_config(
    tool_config: dict[str, Any] | None,
) -> ToolChoice | None:
    """Translate Google toolConfig to Inspect tool choice."""
    if not tool_config:
        return None

    function_calling_config = tool_config.get(
        "functionCallingConfig", tool_config.get("function_calling_config", {})
    )
    mode = function_calling_config.get("mode", "AUTO")

    match mode:
        case "AUTO":
            return "auto"
        case "ANY":
            return "any"
        case "NONE":
            return "none"
        case _:
            allowed = function_calling_config.get(
                "allowedFunctionNames",
                function_calling_config.get("allowed_function_names", []),
            )
            if allowed and len(allowed) == 1:
                return ToolFunction(name=allowed[0])
            return "auto"


# =============================================================================
# Stream Capture Wrappers
# =============================================================================


class GoogleStreamAccumulator:
    """Helper class to accumulate Google GenAI stream chunks.

    Google streams are incremental - each chunk contains new parts.
    This accumulator collects all parts by candidate index following the
    same pattern as inspect_ai's _stream_generate_content.
    """

    def __init__(self) -> None:
        self.candidates_parts: dict[int, list[Any]] = {}
        self.last_chunk: Any = None

    def accumulate_chunk(self, chunk: Any) -> None:
        """Accumulate parts from a streaming chunk."""
        self.last_chunk = chunk
        if hasattr(chunk, "candidates") and chunk.candidates:
            for candidate in chunk.candidates:
                idx = getattr(candidate, "index", 0) or 0
                if idx not in self.candidates_parts:
                    self.candidates_parts[idx] = []
                if (
                    hasattr(candidate, "content")
                    and candidate.content
                    and hasattr(candidate.content, "parts")
                    and candidate.content.parts
                ):
                    self.candidates_parts[idx].extend(candidate.content.parts)

    def get_response_data(self, request_kwargs: dict[str, Any]) -> dict[str, Any]:
        """Get the accumulated response data for emission."""
        return {
            "request": request_kwargs,
            "response": self.last_chunk,
            "accumulated_parts": self.candidates_parts,
        }


class GoogleStreamCapture:
    """Capture wrapper for Google GenAI sync streams."""

    def __init__(
        self,
        stream: Any,
        request_kwargs: dict[str, Any],
        emit: ObserveEmit,
    ) -> None:
        self._stream = stream
        self._request_kwargs = request_kwargs
        self._emit = emit
        self._accumulator = GoogleStreamAccumulator()

    def __iter__(self) -> Iterator[Any]:
        for chunk in self._stream:
            self._accumulator.accumulate_chunk(chunk)
            yield chunk

        if self._accumulator.last_chunk is not None:
            self._emit(self._accumulator.get_response_data(self._request_kwargs))


class GoogleAsyncStreamCapture:
    """Capture wrapper for Google GenAI async streams."""

    def __init__(
        self,
        stream: Any,
        request_kwargs: dict[str, Any],
        emit: ObserveEmit,
    ) -> None:
        self._stream = stream
        self._request_kwargs = request_kwargs
        self._emit = emit
        self._accumulator = GoogleStreamAccumulator()

    async def __aiter__(self) -> AsyncIterator[Any]:
        async for chunk in self._stream:
            self._accumulator.accumulate_chunk(chunk)
            yield chunk

        if self._accumulator.last_chunk is not None:
            self._emit(self._accumulator.get_response_data(self._request_kwargs))
