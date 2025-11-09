"""Tests for structured_result function."""

import re
from typing import Any, Literal, cast

import pytest
from inspect_ai.model import ModelOutput
from inspect_scout._llm_scanner.structured import structured_result
from inspect_scout._llm_scanner.types import AnswerStructured
from inspect_scout._scanner.result import Reference
from pydantic import BaseModel, Field


def mock_extract_references(text: str) -> list[Reference]:
    """Mock reference extraction for testing."""
    # Simple mock that looks for [M1], [E1] patterns
    refs = []
    for match in re.finditer(r"\[(M|E)(\d+)\]", text):
        ref_type: Literal["message", "event"] = (
            "message" if match.group(1) == "M" else "event"
        )
        refs.append(
            Reference(type=ref_type, cite=match.group(0), id=f"test-{match.group(0)}")
        )
    return refs


class TestSingleResultWithTrueValue:
    """Tests for single results with result_value='true'."""

    def test_basic_single_result_true(self) -> None:
        """Test single result with value=True."""

        class Analysis(BaseModel):
            explanation: str = Field(description="Analysis explanation")
            confidence: float = Field(description="Confidence score")

        answer = AnswerStructured(type=Analysis, result_value="true")
        output = ModelOutput(
            model="test",
            completion='{"explanation": "Test explanation", "confidence": 0.9}',
        )

        result = structured_result(answer, output, mock_extract_references)

        assert result.value is True
        assert result.explanation == "Test explanation"
        assert result.label is None
        assert result.metadata == {"confidence": 0.9}
        assert result.references == []

    def test_single_result_with_references(self) -> None:
        """Test that references are extracted from explanation."""

        class Analysis(BaseModel):
            explanation: str = Field(description="Analysis explanation")

        answer = AnswerStructured(type=Analysis, result_value="true")
        output = ModelOutput(
            model="test",
            completion='{"explanation": "See [M1] and [E2] for details"}',
        )

        result = structured_result(answer, output, mock_extract_references)

        assert result.value is True
        assert len(result.references) == 2
        assert result.references[0].type == "message"
        assert result.references[0].cite == "[M1]"
        assert result.references[1].type == "event"
        assert result.references[1].cite == "[E2]"


class TestSingleResultWithObjectValue:
    """Tests for single results with result_value='object'."""

    def test_single_result_object(self) -> None:
        """Test single result with value as object."""

        class Analysis(BaseModel):
            explanation: str = Field(description="Analysis explanation")
            clarity: int = Field(description="Clarity rating")
            persuasiveness: int = Field(description="Persuasiveness rating")

        answer = AnswerStructured(type=Analysis, result_value="object")
        output = ModelOutput(
            model="test",
            completion='{"explanation": "Good analysis", "clarity": 8, "persuasiveness": 7}',
        )

        result = structured_result(answer, output, mock_extract_references)

        assert result.value == {"clarity": 8, "persuasiveness": 7}
        assert result.explanation == "Good analysis"
        assert result.metadata is None  # All fields used in value

    def test_single_result_object_with_label(self) -> None:
        """Test object value doesn't include label field."""

        class Analysis(BaseModel):
            label: str = Field(description="Label")
            explanation: str = Field(description="Explanation")
            score: int = Field(description="Score")

        answer = AnswerStructured(type=Analysis, result_value="object")
        output = ModelOutput(
            model="test",
            completion='{"label": "positive", "explanation": "Good", "score": 9}',
        )

        result = structured_result(answer, output, mock_extract_references)

        assert result.value == {"score": 9}
        assert result.label == "positive"
        assert result.explanation == "Good"


class TestSingleResultWithValueAlias:
    """Tests for single results with alias='value' field."""

    def test_single_result_with_value_alias(self) -> None:
        """Test that field with alias='value' is used for result value."""

        class Classification(BaseModel):
            category: str = Field(alias="value", description="Category")
            explanation: str = Field(description="Explanation")
            confidence: float = Field(description="Confidence")

        answer = AnswerStructured(type=Classification)  # result_value=None
        output = ModelOutput(
            model="test",
            completion='{"value": "spam", "explanation": "Looks like spam", "confidence": 0.95}',
        )

        result = structured_result(answer, output, mock_extract_references)

        assert result.value == "spam"
        assert result.explanation == "Looks like spam"
        assert result.metadata == {"confidence": 0.95}

    def test_single_result_no_value_alias_defaults_true(self) -> None:
        """Test that without value alias, value defaults to True."""

        class Analysis(BaseModel):
            explanation: str = Field(description="Explanation")
            score: int = Field(description="Score")

        answer = AnswerStructured(type=Analysis)  # result_value=None
        output = ModelOutput(
            model="test", completion='{"explanation": "Good", "score": 8}'
        )

        result = structured_result(answer, output, mock_extract_references)

        assert result.value is True
        assert result.metadata == {"score": 8}


