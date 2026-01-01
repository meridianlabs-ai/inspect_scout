"""Example scanners using grep_scanner for pattern-based analysis."""

from inspect_scout import Scanner, grep_scanner, scanner
from inspect_scout._transcript.types import Transcript

# =============================================================================
# Message-based scanners
# =============================================================================


@scanner(messages=["assistant"])
def error_keywords() -> Scanner[Transcript]:
    """Find common error-related keywords in assistant messages.

    Searches for common error terminology that might indicate
    issues or problems in the agent's responses.
    """
    return grep_scanner(
        ["error", "failed", "exception", "crash", "timeout"],
        word_boundary=True,
    )


@scanner(messages="all")
def url_references() -> Scanner[Transcript]:
    """Find URL references in transcript messages.

    Detects http and https URLs in any message, useful for
    tracking external resource references.
    """
    return grep_scanner(
        r"https?://[^\s<>\"']+",
        regex=True,
    )


@scanner(messages=["assistant"])
def content_categories() -> Scanner[Transcript]:
    """Categorize content in assistant messages.

    Returns separate results for different content categories:
    - code_indicators: Signs of code snippets
    - questions: Questions posed by the assistant
    - refusal_phrases: Potential refusal language
    """
    return grep_scanner(
        {
            "code_indicators": ["```", "def ", "class ", "import ", "function "],
            "questions": [r"\?\s*$"],
            "refusal_phrases": [
                "I cannot",
                "I can't",
                "I'm unable",
                "I am unable",
                "I apologize",
            ],
        },
        regex=True,
        ignore_case=True,
    )


@scanner(messages=["assistant"])
def sensitive_content() -> Scanner[Transcript]:
    """Detect potentially sensitive content patterns.

    Searches for patterns that might indicate sensitive
    information being shared, such as credentials or personal data.
    """
    return grep_scanner(
        {
            "credentials": [
                r"password[\s:=]",
                r"api[_-]?key[\s:=]",
                r"secret[\s:=]",
                r"token[\s:=]",
            ],
            "personal_info": [
                r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # Phone numbers
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
            ],
        },
        regex=True,
    )


# =============================================================================
# Event-based scanners
# =============================================================================


@scanner(events=["tool"])
def tool_errors() -> Scanner[Transcript]:
    """Find errors in tool execution results.

    Searches tool events for common error indicators like
    timeouts, permission issues, and connection failures.
    """
    return grep_scanner(
        ["timeout", "permission denied", "connection refused", "not found"],
        ignore_case=True,
    )


@scanner(events=["error"])
def runtime_errors() -> Scanner[Transcript]:
    """Find specific runtime error types in error events.

    Categorizes error events by common exception types.
    """
    return grep_scanner(
        {
            "type_errors": ["TypeError", "AttributeError"],
            "value_errors": ["ValueError", "KeyError", "IndexError"],
            "io_errors": ["FileNotFoundError", "PermissionError", "IOError"],
        },
        regex=False,
    )


# =============================================================================
# Combined message and event scanners
# =============================================================================


@scanner(messages="all", events=["tool", "error"])
def comprehensive_error_scan() -> Scanner[Transcript]:
    """Search both messages and events for error indicators.

    Provides a comprehensive view of errors across the entire
    transcript, including both conversation content and tool execution.
    """
    return grep_scanner(
        {
            "errors": ["error", "failed", "exception"],
            "warnings": ["warning", "deprecated", "caution"],
        },
    )
