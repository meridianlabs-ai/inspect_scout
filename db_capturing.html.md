# Capturing Transcripts


## Overview

The `observe()` decorator and context manager captures LLM calls and
writes transcripts directly to a database. This is useful for recording
agent interactions during development and building transcript datasets
from custom inference pipelines.

Observe can be used with either the Inspect AI [Model
API](https://inspect.aisi.org.uk/models.html) or with the native SDKs
from [OpenAI](https://github.com/openai/openai-python),
[Anthropic](https://github.com/anthropics/anthropic-sdk-python), and
[Google](https://github.com/googleapis/python-genai).

Use `observe()` as a decorator on async functions:

``` python
from inspect_ai.model import get_model, ChatMessageUser
from inspect_scout import observe, observe_update

@observe(db="./transcripts", task_set="my_eval", task_id="case_1")
async def run_case():
    model = get_model("openai/gpt-4o")
    response = await model.generate([
        ChatMessageUser(content="What is the capital of France?")
    ])
    observe_update(score=1.0, success=True)
    return response.completion
```

Or use it as an async context manager:

``` python
async with observe(db="./transcripts", task_set="my_eval"):
    model = get_model("openai/gpt-4o")
    response = await model.generate([
        ChatMessageUser(content="What is the capital of France?")
    ])
```

The `db` parameter accepts either a path string or a `TranscriptsDB`
instance. If omitted, it defaults to the project’s configured
transcripts directory (or `./transcripts` if none is configured).

## Providers

Above we demonstrated capturing transcripts when using the Inspect Model
API. You can alternatively capture LLM generation from a native SDK by
specifying an alternate `provider` (“openai”, “anthropic”, or “google”).

For example, here we `observe()` transcripts generated with the
Anthropic SDK:

``` python
import anthropic
from inspect_scout import observe, observe_update

@observe(db="./transcripts", provider="anthropic")
async def run_case():
    client = anthropic.AsyncAnthropic()
    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{
            "role": "user", 
            "content": "What is the capital of France?"
        }],
    )
    observe_update(score=1.0, success=True)
    return response.content[0].text
```

The `provider` parameter tells `observe()` to patch the specified SDK to
capture LLM calls. Available providers include:

| Provider | SDK | Description |
|----|----|----|
| `inspect` | [Inspect AI](https://inspect.aisi.org.uk/models.html) | Inspect Model API (default) |
| `openai` | [OpenAI](https://github.com/openai/openai-python) | OpenAI Chat Completions and Responses APIs |
| `anthropic` | [Anthropic](https://github.com/anthropics/anthropic-sdk-python) | Anthropic Messages API |
| `google` | [Google GenAI](https://github.com/googleapis/python-genai) | Google Gemini API |

You can also implement a custom provider by implementing the
`ObserveProvider` protocol.

## Decorator Usage

The `observe()` decorator supports several usage patterns:

``` python
# without parameters (uses project default db)
@observe
async def my_function():
    ...

# with parameters
@observe(task_set="eval", task_id="case_1")
async def my_function():
    ...

# with explicit database path
@observe(db="./my_transcripts", task_set="eval")
async def my_function():
    ...
```

## Parameters

The `observe()` function accepts the following parameters.

| Parameter | Type | Description |
|----|----|----|
| `db` | `str | TranscriptsDB` | Database path or instance. Only valid on outermost observe. |
| `source_type` | `str` | Type of source for transcript. Defaults to “observe”. |
| `source_id` | `str` | Globally unique ID for transcript source. |
| `source_uri` | `str` | URI for source data. |
| `task_set` | `str` | Set from which transcript task was drawn (e.g., benchmark name). |
| `task_id` | `str` | Identifier for task (e.g., dataset sample id). |
| `task_repeat` | `int` | Repeat number for a given task id (e.g., epoch). |
| `model` | `str` | Main model used by agent. |
| `model_options` | `dict` | Generation options for main model. |
| `agent` | `str` | Agent used to execute task. |
| `agent_args` | `dict` | Arguments passed to create agent. |
| `metadata` | `dict` | Additional metadata (merged with parent context). |

The `task_set` and `task_id` parameters are not required but are a good
way of providing context on transcripts (e.g in evaluations these are
often used for dataset name and sample id).

The following `Transcript` fields are automatically populated when a
transcript is written:

| Field | Description |
|----|----|
| `transcript_id` | Unique UUID generated for each transcript |
| `date` | UTC timestamp when the context exited |
| `total_time` | Duration of the observe context in seconds |
| `message_count` | Number of messages in the transcript |
| `total_tokens` | Sum of tokens from all model calls |
| `model` | Model name from the final generation (if not explicitly set) |
| `model_options` | Generation config from the final generation (if not explicitly set) |
| `error` | Error message if an exception occurred |
| `events` | Events which occurred during execution (e.g. `ModelEvent`, `ToolEvent`). |
| `messages` | Input and output message(s) of the final generation in the transcript. |

## Updating Fields

Use `observe_update()` to set transcript fields after execution, which
is useful for recording scores or outcomes:

``` python
@observe(db="./transcripts", task_set="eval")
async def run_and_score():
    model = get_model("openai/gpt-4o")
    response = await model.generate([
        ChatMessageUser(content="Solve: 2 + 2 = ?")
    ])

    # Evaluate and update transcript
    correct = "4" in response.completion
    observe_update(
        score=1.0 if correct else 0.0,
        success=correct,
        metadata={"answer": response.completion}
    )

    return response.completion
```

You can call `observe_update()` multiple times—fields are merged
(metadata is combined, other fields are overwritten).

## Nested Contexts

Nested `observe` contexts support batch processing where an outer
context sets shared parameters and inner contexts represent individual
transcripts:

``` python
@observe(db="./transcripts", task_set="cybench")
async def run_evaluation():
    model = get_model("openai/gpt-4o")

    for case in test_cases:
        async with observe(task_id=case.id):
            response = await model.generate([
                ChatMessageUser(content=case.prompt)
            ])
            score = evaluate(response, case.expected)
            observe_update(score=score, success=score > 0.8)
```

Key behaviors for nested contexts:

1.  **Inheritance**: Inner contexts inherit parameters from outer
    contexts.
2.  **Leaf detection**: Only the innermost context (the “leaf”) writes a
    transcript
3.  **Database scope**: The `db` parameter can only be set on the
    outermost context
4.  **Metadata merging**: The `metadata` dict is merged across all
    levels

## Error Handling

Exceptions within an `observe` context are caught, logged, and saved to
the transcript’s `error` field. The exception is suppressed to allow
batch processing to continue:

``` python
@observe(db="./transcripts", task_set="eval")
async def run_with_error():
    model = get_model("openai/gpt-4o")
    await model.generate([ChatMessageUser(content="Hello")])
    raise ValueError("Something went wrong")
    # Transcript is still written with error="Something went wrong"

# This completes without raising
await run_with_error()
```

## Example: Evaluation

Here’s a complete example of running a batch evaluation with parallel
processing:

``` python
import asyncio
from inspect_ai.model import get_model, ChatMessageUser
from inspect_scout import observe, observe_update

async def main():
    test_cases = [
        {"id": "math_1", "prompt": "What is 2+2?", "expected": "4"},
        {"id": "math_2", "prompt": "What is 3*3?", "expected": "9"},
        {"id": "math_3", "prompt": "What is 10/2?", "expected": "5"},
    ]

    async def run_case(case: dict) -> None:
        async with observe(task_id=case["id"]):
            model = get_model("openai/gpt-4o")
            response = await model.generate([
                ChatMessageUser(content=case["prompt"])
            ])
            correct = case["expected"] in response.completion
            observe_update(
                score=1.0 if correct else 0.0, 
                success=correct
            )

    async with observe(db="./transcripts", task_set="math_eval"):
        await asyncio.gather(*[run_case(case) for case in test_cases])

asyncio.run(main())
```

After running, you can view the transcripts:

``` bash
scout view -T ./transcripts
```

Or scan them with your scanners:

``` python
from inspect_scout import scan, transcripts_from
from my_scanners import math_checker

scan(
    scanners=[math_checker()],
    transcripts=transcripts_from("./transcripts")
)
```
