"""Tests for the shared OpenClaw extraction helpers."""

from __future__ import annotations

from inspect_scout.sources._openclaw.extraction import (
    tokens_from_usage,
    usage_to_inspect,
)

USAGE = {
    "input": 10,
    "output": 20,
    "cacheRead": 5,
    "cacheWrite": 5,
    "totalTokens": 999,  # deliberately inconsistent with the component sum
}


class TestUsageToInspect:
    def test_total_is_component_sum_not_raw_total(self) -> None:
        # raw totalTokens can exclude cache tokens on some turns, so the
        # mapping recomputes it from the components
        mapped = usage_to_inspect(USAGE)
        assert mapped["total_tokens"] == tokens_from_usage(USAGE) == 40
        assert mapped["input_tokens"] == 10
        assert mapped["output_tokens"] == 20
        assert mapped["input_tokens_cache_read"] == 5
        assert mapped["input_tokens_cache_write"] == 5

    def test_none_usage_maps_to_zeros(self) -> None:
        assert usage_to_inspect(None)["total_tokens"] == 0
