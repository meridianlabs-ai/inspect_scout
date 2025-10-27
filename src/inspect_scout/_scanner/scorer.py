from typing import Any, Mapping, Sequence

from inspect_ai._util.registry import is_registry_object, registry_unqualified_name
from inspect_ai.log import transcript as sample_transcript
from inspect_ai.scorer import (
    Metric,
    Score,
    Scorer,
    Target,
    Value,
    accuracy,
    scorer,
    stderr,
)
from inspect_ai.solver import TaskState
from pydantic import JsonValue

from inspect_scout._scanner.result import Result
from inspect_scout._scanner.scanner import Scanner, metrics_for_scanner
from inspect_scout._transcript.types import Transcript


def as_scorer(
    scanner: Scanner[Transcript],
    metrics: Sequence[Metric | Mapping[str, Sequence[Metric]]]
    | Mapping[str, Sequence[Metric]]
    | None = None,
) -> Scorer:
    """Convert a `Scanner` to an Inspect `Scorer`.

    Args:
       scanner: Scanner to convert (must take a `Transcript`).
       metrics: Metrics for scorer. Defaults to `metrics` specified on the `@scanner` decorator (or `[accuracy(), stderr()]` if none were specified).

    Returns:
       Scorer from scanner.
    """
    # scaner must be registered (so we can get its name)
    if not is_registry_object(scanner):
        raise RuntimeError(
            "Agent passed to as_solver was not created by an @agent decorated function"
        )
    scanner_name = registry_unqualified_name(scanner)

    # determine metrics (passed, declared on scanner, or default)
    metrics = metrics or metrics_for_scanner(scanner) or [accuracy(), stderr()]

    @scorer(name=scanner_name, metrics=metrics)
    def scanner_to_scorer() -> Scorer:
        async def score(state: TaskState, target: Target) -> Score | None:
            # prepare transcript from state
            transcript = Transcript(
                id=state.uuid,
                source_id="",
                source_uri="",
                metadata={
                    "id": state.sample_id,
                    "epoch": state.epoch,
                    "sample_metadata": state.metadata,
                },
                messages=state.messages,
                events=list(sample_transcript().events),
            )

            # call scanner
            result = await scanner(transcript)

            # None means no score
            if result.value is None:
                return None

            # return score
            return Score(
                value=_as_score_value(result.value),
                answer=result.answer,
                explanation=result.explanation,
                metadata=_metadata_from_result(result),
            )

        return score

    return scanner_to_scorer()


def _metadata_from_result(result: Result) -> dict[str, Any] | None:
    # references
    def references_for_type(type: str) -> list[str]:
        return [ref.id for ref in result.references if ref.type == type]

    if result.metadata or result.references:
        # base metadata
        metadata = result.metadata or {}

        # convert references to metadata
        msg_references = references_for_type("message")
        if msg_references:
            metadata["message_references"] = msg_references
        evt_references = references_for_type("event")
        if evt_references:
            metadata["event_references"] = evt_references

        # return metadata
        return metadata
    else:
        return None


def _as_score_value(value: JsonValue) -> Value:
    if isinstance(value, list):
        return [v if isinstance(v, str | int | float | bool) else str(v) for v in value]
    elif isinstance(value, dict):
        return {
            k: v if isinstance(v, str | int | float | bool | None) else str(v)
            for k, v in value.items()
        }
    elif isinstance(value, str | int | float | bool):
        return value
    else:
        raise AssertionError("None should not be passed to as_score_value")
