"""TypeSafe Jev as an Inspect model provider (``typesafe/<model>``).

Jev is a classifier, not a text generator: ``generate()`` accepts exactly one
user message whose text is a JSON Jev request (see `JevRequest`) and returns
the answers in ``ModelOutput.metadata["answers"]``. Routing Jev through Inspect
this way gives it Inspect's usage accounting, generate cache, retries, and
connection limits.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
from typing import TYPE_CHECKING, Any, TypedDict, cast

from inspect_ai._util.error import PrerequisiteError
from inspect_ai.model import (
    ChatMessage,
    ChatMessageUser,
    GenerateConfig,
    ModelAPI,
    ModelOutput,
    ModelUsage,
    modelapi,
)
from inspect_ai.tool import ToolChoice, ToolInfo
from typing_extensions import NotRequired

if TYPE_CHECKING:
    from typesafe_sdk import AsyncTypeSafeClient, QuestionModel

TYPESAFE_API_KEY = "TYPESAFE_API_KEY"
"""Environment variable holding the TypeSafe API key."""

LONG_CONTEXT_HEADER = {"TypeSafe-Danger-Zone-Long-Context": "true"}
"""Raises Jev's request limit from 64k to ~262k tokens (and lifts the 32k per-question limit)."""

CHARS_PER_TOKEN = 2.3
"""Characters per Jev token; Jev's tokenizer counts ~1.2-1.4x Inspect's default estimate."""

_TOO_LONG_CODE = "max_tokens_exceeded"

JEV_PROVIDER_ATTR = "jev_provider"
"""Class attribute marking a `ModelAPI` that answers Jev requests."""

_NOT_A_JEV_REQUEST = (
    "typesafe/* models are classifiers and cannot generate text: use jev_scanner(), "
    "which sends a JSON {state, questions} request."
)


class JevRequest(TypedDict):
    """A Jev request, sent as the JSON text of a single user message."""

    state: str | dict[str, Any] | list[Any]
    """The content all questions refer to."""

    questions: dict[str, dict[str, Any]]
    """Jev questions (noul/choice/score dicts) keyed by name."""

    long_context: NotRequired[bool]
    """Send the long-context header."""


class JevInputTooLongError(Exception):
    """Jev rejected a request as exceeding its token limit."""


