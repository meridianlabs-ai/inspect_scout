from typing import Any, Sequence

from pydantic import BaseModel, Field

from inspect_scout._scanner.result import ResultReport
from inspect_scout._transcript.types import TranscriptInfo


class ScannerSummary(BaseModel):
    scans: int = Field(default=0)
    results: int = Field(default=0)
    errors: int = Field(default=0)
    tokens: int = Field(default=0)


class ScanSummary(BaseModel):
    results: dict[str, ScannerSummary] = Field(default_factory=dict)

    def __init__(self, scanners: list[str] | None = None, **data: Any):
        if scanners is not None and not data:
            super().__init__(results={k: ScannerSummary() for k in scanners})
        else:
            super().__init__(**data)

    def report(
        self, transcript: TranscriptInfo, scanner: str, results: Sequence[ResultReport]
    ) -> None:
        # aggregate over all results
        agg_results = ScannerSummary()
        for result in results:
            agg_results.results += (
                1 if result.result and result.result.value is not None else 0
            )
            agg_results.errors += 1 if result.error is not None else 0
            agg_results.tokens += sum(
                [usage.total_tokens for usage in result.model_usage.values()]
            )

        # insert if required
        if scanner not in self.results:
            self.results[scanner] = ScannerSummary()

        # further aggregate
        tot_results = self.results[scanner]
        tot_results.scans += 1
        tot_results.results += agg_results.results
        tot_results.errors += agg_results.errors
        tot_results.tokens += agg_results.tokens

    def __getitem__(self, scanner: str) -> ScannerSummary:
        return self.results[scanner]
