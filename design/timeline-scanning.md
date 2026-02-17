# Timeline Scanning

## 1. Universal Message Numbering

### Problem

The existing `messages_as_str()` function (`_scanner/extract.py`) numbers messages sequentially starting at `M1`. When scanning a timeline, we scan multiple spans — each span has its own `ModelEvent`s with `input` messages. If each span independently starts numbering at `M1`, references conflict: an LLM citing `[M3]` in one span's scan could collide with `[M3]` from another span.

### Current Behavior

```python
messages_str, extract_references = await messages_as_str(
    transcript,
    preprocessor=preprocessor,
    include_ids=True,
)
```

- Input: `Transcript` or `list[ChatMessage]`
- Numbering: `M1`, `M2`, `M3`, ... (sequential, 1-indexed)
- Returns: `(formatted_str, extract_references_fn)`
- The `extract_references` closure captures an `id_map: dict[str, str]` mapping ordinals like `"M1"` to actual message IDs

### Requirements for Timeline Scanning

When scanning a timeline with spans like `Explore → Plan → Build`:

1. Each span is scanned independently — its messages are formatted and sent to an LLM
2. References must be globally unique across all span scans within a single timeline scan
3. The `extract_references` function must resolve any citation from any span scan
4. A unified `id_map` must accumulate across all span scans

### Proposed Design

A factory function `message_numbering()` returns a pair of functions — a `messages_as_str` that auto-numbers with globally unique IDs, and an `extract_references` that resolves citations across all calls. The numbering state is hidden in the closure:

```python
MessagesAsStr: TypeAlias = Callable[[list[ChatMessage]], Awaitable[str]]
ExtractReferences: TypeAlias = Callable[[str], list[Reference]]

def message_numbering(
    preprocessor: MessagesPreprocessor | None = None,
) -> tuple[MessagesAsStr, ExtractReferences]:
    """Create a messages_as_str / extract_references pair with shared numbering.

    Args:
        preprocessor: Message preprocessing options applied to every call
            (e.g., exclude_system, exclude_reasoning). Defaults to excluding
            system messages.

    Returns:
        Tuple of:
        - messages_as_str: takes list[ChatMessage], returns formatted string
          with globally unique [M1], [M2], etc.
        - extract_references: resolves citations from any prior messages_as_str call
    """
    ...
```

Usage across spans:

```python
messages_as_str, extract_references = message_numbering(
    preprocessor=MessagesPreprocessor(exclude_reasoning=True)
)

# Span 1: Explore — messages get M1..M12
explore_str = await messages_as_str(explore_messages)

# Span 2: Plan — messages continue at M13..M20
plan_str = await messages_as_str(plan_messages)

# Span 3: Build — messages continue at M21..M45
build_str = await messages_as_str(build_messages)

# Any citation from any span scan resolves correctly
refs = extract_references("See [M14] and [M35]")
```

### Changes to `messages_as_str()`

