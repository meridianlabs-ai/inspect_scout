"""Tests for SampleMetadata typed accessor for Inspect eval log transcripts."""

from typing import Any

import pytest
from inspect_scout import SampleMetadata, Transcript
from inspect_scout._transcript.eval_log import EVAL_LOG_SOURCE_TYPE


def create_test_transcript(
    source_type: str = EVAL_LOG_SOURCE_TYPE,
    metadata: dict[str, object] | None = None,
) -> Transcript:
    """Create a test transcript with the given metadata."""
    # Include required fields by default
    default_metadata: dict[str, object] = {
        "eval_id": "eval-abc-123",
        "log": "/path/to/eval.log",
        "eval_status": "success",
        "id": "sample-123",
        "epoch": 3,
        "input": "What is 2+2?",
        "target": "default target",
    }
    if metadata is not None:
        default_metadata.update(metadata)
    return Transcript(
        transcript_id="test-id",
        source_type=source_type,
        source_id="eval-id",
        source_uri="/path/to/log.eval",
        metadata=default_metadata,
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
    """Test that typed properties with transformation logic work correctly."""
    transcript = create_test_transcript(
        metadata={
            "eval_tags": "tag1, tag2",
            "eval_metadata": {"key": "value"},
            "task_args": {"temperature": 0.7},
            "generate_config": {"max_tokens": 100},
            "model_roles": {"system": "You are helpful"},
            "target": "4",
            "sample_metadata": {"difficulty": "easy"},
            "score_accuracy": 0.9,
        }
    )
    metadata = SampleMetadata(transcript)

    # Comma-separated parsing
    assert metadata.eval_tags == ["tag1", "tag2"]
    assert metadata.target == ["4"]

    # Dict properties
    assert metadata.eval_metadata == {"key": "value"}
    assert metadata.task_args == {"temperature": 0.7}
    assert metadata.model_roles == {"system": "You are helpful"}
    assert metadata.sample_metadata == {"difficulty": "easy"}

    # Object construction
    assert metadata.generate_config.max_tokens == 100

    # Score prefix stripping
    assert "accuracy" in metadata.score_values
    assert metadata.score_values["accuracy"] == 0.9


def test_optional_fields_defaults() -> None:
    """Test that optional properties return appropriate defaults."""
    transcript = create_test_transcript()
    metadata = SampleMetadata(transcript)

    # Optional fields return None
    assert metadata.working_time is None
    assert metadata.generate_config.max_tokens is None
    assert metadata.eval_tags is None
    assert metadata.eval_metadata is None
    assert metadata.model_roles is None

    # Collection fields return empty collections
    assert metadata.task_args == {}
    assert metadata.sample_metadata == {}
    assert metadata.score_values == {}


def test_typed_properties_have_docstrings() -> None:
    """Test that typed properties have meaningful docstrings."""
    assert "eval" in get_property_doc(SampleMetadata.eval_id).lower()
    assert "log" in get_property_doc(SampleMetadata.log).lower()
    assert "status" in get_property_doc(SampleMetadata.eval_status).lower()
    assert "tag" in get_property_doc(SampleMetadata.eval_tags).lower()
    assert "id" in get_property_doc(SampleMetadata.id).lower()
    assert "epoch" in get_property_doc(SampleMetadata.epoch).lower()
    assert "score" in get_property_doc(SampleMetadata.score_values).lower()
