from typing import Any, Mapping, Sequence, cast

from inspect_ai._util.json import to_json_str_safe
from inspect_ai._util.registry import is_registry_object, registry_unqualified_name
from inspect_ai.event import Event
from inspect_ai.log import transcript as sample_transcript
from inspect_ai.model import ChatMessage
from inspect_ai.scorer import (
    Metric,
    Score,
    Scorer,
    Target,
    mean,
    scorer,
    stderr,
)
from inspect_ai.solver import TaskState
from pydantic import JsonValue

from inspect_scout._scanner.metrics import as_score_value, metrics_for_scanner
from inspect_scout._scanner.result import Result, as_resultset
from inspect_scout._scanner.scanner import Scanner, ScannerConfig, config_for_scanner
from inspect_scout._transcript.eval_log import EVAL_LOG_SOURCE_TYPE
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
       metrics: Metrics for scorer. Defaults to `metrics` specified on the `@scanner` decorator (or `[mean(), stderr()]` if none were specified).

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
    metrics = metrics or metrics_for_scanner(scanner) or [mean(), stderr()]

    @scorer(name=scanner_name, metrics=metrics)
    def scanner_to_scorer() -> Scorer:
        async def score(state: TaskState, target: Target) -> Score | None:
            # filter transcript messages and events
            config = config_for_scanner(scanner)
            messages, events = _scanner_messages_and_events(
                config, state.messages, list(sample_transcript().events)
            )

            # prepare transcript from state
            transcript = Transcript(
                transcript_id=state.uuid,
                source_type=EVAL_LOG_SOURCE_TYPE,
                metadata={
                    "id": state.sample_id,
                    "epoch": state.epoch,
                    "sample_metadata": state.metadata,
                    "target": target.target if len(target) > 1 else target.text,
                    "scores": state.scores,
                },
                messages=messages,
                events=events,
            )

            # call scanner
            result = await scanner(transcript)
            if isinstance(result, list):
                result = as_resultset(result)

            # None means no score
            if result.value is None:
                return None

            # if its a resultset, then project as dict
            if result.type == "resultset":
                results_list = cast(list[dict[str, JsonValue]], result.value)
                results_dict: dict[str, int | bool | float | str | None] = {}
                for result_item in results_list:
                    # get and validate label (required for scores)
                    label = result_item.get("label", None)
                    if label is None:
                        raise RuntimeError(
                            "Result sets used as scores must have labels for all items."
                        )
                    # take first label only
                    if label not in results_dict:
                        # extract and setvalue (must be scalar)
                        value = result_item.get("value")
                        if isinstance(value, list | dict):
                            value = to_json_str_safe(value)
                        results_dict[str(label)] = value
                return Score(value=results_dict)
            else:
                return Score(
                    value=as_score_value(result.value),
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


def _scanner_messages_and_events(
    config: ScannerConfig, messages: list[ChatMessage], events: list[Event]
) -> tuple[list[ChatMessage], list[Event]]:
    if config.content.messages == "all":
        scanner_messages = list(messages)
    elif isinstance(config.content.messages, list):
        scanner_messages = [m for m in messages if m.role in config.content.messages]
    elif config.content.messages is None:
        scanner_messages = []
    else:
        raise TypeError(
            f"Unexpected type for messages: {type(config.content.messages)}"
        )

    if config.content.events == "all":
        scanner_events = list(events)
    elif isinstance(config.content.events, list):
        scanner_events = [e for e in events if e.event in config.content.events]
    elif config.content.events is None:
        scanner_events = []
    else:
        raise TypeError(f"Unexpected type for events: {type(config.content.events)}")

    return scanner_messages, scanner_events
