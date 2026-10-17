"""Evidence questions: Jev choice questions over a segment's ``[M#]`` message labels."""

import re
from collections.abc import Sequence
from typing import NamedTuple

from .._scanner.extract import ExtractReferences
from ._answers import MAX_CHOICE_OPTIONS, JevAnswers, JevQuestion

EVIDENCE_WINDOW = MAX_CHOICE_OPTIONS - 5
"""Message labels per evidence question (Jev allows 255 options; ``NONE`` is one, the rest is headroom)."""

EVIDENCE_LABELS_PER_REQUEST = 4 * EVIDENCE_WINDOW
"""Message labels per request (~7k tokens of options, within `EVIDENCE_RESERVE`)."""

EVIDENCE_RESERVE = 8_000
"""Tokens of each segment's budget reserved for evidence questions."""

MIN_EVIDENCE_PROBABILITY = 0.3
"""A cited message must have at least this probability."""

MAX_EVIDENCE_ROUNDS = 8
"""Maximum citations found per segment with ``references="all"``."""

NONE = "NONE"

_LABEL_PATTERN = re.compile(r"^\[M(\d+)\] ", re.MULTILINE)


def segment_labels(messages_str: str, extract_refs: ExtractReferences) -> list[str]:
    """The ``[M#]`` labels of the messages rendered in a segment, in order.

    A segment's messages are numbered consecutively and its text starts with
    the first header, so only the run of consecutive labels from there counts;
    message text that imitates a header (e.g. ``[M1]`` inside a later
    segment) cannot add options.
    """
    labels: list[str] = []
    expected: int | None = None
    for number in _LABEL_PATTERN.findall(messages_str):
        n = int(number)
        if expected is None or n == expected:
            label = f"M{n}"
            if not extract_refs(f"[{label}]"):
                break
            labels.append(label)
            expected = n + 1
    return labels


def evidence_requests(
    question: str,
    target: str,
    labels: Sequence[str],
    *,
    exclude: Sequence[str] = (),
) -> list[dict[str, JevQuestion]]:
    """Evidence questions over `labels`, split into requests of bounded size.

    Each request holds up to `EVIDENCE_LABELS_PER_REQUEST` labels (as choice
    questions of `EVIDENCE_WINDOW` labels plus ``NONE``), so the options fit the
    reserved budget however many messages a segment has. Labels in ``exclude``
    (and their immediate neighbours) are left out, for finding further,
    separate occurrences.
    """
    remaining = [
        label for label in labels if label not in _with_neighbours(labels, exclude)
    ]
    instructions = (
        f"Which single message directly shows the evidence {target} for this "
        f"question: {question}\nPick the message where it actually happens, not a "
        "message that only reports, confirms, or follows up on it. "
        f"Choose {NONE} if no message among the options shows it."
    )
    if exclude:
        instructions += (
            " Messages listed in already_found were already identified; pick a "
            f"message showing a separate occurrence, or {NONE}."
        )
    requests: list[dict[str, JevQuestion]] = []
    for start in range(0, len(remaining), EVIDENCE_LABELS_PER_REQUEST):
        chunk = remaining[start : start + EVIDENCE_LABELS_PER_REQUEST]
        requests.append(
            {
                f"evidence_{i // EVIDENCE_WINDOW}": {
                    "type": "choice",
                    "instructions": instructions,
                    "criteria": {
                        **{label: None for label in chunk[i : i + EVIDENCE_WINDOW]},
                        NONE: None,
                    },
                }
                for i in range(0, len(chunk), EVIDENCE_WINDOW)
            }
        )
    return requests


def _with_neighbours(labels: Sequence[str], found: Sequence[str]) -> set[str]:
    """Found labels plus the messages right before and after each.

    Those neighbours are usually the same occurrence seen again (a tool call's
    output, or the turn that announces it), not a separate one.
    """
    excluded = set(found)
    index = {label: i for i, label in enumerate(labels)}
    for label in found:
        if (i := index.get(label)) is not None:
            excluded.update(labels[max(0, i - 1) : i + 2])
    return excluded


class Evidence(NamedTuple):
    """The best cited message across evidence windows."""

    label: str
    probability: float


def best_evidence(answers: Sequence[JevAnswers]) -> Evidence | None:
    """The best cited message across the evidence answers, if any window cites one.

    A window whose answer is ``NONE`` cites nothing, and a cited message needs
    at least `MIN_EVIDENCE_PROBABILITY`.
    """
    best: Evidence | None = None
    for response in answers:
        for name, answer in response.items():
            if not name.startswith("evidence_"):
                continue
            choice = str(answer["choice"])
            if choice == NONE:
                continue
            p = float(answer["probabilities"].get(choice, 0.0))
            if p >= MIN_EVIDENCE_PROBABILITY and (best is None or p > best.probability):
                best = Evidence(choice, p)
    return best
