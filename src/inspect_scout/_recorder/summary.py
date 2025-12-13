from typing import Any, Sequence

from inspect_ai.model import ModelUsage
from pydantic import BaseModel, Field

from inspect_scout._scanner.result import ResultReport
from inspect_scout._transcript.types import TranscriptInfo


class ScannerSummary(BaseModel):
    """Summary of scanner results."""

    scans: int = Field(default=0)
    """Number of scans."""

    results: int = Field(default=0)
    """Scans which returned truthy results."""

    errors: int = Field(default=0)
    """Scans which resulted in errors."""

    validations: list[bool | dict[str, bool]] = Field(default_factory=list)
    """Results for validation cases."""

    metrics: dict[str, dict[str, float]] | None = Field(default=None)
    """Metrics computed for scanners with metrics."""

    tokens: int = Field(default=0)
    """Total tokens used for scanner."""

    model_usage: dict[str, ModelUsage] = Field(default_factory=dict)
    """Detailed model usage for scanner."""


class Summary(BaseModel):
    """Summary of scan results."""

    complete: bool = Field(default=True)
    """Is the scan complete?"""

    scanners: dict[str, ScannerSummary] = Field(default_factory=dict)
    """Summary for each scanner."""

    def __init__(
        self,
        scanners: list[str] | dict[str, ScannerSummary] | None = None,
        **data: Any,
    ):
        if isinstance(scanners, list):
            super().__init__(scanners={k: ScannerSummary() for k in scanners}, **data)
        else:
            super().__init__(scanners=scanners, **data)

    def _report(
        self,
        transcript: TranscriptInfo,
        scanner: str,
        results: Sequence[ResultReport],
        metrics: dict[str, dict[str, float]] | None,
    ) -> None:
        # aggregate over all results
        agg_results = ScannerSummary()
        for result in results:
            if result.result and result.result.value:
                if result.result.type == "resultset" and isinstance(
                    result.result.value, list
                ):
                    agg_results.results += len(result.result.value)
                else:
                    agg_results.results += 1
            if result.validation is not None:
                agg_results.validations.append(result.validation.valid)
            agg_results.errors += 1 if result.error is not None else 0
            agg_results.tokens += sum(
                [usage.total_tokens for usage in result.model_usage.values()]
            )
            for model, usage in result.model_usage.items():
                if model not in agg_results.model_usage:
                    agg_results.model_usage[model] = ModelUsage()
                agg_results.model_usage[model] = add_model_usage(
                    agg_results.model_usage[model], usage
                )

        # insert if required
        if scanner not in self.scanners:
            self.scanners[scanner] = ScannerSummary()

        # further aggregate
        tot_results = self.scanners[scanner]
        tot_results.scans += 1
        tot_results.results += agg_results.results
        tot_results.metrics = metrics
        tot_results.validations.extend(agg_results.validations)
        tot_results.errors += agg_results.errors
        tot_results.tokens += agg_results.tokens
        for model, usage in agg_results.model_usage.items():
            if model not in tot_results.model_usage:
                tot_results.model_usage[model] = ModelUsage()
            tot_results.model_usage[model] = add_model_usage(
                tot_results.model_usage[model], usage
            )

    def _report_metrics(
        self,
        scanner: str,
        metrics: dict[str, dict[str, float]] | None,
    ) -> None:
        if scanner not in self.scanners:
            self.scanners[scanner] = ScannerSummary()
        self.scanners[scanner].metrics = metrics

    def __getitem__(self, scanner: str) -> ScannerSummary:
        return self.scanners[scanner]


def add_model_usage(a: ModelUsage, b: ModelUsage) -> ModelUsage:
    return ModelUsage(
        input_tokens=a.input_tokens + b.input_tokens,
        output_tokens=a.output_tokens + b.output_tokens,
        total_tokens=a.total_tokens + b.total_tokens,
        input_tokens_cache_write=(a.input_tokens_cache_write or 0)
        + (b.input_tokens_cache_write or 0),
        input_tokens_cache_read=(a.input_tokens_cache_read or 0)
        + (b.input_tokens_cache_read or 0),
        reasoning_tokens=(a.reasoning_tokens or 0) + (b.reasoning_tokens or 0),
    )
