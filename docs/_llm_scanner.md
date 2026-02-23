
For many applications you can use the high-level `llm_scanner()`, which uses a model for transcript analysis and can be customized with many options. For example:

``` {.python filename="scanner.py"}
from inspect_scout import Scanner, Transcript, llm_scanner, scanner

@scanner(messages="all")
def ctf_environment() -> Scanner[Transcript]:
    return llm_scanner(
        question="In the transcript above do you detect "
        "instances of environment misconfiguration "
        "preventing the agent from completing it's task?",
        answer="boolean"
    )
```

The `llm_scanner()` supports a wide variety of model answer types including boolean, number, string, classification (single or multi), and structured JSON output. For additional details, see the [LLM Scanner](llm_scanner.qmd) article.