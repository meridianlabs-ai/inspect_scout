from typing import Any, Mapping, Sequence, cast

from inspect_ai._eval.task.results import ScorerInfo, compute_eval_scores
from inspect_ai._util.json import to_json_str_safe
from inspect_ai._util.registry import registry_info
from inspect_ai.scorer import Metric, SampleScore, Score, Value
from pydantic import JsonValue

from inspect_scout._scanner.scanner import SCANNER_METRICS, Scanner
from inspect_scout._util.throttle import throttle


class MetricsAccumulator:
    def __init__(
        self,
        scanner: str,
        metrics: list[Metric | dict[str, list[Metric]]] | dict[str, list[Metric]],
    ) -> None:
        self._scanner = scanner
        self._metrics = metrics
        self._scores: list[SampleScore] = []

    def add_result(self, value: JsonValue) -> None:
        if value is not None:
            self._scores.append(SampleScore(score=Score(value=as_score_value(value))))

    def compute_metrics(self) -> dict[str, dict[str, float]]:
        scores = compute_eval_scores(
            scores=self._scores,
            metrics=self._metrics,
            scorer_name=self._scanner,
            scorer_info=ScorerInfo(self._scanner, self._metrics),
        )

        # scorer -> metrics dict (note typically there will be one
        # scorer only unless a dict of metrics was spread against
        # a dict of values returned from the scorer)
        metrics: dict[str, dict[str, float]] = {}
        for score in scores:
            metrics[score.name] = {k: v.value for k, v in score.metrics.items()}
        return metrics

    @throttle(3)
    def compute_metrics_throttled(self) -> dict[str, dict[str, float]]:
        return self.compute_metrics()


def metrics_accumulators(
    scanners: dict[str, Scanner[Any]],
) -> dict[str, MetricsAccumulator]:
    accumulators: dict[str, MetricsAccumulator] = {}
    for name, scanner in scanners.items():
        metrics = metrics_for_scanner(scanner)
        if metrics is not None:
            accumulators[name] = MetricsAccumulator(
                scanner=name,
                metrics=cast(
                    list[Metric | dict[str, list[Metric]]] | dict[str, list[Metric]],
                    metrics,
                ),
            )
    return accumulators


def metrics_for_scanner(
    scanner: Scanner[Any],
) -> (
    Sequence[Metric | Mapping[str, Sequence[Metric]]]
    | Mapping[str, Sequence[Metric]]
    | None
):
    return cast(
        Sequence[Metric | Mapping[str, Sequence[Metric]]]
        | Mapping[str, Sequence[Metric]]
        | None,
        registry_info(scanner).metadata.get(SCANNER_METRICS, None),
    )


def as_score_value(value: JsonValue) -> Value:
    if isinstance(value, list):
        return [
            v if isinstance(v, str | int | float | bool) else to_json_str_safe(v)
            for v in value
        ]
    elif isinstance(value, dict):
        return {
            k: v
            if isinstance(v, str | int | float | bool | None)
            else to_json_str_safe(v)
            for k, v in value.items()
        }
    elif isinstance(value, str | int | float | bool):
        return value
    else:
        raise AssertionError("None should not be passed to as_score_value")
