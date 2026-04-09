"""Tests for transcript search endpoints."""

import base64
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from inspect_ai.model._chat_message import ChatMessageAssistant, ChatMessageUser
from inspect_scout._scanner.result import Result
from inspect_scout._transcript.types import Transcript
from inspect_scout._view._api_v2 import v2_api_app
from inspect_scout._view._api_v2_search import LLM_SEARCH_TEMPLATE


def _base64url(s: str) -> str:
    """Encode string as base64url (URL-safe base64 without padding)."""
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


def _create_transcript(transcript_id: str = "t001") -> Transcript:
    """Create a transcript for search endpoint tests."""
    return Transcript(
        transcript_id=transcript_id,
        source_type="test",
        source_id="source-001",
        source_uri="test://uri",
        model="gpt-4.1",
        metadata={"topic": "search"},
        messages=[
            ChatMessageUser(content="Where is the needle?"),
            ChatMessageAssistant(content="The needle is in the haystack."),
        ],
        events=[],
    )


async def _populate_transcripts(location: Path, transcripts: list[Transcript]) -> None:
    """Populate transcript database for testing."""
    from inspect_scout import transcripts_db

    async with transcripts_db(str(location)) as db:
        await db.insert(transcripts)


def _search_data_dir(root: Path) -> Callable[[str], Path]:
    """Build a scout_data_dir replacement rooted at a temp directory."""

    def _inner(subdir: str) -> Path:
        path = root / subdir
        path.mkdir(parents=True, exist_ok=True)
        return path

    return _inner


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(v2_api_app())


@pytest_asyncio.fixture
async def transcript_location(tmp_path: Path) -> AsyncIterator[Path]:
    """Create and populate a temporary transcript database."""
    location = tmp_path / "transcripts"
    location.mkdir(parents=True, exist_ok=True)
    await _populate_transcripts(location, [_create_transcript()])
    yield location


