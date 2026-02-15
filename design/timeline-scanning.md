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
# Type of the returned messages_as_str function
MessagesAsStrFn = Callable[[list[ChatMessage]], Awaitable[str]]

def message_numbering(
    preprocessor: MessagesPreprocessor | None = None,
) -> tuple[
    MessagesAsStrFn,
    Callable[[str], list[Reference]]
]:
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

## 2. Extracting Messages from Timeline Spans

### Context

A `TimelineSpan.content` is a list of `TimelineEvent | TimelineSpan`. Each `TimelineEvent` wraps an `Event` — which may be a `ModelEvent`, `ToolEvent`, `CompactionEvent`, etc.

A `ModelEvent` contains:
- `input: list[ChatMessage]` — the full conversation history at that point
- `output.choices[0].message: ChatMessageAssistant` — the model's response

For scanning, we need to extract the "conversation" from each span. The natural representation is the **last `ModelEvent`'s input + output** — this captures the complete conversation the agent had. But compaction boundaries complicate this: a `CompactionEvent` means the context was compressed, so messages before and after compaction represent different conversational states.

### Generator Design

A generator function walks the timeline tree, applies filtering, handles compaction splitting, and yields message lists ready for `messages_as_str()`:

```python
async def timeline_messages(
    timeline: Timeline | TimelineSpan,
    *,
    include: Callable[[TimelineSpan], bool] | str | None = None,
) -> AsyncIterator[TimelineMessages]:
    """Yield message lists from timeline spans for scanning.

    Walks the span tree, extracts messages from each matching span,
    and splits at summary compaction boundaries. Trim compaction yields
    a prefix-only segment for the dropped messages.

    Args:
        timeline: The timeline (or a specific span subtree) to extract
            messages from. If a Timeline, starts from timeline.root.
        include: Filter for which spans to process.
            - None: all non-utility spans with direct ModelEvents (default)
            - str: only spans whose name matches (case-insensitive)
            - callable: predicate on TimelineSpan

    Yields:
        TimelineMessages for each segment. Empty segments (no ModelEvents
        before a compaction boundary, or empty trim prefix) are skipped.
    """
    ...
```

### `TimelineMessages` Type

Each yielded item pairs a message list with its source span context:

```python
@dataclass(frozen=True)
class TimelineMessages:
    """Messages extracted from a single span segment."""
    span: TimelineSpan
    messages: list[ChatMessage]
    segment: int           # 0-based segment index within the span
    segment_count: int     # total segments (1 if no compaction splits)
```

`segment` / `segment_count` distinguish compaction-split segments:

- **No compaction** (or edit-only): one `TimelineMessages` with `segment=0, segment_count=1`. Messages are the last `ModelEvent`'s `input + output`.
- **Summary compaction**: `N+1` segments for `N` summary compaction events. Each segment's messages are the last `ModelEvent`'s `input + output` within that segment boundary.
- **Trim compaction**: yields a **prefix segment** containing only the messages dropped by trim, followed by the post-compaction segment. The prefix segment contains orphaned early messages (not a full conversation with an output), which scanners should be aware of.

Empty segments are skipped — if there are no `ModelEvent`s before a compaction boundary, or a trim prefix is empty, no `TimelineMessages` is yielded for that segment.

### Message Extraction per Span

For a given span, messages are extracted from `ModelEvent`s in its direct content:

1. Collect all `ModelEvent`s and `CompactionEvent`s from `span.content` (only `TimelineEvent` items, not child `TimelineSpan`s)
2. Process compaction events by type:
   - **Summary**: split `ModelEvent`s into segments at the compaction boundary
   - **Trim**: compute the trimmed prefix between the last `ModelEvent` before and first `ModelEvent` after the compaction (see Trim Prefix Extraction)
   - **Edit**: ignore
3. For each segment, take the **last `ModelEvent`** — its `input + [output.choices[0].message]` is the conversation for that segment

```
Span content:  [Model₁, Model₂, CompactionSummary, Model₃, Model₄]
                 └──── segment 0 ────┘                └── segment 1 ──┘
                        ↓                                    ↓
                 Model₂.input + output               Model₄.input + output
```

Trim compaction yields a prefix-only segment (see Trim Prefix Extraction below):

```
Span content:  [Model₁, Model₂, CompactionTrim, Model₃, Model₄]

  Model₂.input = [A, B, C, D, E, F, G, H]        (pre-trim, full conversation)
  Model₄.input =             [D, E, F, G, H, I]   (post-trim, trimmed conversation)

  segment 0: [A, B, C]                             (trimmed prefix only)
  segment 1: Model₄.input + output                 (post-trim conversation)
```

Edit compaction is not a split point — the last `ModelEvent` in the span is used as-is.

### Compaction Splitting Strategy

`CompactionEvent` has a `type` field distinguishing the compaction strategy. Only **summary** compaction triggers a split:

| Compaction Type | Split? | Rationale |
|-----------------|--------|-----------|
| **Summary** | Yes — full split | Original messages replaced by a summary — content is lost. Pre-compaction must be scanned separately. Each segment is roughly one context window, preventing overflow. |
| **Edit** | No | Same messages survive with reasoning/tool calls stripped. No content loss, no duplication. |
| **Trim** | Yes — prefix only | Later messages are preserved unchanged, so a full split would create duplication. Instead, yield only the **trimmed prefix** (messages dropped from the beginning) as a separate segment. |

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

### Filtering

The `include` parameter controls which spans yield messages:

- **`None` (default)**: all non-utility spans that have at least one `ModelEvent` in their direct `content` (not inherited from child spans). A span that contains only child `TimelineSpan`s and no `ModelEvent`s of its own is a pure container and yields nothing — its children are visited instead.
- **`str`**: only spans whose name matches (case-insensitive) — e.g., `include="Build"` processes only spans named "Build"
- **`callable`**: arbitrary predicate — e.g., `include=lambda s: s.span_type == "agent"`

The generator walks the tree recursively. Non-matching spans are skipped but their children are still visited — the filter controls *which spans yield messages*, not *which subtrees are traversed*.

### Usage with `message_numbering()`

```python
messages_as_str, extract_references = message_numbering(
    preprocessor=MessagesPreprocessor(exclude_reasoning=True)
)

spans_scanned: list[tuple[TimelineMessages, str]] = []

async for span_msgs in timeline_messages(timeline, include="Build"):
    formatted = await messages_as_str(span_msgs.messages)
    spans_scanned.append((span_msgs, formatted))

# All references resolve across all spans
refs = extract_references(llm_output)
```
