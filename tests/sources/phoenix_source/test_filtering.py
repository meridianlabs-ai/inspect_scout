"""Tests for Phoenix query filtering and metadata extraction.

Tests for _find_root_span, _matches_filters, and improved _extract_metadata
that auto-extracts OpenInference context attributes.
"""

from typing import Any

from inspect_scout.sources._phoenix import (
    _extract_metadata,
    _find_root_span,
    _matches_filters,
)


def _make_span(
    *,
    span_id: str = "span1",
    parent_id: str | None = None,
    start_time: str = "2024-01-01T00:00:00Z",
    attributes: dict[str, Any] | None = None,
    span_kind: str | None = None,
) -> dict[str, Any]:
    """Create a minimal span dict for testing."""
    span: dict[str, Any] = {
        "context": {"span_id": span_id, "trace_id": "trace1"},
        "start_time": start_time,
        "name": "test-span",
        "attributes": attributes or {},
    }
    if parent_id is not None:
        span["parent_id"] = parent_id
    if span_kind is not None:
        span["span_kind"] = span_kind
    return span


# -- _find_root_span tests --


class TestFindRootSpan:
    def test_finds_span_with_no_parent_id(self) -> None:
        root = _make_span(span_id="root")
        child = _make_span(span_id="child", parent_id="root")
        result = _find_root_span([child, root])
        assert result["context"]["span_id"] == "root"

    def test_falls_back_to_earliest_start_time(self) -> None:
        """When all spans have parent_id, pick the earliest."""
        early = _make_span(
            span_id="early",
            parent_id="external",
            start_time="2024-01-01T00:00:00Z",
        )
        late = _make_span(
            span_id="late",
            parent_id="external",
            start_time="2024-01-01T01:00:00Z",
        )
        result = _find_root_span([late, early])
        assert result["context"]["span_id"] == "early"

    def test_single_span_trace(self) -> None:
        span = _make_span(span_id="only")
        result = _find_root_span([span])
        assert result["context"]["span_id"] == "only"

    def test_empty_list_returns_empty_dict(self) -> None:
        assert _find_root_span([]) == {}


# -- _matches_filters tests --


class TestMatchesFilters:
    def test_no_filters_returns_true(self) -> None:
        spans = [_make_span()]
        assert _matches_filters(spans, None, None, None) is True

    def test_match_single_session_id(self) -> None:
        spans = [_make_span(attributes={"session.id": "sess-abc"})]
        assert _matches_filters(spans, "sess-abc", None, None) is True

    def test_no_match_single_session_id(self) -> None:
        spans = [_make_span(attributes={"session.id": "sess-abc"})]
        assert _matches_filters(spans, "sess-xyz", None, None) is False

    def test_match_session_id_list(self) -> None:
        spans = [_make_span(attributes={"session.id": "sess-abc"})]
        assert _matches_filters(spans, ["sess-abc", "sess-def"], None, None) is True

    def test_no_match_session_id_list(self) -> None:
        spans = [_make_span(attributes={"session.id": "sess-abc"})]
        assert _matches_filters(spans, ["sess-def", "sess-ghi"], None, None) is False

    def test_no_match_missing_session_id(self) -> None:
        spans = [_make_span(attributes={})]
        assert _matches_filters(spans, "sess-abc", None, None) is False

    def test_match_all_tags_present(self) -> None:
        spans = [_make_span(attributes={"tag.tags": ["prod", "v2", "important"]})]
        assert _matches_filters(spans, None, ["prod", "v2"], None) is True

    def test_no_match_some_tags_missing(self) -> None:
        spans = [_make_span(attributes={"tag.tags": ["prod"]})]
        assert _matches_filters(spans, None, ["prod", "v2"], None) is False

    def test_no_match_missing_tags_attribute(self) -> None:
        spans = [_make_span(attributes={})]
        assert _matches_filters(spans, None, ["prod"], None) is False

    def test_no_match_tags_not_a_list(self) -> None:
        spans = [_make_span(attributes={"tag.tags": "prod"})]
        assert _matches_filters(spans, None, ["prod"], None) is False

    def test_match_metadata_key_value(self) -> None:
        spans = [
            _make_span(
                attributes={"metadata.env": "production", "metadata.region": "us-east"}
            )
        ]
        assert _matches_filters(spans, None, None, {"env": "production"}) is True

    def test_match_multiple_metadata_pairs(self) -> None:
        spans = [
            _make_span(
                attributes={"metadata.env": "production", "metadata.region": "us-east"}
            )
        ]
        assert (
            _matches_filters(
                spans, None, None, {"env": "production", "region": "us-east"}
            )
            is True
        )

    def test_no_match_metadata_value_differs(self) -> None:
        spans = [_make_span(attributes={"metadata.env": "staging"})]
        assert _matches_filters(spans, None, None, {"env": "production"}) is False

    def test_no_match_metadata_key_missing(self) -> None:
        spans = [_make_span(attributes={})]
        assert _matches_filters(spans, None, None, {"env": "production"}) is False

    def test_combined_session_and_tags(self) -> None:
        spans = [
            _make_span(
                attributes={"session.id": "sess-abc", "tag.tags": ["prod", "v2"]}
            )
        ]
        assert _matches_filters(spans, "sess-abc", ["prod"], None) is True

    def test_combined_filters_partial_fail(self) -> None:
        """Session matches but tags don't → overall False."""
        spans = [
            _make_span(attributes={"session.id": "sess-abc", "tag.tags": ["staging"]})
        ]
        assert _matches_filters(spans, "sess-abc", ["prod"], None) is False

    def test_uses_root_span_attributes(self) -> None:
        """Filters should check the root span, not child spans."""
        root = _make_span(
            span_id="root",
            attributes={"session.id": "sess-root"},
        )
        child = _make_span(
            span_id="child",
            parent_id="root",
            attributes={"session.id": "sess-child"},
        )
        assert _matches_filters([child, root], "sess-root", None, None) is True
        assert _matches_filters([child, root], "sess-child", None, None) is False