The existing `messages_as_str()` function is unchanged. The `message_numbering()` factory returns a wrapper that:
- Delegates to the same formatting logic (`message_as_str()` per message, same preprocessor support)
- Uses a closure-captured counter instead of `f"M{len(id_map) + 1}"`
- Accumulates into a closure-captured `id_map`
- Always includes IDs (that's the purpose of creating the numbering scope)

The standalone `messages_as_str(..., include_ids=True)` continues to work for non-timeline scanners.

## 2. Composable Message Extraction

### Data Model Context

A `TimelineSpan.content` is a list of `TimelineEvent | TimelineSpan`. Each `TimelineEvent` wraps an `Event` — which may be a `ModelEvent`, `ToolEvent`, `CompactionEvent`, etc.

A `ModelEvent` contains:
- `input: list[ChatMessage]` — the full conversation history at that point
- `output.choices[0].message: ChatMessageAssistant` — the model's response

For scanning, we need to extract the "conversation" from events. The natural representation is the **last `ModelEvent`'s input + output** — this captures the complete conversation the agent had. But compaction boundaries complicate this: a `CompactionEvent` means the context was compressed, so messages before and after compaction represent different conversational states.

### Architecture

The message extraction pipeline is composed of four layers, each independently useful:

1. **`messages_by_compaction()`** — splits events into message lists at compaction boundaries
2. **`chunked_messages()`** — renders and chunks message lists to fit a context window
3. **`timeline_messages()`** — walks a timeline tree, delegates to `chunked_messages()` per span
4. **`transcript_messages()`** — adaptive dispatch based on available transcript data

### File Locations

| Component | Module |
|-----------|--------|
| `messages_by_compaction()`, `chunked_messages()`, `transcript_messages()`, `RenderedMessages` | `_transcript/messages.py` (new) |
| `timeline_messages()`, `TimelineMessages` | `_transcript/timeline.py` (existing) |
| `message_numbering()`, `MessagesAsStr` | `_scanner/extract.py` (existing) |
| `parse_answer()`, `generate_for_answer()`, `generate_answer()` | `_llm_scanner/generate.py` (new) |

### Event Extraction from Spans

`timeline_messages()` needs to extract a flat `list[Event]` from a `TimelineSpan` to pass to `chunked_messages()`. A span's `content` is `list[TimelineContentItem]` where `TimelineContentItem = TimelineEvent | TimelineSpan`. To get the span's direct events:

```python
events = [item.event for item in span.content if isinstance(item, TimelineEvent)]
```

Only direct events are extracted — child `TimelineSpan`s are visited recursively by the tree walk, not flattened into the parent's event list.

### Layer 1: Compaction Splitting

A pure function that extracts message lists from events, splitting at compaction boundaries:

```python
def messages_by_compaction(events: list[Event]) -> list[list[ChatMessage]]:
    """Split events into message lists at compaction boundaries.

    Filters for ModelEvent and CompactionEvent, then splits based on
    compaction type:
    - Summary: full split — each segment uses its last ModelEvent's
      input + output
    - Trim: prefix split — yields trimmed prefix (dropped messages)
      as a separate segment, followed by the post-compaction segment
    - Edit: ignored — no split

    Args:
        events: Events to process (non-Model/Compaction events are
            ignored).

    Returns:
        List of message lists, one per segment. Empty segments
        (no ModelEvents before a compaction boundary, or empty trim
        prefix) are omitted.
    """
    ...
```

#### Compaction Splitting Strategy

`CompactionEvent` has a `type` field distinguishing the compaction strategy:

| Compaction Type | Split? | Rationale |
|-----------------|--------|-----------|
| **Summary** | Yes — full split | Original messages replaced by a summary — content is lost. Pre-compaction must be scanned separately. |
| **Edit** | No | Same messages survive with reasoning/tool calls stripped. No content loss, no duplication. |
| **Trim** | Yes — prefix only | Later messages are preserved unchanged, so a full split would create duplication. Instead, yield only the **trimmed prefix** (messages dropped from the beginning) as a separate segment. |

#### Message Extraction per Segment

For each segment between compaction boundaries:

1. Collect `ModelEvent`s and `CompactionEvent`s from the input (ignoring other event types)
2. Split at compaction boundaries by type (summary, trim; edit ignored)
3. For each segment, take the **last `ModelEvent`** — its `input + [output.choices[0].message]` is the conversation for that segment

```
Events:  [Model₁, Model₂, CompactionSummary, Model₃, Model₄]
          └──── segment 0 ────┘                └── segment 1 ──┘
                 ↓                                    ↓
          Model₂.input + output               Model₄.input + output
```

Trim compaction yields a prefix-only segment:

```
Events:  [Model₁, Model₂, CompactionTrim, Model₃, Model₄]

  Model₂.input = [A, B, C, D, E, F, G, H]        (pre-trim, full conversation)
  Model₄.input =             [D, E, F, G, H, I]   (post-trim, trimmed conversation)

  segment 0: [A, B, C]                             (trimmed prefix only)
  segment 1: Model₄.input + output                 (post-trim conversation)
```

#### Trim Prefix Extraction

Trim drops messages from the beginning of the conversation. The post-compaction `ModelEvent.input` is a strict suffix of the pre-compaction input. We compute the trimmed prefix to avoid scanning duplicate messages:

```
Pre-compaction input:   [A, B, C, D, E, F, G, H]
Post-compaction input:              [D, E, F, G, H, I, J]
                         └─────┘
                         trimmed prefix → segment 0 (messages lost by trim)
                                    └──────────────┘
                                    post-compaction → segment 1 (no duplication)
```

The prefix is computed by finding the first message in the post-compaction input within the pre-compaction input. Messages use their `id` field for matching when available; when IDs are absent, fall back to index-based alignment (find the longest common suffix of pre-compaction that matches the prefix of post-compaction by content equality). All pre-compaction messages before the match point form the trimmed prefix segment.

If the prefix is empty (trim removed no messages, or the inputs can't be aligned), no prefix segment is yielded.

### Layer 2: Chunked Messages

An async generator that renders and chunks messages to fit a context window. Accepts either a plain message list or a list of events (in which case it delegates to `messages_by_compaction()` internally):

```python
async def chunked_messages(
    source: list[ChatMessage] | list[Event],
    *,
    messages_as_str: MessagesAsStr,
    model: Model,
    context_window: int | None = None,
) -> AsyncIterator[RenderedMessages]:
    """Render and chunk messages to fit a model's context window.

    When given a list of events, delegates to messages_by_compaction()
    to handle compaction boundaries before chunking. When given a
    plain message list, treats it as a single segment.

    Each yielded item includes the pre-rendered text (via messages_as_str)
    for direct use in scanning.

    Args:
        source: Either a list of ChatMessages (single segment) or a
            list of Events (split at compaction boundaries, then chunked).
        messages_as_str: Rendering function from message_numbering() that
            formats messages with globally unique IDs.
        model: The model used for scanning. Provides count_tokens() for
            measuring rendered text, and max_tokens() for default context
            window lookup.
        context_window: Override for the model's context window size
            (in tokens). When None, looked up via get_model_info().
            An 80% discount factor is applied to leave room for system
            prompts and scanning overhead.

    Yields:
        RenderedMessages for each segment/chunk. Empty segments are
        skipped.
    """
    ...
```

#### `RenderedMessages` Type

```python
@dataclass(frozen=True)
class RenderedMessages:
    """A chunk of messages, pre-rendered and sized to fit a context window."""
    messages: list[ChatMessage]
    text: str              # pre-rendered string from messages_as_str
    segment: int           # 0-based segment index
```

Segments result from either compaction boundaries (when given events) or context window chunking — `RenderedMessages` does not distinguish the cause. The `segment` index is 0-based and auto-increments across yields. No total count is tracked — async generators yield lazily and the total isn't known upfront.

#### Budget Calculation

```python
from inspect_ai.model._model_info import get_model_info

DEFAULT_CONTEXT_WINDOW = 128_000

if context_window is not None:
    budget_base = context_window
else:
    info = get_model_info(model)
    budget_base = (info.input_tokens() if info else None) or DEFAULT_CONTEXT_WINDOW

effective_budget = int(budget_base * 0.8)
```

Context window lookup uses `get_model_info(model).input_tokens()` — the same approach used by `inspect_ai`'s compaction system. The 80% discount factor reserves headroom for system prompts, scanning instructions, and other overhead that the scanning LLM needs alongside the conversation text.

#### Chunking Algorithm

When a segment's messages might exceed the budget, we find chunk boundaries first using `model.count_tokens()` on the raw messages, then render each chunk via `messages_as_str()`:

1. Use `model.count_tokens(messages)` (which accepts `list[ChatMessage]`) to estimate the full segment's token count
2. If within budget, render the entire segment as one chunk via `messages_as_str()`
3. If over budget, find chunk boundaries by counting tokens on progressively larger prefixes of messages
4. Render each chunk via `messages_as_str()` — the `message_numbering()` counter auto-increments across calls, so numbering is continuous

```
Segment messages: [A, B, C, D, E, F, G, H]   (too large for context window)

  chunk 0: messages_as_str([A, B, C]) → M1..M3, fits in budget
  chunk 1: messages_as_str([D, E, F]) → M4..M6, fits in budget
  chunk 2: messages_as_str([G, H])    → M7..M8, fits in budget
```

Note: token counting on raw messages is an approximation (the rendered format adds IDs and formatting), but this is acceptable since the 80% discount factor provides ample headroom. The rendered text will always be somewhat larger than raw messages, but well within the 20% margin.

#### Interaction with Compaction Splitting

When given events, compaction splitting happens first, then each resulting segment is independently checked against the context window budget. Events with one summary compaction and one oversized post-compaction segment might yield:

```
segment 0: pre-compaction messages              (fits → 1 chunk)
segment 1a: post-compaction chunk 1             (oversized → split)
segment 1b: post-compaction chunk 2
```

Total: 3 segments numbered 0, 1, 2. The chunking is transparent — callers see a flat sequence of segments.

#### Standalone Usage

```python
messages_as_str, extract_references = message_numbering(
    preprocessor=MessagesPreprocessor(exclude_reasoning=True)
)

# With plain messages (no compaction)
async for chunk in chunked_messages(
    my_messages,
    messages_as_str=messages_as_str,
    model=model,
):
    # chunk.text is pre-rendered, fits in context window
    result = await scan_with_llm(chunk.text)

# With events (compaction handled automatically)
async for chunk in chunked_messages(
    transcript.events,
    messages_as_str=messages_as_str,
    model=model,
):
    result = await scan_with_llm(chunk.text)
```

### Layer 3: Timeline Messages

A high-level async generator that walks a timeline tree, extracts events per span, and delegates to `chunked_messages()`:

```python
async def timeline_messages(
    timeline: Timeline | TimelineSpan,
    *,
    messages_as_str: MessagesAsStr,
    model: Model,
    context_window: int | None = None,
    include: Callable[[TimelineSpan], bool] | str | None = None,
) -> AsyncIterator[TimelineMessages]:
    """Yield pre-rendered message segments from timeline spans.

    Walks the span tree, extracts events from each matching span,
    and delegates to chunked_messages() for compaction splitting and
    context window chunking. Each yielded item includes the span
    context alongside the pre-rendered text.

    Args:
        timeline: The timeline (or a specific span subtree) to extract
            messages from. If a Timeline, starts from timeline.root.
        messages_as_str: Rendering function from message_numbering() that
            formats messages with globally unique IDs.
        model: The model used for scanning. Provides count_tokens() for
            measuring rendered text, and max_tokens() for default context
            window lookup.
        context_window: Override for the model's context window size
            (in tokens). When None, looked up via get_model_info().
            An 80% discount factor is applied to leave room for system
            prompts and scanning overhead.
        include: Filter for which spans to process.
            - None: all non-utility spans with direct ModelEvents (default)
            - str: only spans whose name matches (case-insensitive)
            - callable: predicate on TimelineSpan

    Yields:
        TimelineMessages for each segment. Empty spans are skipped.
    """
    ...
```

#### `TimelineMessages` Type

Extends `RenderedMessages` with span context:

```python
@dataclass(frozen=True)
class TimelineMessages(RenderedMessages):
    """A chunk of messages from a specific timeline span."""
    span: TimelineSpan
```

Since `TimelineMessages` inherits from `RenderedMessages`, it can be used anywhere a `RenderedMessages` is expected. `timeline_messages()` constructs these from the `RenderedMessages` yielded by `chunked_messages()`, adding the span context for each.

#### Filtering

The `include` parameter controls which spans yield messages:

- **`None` (default)**: all non-utility spans that have at least one `ModelEvent` in their direct `content` (not inherited from child spans). A span that contains only child `TimelineSpan`s and no `ModelEvent`s of its own is a pure container and yields nothing — its children are visited instead.
- **`str`**: only spans whose name matches (case-insensitive) — e.g., `include="Build"` processes only spans named "Build"
- **`callable`**: arbitrary predicate — e.g., `include=lambda s: s.span_type == "agent"`

The generator walks the tree recursively. Non-matching spans are skipped but their children are still visited — the filter controls *which spans yield messages*, not *which subtrees are traversed*.

#### Usage

```python
messages_as_str, extract_references = message_numbering(
    preprocessor=MessagesPreprocessor(exclude_reasoning=True)
)

segments: list[TimelineMessages] = []

async for span_msgs in timeline_messages(
    timeline,
    messages_as_str=messages_as_str,
    model=model,
    include="Build",
):
    # span_msgs.text is already pre-rendered with unique message IDs
    segments.append(span_msgs)

# Each segment's .text is ready for the scanning LLM
# All references resolve across all segments
refs = extract_references(llm_output)
```

### Layer 4: Transcript Messages

A convenience generator that encapsulates the "do the right thing" logic for scanning a `Transcript`. It checks what data is available and delegates to the appropriate lower layer:

```python
async def transcript_messages(
    transcript: Transcript,
    *,
    messages_as_str: MessagesAsStr,
    model: Model,
    context_window: int | None = None,
) -> AsyncIterator[RenderedMessages]:
    """Yield pre-rendered message segments from a transcript.

    Automatically selects the best extraction strategy based on
    what data is available on the transcript:
    - If timelines are present, delegates to timeline_messages()
    - If events are present (no timelines), delegates to
      chunked_messages() with compaction handling
    - If only messages are present, delegates to chunked_messages()
      for context window chunking only

    Since TimelineMessages inherits from RenderedMessages, callers
    get a uniform interface. Those needing span context can
    isinstance-check for TimelineMessages.

    Args:
        transcript: The transcript to extract messages from.
        messages_as_str: Rendering function from message_numbering().
        model: The model used for scanning.
        context_window: Override for the model's context window size.

    Yields:
        RenderedMessages (or TimelineMessages subclass) for each
        segment.
    """
    ...
```

#### Implementation

```python
async def transcript_messages(
    transcript: Transcript,
    *,
    messages_as_str: MessagesAsStr,
    model: Model,
    context_window: int | None = None,
) -> AsyncIterator[RenderedMessages]:
    if transcript.timelines:
        async for seg in timeline_messages(
            transcript.timelines[0],
            messages_as_str=messages_as_str,
            model=model,
            context_window=context_window,
        ):
            yield seg
    elif transcript.events:
        async for chunk in chunked_messages(
            transcript.events,
            messages_as_str=messages_as_str,
            model=model,
            context_window=context_window,
        ):
            yield chunk
    else:
        async for chunk in chunked_messages(
            transcript.messages,
            messages_as_str=messages_as_str,
            model=model,
            context_window=context_window,
        ):
            yield chunk
```

#### Full Architecture Summary

The four layers compose into a clean pipeline:

| Layer | Function | Input | Output |
|-------|----------|-------|--------|
| 1 | `messages_by_compaction()` | `list[Event]` | `list[list[ChatMessage]]` |
| 2 | `chunked_messages()` | `list[ChatMessage] \| list[Event]` | `RenderedMessages` |
| 3 | `timeline_messages()` | `Timeline \| TimelineSpan` | `TimelineMessages` |
| 4 | `transcript_messages()` | `Transcript` | `RenderedMessages` |

Each layer is independently useful. Most callers will use Layer 4 (`transcript_messages`). Custom pipelines can drop to lower layers for finer control.

## 3. Reusable Answer Generation and Parsing

The current `llm_scanner` mixes two concerns: LLM generation (with refusal retry) and answer parsing (extracting a `Result` from model output). These should be independently reusable for custom scanning pipelines.

### Current State

The generation and parsing logic lives inline in `llm_scanner`'s scan function:

- **Normal answers** (boolean, numeric, string, labels): `generate_retry_refusals()` → `resolved_answer.result_for_answer(output, extract_references, value_to_float)`
- **Structured answers** (`AnswerStructured`): `structured_generate()` with tool-based extraction → `structured_result()` for parsing

The `Answer` protocol (`_llm_scanner/answer.py`) already provides a clean interface for parsing via `result_for_answer()`, but there's no standalone function to drive generation + parsing without going through `llm_scanner`.

### Proposed API

Three functions at increasing levels of convenience:

#### `parse_answer()` — parsing only

Extracts a `Result` from a `ModelOutput` using the answer specification. For users who have their own generation logic and just want answer extraction:

```python
def parse_answer(
    output: ModelOutput,
    answer: Answer,
    extract_references: Callable[[str], list[Reference]],
    value_to_float: ValueToFloat | None = None,
) -> Result:
    """Parse a model output into a Result using the answer specification.

    Delegates to the Answer's result_for_answer() method, handling the
    structured answer null-value case.

    Args:
        output: The model's response to parse.
        answer: Answer specification controlling parsing (boolean,
            numeric, string, labels, or structured).
        extract_references: Function to extract [M1]-style references
            from the explanation text.
        value_to_float: Optional function to convert the parsed value
            to a float.

    Returns:
        A Result with value, answer, explanation, and references.
    """
    ...
```

#### `generate_for_answer()` — generation only

Sends a prompt to an LLM using the appropriate strategy (normal or structured), with refusal retry. For users who want our generation logic but custom result handling:

```python
async def generate_for_answer(
    prompt: str | list[ChatMessage],
    answer: Answer,
    model: str | Model | None = None,
    retry_refusals: int = 3,
) -> ModelOutput:
    """Generate a model response appropriate for the answer type.

    For structured answers, uses tool-based extraction with multiple
    attempts. For all other types, uses standard generation with
    refusal retry.

    Args:
        prompt: The scanning prompt (string or message list).
        answer: Answer specification — determines whether to use
            structured (tool-based) or standard generation.
        model: Model to use for generation.
        retry_refusals: Number of times to retry on model refusals.

    Returns:
        The model's output, ready for parsing via parse_answer().
    """
    ...
```

#### `generate_answer()` — generation + parsing

Convenience function combining both steps:

```python
async def generate_answer(
    prompt: str | list[ChatMessage],
    answer: Answer,
    extract_references: Callable[[str], list[Reference]],
    model: str | Model | None = None,
    value_to_float: ValueToFloat | None = None,
    retry_refusals: int = 3,
) -> Result:
    """Generate a model response and parse it into a Result.

    Combines generate_for_answer() and parse_answer() into a single
    call. This is the typical entry point for custom scanning pipelines.

    Args:
        prompt: The scanning prompt (string or message list).
        answer: Answer specification controlling both generation
            strategy and parsing.
        extract_references: Function to extract [M1]-style references.
        model: Model to use for generation.
        value_to_float: Optional function to convert the parsed value.
        retry_refusals: Number of times to retry on model refusals.

    Returns:
        A Result with value, answer, explanation, and references.
    """
    output = await generate_for_answer(prompt, answer, model, retry_refusals)
    return parse_answer(output, answer, extract_references, value_to_float)
```

### Usage

Custom scanning pipeline using the layered API:

```python
messages_as_str_fn, extract_references = message_numbering(
    preprocessor=MessagesPreprocessor(exclude_reasoning=True)
)

answer = answer_from_argument("boolean")

async for chunk in chunked_messages(
    my_messages,
    messages_as_str=messages_as_str_fn,
    model=model,
):
    prompt = f"Here is a conversation:\n{chunk.text}\n\nDid the agent refuse?"

    # Option 1: one-step
    result = await generate_answer(prompt, answer, extract_references, model=model)

    # Option 2: custom generation, standard parsing
    output = await my_custom_generate(prompt)
    result = parse_answer(output, answer, extract_references)
```

### Location

These functions should live in `_llm_scanner/` (alongside the existing `answer.py` and `structured.py`) and be publicly exported. The `Answer` protocol and `answer_from_argument()` factory should also be publicly exported so users can construct answer specs.

## 4. Refactoring `llm_scanner`

This section stress-tests the design by showing how `llm_scanner` (`_llm_scanner/_llm_scanner.py`) would be refactored to use the new infrastructure from Sections 1–3.

### Current Implementation

`llm_scanner` is decorated with `@scanner(messages="all")` and returns `Scanner[Transcript]`. Its scan flow:

1. Call `messages_as_str(transcript, preprocessor=preprocessor, include_ids=True)` → rendered string + `extract_references`
2. Render the prompt template with `{{ messages }}` set to the rendered string
3. Send prompt to LLM, parse response:
   - `AnswerStructured` → `structured_generate()` with tool-based extraction
   - All other answer types → `generate_retry_refusals()` with text parsing
4. Return a single `Result` with references resolved via `extract_references`

Limitations:
- **No context window awareness** — the full message string is injected regardless of size; if it exceeds the model's context window, the call fails
- **No timeline support** — messages are a flat list with no span structure

### New Parameters

Two new parameters on `llm_scanner`:

**`content: TranscriptContent | None`** — controls what data the scanner requests from the framework. `TranscriptContent` (`_transcript/types.py`) is an existing internal dataclass that should be publicly exported with docstrings:

```python
@dataclass
class TranscriptContent:
    """Content filter controlling what data is loaded onto a Transcript.

    Controls which messages, events, and timeline data the scanner
    framework loads. Fields set to None are not loaded; set to "all"
    to load all of that type.

    Args:
        messages: Message types to load (e.g., ["user", "assistant"],
            "all", or None).
        events: Event types to load (e.g., ["model", "tool"], "all",
            or None).
        timeline: Timeline configuration. True or "all" builds a
            timeline from all events; a list of event types builds
            a filtered timeline.
    """
    messages: MessageFilter = field(default=None)
    events: EventFilter = field(default=None)
    timeline: TimelineFilter = field(default=None)
```

When provided, `content` overrides the decorator's content filter. `llm_scanner` sets this on the inner scan function via a `SCANNER_CONTENT_ATTR` attribute — the same pattern used by `SCANNER_NAME_ATTR` for the `name` parameter. The `@scanner()` decorator reads this attribute at factory call time and merges it with its own filters before building `ScannerConfig`:

```python
# In llm_scanner, after creating the scan function:
if content is not None:
    setattr(scan, SCANNER_CONTENT_ATTR, content)
```

```python
# In the @scanner() decorator, when building ScannerConfig:
# After computing inferred_messages/events/timeline from decorator args...
if hasattr(scanner_fn, SCANNER_CONTENT_ATTR):
    override = getattr(scanner_fn, SCANNER_CONTENT_ATTR)
    if override.messages is not None:
        inferred_messages = override.messages
    if override.events is not None:
        inferred_events = override.events
    if override.timeline is not None:
        inferred_timeline = override.timeline
```

Fields set on the override take precedence; fields left as `None` fall through to the decorator's values. So `content=TranscriptContent(timeline=True)` adds timeline support while the decorator's `messages="all"` remains active.

**`context_window: int | None`** — override for the model's context window size, passed through to `transcript_messages()`.

### Adaptive Detection

`llm_scanner` keeps its existing decorator — `@scanner(messages="all")` — as the base config. The `content` parameter extends it at factory call time via `SCANNER_CONTENT_ATTR`. At scan time, `transcript_messages()` (Layer 4) handles the adaptive detection — it checks `transcript.timelines`, then `transcript.events`, then falls back to `transcript.messages`.

This is fully backward compatible — direct use without `content` behaves exactly as today, now with context window protection.

### Refactored Implementation

```python
@scanner(messages="all")
def llm_scanner(
    *,
    question: str | Callable[[Transcript], Awaitable[str]] | None = None,
    answer: Literal["boolean", "numeric", "string"]
    | list[str]
    | AnswerMultiLabel
    | AnswerStructured,
    value_to_float: ValueToFloat | None = None,
    template: str | None = None,
    template_variables: dict[str, Any]
    | Callable[[Transcript], dict[str, Any]]
    | None = None,
    preprocessor: MessagesPreprocessor[Transcript] | None = None,
    model: str | Model | None = None,
    content: TranscriptContent | None = None,
    context_window: int | None = None,
    retry_refusals: bool | int = 3,
    name: str | None = None,
) -> Scanner[Transcript]:
    if template is None:
        template = DEFAULT_SCANNER_TEMPLATE
    resolved_answer = answer_from_argument(answer)
    retry_refusals = (
        retry_refusals if isinstance(retry_refusals, int)
        else 3 if retry_refusals is True
        else 0
    )

    # Serialize Model instances for cloudpickle roundtrips
    serializable_model: str | ModelConfig | None
    if isinstance(model, Model):
        serializable_model = model_to_model_config(model)
    else:
        serializable_model = model

    async def scan(transcript: Transcript) -> Result | list[Result]:
        resolved_model: str | Model | None = (
            model_config_to_model(serializable_model)
            if isinstance(serializable_model, ModelConfig)
            else serializable_model
        )
        model_instance = get_model(resolved_model)

        # Shared numbering scope — globally unique message IDs,
        # extract_references resolves across all segments
        messages_as_str_fn, extract_references = message_numbering(
            preprocessor=preprocessor,
        )

        # Scan each segment — transcript_messages() handles
        # timelines, events, or plain messages automatically
        results: list[Result] = []
        async for segment in transcript_messages(
            transcript,
            messages_as_str=messages_as_str_fn,
            model=model_instance,
            context_window=context_window,
        ):
            prompt = await render_scanner_prompt(
                template=template,
                template_variables=template_variables,
                transcript=transcript,
                messages=segment.text,
                question=question,
                answer=resolved_answer,
            )

            result = await generate_answer(
                prompt,
                resolved_answer,
                extract_references,
                model=resolved_model,
                value_to_float=value_to_float,
                retry_refusals=retry_refusals,
            )
            results.append(result)

        # Single segment → single Result (backward compatible)
        return results[0] if len(results) == 1 else results

    if content is not None:
        setattr(scan, SCANNER_CONTENT_ATTR, content)
    if name is not None:
        setattr(scan, SCANNER_NAME_ATTR, name)
    return scan
```

### What Changes, What Doesn't

| Aspect | Before | After |
|--------|--------|-------|
| Decorator | `@scanner(messages="all")` | unchanged |
| New params | — | `content`, `context_window` |
| Return type | `Result` | `Result \| list[Result]` (single segment still returns `Result`) |
| Message extraction | `messages_as_str(transcript, ...)` | `transcript_messages()` + `message_numbering()` |
| Context window | no protection | 80% budget, auto-chunked |
| Timeline support | none | opt-in via `content=TranscriptContent(timeline=True)` |
| Compaction handling | none | auto via `transcript_messages()` |
| Prompt template | unchanged | works as-is per segment |
| `extract_references` | scoped to one call | shared across all segments |
| Generation + parsing | inline if/else | `generate_answer()` from Section 3 |

### Usage Examples

Direct use with timeline support:

```python
my_scanner = llm_scanner(
    question="Did the agent follow a clear plan?",
    answer="boolean",
    content=TranscriptContent(timeline=True),
)
```

Direct use with context window override:

```python
my_scanner = llm_scanner(
    question="Summarize the key decisions.",
    answer="string",
    context_window=50000,
)
```

Delegation from a parent scanner (parent's decorator controls loading):

```python
@scanner(timeline=True)
def quality_scanner(*, model: str | None = None) -> Scanner[Transcript]:
    return llm_scanner(
        question="Did the agent follow a clear plan?",
        answer="boolean",
        model=model,
    )
```

### Preprocessor Compatibility

The current `llm_scanner` uses `MessagesPreprocessor[Transcript]` — a preprocessor that can accept a full `Transcript` for transforms that need transcript context. The `message_numbering()` preprocessor operates on `list[ChatMessage]`.

Standard preprocessors (`exclude_system`, `exclude_reasoning`) only need the message list, so they work unchanged. Custom transforms that access `Transcript` metadata would need adaptation — transcript-level transforms can be applied before messages enter the pipeline.

### Public Exports

`TranscriptContent` needs to be publicly exported (currently internal) with the docstrings shown above. The filter type aliases (`MessageFilter`, `EventFilter`, `TimelineFilter`) should also be exported for users constructing `TranscriptContent` instances.

## 5. Parallel Generation (Speculative)

### Motivation

The refactored `llm_scanner` scan loop is sequential:

```python
async for segment in transcript_messages(...):
    prompt = await render_scanner_prompt(...)
    result = await generate_answer(...)      # seconds per call
    results.append(result)
```

For a timeline with 5 spans, each with 2 context window chunks, this means 10 sequential LLM calls. At ~3 seconds each, that's 30 seconds. With parallel generation (bounded to, say, 4 concurrent), the same work completes in ~9 seconds.

### Why Streaming (Not Collect-Then-Parallelize)

Both phases of the pipeline involve remote API calls:

1. **Rendering** — `chunked_messages()` calls `model.count_tokens()` per segment to check budget and find chunk boundaries. Each call hits the LLM provider's token counting API.
2. **Generation** — `generate_answer()` makes LLM generation API calls, each taking seconds.

A naive "collect all segments, then parallelize generation" approach serializes all the token counting before any generation begins. With streaming, generation on segment 0 can start while `transcript_messages()` is still doing `count_tokens()` calls to render segments 1, 2, 3. The overlap between production (token counting) and consumption (generation) provides real throughput gains.

Note: rendering must remain sequential — `message_numbering()` has a monotonic counter, so segments must be produced in order. But once a segment is yielded, its generation is independent.

### Proposed Approach: anyio Memory Streams

anyio memory streams provide a clean producer-consumer pattern with backpressure:

```
transcript_messages() ──[send]──▷ [buffer] ──[receive]──▷ worker 1 → generate_answer()
                                             ──[receive]──▷ worker 2 → generate_answer()
                                             ──[receive]──▷ worker N → generate_answer()
```

```python
import anyio
from anyio.streams.memory import MemoryObjectSendStream, MemoryObjectReceiveStream


async def parallel_scan(
    segments: AsyncIterator[RenderedMessages],
    generate_fn: Callable[[RenderedMessages], Awaitable[Result]],
    model: Model,
) -> list[Result]:
    """Stream segments into parallel generation workers.

    The producer (segments iterator) runs sequentially — it must, because
    message numbering requires ordered rendering. Workers consume segments
    as they arrive and generate in parallel. Results are reassembled in
    segment order.

    Concurrency is derived from the model's max_connections, which is
    already configured by the scan infrastructure to match the provider's
    rate limits.

    Args:
        segments: Async iterator of pre-rendered segments (e.g., from
            transcript_messages()).
        generate_fn: Async function that generates a Result from a
            rendered segment.
        model: Model instance — its max_connections determines worker
            count and buffer size.

    Returns:
        Results in segment order.
    """
    max_concurrency = model.config.max_connections or model.api.max_connections()
    results: dict[int, Result] = {}

    send_stream, receive_stream = anyio.create_memory_object_stream[
        RenderedMessages
    ](max_buffer_size=max_concurrency)

    async def producer() -> None:
        async with send_stream:
            async for segment in segments:
                await send_stream.send(segment)

    async def worker(rx: MemoryObjectReceiveStream[RenderedMessages]) -> None:
        async for segment in rx:
            results[segment.segment] = await generate_fn(segment)

    async with anyio.create_task_group() as tg:
        tg.start_soon(producer)
        # Clone the receive stream for each worker; close original
        for _ in range(max_concurrency):
            tg.start_soon(worker, receive_stream.clone())
        receive_stream.close()

    return [results[i] for i in sorted(results)]
```

### Usage in `llm_scanner`

```python
async def scan(transcript: Transcript) -> Result | list[Result]:
    model_instance = get_model(resolved_model)
    messages_as_str_fn, extract_references = message_numbering(
        preprocessor=preprocessor,
    )

    async def generate_one(segment: RenderedMessages) -> Result:
        prompt = await render_scanner_prompt(
            template=template,
            template_variables=template_variables,
            transcript=transcript,
            messages=segment.text,
            question=question,
            answer=resolved_answer,
        )
        return await generate_answer(
            prompt,
            resolved_answer,
            extract_references,
            model=resolved_model,
            value_to_float=value_to_float,
            retry_refusals=retry_refusals,
        )

    results = await parallel_scan(
        transcript_messages(
            transcript,
            messages_as_str=messages_as_str_fn,
            model=model_instance,
            context_window=context_window,
        ),
        generate_one,
        model=model_instance,
    )

    return results[0] if len(results) == 1 else results
```

### Concurrency Considerations

- **Derived from model**: Worker count and buffer size come from `model.config.max_connections or model.api.max_connections()`. The scan infrastructure already sets `max_connections` on the model's `GenerateConfig` (defaulting to `max_transcripts`, typically 25), so this aligns with the provider's actual rate limits without a magic number.
- **Double-layered throttling**: The model's internal connection semaphore (`_connection_concurrency`) provides API-level rate limiting. Our worker count bounds task creation — preventing excessive coroutines waiting on that semaphore. Both layers work together: workers bound the fan-out, the semaphore bounds actual API calls.
- **Cross-transcript sharing**: In a full scan, multiple transcript scans run concurrently, all sharing the same model connection pool. Each transcript's `parallel_scan` creates up to `max_connections` workers, but they all compete for the same semaphore. The model's backpressure naturally distributes throughput across transcripts.
- **Backpressure**: `max_buffer_size=max_concurrency` means the producer blocks when all workers are busy. This prevents unbounded memory growth if rendering is faster than generation (which it always is, except when `count_tokens()` calls queue behind busy connections).
- **Single segment fast path**: When there's only one segment (common case for short conversations), the stream pattern degenerates to a single send/receive with negligible overhead.
- **Error handling**: `anyio.TaskGroup` propagates the first exception and cancels remaining tasks — the right behavior when one generation fails, since we can't produce a complete result set.
- **Ordering**: Results are keyed by `segment.segment` (the 0-based index) and reassembled in order at the end, regardless of completion order.

## 6. Implementation Phases

### Working Guidelines

1. **One phase at a time.** Implement, test, and verify each phase before moving to the next.
2. **Review before commit.** After tests pass, pause and review the code together before committing. Do not auto-commit.
3. **Full tests at each step.** Every phase produces both an implementation file and a test file.
4. **Use synthetic scenarios.** Build minimal inline test helpers (e.g., `make_model_event()`, `make_compaction_event()`) using direct `inspect_ai` constructors. Reuse the existing `_parse_input_messages()` pattern from `tests/transcript/nodes/test_timeline.py`. Use the shared JSON fixtures in `tests/transcript/nodes/fixtures/events/` where they cover relevant scenarios (e.g., `compaction_boundary.json`).
5. **Update this document.** After completing a phase but before committing, replace the phase's overview section below with a summary of what was actually built and tested — files created/modified, key design decisions made during implementation, and test coverage.

### Phase 1: `message_numbering()` ✓ `563d43aa`

**Implements:** Section 1 (Universal Message Numbering)

**Files modified:**
- `src/inspect_scout/_scanner/extract.py` — added `message_numbering()` factory function
- `src/inspect_scout/__init__.py` — added `message_numbering` to public exports
- `tests/scanner/test_extract.py` — added 9 test cases

**What was built:**
- `message_numbering(preprocessor)` factory that returns a `(messages_as_str, extract_references)` pair with shared closure state (counter + id_map)
- The returned `messages_as_str` takes `list[ChatMessage]`, applies preprocessing, and renders with globally unique `[M1]`, `[M2]`, etc. prefixes using a monotonically incrementing counter
- The returned `extract_references` resolves `[M{n}]` citations from any prior `messages_as_str` call
- `MessagesAsStr` and `ExtractReferences` type aliases for the returned callables
- Existing `messages_as_str()` function unchanged (backward compatible)

**Test coverage:**
- Single call produces M1..Mn
- Multiple calls continue numbering (M1..M2, then M3..M5)
- `extract_references` resolves citations across all prior calls
- Empty message lists don't advance the counter
- Default excludes system messages
- Preprocessor options: `exclude_reasoning`, `exclude_tool_usage`
- Custom `transform` function
- Filtered messages don't consume numbers across calls

**Dependencies:** None — standalone.

### Phase 2: `messages_by_compaction()` ✓ `f38279f4`

**Implements:** Section 2, Layer 1 (Compaction Splitting)

**Files created:**
- `src/inspect_scout/_transcript/messages.py` — `messages_by_compaction()`, `_segment_messages()`, `_trim_prefix()`
- `tests/transcript/test_messages.py` — 11 test cases
- `src/inspect_scout/__init__.py` — added `messages_by_compaction` to public exports

**What was built:**
- `messages_by_compaction(events)` — pure function that filters for `ModelEvent` and `CompactionEvent`, splits by compaction type (summary: full split, trim: prefix-only split, edit: no split)
- Each segment's messages come from the **last** `ModelEvent` in that segment: `input + [output.choices[0].message]`
- `_trim_prefix(pre_input, post_input)` — finds overlap point via message `id` matching, falls back to content equality (`text` + `role`)
- `_segment_messages(model_event)` — extracts `input + output` with edge case handling for missing output

**Test coverage:**
- No compaction, summary, trim, edit compaction types
- Multiple compactions in sequence
- Empty segments omitted, non-model events ignored
- Trim with empty prefix (all messages survive)
- Trim prefix via id matching
- Empty event list, only compaction events

**Dependencies:** None — standalone pure function.

### Phase 3: `chunked_messages()` + `MessagesChunk` ✓ 8b2a3a22

**Implements:** Section 2, Layer 2 (Chunked Messages)

**Files:**
- Modify: `src/inspect_scout/_transcript/messages.py`
- Modify: `tests/transcript/test_messages.py`

**What to build:**
- `RenderedMessages` dataclass (`messages`, `text`, `segment`)
- `chunked_messages(source, messages_as_str, model, context_window)` async generator
- Accepts `list[ChatMessage]` or `list[Event]` (delegates to `messages_by_compaction()` for events)
- Uses `model.count_tokens()` for budget checking, 80% discount factor
- Yields `RenderedMessages` per segment/chunk

**What to test:**
- Small message list → single `RenderedMessages` (no chunking)
- Large message list exceeding budget → multiple chunks with continuous numbering
- Events with compaction → compaction split, then chunked
- Budget calculation: 80% discount factor applied correctly
- Empty input yields nothing
- Uses a mock or stub model with controllable `count_tokens()` and context window

**Dependencies:** Phase 1 (`message_numbering`), Phase 2 (`messages_by_compaction`).

### Phase 4: `timeline_messages()` + `transcript_messages()` ✓ 3411c21f

**Implements:** Section 2, Layers 3+4 (Timeline Messages + Transcript Messages)

**Files:**
- Modify: `src/inspect_scout/_transcript/timeline.py`
- Modify: `src/inspect_scout/_transcript/messages.py`
- Modify: `tests/transcript/test_messages.py`

**What to build:**
- `TimelineMessages(RenderedMessages)` dataclass — adds `span: TimelineSpan`
- `timeline_messages(timeline, messages_as_str, model, context_window, include)` async generator
- Walks span tree, extracts `[item.event for item in span.content if isinstance(item, TimelineEvent)]`
- Delegates to `chunked_messages()` per span, wraps results as `TimelineMessages`
- `include` filter: `None` (non-utility spans with ModelEvents), `str` (name match), `callable`
- `transcript_messages(transcript, messages_as_str, model, context_window)` async generator
- Adaptive dispatch: `transcript.timelines` → `timeline_messages()`, `transcript.events` → `chunked_messages()`, else `transcript.messages` → `chunked_messages()`

**What to test:**
- Single-span timeline → yields `TimelineMessages` with correct span context
- Multi-span timeline → yields segments in tree-walk order with continuous numbering
- Nested spans → child spans visited recursively
- `include=None` skips utility spans and empty container spans
- `include="Build"` filters by name (case-insensitive)
- `include=callable` with custom predicate
- `transcript_messages` dispatches to correct layer based on available data

**Dependencies:** Phase 3 (`chunked_messages`).

### Phase 5: Answer Generation Functions ✓

**Implements:** Section 3 (Reusable Answer Generation)

**Files created:**
- `src/inspect_scout/_llm_scanner/generate.py` — `parse_answer()` and `generate_answer()`
- `tests/llm_scanner/test_generate.py` — 18 test cases

**Files modified:**
- `src/inspect_scout/_llm_scanner/types.py` — added `AnswerSpec` type alias (the answer union type, previously spelled out inline three times in `llm_scanner`)
- `src/inspect_scout/_llm_scanner/_llm_scanner.py` — uses `AnswerSpec` instead of repeating the union; cleaned up unused imports
- `src/inspect_scout/_llm_scanner/__init__.py` — re-exports new public API
- `src/inspect_scout/__init__.py` — public exports

**What was built:**

The design doc proposed three separate functions (`parse_answer`, `generate_for_answer`, `generate_answer`). The implementation simplified this to two, combining generation and optional parsing into a single overloaded `generate_answer` function:

- `parse_answer(output, answer, extract_references, value_to_float)` → `Result` — pure parsing, no LLM call. Accepts `AnswerSpec`, resolves internally via `answer_from_argument()`.

- `generate_answer(prompt, answer, *, model, retry_refusals, parse, extract_references, value_to_float)` → `Result | ModelOutput` — overloaded on `parse`:
  - `parse=True` (default): generates then parses → returns `Result`
  - `parse=False`: generation only → returns `ModelOutput`
  - Dispatches structured answers to `structured_generate()`, normal answers to `generate_retry_refusals()`
  - Handles the structured null-value case (`value=None` → `Result(value=None, answer=completion)`)
  - `extract_references` defaults to a no-op (no references), so callers who don't need references don't pass a dummy function

- `AnswerSpec` type alias in `types.py` — defines the answer union once, used by both `llm_scanner` and `generate_answer`

**Design decisions:**
- `generate_for_answer` was merged into `generate_answer` with `parse=False` instead of being a separate function — reduces API surface without losing capability
- `Answer` protocol and `answer_from_argument()` remain internal — external users construct `AnswerSpec` values directly; resolution happens inside the functions
- Parameter ordering: generation params (`model`, `retry_refusals`) before parsing params (`parse`, `extract_references`, `value_to_float`)

**Test coverage:**
- `parse_answer`: boolean yes/no, numeric integer/decimal, string text/no-pattern, labels single/invalid, references extraction, value_to_float, structured
- `generate_answer`: normal dispatch, structured dispatch, parse=False returns ModelOutput, parse=True returns Result, extract_references used/default, structured null value

**Dependencies:** None — independent of Phases 2-4.

### Phase 6: Refactor `llm_scanner`

**Implements:** Section 4 (Refactoring)

**Files:**
- Modify: `src/inspect_scout/_llm_scanner/_llm_scanner.py`
- Modify: `src/inspect_scout/_scanner/scanner.py` (for `SCANNER_CONTENT_ATTR`)
- Modify or add integration tests

**What to build:**
- Add `content: TranscriptContent | None` and `context_window: int | None` parameters
- Replace inline message extraction with `message_numbering()` + `transcript_messages()`
- Replace inline generation/parsing with `generate_answer()`
- `SCANNER_CONTENT_ATTR` support in `@scanner` decorator
- Return type: `Result | list[Result]` (single segment → `Result` for backward compat)
- Public export of `TranscriptContent` and filter type aliases

**What to test:**
- Existing `llm_scanner` tests continue to pass (backward compatibility)
- `content=TranscriptContent(timeline=True)` enables timeline scanning
- `context_window` override works
- Multi-segment transcript returns `list[Result]`
- Single-segment transcript returns `Result` (not wrapped in list)

**Dependencies:** All prior phases (1-5).

### Phase 7: Parallel Generation

**Implements:** Section 5 (Parallel Generation)

**Files:**
- Modify: `src/inspect_scout/_llm_scanner/_llm_scanner.py` (or new utility module)
- Modify: tests for `llm_scanner`

**What to build:**
- `parallel_scan(segments, generate_fn, model)` using anyio memory streams
- Producer: sequential `transcript_messages()` iterator (numbering must stay ordered)
- Workers: `max_concurrency` parallel consumers calling `generate_answer()`
- Concurrency derived from `model.config.max_connections` or `model.api.max_connections()`
- Results reassembled in segment order via `segment.segment` index
- Backpressure via `max_buffer_size=max_concurrency`

**What to test:**
- Single segment → degenerates to single send/receive (no overhead)
- Multiple segments → results returned in order regardless of completion order
- Worker count matches model's `max_connections`
- Error in one generation cancels remaining tasks (anyio TaskGroup behavior)
- Backpressure: producer blocks when buffer is full

**Dependencies:** Phase 6 (`llm_scanner` refactor).
