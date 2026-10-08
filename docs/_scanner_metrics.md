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

A result whose `value` is `None` (for example, a scanner that caught a judge refusal and returned no value) is not included in the metrics. The number of such results is reported as `unscored` on the scanner's summary, alongside `scans`, `results`, and `errors`, so a metric is always readable against how many results it was computed over.