"""Tests for applying scanner changes in-place."""

from pathlib import Path

import pytest
from inspect_scout._scanner_ir import (
    SourceChangedError,
    apply_scanner_changes,
    parse_scanner_file,
)


class TestApplyChanges:
    """Tests for apply_scanner_changes function."""

    def test_update_question(self) -> None:
        """Update just the question, preserving comments."""
        source = """
from inspect_scout import Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript


# Important scanner for detecting refusals
@scanner(messages="all")
def refusal_check() -> Scanner[Transcript]:
    # Check if the assistant refused
    return llm_scanner(
        question="Did the assistant refuse?",  # Original question
        answer="boolean",
    )
"""
        result = parse_scanner_file(source)
        assert result.editable is True
        assert result.scanner is not None
        assert result.scanner.llm_scanner is not None

        # Update the question
        updated_scanner = result.scanner.model_copy(deep=True)
        assert updated_scanner.llm_scanner is not None
        updated_scanner.llm_scanner.question = "Was there a refusal in the response?"

        new_source = apply_scanner_changes(source, updated_scanner)

        # Check that comments are preserved
        assert "# Important scanner" in new_source
        # Check that the question was updated
        assert "Was there a refusal in the response?" in new_source
        # Check the old question is gone
        assert "Did the assistant refuse?" not in new_source

    def test_update_answer_type(self) -> None:
        """Update answer type from boolean to numeric."""
        source = """
from inspect_scout import Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript


@scanner(messages="all")
def score() -> Scanner[Transcript]:
    return llm_scanner(
        question="Rate this",
        answer="boolean",
    )
"""
        result = parse_scanner_file(source)
        assert result.editable is True
        assert result.scanner is not None
        assert result.scanner.llm_scanner is not None

        # Update to numeric
        updated_scanner = result.scanner.model_copy(deep=True)
        assert updated_scanner.llm_scanner is not None
        updated_scanner.llm_scanner.answer_type = "numeric"

        new_source = apply_scanner_changes(source, updated_scanner)

        # Check for answer type (spacing may vary without ruff formatting)
        assert "numeric" in new_source
        assert (
            'answer="boolean"' not in new_source
            and 'answer = "boolean"' not in new_source
        )

    def test_add_model_option(self) -> None:
        """Add model option to scanner."""
        source = """
from inspect_scout import Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript


@scanner(messages="all")
def simple() -> Scanner[Transcript]:
    return llm_scanner(
        question="Question?",
        answer="boolean",
    )
"""
        result = parse_scanner_file(source)
        assert result.editable is True
        assert result.scanner is not None
        assert result.scanner.llm_scanner is not None

        # Add model
        updated_scanner = result.scanner.model_copy(deep=True)
        assert updated_scanner.llm_scanner is not None
        updated_scanner.llm_scanner.model = "openai/gpt-4o"

        new_source = apply_scanner_changes(source, updated_scanner)

        # Check model was added (spacing may vary without ruff formatting)
        assert "openai/gpt-4o" in new_source

    def test_update_decorator_messages(self) -> None:
        """Update decorator messages filter."""
        source = """
from inspect_scout import Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript


@scanner(messages="all")
def filtered() -> Scanner[Transcript]:
    return llm_scanner(
        question="Q?",
        answer="boolean",
    )
"""
        result = parse_scanner_file(source)
        assert result.editable is True
        assert result.scanner is not None

        # Update messages filter
        updated_scanner = result.scanner.model_copy(deep=True)
        updated_scanner.decorator.messages = ["user", "assistant"]

        new_source = apply_scanner_changes(source, updated_scanner)

        # Check for messages filter (spacing/quotes may vary without ruff formatting)
        assert "messages" in new_source
        assert "user" in new_source
        assert "assistant" in new_source

    def test_update_labels(self) -> None:
        """Update label list."""
        source = """
from inspect_scout import Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript


@scanner(messages="all")
def quality() -> Scanner[Transcript]:
    return llm_scanner(
        question="Rate quality",
        answer=["Good", "Bad"],
    )
"""
        result = parse_scanner_file(source)
        assert result.editable is True
        assert result.scanner is not None
        assert result.scanner.llm_scanner is not None

        # Update labels
        updated_scanner = result.scanner.model_copy(deep=True)
        assert updated_scanner.llm_scanner is not None
        updated_scanner.llm_scanner.labels = ["Excellent", "Good", "Fair", "Poor"]

        new_source = apply_scanner_changes(source, updated_scanner)

        assert "Excellent" in new_source
        assert "Fair" in new_source
        assert "Poor" in new_source


