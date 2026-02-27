
Using an LLM to search transcripts is often required for more nuanced judgements, but if you are just looking for text patterns, you can also use the `grep_scanner()`. For example, here we search assistant messages for references to phrases that might indicate secrets:

```python
from inspect_scout import Transcript, grep_scanner, scanner

@scanner(messages=["assistant"])
def secrets() -> Scanner[Transcript]:
    return grep_scanner(["password", "secret", "token"])
```

For additional details on using this scanner, see the [Grep Scanner](grep_scanner.qmd) article.
