"""Tests for structured_schema validation."""

import pytest
from inspect_ai._util.error import PrerequisiteError
from inspect_scout._llm_scanner.structured import structured_schema
from inspect_scout._llm_scanner.types import AnswerStructured
from pydantic import BaseModel, Field


class TestSingleResultValid:
    """Tests for valid single result schemas."""

    def test_basic_single_result(self) -> None:
        """Test basic single result with explanation (label optional for single)."""

        class BasicAnswer(BaseModel):
            explanation: str = Field(description="Explanation of the classification")
            confidence: float = Field(description="Confidence score")

        schema = structured_schema(AnswerStructured(type=BasicAnswer))
        assert schema is not None
        assert schema.properties is not None
        assert "explanation" in schema.properties
        assert "confidence" in schema.properties

    def test_single_result_with_label(self) -> None:
        """Test single result can optionally have label field."""

        class AnswerWithLabel(BaseModel):
            label: str = Field(description="The classification label")
            explanation: str = Field(description="Explanation of the classification")
            confidence: float = Field(description="Confidence score")

        schema = structured_schema(AnswerStructured(type=AnswerWithLabel))
        assert schema is not None
        assert schema.properties is not None
        assert "label" in schema.properties
        assert "explanation" in schema.properties
        assert "confidence" in schema.properties

    def test_single_result_with_aliases(self) -> None:
        """Test single result with aliased explanation field."""

        class AliasedAnswer(BaseModel):
            exp: str = Field(alias="explanation", description="The explanation")
            other: int = Field(description="Other field")

        schema = structured_schema(AnswerStructured(type=AliasedAnswer))
        assert schema is not None

    def test_single_result_with_nested_object(self) -> None:
        """Test single result with nested object."""

        class NestedInfo(BaseModel):
            value: str = Field(description="Some value")
            count: int = Field(description="A count")

        class NestedAnswer(BaseModel):
            explanation: str = Field(description="The explanation")
            info: NestedInfo = Field(description="Nested information")

        schema = structured_schema(AnswerStructured(type=NestedAnswer))
        assert schema is not None

    def test_single_result_with_array_field(self) -> None:
        """Test single result with array field."""

        class ArrayAnswer(BaseModel):
            explanation: str = Field(description="The explanation")
            tags: list[str] = Field(description="List of tags")

        schema = structured_schema(AnswerStructured(type=ArrayAnswer))
        assert schema is not None


class TestMultipleResultsValid:
    """Tests for valid multiple results schemas."""

    def test_basic_multiple_results(self) -> None:
        """Test basic multiple results structure."""

        class Finding(BaseModel):
            label: str = Field(description="Finding type")
            explanation: str = Field(description="Finding explanation")
            severity: str = Field(description="Severity level")

        schema = structured_schema(AnswerStructured(type=list[Finding]))
        assert schema is not None
        assert schema.properties is not None
        assert "results" in schema.properties
        # Verify it's an array type
        assert schema.properties["results"].type == "array"

    def test_multiple_results_with_aliases(self) -> None:
        """Test multiple results with aliased fields in inner type."""

        class Issue(BaseModel):
            lbl: str = Field(alias="label", description="Issue type")
            exp: str = Field(alias="explanation", description="Issue details")

        schema = structured_schema(AnswerStructured(type=list[Issue]))
        assert schema is not None
        assert schema.properties is not None
        assert "results" in schema.properties

    def test_multiple_results_with_nested_objects(self) -> None:
        """Test multiple results with nested objects in items."""

        class Location(BaseModel):
            file: str = Field(description="File path")
            line: int = Field(description="Line number")

        class Bug(BaseModel):
            label: str = Field(description="Bug type")
            explanation: str = Field(description="Bug description")
            location: Location = Field(description="Bug location")

        schema = structured_schema(AnswerStructured(type=list[Bug]))
        assert schema is not None
        assert schema.properties is not None
        assert "results" in schema.properties