class TestPreserveFormatting:
    """Tests for formatting preservation."""

    def test_preserve_blank_lines(self) -> None:
        """Preserve blank lines in file."""
        source = """
from inspect_scout import Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript


@scanner(messages="all")
def my_scanner() -> Scanner[Transcript]:

    return llm_scanner(
        question="Original",
        answer="boolean",
    )
"""
        result = parse_scanner_file(source)
        assert result.editable is True
        assert result.scanner is not None
        assert result.scanner.llm_scanner is not None

        # Update question
        updated_scanner = result.scanner.model_copy(deep=True)
        assert updated_scanner.llm_scanner is not None
        updated_scanner.llm_scanner.question = "Updated"

        new_source = apply_scanner_changes(source, updated_scanner)

        # Formatting should be reasonable (ruff will handle it)
        assert "Updated" in new_source
        assert "def my_scanner()" in new_source


class TestSourceChangedError:
    """Tests for SourceChangedError validation."""

    def test_error_when_disk_source_changed(self, tmp_path: Path) -> None:
        """Error when file on disk differs from client's source."""
        # Original source client has
        client_source = """
from inspect_scout import Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript


@scanner(messages="all")
def my_scanner() -> Scanner[Transcript]:
    return llm_scanner(
        question="Original question",
        answer="boolean",
    )
"""
        # Modified source on disk (someone changed the question)
        disk_source = """
from inspect_scout import Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript


@scanner(messages="all")
def my_scanner() -> Scanner[Transcript]:
    return llm_scanner(
        question="Changed question on disk",
        answer="boolean",
    )
"""
        # Write disk version to file
        file_path = tmp_path / "scanner.py"
        file_path.write_text(disk_source)

        result = parse_scanner_file(client_source)
        assert result.scanner is not None
        assert result.scanner.llm_scanner is not None
        updated = result.scanner.model_copy(deep=True)
        assert updated.llm_scanner is not None
        updated.llm_scanner.question = "UI edited question"

        with pytest.raises(SourceChangedError, match="modified"):
            apply_scanner_changes(client_source, updated, file_path=file_path)

    def test_no_error_when_disk_unchanged(self, tmp_path: Path) -> None:
        """No error when file on disk matches client's source."""
        source = """
from inspect_scout import Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript


@scanner(messages="all")
def my_scanner() -> Scanner[Transcript]:
    return llm_scanner(
        question="Original",
        answer="boolean",
    )
"""
        file_path = tmp_path / "scanner.py"
        file_path.write_text(source)

        result = parse_scanner_file(source)
        assert result.scanner is not None
        assert result.scanner.llm_scanner is not None
        updated = result.scanner.model_copy(deep=True)
        assert updated.llm_scanner is not None
        updated.llm_scanner.question = "Updated"

        # Should succeed - no SourceChangedError
        new_source = apply_scanner_changes(source, updated, file_path=file_path)
        assert "Updated" in new_source

    def test_no_validation_without_file_path(self) -> None:
        """No validation when file_path not provided (backward compatible)."""
        source = """
from inspect_scout import Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript


@scanner(messages="all")
def my_scanner() -> Scanner[Transcript]:
    return llm_scanner(
        question="Original",
        answer="boolean",
    )
"""
        result = parse_scanner_file(source)
        assert result.scanner is not None
        assert result.scanner.llm_scanner is not None
        updated = result.scanner.model_copy(deep=True)
        assert updated.llm_scanner is not None
        updated.llm_scanner.question = "Updated"

        # Should work without file_path - no disk validation
        new_source = apply_scanner_changes(source, updated)
        assert "Updated" in new_source

    def test_formatting_changes_tolerated(self, tmp_path: Path) -> None:
        """Formatting changes should not trigger error."""
        # Client source with specific formatting
        client_source = """
from inspect_scout import Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript


@scanner(messages="all")
def my_scanner() -> Scanner[Transcript]:
    return llm_scanner(
        question="Same question",
        answer="boolean",
    )
"""
        # Disk source with different whitespace but same content
        disk_source = """
from inspect_scout import Scanner, llm_scanner, scanner
from inspect_scout._transcript.types import Transcript

@scanner(messages="all")
def my_scanner() -> Scanner[Transcript]:
    return llm_scanner(question="Same question", answer="boolean")
"""
        file_path = tmp_path / "scanner.py"
        file_path.write_text(disk_source)

        result = parse_scanner_file(client_source)
        assert result.scanner is not None
        assert result.scanner.llm_scanner is not None
        updated = result.scanner.model_copy(deep=True)
        assert updated.llm_scanner is not None
        updated.llm_scanner.question = "New question"

        # Should succeed - formatting differences don't affect parsed ScannerFile
        new_source = apply_scanner_changes(client_source, updated, file_path=file_path)
        assert "New question" in new_source
