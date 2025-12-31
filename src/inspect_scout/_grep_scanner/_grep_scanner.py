"""Pattern-based transcript scanner using grep-style matching."""

from .._scanner.result import Reference, Result
from .._scanner.scanner import Scanner
from .._transcript.types import Transcript
from ._match import Match, compile_pattern, find_matches


def grep_scanner(
    pattern: str | list[str] | dict[str, str | list[str]],
    *,
    regex: bool = False,
    ignore_case: bool = True,
    word_boundary: bool = False,
) -> Scanner[Transcript]:
    r"""Pattern-based transcript scanner.

    Scans transcript messages for text patterns using grep-style matching.
    By default, patterns are treated as literal strings (like grep without -E).
    Set `regex=True` to treat patterns as regular expressions.

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

    Returns:
        Scanner that returns:
        - Single Result (for str/list input): value=count of matches,
          explanation=context snippets, references=message citations
        - list[Result] (for dict input): one Result per label with its count

    Examples:
        Simple pattern:
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
    """

    async def scan(transcript: Transcript) -> Result | list[Result]:
        if isinstance(pattern, dict):
            # Labeled patterns - return multiple results
            return _scan_labeled(transcript, pattern, regex, ignore_case, word_boundary)
        else:
            # Single or list pattern - return single result
            return _scan_single(transcript, pattern, regex, ignore_case, word_boundary)

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
    for match in find_matches(transcript.messages, compiled):
        all_matches.append(match)

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

        matches: list[Match] = list(find_matches(transcript.messages, compiled))
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
    seen_message_ids: set[str] = set()

    for m in matches:
        cite = f"[M{m.message_index}]"
        explanation_parts.append(f"{cite}: {m.context}")

        # Add reference for each unique message
        if m.message_id not in seen_message_ids:
            references.append(Reference(type="message", cite=cite, id=m.message_id))
            seen_message_ids.add(m.message_id)

    return Result(
        value=len(matches),
        explanation="\n".join(explanation_parts),
        references=references,
    )