class TestSingleResultInvalid:
    """Tests for invalid single result schemas."""

    def test_auto_adds_explanation_field(self) -> None:
        """Test that explanation field is automatically added if missing."""

        class NoExplanation(BaseModel):
            other: str = Field(description="Other field")

        # Should not raise - explanation is auto-added
        schema = structured_schema(AnswerStructured(type=NoExplanation))
        assert schema is not None
        assert schema.properties is not None
        # Verify explanation was added to the schema
        assert "explanation" in schema.properties

    def test_optional_explanation_field(self) -> None:
        """Test that optional explanation field is preserved."""

        class OptionalExplanation(BaseModel):
            explanation: str | None = Field(
                default=None, description="Optional explanation"
            )

        # Should not raise - optional explanation is preserved as-is
        schema = structured_schema(AnswerStructured(type=OptionalExplanation))
        assert schema is not None
        assert schema.properties is not None
        assert "explanation" in schema.properties

    def test_missing_description_on_field(self) -> None:
        """Test that missing description raises error."""

        class MissingDescription(BaseModel):
            explanation: str = Field(description="The explanation")
            bad_field: str  # No description

        with pytest.raises(PrerequisiteError, match="missing descriptions"):
            structured_schema(AnswerStructured(type=MissingDescription))

    def test_missing_description_on_nested_field(self) -> None:
        """Test that missing description on nested field raises error."""

        class NestedBad(BaseModel):
            value: str  # No description

        class WithBadNested(BaseModel):
            explanation: str = Field(description="The explanation")
            nested: NestedBad = Field(description="Nested object")

        with pytest.raises(PrerequisiteError, match="missing descriptions"):
            structured_schema(AnswerStructured(WithBadNested))


class TestMultipleResultsInvalid:
    """Tests for invalid multiple results schemas."""

    def test_auto_adds_explanation_in_list_items(self) -> None:
        """Test that explanation is auto-added for result set items."""

        class FindingNoExplanation(BaseModel):
            label: str = Field(description="Finding label")
            severity: str = Field(description="Severity")

        # Should not raise - explanation is auto-added
        schema = structured_schema(AnswerStructured(type=list[FindingNoExplanation]))
        assert schema is not None
        # Result sets have a wrapper, so check the items schema
        assert schema.properties is not None
        assert "results" in schema.properties

    def test_missing_description_in_list_items(self) -> None:
        """Test that missing description in list items raises error."""

        class FindingBadDescription(BaseModel):
            label: str = Field(description="Finding label")
            explanation: str = Field(description="Finding explanation")
            bad_field: str  # No description

        with pytest.raises(PrerequisiteError, match="missing descriptions"):
            structured_schema(AnswerStructured(type=list[FindingBadDescription]))


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_explanation_via_alias_only(self) -> None:
        """Test that explanation field can be provided only via alias."""

        class ViaAlias(BaseModel):
            reason: str = Field(alias="explanation", description="Reason (explanation)")

        schema = structured_schema(AnswerStructured(type=ViaAlias))
        assert schema is not None

    def test_label_via_alias_in_multiple(self) -> None:
        """Test that label field can be provided via alias for multiple results."""

        class Finding(BaseModel):
            cat: str = Field(alias="label", description="Category")
            explanation: str = Field(description="Explanation")

        schema = structured_schema(AnswerStructured(type=list[Finding]))
        assert schema is not None
        assert schema.properties is not None
        assert "results" in schema.properties

    def test_both_fields_via_alias_multiple(self) -> None:
        """Test that both required fields can be provided via alias for multiple results."""

        class Finding(BaseModel):
            cat: str = Field(alias="label", description="Category")
            reason: str = Field(alias="explanation", description="Reason")

        schema = structured_schema(AnswerStructured(type=list[Finding]))
        assert schema is not None
        assert schema.properties is not None
        assert "results" in schema.properties

    def test_many_additional_fields(self) -> None:
        """Test schema with many additional fields beyond required ones."""

        class ManyFields(BaseModel):
            explanation: str = Field(description="Explanation")
            field1: str = Field(description="Field 1")
            field2: int = Field(description="Field 2")
            field3: float = Field(description="Field 3")
            field4: bool = Field(description="Field 4")
            field5: list[str] = Field(description="Field 5")

        schema = structured_schema(AnswerStructured(type=ManyFields))
        assert schema is not None
        assert schema.properties is not None
        assert len(schema.properties) == 6
