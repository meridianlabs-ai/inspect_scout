"""Tests for _extract_content_blocks and image content handling."""

from types import SimpleNamespace
from typing import Any

import pytest
from inspect_ai.model import ContentImage, ContentText
from inspect_scout.sources._claude_code.events import to_tool_event
from inspect_scout.sources._claude_code.extraction import (
    _extract_content_blocks,
    extract_tool_result_messages,
)
from inspect_scout.sources._claude_code.models import (
    ContentToolUse,
    UserEvent,
    UserMessage,
)


def _capture_logger(warnings: list[str]) -> SimpleNamespace:
    """Create a fake logger that captures warning messages."""
    return SimpleNamespace(warning=lambda msg, *args: warnings.append(msg % args))


def _base64_image_block(
    data: str = "AAAA", media_type: str = "image/png"
) -> dict[str, Any]:
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": data},
    }


def _text_block(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text}


class TestExtractContentBlocks:
    """Tests for _extract_content_blocks()."""

    def test_text_only_returns_string(self) -> None:
        """Text-only content returns a plain joined string."""
        items = [_text_block("line one"), _text_block("line two")]
        result = _extract_content_blocks(items)
        assert result == "line one\nline two"

    def test_images_only(self) -> None:
        """Image-only content returns a list of ContentImage."""
        items = [_base64_image_block("img1"), _base64_image_block("img2")]
        result = _extract_content_blocks(items)
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(b, ContentImage) for b in result)

    def test_mixed_preserves_interleaving(self) -> None:
        """Text-image-text ordering is preserved, not reordered."""
        items = [
            _text_block("before"),
            _base64_image_block("IMG"),
            _text_block("after"),
        ]
        result = _extract_content_blocks(items)
        assert isinstance(result, list)
        assert len(result) == 3
        assert isinstance(result[0], ContentText)
        assert result[0].text == "before"
        assert isinstance(result[1], ContentImage)
        assert isinstance(result[2], ContentText)
        assert result[2].text == "after"

    def test_adjacent_text_blocks_merged(self) -> None:
        """Adjacent text blocks are merged into one ContentText."""
        items = [
            _text_block("a"),
            _text_block("b"),
            _base64_image_block("IMG"),
            _text_block("c"),
        ]
        result = _extract_content_blocks(items)
        assert isinstance(result, list)
        assert len(result) == 3
        assert isinstance(result[0], ContentText)
        assert result[0].text == "a\nb"
        assert isinstance(result[1], ContentImage)
        assert isinstance(result[2], ContentText)
        assert result[2].text == "c"

    def test_empty_list_returns_empty_string(self) -> None:
        """Empty input returns empty string."""
        assert _extract_content_blocks([]) == ""

    def test_base64_data_uri_format(self) -> None:
        """Base64 images are formatted as data URIs with correct media type."""
        items = [_base64_image_block("QUJD", "image/jpeg")]
        result = _extract_content_blocks(items)
        assert isinstance(result, list)
        img = result[0]
        assert isinstance(img, ContentImage)
        assert img.image == "data:image/jpeg;base64,QUJD"

    def test_non_base64_source_warns(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-base64 image source logs a warning and is dropped."""
        items = [
            _text_block("text"),
            {
                "type": "image",
                "source": {"type": "url", "url": "https://example.com/img.png"},
            },
        ]
        warnings: list[str] = []
        monkeypatch.setattr(
            "inspect_scout.sources._claude_code.extraction.logger",
            _capture_logger(warnings),
        )
        result = _extract_content_blocks(items)

        # No images → falls back to plain string
        assert result == "text"
        assert any("url" in w for w in warnings)

    def test_missing_source_warns(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Image block with no source dict logs a warning."""
        items = [{"type": "image", "source": "not-a-dict"}]
        warnings: list[str] = []
        monkeypatch.setattr(
            "inspect_scout.sources._claude_code.extraction.logger",
            _capture_logger(warnings),
        )
        result = _extract_content_blocks(items)

        assert result == ""
        assert any("unknown" in w for w in warnings)

    def test_non_dict_items_skipped(self) -> None:
        """Non-dict items in the list are silently skipped."""
        items: list[Any] = ["raw string", 42, _text_block("valid")]
        result = _extract_content_blocks(items)
        assert result == "valid"


class TestToolResultWithImages:
    """Integration: image content flows through tool result extraction."""

    def test_extract_tool_result_messages_with_images(self) -> None:
        """ChatMessageTool.content is a list when tool result has images."""
        event = UserEvent(
            uuid="1",
            timestamp="2026-01-15T12:00:00Z",
            sessionId="test",
            type="user",
            message=UserMessage(
                content=[
                    {
                        "type": "tool_result",
                        "tool_use_id": "t1",
                        "content": [
                            _text_block("screenshot captured"),
                            _base64_image_block("PNG_DATA"),
                        ],
                    }
                ]
            ),
        )
        msgs = extract_tool_result_messages(event)
        assert len(msgs) == 1
        content = msgs[0].content
        assert isinstance(content, list)
        assert len(content) == 2
        assert isinstance(content[0], ContentText)
        assert isinstance(content[1], ContentImage)

    def test_to_tool_event_with_images(self) -> None:
        """ToolEvent.result is a list when tool result has images."""
        from datetime import datetime, timezone

        block = ContentToolUse(type="tool_use", id="t1", name="screenshot", input={})
        tool_result: dict[str, Any] = {
            "type": "tool_result",
            "tool_use_id": "t1",
            "content": [
                _text_block("captured"),
                _base64_image_block("IMG"),
            ],
        }
        dt = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        event = to_tool_event(block, tool_result, dt)

        assert isinstance(event.result, list)
        assert len(event.result) == 2
        assert isinstance(event.result[0], ContentText)
        assert isinstance(event.result[1], ContentImage)

    def test_to_tool_event_text_only_still_string(self) -> None:
        """ToolEvent.result remains a plain string for text-only results."""
        from datetime import datetime, timezone

        block = ContentToolUse(type="tool_use", id="t1", name="Read", input={})
        tool_result: dict[str, Any] = {
            "type": "tool_result",
            "tool_use_id": "t1",
            "content": [_text_block("line 1"), _text_block("line 2")],
        }
        dt = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        event = to_tool_event(block, tool_result, dt)

        assert event.result == "line 1\nline 2"