# -- _extract_metadata tests --


class TestExtractMetadata:
    def test_extracts_session_id(self) -> None:
        span = _make_span(attributes={"session.id": "sess-123"})
        meta = _extract_metadata(span)
        assert meta["session_id"] == "sess-123"

    def test_extracts_user_id(self) -> None:
        span = _make_span(attributes={"user.id": "user-456"})
        meta = _extract_metadata(span)
        assert meta["user_id"] == "user-456"

    def test_extracts_tags(self) -> None:
        span = _make_span(attributes={"tag.tags": ["prod", "v2"]})
        meta = _extract_metadata(span)
        assert meta["tags"] == ["prod", "v2"]

    def test_extracts_metadata_dict(self) -> None:
        span = _make_span(
            attributes={
                "metadata.env": "production",
                "metadata.region": "us-east",
            }
        )
        meta = _extract_metadata(span)
        assert meta["metadata"] == {"env": "production", "region": "us-east"}

    def test_handles_missing_attributes_gracefully(self) -> None:
        span = _make_span(attributes={})
        meta = _extract_metadata(span)
        assert "session_id" not in meta
        assert "user_id" not in meta
        assert "tags" not in meta
        assert "metadata" not in meta

    def test_skips_empty_tags_list(self) -> None:
        span = _make_span(attributes={"tag.tags": []})
        meta = _extract_metadata(span)
        assert "tags" not in meta

    def test_preserves_existing_metadata_fields(self) -> None:
        """Existing fields like provider, span_kind should still work."""
        span = _make_span(
            span_kind="LLM",
            attributes={
                "session.id": "sess-123",
                "llm.provider": "openai",
            },
        )
        meta = _extract_metadata(span)
        assert meta["span_kind"] == "LLM"
        assert meta["session_id"] == "sess-123"

    def test_extracts_all_openinference_attributes(self) -> None:
        """All four OpenInference context attributes extracted together."""
        span = _make_span(
            attributes={
                "session.id": "sess-1",
                "user.id": "user-2",
                "tag.tags": ["a", "b"],
                "metadata.env": "prod",
                "metadata.version": "3",
            }
        )
        meta = _extract_metadata(span)
        assert meta["session_id"] == "sess-1"
        assert meta["user_id"] == "user-2"
        assert meta["tags"] == ["a", "b"]
        assert meta["metadata"] == {"env": "prod", "version": "3"}