class TypeSafeAPI(ModelAPI):
    """Inspect model provider for TypeSafe System One models (e.g. ``typesafe/jev-1.13.0``).

    Concurrency follows the scan's ``max_connections`` (by default Scout's
    ``max_transcripts``), like any other model.
    """

    jev_provider = True

    def __init__(
        self,
        model_name: str,
        base_url: str | None = None,
        api_key: str | None = None,
        config: GenerateConfig | None = None,
        **model_args: Any,
    ) -> None:
        super().__init__(
            model_name,
            base_url,
            api_key or os.environ.get(TYPESAFE_API_KEY),
            [TYPESAFE_API_KEY],
            config or GenerateConfig(),
        )
        self._client: AsyncTypeSafeClient | None = None
        self._client_loop: asyncio.AbstractEventLoop | None = None

    async def generate(
        self,
        input: list[ChatMessage],
        tools: list[ToolInfo],
        tool_choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        """Answer the Jev request in `input` (see module docstring)."""
        request = parse_jev_request(input, tools)
        client = self._get_client()
        try:
            response = await client.system_one(
                state=request["state"],
                questions=cast("dict[str, QuestionModel]", request["questions"]),
                model=self.model_name,
                extra_headers=LONG_CONTEXT_HEADER
                if request.get("long_context", False)
                else None,
            )
        except Exception as ex:
            _raise_classified(ex)
            raise
        answers = {
            name: answer.model_dump() for name, answer in response.answers.items()
        }
        input_tokens = response.usage.input_tokens or 0
        output_tokens = response.usage.output_tokens or 0
        output = ModelOutput.from_content(
            model=response.model, content=json.dumps(answers)
        )
        output.metadata = {"answers": answers}
        output.usage = ModelUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        )
        return output

    async def count_text_tokens(self, text: str) -> int:
        """Estimate Jev tokens from characters."""
        # round() first: float division can land a hair above an exact count
        return math.ceil(round(len(text) / CHARS_PER_TOKEN, 6))

    def should_retry(self, ex: Exception) -> bool:
        """Retry rate limits, server errors, connection errors, and timeouts."""
        try:
            from typesafe_sdk import (
                TypeSafeAPIConnectionError,
                TypeSafeAPITimeoutError,
                TypeSafeInternalServerError,
                TypeSafeRateLimitError,
            )
        except ImportError:
            return False
        return isinstance(
            ex,
            (
                TypeSafeRateLimitError,
                TypeSafeInternalServerError,
                TypeSafeAPIConnectionError,
                TypeSafeAPITimeoutError,
            ),
        )

    def connection_key(self) -> str:
        """Share the connection pool per API key."""
        return str(self.initial_api_key)

    def _get_client(self) -> AsyncTypeSafeClient:
        # The SDK's HTTP client is bound to an event loop, and each Scout
        # worker process runs its own loop.
        loop = asyncio.get_running_loop()
        if self._client is None or self._client_loop is not loop:
            try:
                from typesafe_sdk import AsyncTypeSafeClient, RetryPolicy
            except ImportError as ex:
                raise PrerequisiteError(
                    "typesafe/* models require the typesafe-sdk package. "
                    "Install it with: pip install 'typesafe-sdk[zstd]'"
                ) from ex
            if not self.api_key:
                raise PrerequisiteError(
                    f"No TypeSafe API key found: set the {TYPESAFE_API_KEY} environment variable."
                )
            # Inspect retries via should_retry(), so the SDK must not retry too.
            self._client = AsyncTypeSafeClient(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=180,
                retry=RetryPolicy(max_retries=0),
            )
            self._client_loop = loop
        return self._client


def parse_jev_request(input: list[ChatMessage], tools: list[ToolInfo]) -> JevRequest:
    """Parse the Jev request from `generate()` input.

    Raises:
        ValueError: If the input is not a single user message holding a JSON
            Jev request, or if tools are passed.
    """
    if tools or len(input) != 1 or not isinstance(input[0], ChatMessageUser):
        raise ValueError(_NOT_A_JEV_REQUEST)
    try:
        request = json.loads(input[0].text)
    except json.JSONDecodeError as ex:
        raise ValueError(_NOT_A_JEV_REQUEST) from ex
    if (
        not isinstance(request, dict)
        or "state" not in request
        or not isinstance(request.get("questions"), dict)
        or not request["questions"]
    ):
        raise ValueError(_NOT_A_JEV_REQUEST)
    return JevRequest(
        state=request["state"],
        questions=request["questions"],
        long_context=bool(request.get("long_context", False)),
    )


def _raise_classified(ex: Exception) -> None:
    """Re-raise SDK errors that are configuration problems or oversized input."""
    from typesafe_sdk import (
        TypeSafeAPIError,
        TypeSafeAuthenticationError,
        TypeSafeNotFoundError,
        TypeSafePermissionDeniedError,
    )

    if isinstance(ex, TypeSafeAuthenticationError | TypeSafePermissionDeniedError):
        raise PrerequisiteError(f"TypeSafe rejected the API key: {ex}") from ex
    if isinstance(ex, TypeSafeNotFoundError):
        raise PrerequisiteError(f"TypeSafe model not found: {ex}") from ex
    if isinstance(ex, TypeSafeAPIError) and (
        _TOO_LONG_CODE in json.dumps(ex.body, default=str) or _TOO_LONG_CODE in str(ex)
    ):
        raise JevInputTooLongError(str(ex)) from ex


@modelapi(name="typesafe")
def typesafe() -> type[ModelAPI]:
    """Register the TypeSafe provider."""
    return TypeSafeAPI
