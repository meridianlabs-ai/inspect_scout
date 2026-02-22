

## Scanning Toolkit {#scanning-toolkit}

The scanning toolkit provides composable functions for building custom scanning pipelines—the same building blocks that [`llm_scanner()`](llm_scanner.qmd) uses internally. When `llm_scanner` doesn't fit your needs (custom prompting strategy, multi-pass scanning, non-standard result aggregation), drop down to these APIs.

### Incremental Example

Here's how the toolkit functions compose, starting simple and adding capabilities:

**Step 1: Basic scanning.** Use `message_numbering()` to render messages with `[M1]`, `[M2]`... prefixes, then `generate_answer()` to call the LLM and parse the response:

``` python
from inspect_scout import (
    Transcript, Result, message_numbering, generate_answer, scanner,
)

@scanner(messages="all")
def my_scanner():
    async def scan(transcript: Transcript) -> Result:
        messages_as_str, extract_references = message_numbering()
        text = await messages_as_str(transcript.messages)
        prompt = f"Analyze this transcript:\n\n{text}\n\nDid the agent succeed?"
        return await generate_answer(
            prompt, "boolean", extract_references=extract_references,
        )
    return scan
```

**Step 2: Context-aware segmentation.** Wrap with `transcript_messages()` to handle transcripts that exceed the model's context window:

``` python
from inspect_ai.model import get_model
from inspect_scout import (
    Transcript, Result, message_numbering, generate_answer,
    transcript_messages, scanner,
)

@scanner(messages="all")
def my_scanner():
    async def scan(transcript: Transcript) -> Result:
        messages_as_str, extract_references = message_numbering()
        model = get_model()
        results = []
        async for segment in transcript_messages(
            transcript, messages_as_str=messages_as_str, model=model,
        ):
            prompt = f"Analyze this transcript:\n\n{segment.text}\n\nDid the agent succeed?"
            result = await generate_answer(
                prompt, "boolean", extract_references=extract_references,
            )
            results.append(result)
        return results[-1] if results else Result(value=False)
    return scan
```

**Step 3: Parallel scanning.** Replace the manual loop with `scan_segments()` for concurrent generation:

``` python
from inspect_ai.model import get_model
from inspect_scout import (
    Transcript, Result, message_numbering, generate_answer,
    transcript_messages, scan_segments, ResultReducer, scanner,
)

@scanner(messages="all")
def my_scanner():
    async def scan(transcript: Transcript) -> Result:
        messages_as_str, extract_references = message_numbering()
        model = get_model()

        async def scan_one(segment):
            prompt = f"Analyze this transcript:\n\n{segment.text}\n\nDid the agent succeed?"
            return await generate_answer(
                prompt, "boolean", extract_references=extract_references,
            )

        results = await scan_segments(
            transcript_messages(transcript, messages_as_str=messages_as_str, model=model),
            scan_one,
        )
        return await ResultReducer.any(results) if len(results) > 1 else results[0]
    return scan
```

### Message Numbering

`message_numbering()` creates a linked pair of functions with shared state:

``` python
from inspect_scout import message_numbering, MessagesPreprocessor

messages_as_str, extract_references = message_numbering(
    preprocessor=MessagesPreprocessor(exclude_system=True)  # optional
)
```

The returned `messages_as_str(messages)` renders a message list as a numbered string with `[M1]`, `[M2]`... prefixes. The counter auto-increments across calls—if the first call renders `[M1]`–`[M5]`, the next starts at `[M6]`. The returned `extract_references(text)` resolves `[M14]`-style citations from any prior `messages_as_str` call back to their original message identifiers.

``` python
# First call: [M1]...[M5]
text1 = await messages_as_str(first_messages)

# Second call: [M6]...[M10]  (continuous numbering)
text2 = await messages_as_str(second_messages)

# Resolves citations from either call
refs = extract_references("The issue appears in [M3] and [M8]")
```

### Message Extraction

`transcript_messages()` is the high-level entry point for extracting scannable message segments from a transcript. It automatically selects the best strategy based on what data is available:

- **Timelines present** → walks the span tree via `timeline_messages()`
- **Events present** → segments with compaction handling
- **Messages only** → context window segmentation

``` python
from inspect_ai.model import get_model
from inspect_scout import transcript_messages, message_numbering

messages_as_str, extract_references = message_numbering()
model = get_model()

async for segment in transcript_messages(
    transcript,
    messages_as_str=messages_as_str,
    model=model,
    context_window=128_000,  # override detected window
    compaction="all",        # "all" or "last"
    depth=2,                 # limit timeline tree depth
):
    # segment.messages — list[ChatMessage]
    # segment.text — rendered string with [M1]... prefixes
    # segment.segment — segment index (0-based)
    ...
```

For lower-level control:

| Function | Description |
|----------|-------------|
| `segment_messages(source, ...)` | Segments a message list, event list, or span into context-window-sized chunks. |
| `span_messages(source, *, compaction)` | Extracts raw messages from a `TimelineSpan` or event list, handling compaction merging. |

: {tbl-colwidths=\[35,65\]}

### Answer Generation

`generate_answer()` is a one-step function that constructs the LLM call, handles structured vs. text generation, retries on refusals, and parses the response into a `Result`:

