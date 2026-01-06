"""Pattern-based transcript scanner using grep-style matching."""

from .._scanner.result import Reference, Result
from .._scanner.scanner import SCANNER_NAME_ATTR, Scanner, scanner
from .._transcript.types import Transcript
from ._match import (
    Match,
    compile_pattern,
    find_matches_in_events,
    find_matches_in_messages,
)


@scanner(messages="all")
def grep_scanner(
    pattern: str | list[str] | dict[str, str | list[str]],
    *,
    regex: bool = False,
    ignore_case: bool = True,
    word_boundary: bool = False,
    name: str | None = None,
) -> Scanner[Transcript]:
    r"""Pattern-based transcript scanner.

    Scans transcript messages and events for text patterns using grep-style
    matching. By default, patterns are treated as literal strings (like grep
    without -E). Set `regex=True` to treat patterns as regular expressions.

    What gets searched depends on what's populated in the transcript:
    - Messages are searched if `transcript.messages` is populated
    - Events are searched if `transcript.events` is populated
    - Control population via `@scanner(messages=..., events=...)`

    Args:
        pattern: Pattern(s) to search for. Can be:
            - str: Single pattern
            - list[str]: Multiple patterns (OR logic, single aggregated result)
            - dict[str, str | list[str]]: Labeled patterns (returns multiple results,
              one per label)
        regex: If True, treat patterns as regular expressions.
            Default False (literal string matching).
        ignore_case: Case-insensitive matching. Default True (like grep -i).
        word_boundary: Match whole words only (adds \b anchors). Default False.
        name: Scanner name.
            Use this to assign a name when passing `llm_scanner()` directly to `scan()` rather than delegating to it from another scanner.

    Returns:
        Scanner that returns:
        - Single Result (for str/list input): value=count of matches, explanation=context snippets, references=[M1]/[E1] citations
        - list[Result] (for dict input): one Result per label with its count

    Raises:
        ValueError: If pattern list is empty or dict has no labels.
        PatternError: If regex=True and pattern is an invalid regular expression.

    Examples:
        Simple pattern (messages only):
            grep_scanner("error")

        Multiple patterns (OR logic):
            grep_scanner(["error", "failed", "exception"])

        Labeled patterns (separate results):
            grep_scanner({
                "errors": ["error", "failed"],
                "warnings": ["warning", "caution"],
            })

        With regex:
            grep_scanner(r"https?://\S+", regex=True)

        Search both messages and events:
            @scanner(messages="all", events=["tool", "error"])
            def find_errors() -> Scanner[Transcript]:
                return grep_scanner("error")
    """
    # Validate patterns
    if isinstance(pattern, list) and len(pattern) == 0:
        raise ValueError("Pattern list cannot be empty")
    if isinstance(pattern, dict) and len(pattern) == 0:
        raise ValueError("Pattern dict cannot be empty")

    async def scan(transcript: Transcript) -> Result | list[Result]:
        if isinstance(pattern, dict):
            # Labeled patterns - return multiple results
            return _scan_labeled(transcript, pattern, regex, ignore_case, word_boundary)
        else:
            # Single or list pattern - return single result
            return _scan_single(transcript, pattern, regex, ignore_case, word_boundary)

    # set name for collection by @scanner if specified
    if name is not None:
        setattr(scan, SCANNER_NAME_ATTR, name)

    return scan


def _scan_single(
    transcript: Transcript,
    pattern: str | list[str],
    regex: bool,
    ignore_case: bool,
    word_boundary: bool,
) -> Result:
    """Scan with single pattern or list of patterns, returning single result."""
    patterns = [pattern] if isinstance(pattern, str) else pattern
    compiled = [compile_pattern(p, regex, ignore_case, word_boundary) for p in patterns]

    all_matches: list[Match] = []

    # Search messages if present
    if transcript.messages:
        all_matches.extend(find_matches_in_messages(transcript.messages, compiled))

    # Search events if present
    if transcript.events:
        all_matches.extend(find_matches_in_events(transcript.events, compiled))

    return _build_result(all_matches)


def _scan_labeled(
    transcript: Transcript,
    patterns: dict[str, str | list[str]],
    regex: bool,
    ignore_case: bool,
    word_boundary: bool,
) -> list[Result]:
    """Scan with labeled patterns, returning one result per label."""
    results: list[Result] = []

    for label, label_patterns in patterns.items():
        pats = [label_patterns] if isinstance(label_patterns, str) else label_patterns
        compiled = [compile_pattern(p, regex, ignore_case, word_boundary) for p in pats]

        matches: list[Match] = []

        # Search messages if present
        if transcript.messages:
            matches.extend(find_matches_in_messages(transcript.messages, compiled))

        # Search events if present
        if transcript.events:
            matches.extend(find_matches_in_events(transcript.events, compiled))

        result = _build_result(matches)
        result.label = label
        results.append(result)

    return results


def _build_result(matches: list[Match]) -> Result:
    """Build a Result from a list of matches."""
    if not matches:
        return Result(value=0, explanation=None, references=[])

    # Build explanation with context snippets
    explanation_parts: list[str] = []
    references: list[Reference] = []
    seen_ids: set[str] = set()

    for m in matches:
        # Use M for messages, E for events
        prefix = "M" if m.source == "message" else "E"
        cite = f"[{prefix}{m.index}]"
        explanation_parts.append(f"{cite}: {m.context}")

        # Add reference for each unique message/event
        if m.id not in seen_ids:
            references.append(Reference(type=m.source, cite=cite, id=m.id))
            seen_ids.add(m.id)

    return Result(
        value=len(matches),
        explanation="\n".join(explanation_parts),
        references=references,
    )
