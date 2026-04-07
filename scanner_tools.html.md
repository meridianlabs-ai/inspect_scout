# Scanner Tools

## Overview

The [LLM Scanner](llm_scanner.html.md) provides a high-level, batteries-included interface for building LLM-based scanners. Under the hood, it is composed of several lower-level tools: message numbering, prompt construction, answer generation, message extraction, and result reduction. You can use these tools directly when you need more control.

For straightforward scanning tasks, prefer [llm_scanner()](reference/scanner.html.md#llm_scanner) as it handles the entire pipeline for you. Use lower level scanner tools when you need to override or extend specific steps.

Here is roughly the implementation of [llm_scanner()](reference/scanner.html.md#llm_scanner), but using the lower level tools that we’ll cover in more depth below (click on the numbers at right for further explanation):

``` python
from inspect_scout import (
    Result, ResultReducer, Scanner, Transcript, 
    generate_answer, message_numbering, scanner, 
    scanner_prompt, transcript_messages
)

@scanner(messages="all")
def environment_scanner() -> Scanner[Transcript]:

    async def scan(transcript: Transcript) -> Result:

        # setup numbering and references
        messages_as_str, extract_refs = message_numbering() # <1>

        # define question to ask llm
        question = (
            "Did the agent fail to complete the task due to "
            "a broken or misconfigured environment?"
        )

        # scan segments (breaks up transcript to fit in context window)
        results: list[Result] = []
        async for segment in transcript_messages( # <2>
            transcript,                           # <2>
            messages_as_str=messages_as_str       # <2>
        ):                                        # <2>
            # generate prompt using segment, question, and answer type
            prompt = scanner_prompt(              # <3>
                messages=segment.messages_str,    # <3>
                question=question,                # <3>
                answer="boolean"                  # <3>
            )                                     # <3>

            # generate, extract answer/explanation and append results
            results.append(
                await generate_answer(            # <4>
                    prompt,                       # <4>
                    "boolean",                    # <4>
                    extract_refs=extract_refs,    # <4>
                )                                 # <4>
            )

        # reduce per-segment results into a single result
        return await ResultReducer.any(results)   # <5>

    return scan
```

1.  Setup message numbering (returns a function that can be used to number and a function that can be used to extract references to messages from model explanations).
2.  Iterate over transcript segments (if the transcript exceeds the size of the scanning model’s context window it will need to be broken into segments).
3.  Build a prompt for the scanner using the string for this segment (numbered messages), the question, and the answer type.
4.  Call the model to generate an answer, extracting references from its explanation using the `extract_refs` function.
5.  When context-window segmentation produces multiple segments, reduce them into a single result. Here we use the `.any()` reducer which returns `True` if any segment result was `True`.

## Message Presentation

The [message_numbering()](reference/scanner.html.md#message_numbering) function creates a pair of functions that share a closure-captured counter and message ID map. This enables consistent message numbering across multiple calls (e.g., across segments) and lets you extract `[M1]`-style references from model output back to the original messages.

``` python
from inspect_scout import message_numbering

messages_as_str, extract_refs = message_numbering()
```

The returned functions work together:

- `messages_as_str(messages)` — Renders a list of [ChatMessage](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#chatmessage) objects into a numbered string (e.g., `[M1] USER: ...`). The counter auto-increments across calls, so a second call continues from where the first left off.
- `extract_refs(text)` — Resolves `[M1]`, `[M2]`, etc. citations in model output back to [Reference](reference/scanner.html.md#reference) objects pointing to the original messages.

### Preprocessing

You can pass a [MessagesPreprocessor](reference/scanner.html.md#messagespreprocessor) to control which message content is included in the rendered output:

``` python
from inspect_scout import message_numbering, MessagesPreprocessor

messages_as_str, extract_refs = message_numbering(
    preprocessor=MessagesPreprocessor(
        exclude_system=True,       # exclude system messages (default)
        exclude_reasoning=True,    # exclude reasoning content
        exclude_tool_usage=True,   # exclude tool calls and output
    )
)
```

|  |  |
|----|----|
| `exclude_system` | Exclude system messages (defaults to `True`) |
| `exclude_reasoning` | Exclude reasoning content (defaults to `False`) |
| `exclude_tool_usage` | Exclude tool calls and output (defaults to `False`) |
| `transform` | Optional async function that takes the message list and returns a filtered list. |

When no preprocessor is provided, the default behaviour is to exclude system messages only.

## Prompt Construction

The [scanner_prompt()](reference/scanner.html.md#scanner_prompt) function renders the default scanner template—the same template used internally by [llm_scanner()](reference/scanner.html.md#llm_scanner). It combines the transcript messages, question, and answer type into a complete prompt:

``` python
from inspect_scout import scanner_prompt

prompt = scanner_prompt(
    messages=segment.messages_str,
    question="Did the assistant refuse the user's request?",
    answer="boolean",
)
```

### Custom Prompts

For fully custom prompt templates, use [answer_type()](reference/scanner.html.md#answer_type) to resolve an [AnswerSpec](reference/scanner.html.md#answerspec) into an [Answer](reference/scanner.html.md#answer) object that exposes `.prompt` and `.format` strings:

``` python
from inspect_scout import answer_type

answer = answer_type("boolean")
# answer.prompt  -> "Answer the following yes or no question..."
# answer.format  -> "The last line of your response should be..."

prompt = f"""Here is a conversation:

{segment.messages_str}

{answer.prompt}

{question}

{answer.format}
"""
```

This gives you complete control over prompt structure while reusing the answer-type-specific formatting instructions.

## Answer Generation

The [generate_answer()](reference/scanner.html.md#generate_answer) function calls the LLM and parses the response into a [Result](reference/scanner.html.md#result). It supports all answer types, handles refusal retries, and uses tool-based generation for structured answers:

``` python
from inspect_scout import generate_answer

result = await generate_answer(
    prompt,
    answer="boolean",
    extract_refs=extract_refs,
)
```

|  |  |
|----|----|
| `prompt` | The scanning prompt (string or message list). |
| `answer` | Answer specification (`"boolean"`, `"numeric"`, `"string"`, `list[str]`, [AnswerMultiLabel](reference/scanner.html.md#answermultilabel), or [AnswerStructured](reference/scanner.html.md#answerstructured)). |
| `model` | Model to use for generation. Defaults to the current default model. |
| `retry_refusals` | Number of times to retry on content filter refusals (default `3`). |
| `parse` | When `True` (default), parse the output into a [Result](reference/scanner.html.md#result). When `False`, return the raw [ModelOutput](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#modeloutput). |
| `extract_refs` | Function to extract `[M1]`-style references from the explanation. Only used when `parse=True`. |
| `value_to_float` | Optional function to convert the parsed value to a float. Only used when `parse=True`. |

## Answer Parsing

The [parse_answer()](reference/scanner.html.md#parse_answer) function provides pure parsing without making an LLM call. Use this when you generate model output through your own code (e.g., via `get_model().generate()`) but want to use the standard answer extraction logic:

``` python
from inspect_ai.model import get_model
from inspect_scout import parse_answer

# generate with your own code
model = get_model("openai/gpt-4o")
output = await model.generate(prompt)

# parse using standard answer extraction
result = parse_answer(
    output,
    answer="boolean",
    extract_refs=extract_refs,
)
```

|  |  |
|----|----|
| `output` | The [ModelOutput](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#modeloutput) to parse. |
| `answer` | Answer specification (same types as [generate_answer()](reference/scanner.html.md#generate_answer)). |
| `extract_refs` | Function to extract `[M1]`-style references from the explanation text. |
| `value_to_float` | Optional function to convert the parsed value to a float. |

## Answer Types

The `answer` parameter accepted by [scanner_prompt()](reference/scanner.html.md#scanner_prompt), [generate_answer()](reference/scanner.html.md#generate_answer), and [parse_answer()](reference/scanner.html.md#parse_answer) is an [AnswerSpec](reference/scanner.html.md#answerspec)—a union type that determines how the LLM is prompted, how answers are extracted, and the Python type of the result value:

| Type              | LLM Output        | Result Type           |
|-------------------|-------------------|-----------------------|
| boolean           | ANSWER: yes       | `bool`                |
| numeric           | ANSWER: 10        | `float`               |
| string            | ANSWER: brown fox | `str`                 |
| label             | ANSWER: C         | `str`                 |
| labels (multiple) | ANSWER: C, D      | `list[str]`           |
| structured        | JSON object       | `dict[str,JsonValue]` |

### Multi-Label Classification

Pass `list[str]` to prompt the model to select a **single** label. To allow **multiple** label selections, wrap the labels in [AnswerMultiLabel](reference/scanner.html.md#answermultilabel):

``` python
from inspect_scout import AnswerMultiLabel

answer = AnswerMultiLabel(labels=[
    "Factual error",
    "Refusal",
    "Off-topic response",
    "Hallucination",
])
```

Label values (`A`, `B`, `C`, …) are assigned automatically based on position in the list.

### Structured Answers

[AnswerStructured](reference/scanner.html.md#answerstructured) uses tool-based generation to produce JSON output conforming to a Pydantic model:

``` python
from pydantic import BaseModel, Field
from inspect_scout import AnswerStructured

class CyberLint(BaseModel):
    misconfiguration: bool = Field(
        description="Was the environment misconfigured?"
    )
    tool_errors: int = Field(
        description="How many tool errors were encountered?"
    )

answer = AnswerStructured(type=CyberLint)
```

|  |  |
|----|----|
| `type` | Pydantic `BaseModel` subclass, or `list[Model]` for multiple results. |
| `answer_tool` | Name of the tool provided to the model (default `"answer"`). |
| `answer_prompt` | Template for the prompt that precedes the question. |
| `answer_format` | Template for instructions on how to respond. |
| `max_attempts` | Maximum retries for correct schema generation (default `3`). |

See [Structured Answers](llm_scanner.html.md#structured-answers) in the LLM Scanner documentation for details on Pydantic field aliases (`value`, `label`, `explanation`), multiple results via `list[Model]`, and `value_to_float` usage.

## Message Extraction

The [transcript_messages()](reference/transcript.html.md#transcript_messages) function is the primary API for extracting pre-rendered message segments from a transcript. It automatically selects the best extraction strategy based on what data is available:

- If timelines are present, it walks the span tree and yields per-span segments.
- If only events are present, it extracts messages from events with compaction handling.
- If only messages are present, it segments them by context window.

``` python
from inspect_scout import message_numbering, transcript_messages

messages_as_str, extract_refs = message_numbering()

async for segment in transcript_messages(
    transcript,
    messages_as_str=messages_as_str,
):
    # segment.messages     -> list[ChatMessage]
    # segment.messages_str -> pre-rendered numbered string
    # segment.segment      -> 0-based segment index
    ...
```

|  |  |
|----|----|
| `transcript` | The [Transcript](reference/transcript.html.md#transcript) to extract messages from. |
| `messages_as_str` | Rendering function from [message_numbering()](reference/scanner.html.md#message_numbering). |
| `model` | Model used for token counting and context window lookup. |
| `context_window` | Override the model’s detected context window size (in tokens). |
| `compaction` | How to handle compaction boundaries: `"all"` (default) merges across boundaries; `"last"` uses only the final segment. |
| `depth` | Maximum depth of the span tree to process (timelines only). `None` recurses without limit. |
| `include_scorers` | Whether to include scorer events in extraction (default `False`). |

### [segment_messages()](reference/transcript.html.md#segment_messages)

When you have a source other than a full [Transcript](reference/transcript.html.md#transcript)—a list of messages, a list of events, or a [TimelineSpan](https://inspect.aisi.org.uk/reference/inspect_ai.event.html#timelinespan)—use [segment_messages()](reference/transcript.html.md#segment_messages) to render and split them into context-window-sized segments:

``` python
from inspect_scout import message_numbering, segment_messages

messages_as_str, extract_refs = message_numbering()

async for segment in segment_messages(
    source,                            # list[ChatMessage], list[Event], or TimelineSpan
    messages_as_str=messages_as_str,
):
    # segment.messages     -> list[ChatMessage]
    # segment.messages_str -> pre-rendered numbered string
    # segment.segment      -> 0-based segment index
    ...
```

When given events or a [TimelineSpan](https://inspect.aisi.org.uk/reference/inspect_ai.event.html#timelinespan), it delegates to [span_messages()](reference/transcript.html.md#span_messages) internally to extract and merge messages (handling compaction boundaries), then segments the result by token count.

|  |  |
|----|----|
| `source` | A `list[ChatMessage]`, `list[Event]`, or [TimelineSpan](https://inspect.aisi.org.uk/reference/inspect_ai.event.html#timelinespan). |
| `messages_as_str` | Rendering function from [message_numbering()](reference/scanner.html.md#message_numbering). |
| `model` | Model used for token counting and context window lookup. |
| `context_window` | Override the model’s detected context window size (in tokens). |
| `compaction` | How to handle compaction boundaries (passed to [span_messages()](reference/transcript.html.md#span_messages)). |

### [span_messages()](reference/transcript.html.md#span_messages)

The lowest-level extraction function. It takes a [Timeline](https://inspect.aisi.org.uk/reference/inspect_ai.event.html#timeline), [TimelineSpan](https://inspect.aisi.org.uk/reference/inspect_ai.event.html#timelinespan), or raw `list[Event]`, extracts [ChatMessage](https://inspect.aisi.org.uk/reference/inspect_ai.model.html#chatmessage) objects from [ModelEvent](https://inspect.aisi.org.uk/reference/inspect_ai.event.html#modelevent)s, and handles compaction boundaries—all synchronously, without rendering or segmentation:

``` python
from inspect_scout import span_messages

# From a TimelineSpan
messages = span_messages(span)

# From a list of events
messages = span_messages(events, compaction="last")

# Split into per-compaction-region lists
regions = span_messages(span, split_compactions=True)
```

|  |  |
|----|----|
| `source` | A [Timeline](https://inspect.aisi.org.uk/reference/inspect_ai.event.html#timeline), [TimelineSpan](https://inspect.aisi.org.uk/reference/inspect_ai.event.html#timelinespan), or `list[Event]`. |
| `compaction` | How to handle compaction boundaries: `"all"` (default) merges across boundaries; `"last"` uses only the final [ModelEvent](https://inspect.aisi.org.uk/reference/inspect_ai.event.html#modelevent)’s messages; an `int` keeps the last *N* compaction regions. |
| `split_compactions` | When `True`, returns `list[list[ChatMessage]]` with one inner list per compaction region instead of a flat merged list. |

Use [span_messages()](reference/transcript.html.md#span_messages) when you need raw messages without rendering or token-based segmentation—for example, to inspect message content directly, apply your own formatting, or count messages before deciding how to process them.

## Context Chunking

When a transcript’s messages exceed the scanning model’s context window, [transcript_messages()](reference/transcript.html.md#transcript_messages) and [segment_messages()](reference/transcript.html.md#segment_messages) automatically split them into segments sized to fit within 80% of the model’s available context. Each segment is scanned independently with the same prompt. Use the `context_window` parameter on [transcript_messages()](reference/transcript.html.md#transcript_messages) or [segment_messages()](reference/transcript.html.md#segment_messages) to override the model’s detected context window size.

### Result Reduction

Because context-window segmentation can produce multiple results from a single source, those per-segment results need to be combined using a reducer. The [ResultReducer](reference/scanner.html.md#resultreducer) class provides static async reducers for this purpose.

| Reducer | Behaviour |
|----|----|
| `ResultReducer.any` | Boolean OR—`True` if any result is `True`. |
| `ResultReducer.mean` | Arithmetic mean of numeric values. |
| `ResultReducer.median` | Median of numeric values. |
| `ResultReducer.mode` | Mode (most common) of numeric values. |
| `ResultReducer.max` | Maximum of numeric values. |
| `ResultReducer.min` | Minimum of numeric values. |
| `ResultReducer.union` | Union of list values, deduplicated, preserving order. |
| `ResultReducer.majority` | Most common value, with last-result tiebreaker. |
| `ResultReducer.last` | Returns the last result with merged auxiliary fields. |

All reducers are async functions with signature `(list[Result]) -> Result`.

### LLM-Based Reduction

For cases where statistical reduction isn’t sufficient, `ResultReducer.llm()` returns a reducer that uses an LLM to synthesize segment results. It automatically formats each segment’s answer, value, and explanation into a prompt, asks the model to synthesize them, and returns a single combined result. It is the default reducer for `"string"` answer types.

``` python
from inspect_scout import ResultReducer, llm_scanner, scanner

@scanner()
def synthesized_analysis():
    return llm_scanner(
        question="Summarize the agent's key decisions.",
        answer="string",
        reducer=ResultReducer.llm(model="openai/gpt-5"),
    )
```

You can pass a custom `prompt` to guide how the model combines segment results. The per-segment answers, values, and explanations are automatically appended after your prompt:

``` python
@scanner()
def security_summary():
    return llm_scanner(
        question="Identify any security concerns in the agent's actions.",
        answer="string",
        reducer=ResultReducer.llm(
            prompt=(
                "You are reviewing security findings from different "
                "segments of a long agent conversation. Prioritize the "
                "most severe issues, deduplicate overlapping findings, "
                "and produce a concise summary ordered by severity."
            ),
        ),
    )
```

### Custom Reducers

You can also write a custom reducer — any async function with the signature `(list[Result]) -> Result`. Each [Result](reference/scanner.html.md#result) in the list has `.value`, `.answer`, `.explanation`, and `.references` from its segment:

``` python
from inspect_scout import Result, llm_scanner, scanner

async def worst_score(results: list[Result]) -> Result:
    """Keep the result with the lowest numeric value."""
    return min(results, key=lambda r: r.value)

@scanner()
def strictest_scan():
    return llm_scanner(
        question="Rate the quality of the agent's output (1-10).",
        answer="numeric",
        reducer=worst_score,
    )
```

Note that result reduction applies only to context-window segments within a single source. When scanning timelines with multiple spans, each span produces its own result independently — these are collected into a `ResultSet` without reduction.
