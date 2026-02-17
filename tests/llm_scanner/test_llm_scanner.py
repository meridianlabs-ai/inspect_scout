"""Tests for llm_scanner refactoring: content attr, flatten_results, integration."""

from inspect_scout import llm_scanner
from inspect_scout._llm_scanner._parallel import _flatten_results
from inspect_scout._scanner.result import Result, as_resultset
from inspect_scout._scanner.scanner import SCANNER_CONTENT_ATTR
from inspect_scout._transcript.types import TranscriptContent

# ---------------------------------------------------------------------------
# _flatten_results tests
# ---------------------------------------------------------------------------


class TestFlattenResultsPassthrough:
    """Non-resultset results pass through unchanged."""

    def test_single_result(self) -> None:
        r = Result(value=True, answer="Yes")
        assert _flatten_results([r]) == [r]

    def test_multiple_results(self) -> None:
        r1 = Result(value=True, answer="Yes")
        r2 = Result(value=False, answer="No")
        flat = _flatten_results([r1, r2])
        assert len(flat) == 2
        assert flat[0].value is True
        assert flat[1].value is False

    def test_empty_list(self) -> None:
        assert _flatten_results([]) == []


class TestFlattenResultsUnrolls:
    """Resultset Results are unrolled into individual Results."""

    def test_single_resultset(self) -> None:
        sub1 = Result(value="a", answer="A")
        sub2 = Result(value="b", answer="B")
        rs = as_resultset([sub1, sub2])
        flat = _flatten_results([rs])
        assert len(flat) == 2
        assert flat[0].value == "a"
        assert flat[0].answer == "A"
        assert flat[1].value == "b"
        assert flat[1].answer == "B"

    def test_multiple_resultsets(self) -> None:
        rs1 = as_resultset([Result(value=1), Result(value=2)])
        rs2 = as_resultset([Result(value=3)])
        flat = _flatten_results([rs1, rs2])
        assert len(flat) == 3
        assert [r.value for r in flat] == [1, 2, 3]


class TestFlattenResultsMixed:
    """Mix of resultset and non-resultset Results."""

    def test_mixed(self) -> None:
        plain = Result(value="plain", answer="P")
        rs = as_resultset([Result(value="a"), Result(value="b")])
        flat = _flatten_results([plain, rs])
        assert len(flat) == 3
        assert flat[0].value == "plain"
        assert flat[1].value == "a"
        assert flat[2].value == "b"

    def test_preserves_metadata(self) -> None:
        sub = Result(
            value=42,
            answer="42",
            explanation="Found it",
            metadata={"key": "val"},
        )
        rs = as_resultset([sub])
        flat = _flatten_results([rs])
        assert len(flat) == 1
        assert flat[0].value == 42
        assert flat[0].explanation == "Found it"
        assert flat[0].metadata == {"key": "val"}


class TestFlattenResultsEdgeCases:
    def test_result_with_list_value_but_not_resultset(self) -> None:
        """A Result with a list value but type != 'resultset' is NOT unrolled."""
        r = Result(value=[1, 2, 3], type="custom_list")
        flat = _flatten_results([r])
        assert len(flat) == 1
        assert flat[0].value == [1, 2, 3]

    def test_resultset_type_but_non_list_value(self) -> None:
        """A Result with type='resultset' but non-list value is NOT unrolled."""
        r = Result(value="not a list", type="resultset")
        flat = _flatten_results([r])
        assert len(flat) == 1
        assert flat[0].value == "not a list"


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
