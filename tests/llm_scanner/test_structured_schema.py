"""Tests for structured_schema validation."""

from typing import Any

import pytest
from inspect_ai._util.error import PrerequisiteError
from inspect_scout._llm_scanner.structured import structured_schema
from pydantic import BaseModel, Field


class TestSingleResultValid:
    """Tests for valid single result schemas."""

    def test_basic_single_result(self) -> None:
        """Test basic single result with explanation (label optional for single)."""

        class BasicAnswer(BaseModel):
            explanation: str = Field(description="Explanation of the classification")
            confidence: float = Field(description="Confidence score")

        schema = structured_schema(BasicAnswer, False)
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

        schema = structured_schema(AnswerWithLabel, False)
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

        schema = structured_schema(AliasedAnswer, False)
        assert schema is not None

    def test_single_result_with_nested_object(self) -> None:
        """Test single result with nested object."""

        class NestedInfo(BaseModel):
            value: str = Field(description="Some value")
            count: int = Field(description="A count")

        class NestedAnswer(BaseModel):
            explanation: str = Field(description="The explanation")
            info: NestedInfo = Field(description="Nested information")

        schema = structured_schema(NestedAnswer, False)
        assert schema is not None

    def test_single_result_with_array_field(self) -> None:
        """Test single result with array field."""

        class ArrayAnswer(BaseModel):
            explanation: str = Field(description="The explanation")
            tags: list[str] = Field(description="List of tags")

        schema = structured_schema(ArrayAnswer, False)
        assert schema is not None


class TestMultipleResultsValid:
    """Tests for valid multiple results schemas."""

    def test_basic_multiple_results(self) -> None:
        """Test basic multiple results structure."""

        class Finding(BaseModel):
            label: str = Field(description="Finding type")
            explanation: str = Field(description="Finding explanation")
            severity: str = Field(description="Severity level")

        class Findings(BaseModel):
            findings: list[Finding] = Field(description="List of findings")

        schema = structured_schema(Findings, True)
        assert schema is not None
        assert schema.properties is not None
        assert "findings" in schema.properties

    def test_multiple_results_with_aliases(self) -> None:
        """Test multiple results with aliased fields in inner type."""

        class Issue(BaseModel):
            lbl: str = Field(alias="label", description="Issue type")
            exp: str = Field(alias="explanation", description="Issue details")

        class Issues(BaseModel):
            items: list[Issue] = Field(description="List of issues")

        schema = structured_schema(Issues, True)
        assert schema is not None

    def test_multiple_results_with_nested_objects(self) -> None:
        """Test multiple results with nested objects in items."""

        class Location(BaseModel):
            file: str = Field(description="File path")
            line: int = Field(description="Line number")

        class Bug(BaseModel):
            label: str = Field(description="Bug type")
            explanation: str = Field(description="Bug description")
            location: Location = Field(description="Bug location")

        class Bugs(BaseModel):
            bugs: list[Bug] = Field(description="List of bugs")

        schema = structured_schema(Bugs, True)
        assert schema is not None


class TestSingleResultInvalid:
    """Tests for invalid single result schemas."""

    def test_missing_explanation_field(self) -> None:
        """Test that missing explanation field raises error."""

        class NoExplanation(BaseModel):
            other: str = Field(description="Other field")

        with pytest.raises(
            PrerequisiteError, match="must have a required 'explanation'"
        ):
            structured_schema(NoExplanation, False)

    def test_optional_explanation_field(self) -> None:
        """Test that optional explanation field raises error."""

        class OptionalExplanation(BaseModel):
            explanation: str | None = Field(
                default=None, description="Optional explanation"
            )

        with pytest.raises(
            PrerequisiteError, match="must have a required 'explanation'"
        ):
            structured_schema(OptionalExplanation, False)

    def test_missing_description_on_field(self) -> None:
        """Test that missing description raises error."""

        class MissingDescription(BaseModel):
            explanation: str = Field(description="The explanation")
            bad_field: str  # No description

        with pytest.raises(PrerequisiteError, match="missing descriptions"):
            structured_schema(MissingDescription, False)

    def test_missing_description_on_nested_field(self) -> None:
        """Test that missing description on nested field raises error."""

        class NestedBad(BaseModel):
            value: str  # No description

        class WithBadNested(BaseModel):
            explanation: str = Field(description="The explanation")
            nested: NestedBad = Field(description="Nested object")

        with pytest.raises(PrerequisiteError, match="missing descriptions"):
            structured_schema(WithBadNested, False)


