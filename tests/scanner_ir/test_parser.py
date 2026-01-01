"""Tests for scanner IR parser."""

from inspect_scout._scanner_ir import parse_scanner_file


class TestParseLLMScanner:
    """Tests for parsing llm_scanner definitions."""

    def test_parse_simple_boolean_scanner(self) -> None:
        """Parse a simple boolean llm_scanner."""
        source = """
from inspect_scout import Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript


@scanner(messages="all")
def refusal_detected() -> Scanner[Transcript]:
    return llm_scanner(
        question="Did the assistant refuse the request?",
        answer="boolean",
    )
"""
        result = parse_scanner_file(source)

        assert result.editable is True
        assert result.scanner is not None
        assert result.scanner.function_name == "refusal_detected"
        assert result.scanner.scanner_type == "llm"
        assert result.scanner.llm_scanner is not None
        assert (
            result.scanner.llm_scanner.question
            == "Did the assistant refuse the request?"
        )
        assert result.scanner.llm_scanner.answer_type == "boolean"
        assert result.scanner.decorator.messages == "all"

    def test_parse_numeric_scanner_with_model(self) -> None:
        """Parse a numeric scanner with model specified."""
        source = """
from inspect_scout import Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript


@scanner(messages="all")
def efficiency() -> Scanner[Transcript]:
    return llm_scanner(
        question="Rate efficiency 1-10",
        answer="numeric",
        model="openai/gpt-4o",
        retry_refusals=5,
    )
"""
        result = parse_scanner_file(source)

        assert result.editable is True
        assert result.scanner is not None
        assert result.scanner.llm_scanner is not None
        assert result.scanner.llm_scanner.answer_type == "numeric"
        assert result.scanner.llm_scanner.model == "openai/gpt-4o"
        assert result.scanner.llm_scanner.retry_refusals == 5

    def test_parse_labels_scanner(self) -> None:
        """Parse a scanner with label list answer."""
        source = """
from inspect_scout import Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript


@scanner(messages="all")
def quality() -> Scanner[Transcript]:
    return llm_scanner(
        question="Rate quality",
        answer=["Excellent", "Good", "Poor"],
    )
"""
        result = parse_scanner_file(source)

        assert result.editable is True
        assert result.scanner is not None
        assert result.scanner.llm_scanner is not None
        assert result.scanner.llm_scanner.answer_type == "labels"
        assert result.scanner.llm_scanner.labels == ["Excellent", "Good", "Poor"]

    def test_parse_multi_labels_scanner(self) -> None:
        """Parse a scanner with AnswerMultiLabel."""
        source = """
from inspect_scout import AnswerMultiLabel, Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript


@scanner(messages="all")
def categories() -> Scanner[Transcript]:
    return llm_scanner(
        question="Select categories",
        answer=AnswerMultiLabel(labels=["A", "B", "C"]),
    )
"""
        result = parse_scanner_file(source)

        assert result.editable is True
        assert result.scanner is not None
        assert result.scanner.llm_scanner is not None
        assert result.scanner.llm_scanner.answer_type == "multi_labels"
        assert result.scanner.llm_scanner.labels == ["A", "B", "C"]

    def test_parse_scanner_with_template(self) -> None:
        """Parse a scanner with custom template."""
        source = """
from inspect_scout import Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript


@scanner(messages="all")
def custom() -> Scanner[Transcript]:
    return llm_scanner(
        question="Question?",
        answer="boolean",
        template="Custom template: {{ question }}",
    )
"""
        result = parse_scanner_file(source)

        assert result.editable is True
        assert result.scanner is not None
        assert result.scanner.llm_scanner is not None
        assert result.scanner.llm_scanner.template == "Custom template: {{ question }}"

    def test_parse_structured_answer(self) -> None:
        """Parse a scanner with AnswerStructured and Pydantic model."""
        source = """
from pydantic import BaseModel, Field
from inspect_scout import AnswerStructured, Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript


class Analysis(BaseModel):
    score: int = Field(description="Score from 1-10")
    reasoning: str = Field(description="Explanation")


@scanner(messages="all")
def analyze() -> Scanner[Transcript]:
    return llm_scanner(
        question="Analyze this",
        answer=AnswerStructured(type=Analysis),
    )
"""
        result = parse_scanner_file(source)

        assert result.editable is True
        assert result.scanner is not None
        assert result.scanner.llm_scanner is not None
        assert result.scanner.llm_scanner.answer_type == "structured"
        assert result.scanner.llm_scanner.structured_spec is not None
        assert result.scanner.llm_scanner.structured_spec.class_name == "Analysis"
        assert len(result.scanner.llm_scanner.structured_spec.fields) == 2
        assert result.scanner.structured_model is not None

    def test_parse_with_comments(self) -> None:
        """Parse scanner with comments in function body."""
        source = """
from inspect_scout import Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript


@scanner(messages="all")
def with_comments() -> Scanner[Transcript]:
    # This is a comment that should be preserved
    return llm_scanner(
        question="Question?",
        answer="boolean",
    )
"""
        result = parse_scanner_file(source)

        assert result.editable is True
        assert result.scanner is not None


