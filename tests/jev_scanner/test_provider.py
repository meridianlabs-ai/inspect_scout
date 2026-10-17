"""The typesafe/* Inspect model provider."""

import json
import sys
from typing import Any

import httpx2
import pytest
from inspect_ai._util.error import PrerequisiteError
from inspect_ai.model import CachePolicy, ChatMessageUser, GenerateConfig, get_model
from inspect_ai.model._model import init_model_usage, model_usage
from inspect_scout._jev_scanner._provider import (
    JevInputTooLongError,
    TypeSafeAPI,
    parse_jev_request,
)
from typesafe_sdk import (
    NoulAnswer,
    SystemOneResponse,
    TypeSafeAuthenticationError,
    TypeSafeBadRequestError,
    TypeSafeRateLimitError,
    Usage,
)

REQUEST = {"state": "s", "questions": {"q": {"type": "noul", "instructions": "yes?"}}}


class FakeClient:
    """Stands in for the SDK client; records calls and returns a fixed answer."""

    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.error = error

    async def system_one(self, **kwargs: Any) -> SystemOneResponse:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return SystemOneResponse(
            model="jev-1.13.0",
            usage=Usage(input_tokens=40, output_tokens=2),
            answers={"q": NoulAnswer(type="noul", noul=0.8)},
        )


def model_with(client: FakeClient, monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    model = get_model("typesafe/jev-test", memoize=False)
    assert isinstance(model.api, TypeSafeAPI)
    monkeypatch.setattr(model.api, "_get_client", lambda: client)
    return model


@pytest.mark.asyncio
async def test_generate_returns_answers_and_records_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeClient()
    model = model_with(client, monkeypatch)
    init_model_usage()
    output = await model.generate(json.dumps({**REQUEST, "long_context": True}))
    assert output.metadata == {"answers": {"q": {"type": "noul", "noul": 0.8}}}
    assert output.model == "jev-1.13.0"
    assert client.calls[0]["extra_headers"] == {
        "TypeSafe-Danger-Zone-Long-Context": "true"
    }
    assert client.calls[0]["model"] == "jev-test"
    assert model_usage()["typesafe/jev-test"].input_tokens == 40


@pytest.mark.asyncio
async def test_cache_hit_skips_the_api(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    monkeypatch.setenv("INSPECT_CACHE_DIR", str(tmp_path))
    client = FakeClient()
    model = model_with(client, monkeypatch)
    config = GenerateConfig(cache=CachePolicy(expiry="1D"))
    first = await model.generate(json.dumps(REQUEST), config=config)
    second = await model.generate(json.dumps(REQUEST), config=config)
    assert len(client.calls) == 1
    assert second.metadata == first.metadata


@pytest.mark.asyncio
async def test_auth_failure_is_a_prerequisite_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = TypeSafeAuthenticationError(401, {"detail": "bad key"}, httpx2.Headers())
    model = model_with(FakeClient(error=error), monkeypatch)
    with pytest.raises(PrerequisiteError, match="rejected the API key"):
        await model.generate(json.dumps(REQUEST))


@pytest.mark.asyncio
async def test_missing_key_is_a_prerequisite_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    model = get_model("typesafe/jev-test", memoize=False)
    with pytest.raises(PrerequisiteError, match="TYPESAFE_API_KEY"):
        await model.generate(json.dumps(REQUEST))


@pytest.mark.asyncio
async def test_missing_sdk_is_a_prerequisite_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    model = get_model("typesafe/jev-test", memoize=False)
    monkeypatch.setitem(sys.modules, "typesafe_sdk", None)
    with pytest.raises(PrerequisiteError, match="pip install"):
        await model.generate(json.dumps(REQUEST))


@pytest.mark.asyncio
async def test_too_long_is_a_typed_error(monkeypatch: pytest.MonkeyPatch) -> None:
    error = TypeSafeBadRequestError(
        400,
        {"error": {"code": "max_tokens_exceeded", "message": "Request too large"}},
        httpx2.Headers(),
    )
    model = model_with(FakeClient(error=error), monkeypatch)
    with pytest.raises(JevInputTooLongError):
        await model.generate(json.dumps(REQUEST))


@pytest.mark.parametrize(
    "text",
    [
        "Write me a poem",
        json.dumps({"state": "s"}),
        json.dumps({"state": "s", "questions": {}}),
    ],
)
def test_rejects_non_jev_input(text: str) -> None:
    with pytest.raises(ValueError, match="classifiers"):
        parse_jev_request([ChatMessageUser(content=text)], [])


@pytest.mark.asyncio
async def test_count_tokens_uses_jev_ratio(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    assert await TypeSafeAPI("jev-test").count_text_tokens("x" * 230) == 100


def test_retry_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    api = TypeSafeAPI("jev-test")
    assert api.should_retry(TypeSafeRateLimitError(429, None, httpx2.Headers())) is True
    assert api.should_retry(ValueError("bad request")) is False