class TestMultipleResultsInvalid:
    """Tests for invalid multiple results schemas."""

    def test_multiple_fields_in_wrapper(self) -> None:
        """Test that multiple fields in wrapper raises error."""

        class Finding(BaseModel):
            label: str = Field(description="Finding label")
            explanation: str = Field(description="Finding explanation")

        class BadWrapper(BaseModel):
            findings: list[Finding] = Field(description="List of findings")
            metadata: dict[str, Any] = Field(default={}, description="Metadata")

        with pytest.raises(PrerequisiteError, match="must have exactly one field"):
            structured_schema(BadWrapper, True)

    def test_not_a_list_field(self) -> None:
        """Test that non-list field raises error."""

        class Finding(BaseModel):
            label: str = Field(description="Finding label")
            explanation: str = Field(description="Finding explanation")

        class NotAList(BaseModel):
            finding: Finding = Field(description="Single finding")

        with pytest.raises(PrerequisiteError, match="Could not extract BaseModel type"):
            structured_schema(NotAList, True)

    def test_list_of_non_objects(self) -> None:
        """Test that list of non-objects raises error."""

        class ListOfStrings(BaseModel):
            items: list[str] = Field(description="List of strings")

        with pytest.raises(PrerequisiteError, match="Could not extract BaseModel type"):
            structured_schema(ListOfStrings, True)

    def test_missing_label_in_list_items(self) -> None:
        """Test that missing label in list items raises error."""

        class FindingNoLabel(BaseModel):
            explanation: str = Field(description="Finding explanation")
            severity: str = Field(description="Severity")

        class Findings(BaseModel):
            findings: list[FindingNoLabel] = Field(description="List of findings")

        with pytest.raises(PrerequisiteError, match="must have a required 'label'"):
            structured_schema(Findings, True)

    def test_missing_explanation_in_list_items(self) -> None:
        """Test that missing explanation in list items raises error."""

        class FindingNoExplanation(BaseModel):
            label: str = Field(description="Finding label")
            severity: str = Field(description="Severity")

        class Findings(BaseModel):
            findings: list[FindingNoExplanation] = Field(description="List of findings")

        with pytest.raises(
            PrerequisiteError, match="must have a required 'explanation'"
        ):
            structured_schema(Findings, True)

    def test_missing_description_in_list_items(self) -> None:
        """Test that missing description in list items raises error."""

        class FindingBadDescription(BaseModel):
            label: str = Field(description="Finding label")
            explanation: str = Field(description="Finding explanation")
            bad_field: str  # No description

        class Findings(BaseModel):
            findings: list[FindingBadDescription] = Field(
                description="List of findings"
            )

        with pytest.raises(PrerequisiteError, match="missing descriptions"):
            structured_schema(Findings, True)


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_explanation_via_alias_only(self) -> None:
        """Test that explanation field can be provided only via alias."""

        class ViaAlias(BaseModel):
            reason: str = Field(alias="explanation", description="Reason (explanation)")

        schema = structured_schema(ViaAlias, False)
        assert schema is not None

    def test_label_via_alias_in_multiple(self) -> None:
        """Test that label field can be provided via alias for multiple results."""

        class Finding(BaseModel):
            cat: str = Field(alias="label", description="Category")
            explanation: str = Field(description="Explanation")

        class Findings(BaseModel):
            findings: list[Finding] = Field(description="List of findings")

        schema = structured_schema(Findings, True)
        assert schema is not None

    def test_both_fields_via_alias_multiple(self) -> None:
        """Test that both required fields can be provided via alias for multiple results."""

        class Finding(BaseModel):
            cat: str = Field(alias="label", description="Category")
            reason: str = Field(alias="explanation", description="Reason")

        class Findings(BaseModel):
            findings: list[Finding] = Field(description="List of findings")

        schema = structured_schema(Findings, True)
        assert schema is not None

    def test_many_additional_fields(self) -> None:
        """Test schema with many additional fields beyond required ones."""

        class ManyFields(BaseModel):
            explanation: str = Field(description="Explanation")
            field1: str = Field(description="Field 1")
            field2: int = Field(description="Field 2")
            field3: float = Field(description="Field 3")
            field4: bool = Field(description="Field 4")
            field5: list[str] = Field(description="Field 5")

        schema = structured_schema(ManyFields, False)
        assert schema is not None
        assert schema.properties is not None
        assert len(schema.properties) == 6
