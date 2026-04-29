"""Integration tests for the cache-aware llm_scanner template forms.

Verifies llm_scanner produces the right message structure for each template
form (default, tuple, legacy string).
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Any

from inspect_ai._util.content import ContentText
from inspect_ai.model import (
    ChatMessage,
    ChatMessageUser,
    GenerateConfig,
    ModelOutput,
)
from inspect_ai.tool import ToolChoice, ToolInfo
from inspect_scout import Scanner, llm_scanner, scan, scanner, transcripts_db
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript

from tests.scan.test_scan_e2e import create_minimal_transcript

CAPTURED: list[tuple[list[ChatMessage], GenerateConfig]] = []


def _capture_outputs(
    input: list[ChatMessage],
    tools: list[ToolInfo],
    tool_choice: ToolChoice,
    config: GenerateConfig,
) -> ModelOutput:
    CAPTURED.append((list(input), config))
    return ModelOutput.from_content(
        model="mockllm", content="Looks fine.\n\nANSWER: yes"
    )


def _setup_transcripts(db_path: Path, count: int) -> None:
    async def _insert() -> None:
        async with transcripts_db(str(db_path)) as db:
            await db.insert(
                [create_minimal_transcript(f"t-{i:03d}", i) for i in range(count)]
            )

    asyncio.run(_insert())


def _run_scan(
    template: Any,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "db"
    scans_path = tmp_path / "scans"
    db_path.mkdir()
    scans_path.mkdir()
    _setup_transcripts(db_path, count=1)

    @scanner(name="ts_scanner", messages="all")
    def _factory() -> Scanner[Transcript]:
        return llm_scanner(
            question="Was it helpful?", answer="boolean", template=template
        )

    CAPTURED.clear()
    scan(
        scanners=[_factory()],
        transcripts=transcripts_from(str(db_path)),
        scans=str(scans_path),
        max_processes=1,
        model="mockllm/model",
        model_args={"custom_outputs": _capture_outputs},
        display="none",
    )


def test_default_template_sends_two_blocks_with_cache_prompt() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        _run_scan(template=None, tmp_path=Path(tmpdir))

    assert len(CAPTURED) == 1
    messages, config = CAPTURED[0]
    assert config.cache_prompt is True

    assert len(messages) == 1
    msg = messages[0]
    assert isinstance(msg, ChatMessageUser)
    assert isinstance(msg.content, list)
    assert len(msg.content) == 2
    assert all(isinstance(b, ContentText) for b in msg.content)

    prefix_text = msg.content[0].text  # type: ignore[union-attr]
    suffix_text = msg.content[1].text  # type: ignore[union-attr]
    assert "BEGIN TRANSCRIPT" in prefix_text
    assert "Was it helpful?" not in prefix_text
    assert "Was it helpful?" in suffix_text


def test_custom_tuple_template_sends_two_blocks_with_cache_prompt() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        _run_scan(
            template=(
                "PREFIX: {{ messages }}",
                "SUFFIX: {{ question }} {{ answer_format }}",
            ),
            tmp_path=Path(tmpdir),
        )

    assert len(CAPTURED) == 1
    messages, config = CAPTURED[0]
    assert config.cache_prompt is True

    msg = messages[0]
    assert isinstance(msg.content, list) and len(msg.content) == 2
    prefix_text = msg.content[0].text  # type: ignore[union-attr]
    suffix_text = msg.content[1].text  # type: ignore[union-attr]
    assert prefix_text.startswith("PREFIX: ")
    assert suffix_text.startswith("SUFFIX: Was it helpful?")


def test_legacy_string_template_sends_single_block_no_cache_prompt() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        _run_scan(
            template="LEGACY: {{ messages }} | {{ question }}",
            tmp_path=Path(tmpdir),
        )

    assert len(CAPTURED) == 1
    messages, config = CAPTURED[0]
    # Legacy path must not enable cache_prompt — keep today's behavior.
    assert config.cache_prompt is None

    msg = messages[0]
    assert isinstance(msg, ChatMessageUser)
    # Single string content (today's behavior).
    assert isinstance(msg.content, str)
    assert msg.content.startswith("LEGACY: ")
    assert "Was it helpful?" in msg.content