class TestParseGrepScanner:
    """Tests for parsing grep_scanner definitions."""

    def test_parse_single_pattern(self) -> None:
        """Parse grep_scanner with single pattern."""
        source = """
from inspect_scout import Scanner, grep_scanner, scanner
from inspect_scout._transcript.types import Transcript


@scanner(messages="all")
def find_error() -> Scanner[Transcript]:
    return grep_scanner(pattern="error")
"""
        result = parse_scanner_file(source)

        assert result.editable is True
        assert result.scanner is not None
        assert result.scanner.scanner_type == "grep"
        assert result.scanner.grep_scanner is not None
        assert result.scanner.grep_scanner.pattern_type == "single"
        assert result.scanner.grep_scanner.pattern == "error"

    def test_parse_pattern_list(self) -> None:
        """Parse grep_scanner with pattern list."""
        source = """
from inspect_scout import Scanner, grep_scanner, scanner
from inspect_scout._transcript.types import Transcript


@scanner(messages="all")
def find_issues() -> Scanner[Transcript]:
    return grep_scanner(pattern=["error", "warning", "failed"])
"""
        result = parse_scanner_file(source)

        assert result.editable is True
        assert result.scanner is not None
        assert result.scanner.grep_scanner is not None
        assert result.scanner.grep_scanner.pattern_type == "list"
        assert result.scanner.grep_scanner.patterns == ["error", "warning", "failed"]

    def test_parse_labeled_patterns(self) -> None:
        """Parse grep_scanner with labeled dict patterns."""
        source = """
from inspect_scout import Scanner, grep_scanner, scanner
from inspect_scout._transcript.types import Transcript


@scanner(messages="all")
def categorize() -> Scanner[Transcript]:
    return grep_scanner(
        pattern={
            "errors": ["error", "failed"],
            "warnings": ["warning", "caution"],
        }
    )
"""
        result = parse_scanner_file(source)

        assert result.editable is True
        assert result.scanner is not None
        assert result.scanner.grep_scanner is not None
        assert result.scanner.grep_scanner.pattern_type == "labeled"
        assert result.scanner.grep_scanner.labeled_patterns == {
            "errors": ["error", "failed"],
            "warnings": ["warning", "caution"],
        }

    def test_parse_grep_with_options(self) -> None:
        """Parse grep_scanner with regex and other options."""
        source = r"""
from inspect_scout import Scanner, grep_scanner, scanner
from inspect_scout._transcript.types import Transcript


@scanner(messages="all")
def find_url() -> Scanner[Transcript]:
    return grep_scanner(
        pattern="https?://\\S+",
        regex=True,
        ignore_case=False,
    )
"""
        result = parse_scanner_file(source)

        assert result.editable is True
        assert result.scanner is not None
        assert result.scanner.grep_scanner is not None
        assert result.scanner.grep_scanner.regex is True
        assert result.scanner.grep_scanner.ignore_case is False


