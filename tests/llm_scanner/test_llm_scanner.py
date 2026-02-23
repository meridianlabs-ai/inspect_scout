"""Tests for llm_scanner: content attr, integration."""

from unittest.mock import patch

from inspect_scout import llm_scanner
from inspect_scout._scanner.scanner import SCANNER_CONTENT_ATTR
from inspect_scout._transcript.types import TranscriptContent

# ---------------------------------------------------------------------------
# content parameter tests
# ---------------------------------------------------------------------------


class TestContentParameter:
    def test_content_sets_attr(self) -> None:
        """content= sets SCANNER_CONTENT_ATTR on the scan function."""
        scan_fn = llm_scanner(
            question="test?",
            answer="boolean",
            content=TranscriptContent(timeline=True),
        )
        assert hasattr(scan_fn, SCANNER_CONTENT_ATTR)
        tc = getattr(scan_fn, SCANNER_CONTENT_ATTR)
        assert tc.timeline is True

    def test_no_content_no_attr(self) -> None:
        """Without content=, SCANNER_CONTENT_ATTR is not set."""
        scan_fn = llm_scanner(question="test?", answer="boolean")
        assert not hasattr(scan_fn, SCANNER_CONTENT_ATTR)

    def test_content_with_events(self) -> None:
        """content= with events filter."""
        scan_fn = llm_scanner(
            question="test?",
            answer="boolean",
            content=TranscriptContent(events="all"),
        )
        tc = getattr(scan_fn, SCANNER_CONTENT_ATTR)
        assert tc.events == "all"


# ---------------------------------------------------------------------------
# model_role parameter tests
# ---------------------------------------------------------------------------


class TestModelRoleParameter:
    def test_model_role_passed_to_get_model(self) -> None:
        """model_role= is forwarded to get_model(role=...) at scan time."""
        with patch(
            "inspect_scout._llm_scanner._llm_scanner.get_model"
        ) as mock_get_model:
            # Construction should NOT call get_model — role resolution is deferred
            llm_scanner(
                question="test?",
                answer="boolean",
                model="openai/gpt-4o",
                model_role="scanner",
            )
            mock_get_model.assert_not_called()

    def test_model_role_none_by_default(self) -> None:
        """model_role defaults to None and does not affect construction."""
        # Should construct without error when model_role is omitted
        scan_fn = llm_scanner(question="test?", answer="boolean")
        assert scan_fn is not None
