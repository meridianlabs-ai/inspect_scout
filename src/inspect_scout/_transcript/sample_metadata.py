"""Typed metadata accessor for Inspect eval log transcripts.

This module provides a wrapper class that gives typed access to
sample metadata fields from Inspect eval logs.
"""

from typing import Any

from inspect_ai.scorer._metric import Score

from .eval_log import EVAL_LOG_SOURCE_TYPE
from .types import Transcript


class SampleMetadata:
    """Typed accessor for sample metadata from Inspect eval logs.

    Provides typed properties for accessing metadata fields specific to
    Inspect eval logs, while preserving the lazy JSON parsing optimization.
    Raises an error if the transcript is not from an Inspect eval log.

    Usage:
        from inspect_scout import SampleMetadata, Transcript, scanner

        @scanner(messages="all")
        def my_scanner(transcript: Transcript) -> ...:
            metadata = SampleMetadata(transcript)
            print(metadata.eval_status)
            print(metadata.scores)
    """

    def __init__(self, transcript: Transcript) -> None:
        """Initialize SampleMetadata wrapper.

        Args:
            transcript: A Transcript from an Inspect eval log.

        Raises:
            ValueError: If the transcript is not from an Inspect eval log.
        """
        if transcript.source_type != EVAL_LOG_SOURCE_TYPE:
            raise ValueError(
                f"SampleMetadata requires an Inspect eval log transcript "
                f"(source_type='{EVAL_LOG_SOURCE_TYPE}'), "
                f"but got source_type='{transcript.source_type}'"
            )
        self._metadata = transcript.metadata

    # ===== Eval Info properties =====

    @property
    def eval_id(self) -> str | None:
        """Globally unique id for eval."""
        return self._metadata.get("eval_id")

    @property
    def log(self) -> str | None:
        """Location that the log file was read from."""
        return self._metadata.get("log")

    @property
    def eval_status(self) -> str | None:
        """Status of eval (e.g., 'success', 'error', 'cancelled')."""
        return self._metadata.get("eval_status")

    @property
    def eval_tags(self) -> list[str]:
        """Tags associated with evaluation run."""
        tags = self._metadata.get("eval_tags", "")
        if not tags:
            return []
        return [tag.strip() for tag in tags.split(",") if tag.strip()]

    @property
    def eval_metadata(self) -> dict[str, Any]:
        """Additional eval metadata."""
        return self._metadata.get("eval_metadata") or {}

    @property
    def task_args(self) -> dict[str, Any]:
        """Task arguments."""
        return self._metadata.get("task_args") or {}

    # ===== Model properties =====

    @property
    def generate_config(self) -> dict[str, Any]:
        """Generate config specified for model instance."""
        return self._metadata.get("generate_config") or {}

    @property
    def model_roles(self) -> dict[str, Any]:
        """Model roles."""
        return self._metadata.get("model_roles") or {}

    # ===== Sample properties =====

    @property
    def id(self) -> str | None:
        """Unique id for sample."""
        return self._metadata.get("id")

    @property
    def epoch(self) -> int | None:
        """Epoch number for sample."""
        epoch = self._metadata.get("epoch")
        return int(epoch) if epoch is not None else None

    @property
    def input(self) -> str | None:
        """Sample input."""
        return self._metadata.get("input")

    @property
    def target(self) -> str | None:
        """Sample target."""
        return self._metadata.get("target")

    @property
    def sample_metadata(self) -> dict[str, Any]:
        """Sample metadata."""
        return self._metadata.get("sample_metadata") or {}

    @property
    def working_time(self) -> float | None:
        """Time spent working (model generation, sandbox calls, etc.)."""
        working_time = self._metadata.get("working_time")
        return float(working_time) if working_time is not None else None

    # ===== Score properties =====

    @property
    def scores(self) -> dict[str, Score]:
        """Scores dict reconstructed from score_* metadata fields."""
        return {
            k.removeprefix("score_"): Score(value=v)
            for k, v in self._metadata.items()
            if k.startswith("score_")
        }

    # ===== Legacy/deprecated field accessors =====

    @property
    def solver(self) -> str | None:
        """Solver name (deprecated, use 'agent' on TranscriptInfo)."""
        return self._metadata.get("solver")

    @property
    def solver_args(self) -> dict[str, Any]:
        """Solver arguments (deprecated, use 'agent_args' on TranscriptInfo)."""
        return self._metadata.get("solver_args") or {}