class TestParseAdvancedScanner:
    """Tests for detecting advanced/non-editable scanners."""

    def test_dynamic_question_is_advanced(self) -> None:
        """Scanner with callable question is advanced."""
        source = """
from inspect_scout import Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript


async def get_question(t):
    return "Dynamic question"


@scanner(messages="all")
def dynamic() -> Scanner[Transcript]:
    return llm_scanner(
        question=get_question,
        answer="boolean",
    )
"""
        result = parse_scanner_file(source)

        assert result.editable is False
        assert result.advanced_reason is not None
        assert "dynamic question" in result.advanced_reason.lower()

    def test_template_variables_is_advanced(self) -> None:
        """Scanner with template_variables is advanced."""
        source = """
from inspect_scout import Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript


@scanner(messages="all")
def with_vars() -> Scanner[Transcript]:
    return llm_scanner(
        question="Question?",
        answer="boolean",
        template_variables={"key": "value"},
    )
"""
        result = parse_scanner_file(source)

        assert result.editable is False
        assert result.advanced_reason is not None
        assert "template variables" in result.advanced_reason.lower()

    def test_custom_scanner_is_advanced(self) -> None:
        """Custom scanner implementation is advanced."""
        source = """
from inspect_scout import Result, Scanner, scanner
from inspect_scout._transcript.types import Transcript


@scanner(messages="all")
def custom() -> Scanner[Transcript]:
    async def scan(t):
        return Result(value=True)
    return scan
"""
        result = parse_scanner_file(source)

        assert result.editable is False
        assert result.advanced_reason is not None
        assert "custom" in result.advanced_reason.lower()

    def test_no_scanner_decorator(self) -> None:
        """File without @scanner decorator."""
        source = """
def not_a_scanner():
    pass
"""
        result = parse_scanner_file(source)

        assert result.editable is False
        assert result.advanced_reason is not None
        assert "no @scanner" in result.advanced_reason.lower()


class TestParseDecorator:
    """Tests for parsing @scanner decorator options."""

    def test_parse_messages_list(self) -> None:
        """Parse messages as list."""
        source = """
from inspect_scout import Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript


@scanner(messages=["user", "assistant"])
def filtered() -> Scanner[Transcript]:
    return llm_scanner(question="Q?", answer="boolean")
"""
        result = parse_scanner_file(source)

        assert result.editable is True
        assert result.scanner is not None
        assert result.scanner.decorator.messages == ["user", "assistant"]

    def test_parse_events(self) -> None:
        """Parse events filter."""
        source = """
from inspect_scout import Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript


@scanner(messages="all", events=["tool", "error"])
def with_events() -> Scanner[Transcript]:
    return llm_scanner(question="Q?", answer="boolean")
"""
        result = parse_scanner_file(source)

        assert result.editable is True
        assert result.scanner is not None
        assert result.scanner.decorator.events == ["tool", "error"]

    def test_parse_version(self) -> None:
        """Parse version number."""
        source = """
from inspect_scout import Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript


@scanner(messages="all", version=2)
def versioned() -> Scanner[Transcript]:
    return llm_scanner(question="Q?", answer="boolean")
"""
        result = parse_scanner_file(source)

        assert result.editable is True
        assert result.scanner is not None
        assert result.scanner.decorator.version == 2