class TestFieldAliases:
    """Tests for explanation and label field aliases."""

    def test_explanation_via_alias(self) -> None:
        """Test explanation field can be provided via alias."""

        class Analysis(BaseModel):
            reason: str = Field(alias="explanation", description="The reason")
            score: int = Field(description="Score")

        answer = AnswerStructured(type=Analysis, result_value="true")
        output = ModelOutput(
            model="test", completion='{"explanation": "Because reasons", "score": 7}'
        )

        result = structured_result(answer, output, mock_extract_references)

        assert result.explanation == "Because reasons"
        assert result.metadata == {"score": 7}

    def test_label_via_alias(self) -> None:
        """Test label field can be provided via alias."""

        class Observation(BaseModel):
            obs_type: Literal["humor", "irony"] = Field(
                alias="label", description="Type"
            )
            explanation: str = Field(description="Explanation")

        answer = AnswerStructured(type=Observation)
        output = ModelOutput(
            model="test",
            completion='{"label": "humor", "explanation": "Funny joke"}',
        )

        result = structured_result(answer, output, mock_extract_references)

        assert result.label == "humor"
        assert result.explanation == "Funny joke"


class TestResultSets:
    """Tests for result sets (multiple results)."""

    def test_basic_result_set(self) -> None:
        """Test basic result set with multiple items."""

        class Finding(BaseModel):
            label: str = Field(description="Finding type")
            explanation: str = Field(description="Explanation")
            severity: str = Field(description="Severity")

        answer = AnswerStructured(type=Finding, result_set=True)
        output = ModelOutput(
            model="test",
            completion="""{
                "results": [
                    {"label": "bug", "explanation": "Found a bug", "severity": "high"},
                    {"label": "typo", "explanation": "Found a typo", "severity": "low"}
                ]
            }""",
        )

        result = structured_result(answer, output, mock_extract_references)

        assert result.type == "resultset"
        assert isinstance(result.value, list)
        assert len(result.value) == 2

        # Cast to list[dict] for type checking
        value_list = cast(list[dict[str, Any]], result.value)

        # Check first item
        assert value_list[0]["label"] == "bug"
        assert value_list[0]["explanation"] == "Found a bug"
        assert value_list[0]["metadata"] == {"severity": "high"}

        # Check second item
        assert value_list[1]["label"] == "typo"
        assert value_list[1]["explanation"] == "Found a typo"
        assert value_list[1]["metadata"] == {"severity": "low"}

    def test_result_set_with_value_determination(self) -> None:
        """Test result set with result_value setting."""

        class Issue(BaseModel):
            label: str = Field(description="Issue type")
            explanation: str = Field(description="Explanation")
            line_number: int = Field(description="Line number")

        answer = AnswerStructured(type=Issue, result_set=True, result_value="object")
        output = ModelOutput(
            model="test",
            completion="""{
                "results": [
                    {"label": "error", "explanation": "Syntax error", "line_number": 42}
                ]
            }""",
        )

        result = structured_result(answer, output, mock_extract_references)

        # With result_value="object", each item's value should be the object minus label/explanation
        value_list = cast(list[dict[str, Any]], result.value)
        assert value_list[0]["value"] == {"line_number": 42}

    def test_result_set_with_aliases(self) -> None:
        """Test result set where inner type uses field aliases."""

        class Observation(BaseModel):
            obs_type: Literal["humor", "verbosity"] = Field(
                alias="label", description="Type"
            )
            reason: str = Field(alias="explanation", description="Reason")

        answer = AnswerStructured(type=Observation, result_set="observations")
        output = ModelOutput(
            model="test",
            completion="""{
                "observations": [
                    {"label": "humor", "explanation": "Funny"},
                    {"label": "verbosity", "explanation": "Too wordy"}
                ]
            }""",
        )

        result = structured_result(answer, output, mock_extract_references)

        value_list = cast(list[dict[str, Any]], result.value)
        assert len(value_list) == 2
        assert value_list[0]["label"] == "humor"
        assert value_list[0]["explanation"] == "Funny"


class TestErrorCases:
    """Tests for error conditions."""

    def test_missing_explanation_raises(self) -> None:
        """Test that missing explanation field raises ValueError."""

        class BadModel(BaseModel):
            score: int = Field(description="Score")

        answer = AnswerStructured(type=BadModel)
        output = ModelOutput(model="test", completion='{"score": 5}')

        with pytest.raises(ValueError, match="Missing required 'explanation'"):
            structured_result(answer, output, mock_extract_references)

    def test_result_set_missing_label_raises(self) -> None:
        """Test that result set without label raises ValueError."""

        class BadFinding(BaseModel):
            explanation: str = Field(description="Explanation")

        answer = AnswerStructured(type=BadFinding, result_set=True)
        output = ModelOutput(
            model="test",
            completion='{"results": [{"explanation": "Test"}]}',
        )

        with pytest.raises(ValueError, match="Missing required 'label'"):
            structured_result(answer, output, mock_extract_references)
