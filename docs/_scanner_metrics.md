You can add metrics to scanners to aggregate result values. Metrics are computed during scanning and available as part of the scan results. For example:

```python
from inspect_ai.scorer import mean

@scanner(messages="all", metrics=[mean()])
def efficiency() -> Scanner[Transcript]:
    return llm_scanner(
        question="On a scale of 1 to 10, how efficiently did the assistant perform?",
        answer="numeric",
    )
```

Note that we import the `mean` metric from `inspect_ai`. You can use any standard Inspect metric or create custom metrics, and can optionally include more than one metric (e.g. `stderr`). 

See the Inspect documentation on [Built in Metrics](https://inspect.aisi.org.uk/scorers.html#built-in-metrics) and [Custom Metrics](https://inspect.aisi.org.uk/scorers.html#custom-metrics) for additional details.

A result whose `value` is `None` (for example, from a scanner that caught a judge refusal and returned no value) is not included in the metrics. The scanner's summary reports the number of top-level results with a `None` value as `unscored`. Note that:

- `unscored` is not a count of metric inputs, and it is not necessarily a count of transcripts: a scanner can report more than one result for a transcript.
- `None` values inside a result set (a scanner that returns a list of results) are not counted.
- `results`, `unscored`, and `errors` count different things and need not add up to `scans`. For example, a result of `0` or `False` is counted in neither `results` nor `unscored`.