class TestSearchEndpoint:
    """Tests for POST /transcripts/{dir}/{id}/search."""

    def test_grep_search_lifecycle(
        self, client: TestClient, transcript_location: Path, tmp_path: Path
    ) -> None:
        """Persist, list, fetch, and delete a grep search."""
        grep_calls: list[dict[str, str | bool]] = []

        def fake_grep_scanner(
            query: str,
            *,
            regex: bool,
            ignore_case: bool,
            word_boundary: bool,
        ) -> Callable[[Transcript], Awaitable[list[Result]]]:
            grep_calls.append(
                {
                    "query": query,
                    "regex": regex,
                    "ignore_case": ignore_case,
                    "word_boundary": word_boundary,
                }
            )

            async def _scan(_: Transcript) -> list[Result]:
                return [Result(value=1, explanation="Matched one message.")]

            return _scan

        encoded_dir = _base64url(str(transcript_location))
        with (
            patch(
                "inspect_scout._view._api_v2_search.scout_data_dir",
                side_effect=_search_data_dir(tmp_path / "search-data"),
            ),
            patch(
                "inspect_scout._view._api_v2_search.grep_scanner",
                side_effect=fake_grep_scanner,
            ),
        ):
            create_response = client.post(
                f"/transcripts/{encoded_dir}/t001/search",
                json={
                    "query": "needle",
                    "type": "grep",
                    "regex": True,
                    "ignore_case": False,
                    "word_boundary": True,
                },
            )

            assert create_response.status_code == 200
            created = create_response.json()
            assert created["type"] == "grep"
            assert created["query"] == "needle"
            assert created["regex"] is True
            assert created["ignore_case"] is False
            assert created["word_boundary"] is True
            assert "model" not in created
            assert grep_calls == [
                {
                    "query": "needle",
                    "regex": True,
                    "ignore_case": False,
                    "word_boundary": True,
                }
            ]

            list_response = client.get(f"/transcripts/{encoded_dir}/t001/searches")
            assert list_response.status_code == 200
            listed = list_response.json()["items"]
            assert len(listed) == 1
            assert listed[0] == created

            search_id = created["search_id"]
            get_response = client.get(
                f"/transcripts/{encoded_dir}/t001/searches/{search_id}"
            )
            assert get_response.status_code == 200
            assert get_response.json() == created

            delete_response = client.delete(
                f"/transcripts/{encoded_dir}/t001/searches/{search_id}"
            )
            assert delete_response.status_code == 204

            missing_response = client.get(
                f"/transcripts/{encoded_dir}/t001/searches/{search_id}"
            )
            assert missing_response.status_code == 404

    def test_llm_search_uses_cache(
        self, client: TestClient, transcript_location: Path, tmp_path: Path
    ) -> None:
        """Identical LLM searches return the cached saved search."""
        llm_calls: list[dict[str, str | None]] = []

        def fake_llm_scanner(
            *,
            question: str,
            answer: str,
            template: str,
            model: str | None,
        ) -> Callable[[Transcript], Awaitable[Result]]:
            llm_calls.append(
                {
                    "question": question,
                    "answer": answer,
                    "template": template,
                    "model": model,
                }
            )

            async def _scan(_: Transcript) -> Result:
                return Result(
                    value="The assistant says the needle is in the haystack.",
                    explanation="LLM summary.",
                )

            return _scan

        encoded_dir = _base64url(str(transcript_location))
        with (
            patch(
                "inspect_scout._view._api_v2_search.scout_data_dir",
                side_effect=_search_data_dir(tmp_path / "search-data"),
            ),
            patch(
                "inspect_scout._view._api_v2_search.llm_scanner",
                side_effect=fake_llm_scanner,
            ),
        ):
            first_response = client.post(
                f"/transcripts/{encoded_dir}/t001/search",
                json={
                    "query": "Where is the needle?",
                    "type": "llm",
                    "model": "openai/gpt-5.4-mini",
                },
            )
            second_response = client.post(
                f"/transcripts/{encoded_dir}/t001/search",
                json={
                    "query": "Where is the needle?",
                    "type": "llm",
                    "model": "openai/gpt-5.4-mini",
                },
            )

        assert first_response.status_code == 200
        assert second_response.status_code == 200
        first = first_response.json()
        second = second_response.json()
        assert first == second
        assert first["type"] == "llm"
        assert first["model"] == "openai/gpt-5.4-mini"
        assert "regex" not in first
        assert llm_calls == [
            {
                "question": "Where is the needle?",
                "answer": "string",
                "template": LLM_SEARCH_TEMPLATE,
                "model": "openai/gpt-5.4-mini",
            }
        ]

    @pytest.mark.parametrize(
        ("payload", "field_name"),
        [
            (
                {"query": "needle", "type": "grep", "model": "openai/gpt-5.4-mini"},
                "model",
            ),
            (
                {
                    "query": "needle",
                    "type": "llm",
                    "model": "openai/gpt-5.4-mini",
                    "regex": True,
                },
                "regex",
            ),
        ],
    )
    def test_search_request_rejects_cross_type_fields(
        self,
        client: TestClient,
        transcript_location: Path,
        tmp_path: Path,
        payload: dict[str, str | bool],
        field_name: str,
    ) -> None:
        """Reject fields that do not belong to the selected search type."""
        encoded_dir = _base64url(str(transcript_location))
        with patch(
            "inspect_scout._view._api_v2_search.scout_data_dir",
            side_effect=_search_data_dir(tmp_path / "search-data"),
        ):
            response = client.post(
                f"/transcripts/{encoded_dir}/t001/search",
                json=payload,
            )

        assert response.status_code == 422
        assert field_name in response.text

    def test_search_missing_transcript_returns_404(
        self, client: TestClient, transcript_location: Path, tmp_path: Path
    ) -> None:
        """Missing transcript ids return 404 before invoking scanners."""
        encoded_dir = _base64url(str(transcript_location))
        with patch(
            "inspect_scout._view._api_v2_search.scout_data_dir",
            side_effect=_search_data_dir(tmp_path / "search-data"),
        ):
            response = client.post(
                f"/transcripts/{encoded_dir}/does-not-exist/search",
                json={"query": "needle", "type": "grep"},
            )

        assert response.status_code == 404
        assert response.json() == {"detail": "Transcript not found"}