``` python
from inspect_scout import generate_answer

result = await generate_answer(
    prompt="Analyze this transcript:\n\n{text}\n\nDid the agent succeed?",
    answer="boolean",
    extract_references=extract_references,  # from message_numbering()
)
# result.value: bool
# result.answer: str ("yes" or "no")
# result.explanation: str
# result.references: list[Reference]
```

For structured answers, `generate_answer` automatically uses tool-based generation. Set `parse=False` to get the raw `ModelOutput` instead of a parsed `Result`.

For custom generation pipelines, use `parse_answer()` to handle only the parsing step:

``` python
from inspect_scout import parse_answer

# After your own model call...
result = parse_answer(output, answer="boolean", extract_references=extract_references)
```

The `answer` parameter accepts any `AnswerSpec`:

| Type | Description |
|------|-------------|
| `"boolean"` | Yes/no answer → `bool` value |
| `"numeric"` | Numeric answer → `float` value |
| `"string"` | Free-text answer → `str` value |
| `list[str]` | Single-label classification |
| `AnswerMultiLabel` | Multi-label classification |
| `AnswerStructured` | Structured JSON via Pydantic model |

: {tbl-colwidths=\[25,75\]}

### Scanning Timelines

A timeline is a tree of **spans** representing the structure of an agent's execution. Each span corresponds to an agent, tool, or scorer invocation and contains its own events (model calls, tool calls). Timelines are auto-detected from transcript events: agent hierarchy, conversation threads, branches, and utility agents.

`timeline_messages()` walks the span tree and yields `TimelineMessages` segments (which extend `MessagesSegment` with an additional `.span` field):

``` python
from inspect_ai.model import get_model
from inspect_scout import timeline_messages, message_numbering

messages_as_str, extract_references = message_numbering()
model = get_model()

async for tm in timeline_messages(
    transcript.timelines[0],
    messages_as_str=messages_as_str,
    model=model,
):
    # tm.span — the TimelineSpan being scanned
    # tm.text — rendered messages for this span
    # tm.segment — segment index within this span
    print(f"Scanning span: {tm.span.name}")
```

The `include` parameter controls which spans are visited:

| Value | Behavior |
|-------|----------|
| `None` (default) | Non-utility spans that contain direct `ModelEvent`s |
| `str` | Spans whose name matches (case-insensitive) |
| `callable` | Custom predicate: `(TimelineSpan) -> bool` |

: {tbl-colwidths=\[25,75\]}

Here is an example of a custom timeline scanner that only scans spans matching a specific agent name:

``` python
from inspect_scout import (
    Transcript, Result, message_numbering, generate_answer,
    timeline_messages, scan_segments, scanner,
)
from inspect_ai.model import get_model

@scanner
def scan_researcher():
    async def scan(transcript: Transcript) -> list[Result]:
        messages_as_str, extract_references = message_numbering()
        model = get_model()

        async def scan_one(segment):
            prompt = f"Analyze this conversation:\n\n{segment.text}\n\nWhat did the agent find?"
            return await generate_answer(
                prompt, "string", extract_references=extract_references,
            )

        return await scan_segments(
            timeline_messages(
                transcript.timelines[0],
                messages_as_str=messages_as_str,
                model=model,
                include="researcher",  # only spans named "researcher"
                depth=2,
            ),
            scan_one,
        )
    return scan
```

### Parallel Scanning

`scan_segments()` runs a scan function concurrently over a sequence of message segments:

``` python
from inspect_scout import scan_segments

results = await scan_segments(segments, scan_fn)
```

Segments are iterated sequentially (message numbering requires ordered rendering), but each segment's `scan_fn` call runs concurrently. The model's internal connection semaphore handles rate limiting. Results are returned in segment order regardless of completion order.

### Result Reduction

`ResultReducer` provides standard reducers for combining multi-segment results into a single result:

| Reducer | Behavior |
|---------|----------|
| `ResultReducer.any` | `True` if any segment returned `True` |
| `ResultReducer.mean` | Mean of numeric values |
| `ResultReducer.median` | Median of numeric values |
| `ResultReducer.mode` | Most common value |
| `ResultReducer.max` | Maximum numeric value |
| `ResultReducer.min` | Minimum numeric value |
| `ResultReducer.union` | Union of multi-label sets |
| `ResultReducer.last` | Result from the last segment |
| `ResultReducer.llm(model, prompt)` | LLM-based synthesis of results |

Each reducer is an async function with signature `async (list[Result]) -> Result`:

``` python
from inspect_scout import ResultReducer

combined = await ResultReducer.any(results)
```

`ResultReducer.llm()` is a factory that returns a reducer which uses an LLM to synthesize results:

``` python
reducer = ResultReducer.llm(model="openai/gpt-4o", prompt="Synthesize these findings...")
combined = await reducer(results)
```

Default reducers by answer type:

| Answer Type | Default Reducer |
|-------------|----------------|
| `"boolean"` | `ResultReducer.any` |
| `"numeric"` | `ResultReducer.mean` |
| `"string"` | `ResultReducer.last` |
| labels | `ResultReducer.last` |
| `AnswerMultiLabel` | `ResultReducer.union` |
| `AnswerStructured` | `ResultReducer.last` |

When using structured list answers with timeline scanning, reduction is often unnecessary—each span's findings are collected into a combined result set that preserves per-span detail.

