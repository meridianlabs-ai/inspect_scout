"""Tests for llm_scanner: content attr, integration."""

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
