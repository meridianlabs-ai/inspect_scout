"""Tests for SampleMetadata typed accessor for Inspect eval log transcripts."""

from typing import Any

import pytest
from inspect_ai.scorer._metric import Score
from inspect_scout import SampleMetadata, Transcript
from inspect_scout._transcript.eval_log import EVAL_LOG_SOURCE_TYPE


def create_test_transcript(
    source_type: str = EVAL_LOG_SOURCE_TYPE,
    metadata: dict[str, object] | None = None,
) -> Transcript:
    """Create a test transcript with the given metadata."""
    return Transcript(
        transcript_id="test-id",
        source_type=source_type,
        source_id="eval-id",
        source_uri="/path/to/log.eval",
        metadata=metadata or {},
    )


def get_property_doc(prop: Any) -> str:
    """Get docstring from a property descriptor."""
    if not isinstance(prop, property):
        raise TypeError(f"Expected property, got {type(prop)}")
    assert prop.fget is not None
    assert prop.fget.__doc__ is not None
    return prop.fget.__doc__


# ============================================================================
# Constructor Tests
# ============================================================================


def test_eval_log_source() -> None:
    """Test that SampleMetadata accepts transcripts from eval logs."""
    transcript = create_test_transcript(source_type=EVAL_LOG_SOURCE_TYPE)
    metadata = SampleMetadata(transcript)
    assert metadata is not None


def test_non_eval_log_raises() -> None:
    """Test that SampleMetadata rejects transcripts from other sources."""
    transcript = create_test_transcript(source_type="weave")
    with pytest.raises(ValueError, match="source_type='eval_log'"):
        SampleMetadata(transcript)


# ============================================================================
# Typed Interface Tests
# ============================================================================


def test_typed_properties_exist() -> None:
    """Test that all typed properties exist and return correct types."""
    transcript = create_test_transcript(
        metadata={
            "eval_id": "eval-abc-123",
            "log": "/path/to/eval.log",
            "eval_status": "success",
            "eval_tags": "tag1, tag2",
            "eval_metadata": {"key": "value"},
            "task_args": {"temperature": 0.7},
            "generate_config": {"max_tokens": 100},
            "model_roles": {"system": "You are helpful"},
            "id": "sample-123",
            "epoch": 3,
            "input": "What is 2+2?",
            "target": "4",
            "sample_metadata": {"difficulty": "easy"},
            "working_time": 1.5,
            "score_accuracy": 0.9,
            "solver": "cot",
            "solver_args": {"depth": 3},
        }
    )
    metadata = SampleMetadata(transcript)

    # Eval info properties
    assert metadata.eval_id == "eval-abc-123"
    assert metadata.log == "/path/to/eval.log"
    assert metadata.eval_status == "success"
    assert metadata.eval_tags == ["tag1", "tag2"]
    assert metadata.eval_metadata == {"key": "value"}
    assert metadata.task_args == {"temperature": 0.7}

    # Model properties
    assert metadata.generate_config == {"max_tokens": 100}
    assert metadata.model_roles == {"system": "You are helpful"}

    # Sample properties
    assert metadata.id == "sample-123"
    assert metadata.epoch == 3
    assert metadata.input == "What is 2+2?"
    assert metadata.target == "4"
    assert metadata.sample_metadata == {"difficulty": "easy"}
    assert metadata.working_time == 1.5

    # Score properties
    assert "accuracy" in metadata.scores
    assert isinstance(metadata.scores["accuracy"], Score)
    assert metadata.scores["accuracy"].value == 0.9

    # Legacy properties
    assert metadata.solver == "cot"
    assert metadata.solver_args == {"depth": 3}


def test_empty_metadata_defaults() -> None:
    """Test that properties return appropriate defaults when metadata is empty."""
    transcript = create_test_transcript(metadata={})
    metadata = SampleMetadata(transcript)

    # Optional fields return None
    assert metadata.eval_id is None
    assert metadata.log is None
    assert metadata.eval_status is None
    assert metadata.id is None
    assert metadata.epoch is None
    assert metadata.input is None
    assert metadata.target is None
    assert metadata.working_time is None
    assert metadata.solver is None

    # Collection fields return empty collections
    assert metadata.eval_tags == []
    assert metadata.eval_metadata == {}
    assert metadata.task_args == {}
    assert metadata.generate_config == {}
    assert metadata.model_roles == {}
    assert metadata.sample_metadata == {}
    assert metadata.scores == {}
    assert metadata.solver_args == {}


def test_typed_properties_have_docstrings() -> None:
    """Test that typed properties have meaningful docstrings."""
    assert "eval" in get_property_doc(SampleMetadata.eval_id).lower()
    assert "log" in get_property_doc(SampleMetadata.log).lower()
    assert "status" in get_property_doc(SampleMetadata.eval_status).lower()
    assert "tag" in get_property_doc(SampleMetadata.eval_tags).lower()
    assert "id" in get_property_doc(SampleMetadata.id).lower()
    assert "epoch" in get_property_doc(SampleMetadata.epoch).lower()
    assert "score" in get_property_doc(SampleMetadata.scores).lower()
