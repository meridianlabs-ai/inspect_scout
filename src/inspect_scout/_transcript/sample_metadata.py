"""Typed metadata accessor for Inspect eval log transcripts.

This module provides a wrapper class that gives typed access to
sample metadata fields from Inspect eval logs.
"""

from typing import Any, Literal, cast

from inspect_ai.model import GenerateConfig
from inspect_ai.scorer._metric import Value

from .eval_log import EVAL_LOG_SOURCE_TYPE
from .types import Transcript

EvalStatus = Literal["started", "success", "cancelled", "error"]


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
            print(metadata.score_values)
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
    def eval_id(self) -> str:
        """Globally unique id for eval. Same as EvalLog.eval.eval_id."""
        return cast(str, self._metadata["eval_id"])

    @property
    def log(self) -> str:
        """Location that the log file was read from. Same as EvalLog.location."""
        return cast(str, self._metadata["log"])

    @property
    def eval_status(self) -> EvalStatus:
        """Status of eval. Same as EvalLog.status."""
        return cast(EvalStatus, self._metadata["eval_status"])

    @property
    def eval_tags(self) -> list[str] | None:
        """Tags associated with evaluation run. Same as EvalLog.eval.tags."""
        tags = self._metadata.get("eval_tags")
        if not tags:
            return None
        return [tag.strip() for tag in tags.split(",") if tag.strip()]

    @property
    def eval_metadata(self) -> dict[str, Any] | None:
        """Additional eval metadata. Same as EvalLog.eval.metadata."""
        return self._metadata.get("eval_metadata") or None

    @property
    def task_args(self) -> dict[str, Any]:
        """Task arguments. Same as EvalLog.eval.task_args."""
        return self._metadata.get("task_args") or {}

    # ===== Model properties =====

    @property
    def generate_config(self) -> GenerateConfig:
        """Generate config for model instance. Same as EvalLog.eval.model_generate_config."""
        return GenerateConfig(**(self._metadata.get("generate_config") or {}))

    @property
    def model_roles(self) -> dict[str, Any] | None:
        """Model roles. Same as EvalLog.eval.model_roles."""
        return self._metadata.get("model_roles") or None

    # ===== Sample properties =====

    @property
    def id(self) -> str:
        """Unique id for sample. Same as EvalSampleSummary.id."""
        return str(self._metadata["id"])

    @property
    def epoch(self) -> int:
        """Epoch number for sample. Same as EvalSampleSummary.epoch."""
        return int(self._metadata["epoch"])

    @property
    def input(self) -> str:
        """Sample input. Derived from EvalSampleSummary.input (converted to string)."""
        return cast(str, self._metadata["input"])

    @property
    def target(self) -> list[str]:
        """Sample target value(s). Derived from EvalSampleSummary.target.

        Stored as comma-separated string; parsed back to list.
        """
        target = self._metadata["target"]
        if not target:
            return []
        return [t.strip() for t in target.split(",") if t.strip()]

    @property
    def sample_metadata(self) -> dict[str, Any]:
        """Sample metadata. Same as EvalSampleSummary.metadata."""
        return self._metadata.get("sample_metadata") or {}

    @property
    def working_time(self) -> float | None:
        """Working time for the sample. Same as EvalSampleSummary.working_time."""
        working_time = self._metadata.get("working_time")
        return float(working_time) if working_time is not None else None

    # ===== Score properties =====

    @property
    def score_values(self) -> dict[str, Value]:
        """Score values for this sample. Derived from EvalSampleSummary.scores.

        Note: Only score values are stored in transcript metadata,
        not full Score objects (answer, explanation, metadata are not available).
        """
        return {
            k.removeprefix("score_"): v
            for k, v in self._metadata.items()
            if k.startswith("score_")
        }