class TestNestedPydanticModels:
    """Tests for parsing nested Pydantic models in structured answers."""

    def test_parse_simple_nested_model(self) -> None:
        """Parse scanner with simple nested Pydantic model."""
        source = """
from pydantic import BaseModel, Field
from inspect_scout import AnswerStructured, Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript


class Details(BaseModel):
    reason: str = Field(description="The reason")
    confidence: float = Field(description="Confidence score")


class Analysis(BaseModel):
    score: int = Field(description="Score from 1-10")
    details: Details = Field(description="Detailed analysis")


@scanner(messages="all")
def analyze() -> Scanner[Transcript]:
    return llm_scanner(
        question="Analyze this",
        answer=AnswerStructured(type=Analysis),
    )
"""
        result = parse_scanner_file(source)

        assert result.editable is True
        assert result.scanner is not None
        assert result.scanner.structured_model is not None
        assert result.scanner.structured_model.class_name == "Analysis"
        assert result.scanner.structured_model.nested_models is not None
        assert len(result.scanner.structured_model.nested_models) == 1
        assert result.scanner.structured_model.nested_models[0].class_name == "Details"
        assert len(result.scanner.structured_model.nested_models[0].fields) == 2

    def test_parse_optional_nested_model(self) -> None:
        """Parse scanner with optional nested model (Model | None)."""
        source = """
from pydantic import BaseModel, Field
from inspect_scout import AnswerStructured, Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript


class Metadata(BaseModel):
    source: str = Field(description="Source")


class Result(BaseModel):
    value: int = Field(description="The value")
    metadata: Metadata | None = Field(description="Optional metadata")


@scanner(messages="all")
def check() -> Scanner[Transcript]:
    return llm_scanner(
        question="Check this",
        answer=AnswerStructured(type=Result),
    )
"""
        result = parse_scanner_file(source)

        assert result.editable is True
        assert result.scanner is not None
        assert result.scanner.structured_model is not None
        assert result.scanner.structured_model.nested_models is not None
        assert len(result.scanner.structured_model.nested_models) == 1
        assert result.scanner.structured_model.nested_models[0].class_name == "Metadata"

    def test_parse_list_nested_model(self) -> None:
        """Parse scanner with list of nested models (list[Model])."""
        source = """
from pydantic import BaseModel, Field
from inspect_scout import AnswerStructured, Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript


class Item(BaseModel):
    name: str = Field(description="Item name")
    value: int = Field(description="Item value")


class Container(BaseModel):
    items: list[Item] = Field(description="List of items")


@scanner(messages="all")
def extract() -> Scanner[Transcript]:
    return llm_scanner(
        question="Extract items",
        answer=AnswerStructured(type=Container),
    )
"""
        result = parse_scanner_file(source)

        assert result.editable is True
        assert result.scanner is not None
        assert result.scanner.structured_model is not None
        assert result.scanner.structured_model.nested_models is not None
        assert len(result.scanner.structured_model.nested_models) == 1
        assert result.scanner.structured_model.nested_models[0].class_name == "Item"

    def test_parse_deeply_nested_models(self) -> None:
        """Parse scanner with multiple levels of nesting."""
        source = """
from pydantic import BaseModel, Field
from inspect_scout import AnswerStructured, Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript


class Address(BaseModel):
    street: str = Field(description="Street address")
    city: str = Field(description="City name")


class Person(BaseModel):
    name: str = Field(description="Person name")
    address: Address = Field(description="Person address")


class Company(BaseModel):
    name: str = Field(description="Company name")
    employees: list[Person] = Field(description="Company employees")


@scanner(messages="all")
def analyze_company() -> Scanner[Transcript]:
    return llm_scanner(
        question="Analyze the company",
        answer=AnswerStructured(type=Company),
    )
"""
        result = parse_scanner_file(source)

        assert result.editable is True
        assert result.scanner is not None
        assert result.scanner.structured_model is not None
        assert result.scanner.structured_model.class_name == "Company"

        # Company should have Person as nested model
        assert result.scanner.structured_model.nested_models is not None
        person_model = result.scanner.structured_model.nested_models[0]
        assert person_model.class_name == "Person"

        # Person should have Address as nested model
        assert person_model.nested_models is not None
        assert person_model.nested_models[0].class_name == "Address"
