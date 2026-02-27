# Documentation Plan: Scanner Articles

## Status

The following scanner documentation is already complete and does not need further work:

- **`scanners.qmd`** — Overview, using scanners, includes for LLM/Grep/Custom scanner summaries, scan jobs, learning more links
- **`llm_scanner.qmd`** — Basic usage, answer types, prompt templates, scanner results, message filtering, structured answers, value to float, dynamic questions, context windows, scanning timelines, parameter reference. **TODO:** Add callout near top (e.g. in Overview) pointing to Scanner Tools article for users who need custom prompting logic beyond what `llm_scanner()` offers.
- **`grep_scanner.qmd`** — Basic usage, pattern types, options, scanner results, searching events, examples

The following articles exist and are also complete:

- **`db_importing.qmd`** — Claude Code source, well documented

## Uncovered Topics

The topics below need new documentation. They are currently either undocumented or live in `custom_scanner.qmd` which is being reorganized into new articles.

### Transcripts & Timelines

Data model and content access — what scanners operate on.

| Topic | Source | Notes |
|-------|--------|-------|
| **Transcript fields** | `custom_scanner.qmd` | Field table via `_transcript_fields.md` include. Currently missing the `timelines` field. |
| **Content filtering** | `custom_scanner.qmd` | How `messages`, `events`, and `timeline` filters on `@scanner` control what gets loaded. Examples of `messages="all"`, `events=["model", "tool"]`, `messages=["assistant"]`. |
| **`Transcript.timelines`** | New | New field on `Transcript`. Missing from `_transcript_fields.md`. |
| **Timeline data model** | New | `Timeline`, `TimelineSpan`, `TimelineEvent`, `TimelineBranch` — the node types, their fields, span types, branches, outline, token counts. Currently only stub listings in `reference/transcript.qmd`. |
| **`build_timeline(events)`** | New | Converts flat event list into hierarchical timeline. No narrative docs exist. |
| **`filter_timeline(timeline, predicate)`** | New | Prune a timeline by span predicate. No narrative docs exist. |
| **`timeline.render()`** | New | ASCII swimlane diagram of a timeline. Undocumented. |
| **Presenting messages** | `custom_scanner.qmd` | `messages_as_str()` function, `MessagesPreprocessor` usage for custom scanners. |
| **Message extraction pipeline** | New | `transcript_messages`, `segment_messages`, `span_messages`, `timeline_messages`, `MessagesSegment`, `TimelineMessages` — the full pipeline for extracting and segmenting messages from transcripts and timelines. |

### Custom Scanners

How to write scanners — the authoring guide.

| Topic | Source | Notes |
|-------|--------|-------|
| **Scanner basics** | `custom_scanner.qmd` | What a `Scanner` is, the function signature, `Result` type, `value`/`answer`/`explanation`/`references` fields. |
| **`@scanner` decorator** | `custom_scanner.qmd` | Decorator parameters: `messages`, `events`, `timeline`, `name`, `version`, `metrics`, `loader`. The `timeline` and `version` params are new and not yet documented in prose. |
| **Input types** | `custom_scanner.qmd` | `Transcript`, `Event`, `ChatMessage`, `list[Event]`, `list[ChatMessage]`. |
| **Input filtering** | `custom_scanner.qmd` | Performance principle — only requested data is deserialized. Default is no filters (scanner won't be called without them). |
| **Transcript scanners** | `custom_scanner.qmd` | Most common type. Includes the "confusion" example with `get_model().generate()`. |
| **Event scanners** | `custom_scanner.qmd` | `Scanner[ModelEvent]`, `Scanner[ModelEvent | ToolEvent]`, auto-inference of event filters from type annotations. |
| **Message scanners** | `custom_scanner.qmd` | `Scanner[ChatMessageTool]`, `Scanner[ChatMessageUser | ChatMessageAssistant]`, auto-inference of message filters. |
| **Timeline scanners** | New | `@scanner(timeline=True)`, `Scanner[Timeline]` — auto-inference from type annotation. Covered implicitly in `llm_scanner.qmd` examples but not in custom scanner context. |
| **Multiple results** | `custom_scanner.qmd` | Returning `list[Result]` with `label` field, interaction with results data frame and validation. |
| **Custom loaders** | `custom_scanner.qmd` | `@loader` decorator, yielding custom content (e.g., message pairs), `loader=` parameter on `@scanner`. |

### Scanner Integration

Packaging, distribution, and reuse with Inspect.

| Topic | Source | Notes |
|-------|--------|-------|
| **Packaging** | `custom_scanner.qmd` | Python packages, `_registry.py`, setuptools entry points (`inspect_ai`), `scout scan myscanners/reward_hacking`. |
| **Scanners as scorers** | `custom_scanner.qmd` | Using scanners in Inspect `Task`, `inspect score` CLI, `as_scorer()` function. |
| **Scanner metrics** | `custom_scanner.qmd` | `metrics=` on `@scanner`, built-in Inspect metrics, custom metrics. Via `_scanner_metrics.md` include. |
| **Result set metrics** | `custom_scanner.qmd` | Dict-based metrics for multi-label scanners, glob (`*`) shorthand. |

### Scanner Tools

Lower-level building blocks for advanced custom scanners.

| Topic | Source | Notes |
|-------|--------|-------|
| **`generate_answer()`** | New | Standalone LLM generation that returns a `Result`. Undocumented. |
| **`parse_answer()`** | New | Pure parsing of model output into a `Result`, no LLM call. Undocumented. |
| **`message_numbering()`** | New | Creates `[M1]`, `[M2]` counter pair for cross-segment consistency. Undocumented. |
| **`scan_segments()`** | New | Concurrent segment scanning with ordered results. Undocumented. |
| **`AnswerSpec`** | New | Type alias unifying all answer specifications. Undocumented. |
| **`ResultReducer`** | New | `mean/median/mode/max/min/any/union/last` static reducers, `ResultReducer.llm()` factory. Documented in `llm_scanner.qmd` context windows section but not as standalone reference. |

### Other Gaps

| Topic | Priority | Notes |
|-------|----------|-------|
| **`scout import` CLI command** | High | Entirely undocumented. `scout import <source> [options]`, flags: `--limit`, `--from`, `--to`, `-P key=value`, `--dry-run`, `--overwrite`, `--sources`. |
| **CLI reference stubs** | Low | Pre-existing gap — all empty. |

## Proposed Article Structure

Based on the Option B (progressive disclosure) approach discussed:

1. **Custom Scanners** — Entry point for scanner authoring. Scanner basics, `@scanner` decorator, `Result`, input types and filtering, transcript/event/message/timeline scanners, multiple results, custom loaders, packaging, scanners as scorers, metrics.

2. **Scanner Tools** — Power tools for advanced scanner development that apply to all custom scanners. `generate_answer`, `parse_answer`, `message_numbering`, `scan_segments`, `ResultReducer`, message extraction pipeline.

3. **Timelines** — Specialized: understanding hierarchical agent execution traces. Timeline data model (`Timeline`, `TimelineSpan`, `TimelineEvent`, `TimelineBranch`), `build_timeline`, `filter_timeline`, `render()`.

---

## Article Outlines

### Article 1: Custom Scanners (`custom_scanners.qmd`)

*Audience:* Someone who has used `llm_scanner()` or `grep_scanner()` and now needs more control.

*Sequence:* Concepts first (what is a scanner, what can it target), then progressively more advanced patterns.

#### Overview
- What custom scanners are and when you need them (vs. `llm_scanner`/`grep_scanner`)
- Scanner as a function: takes `ScannerInput`, returns `Result`
- Link to LLM Scanner and Grep Scanner for the common cases

#### Scanner Basics
- The `@scanner` decorator and its role
- The inner function pattern (factory returns scan function)
- `Result` type: `value`, `answer`, `explanation`, `references`, `label`
- Simple example: the "confusion" scanner with `get_model().generate()`
- Comparison: same scanner implemented with `llm_scanner()` (show both, motivate when custom is needed)

#### Input Types & Filtering
- The performance principle: only requested data is deserialized
- **Important:** default is no filters — scanner won't be called without `messages` and/or `events`
- `@scanner` filter parameters: `messages`, `events`, `timeline`
- Filter values: `"all"`, specific types (`["assistant"]`, `["model", "tool"]`)

#### Transcript Scanners
- Most common type (`Scanner[Transcript]`)
- Accessing `transcript.messages`, `transcript.events`, `transcript.metadata`
- Presenting messages and extracting references with `message_numbering()`
  - Returns a `(messages_as_str, extract_references)` pair with shared numbering
  - `messages_as_str()` produces numbered text (`[M1]`, `[M2]`, ...) for LLM prompts
  - `extract_references()` resolves model citations back to message IDs for `Result.references`
  - Update "confusion" example to use `message_numbering()` instead of bare `messages_as_str()`

#### Event Scanners
- `Scanner[ModelEvent]`, `Scanner[ModelEvent | ToolEvent]`
- Auto-inference: type annotation implies event filter (no need for `events=` on decorator)
- Called once per matching event in the transcript

#### Message Scanners
- `Scanner[ChatMessageTool]`, `Scanner[ChatMessageUser | ChatMessageAssistant]`
- Auto-inference from type annotation
- Called once per matching message

#### Timeline Scanners
- `@scanner(timeline=True)` or `Scanner[Timeline]` type annotation
- How timeline scanning differs: each span scanned independently
- Brief conceptual intro (link to Timelines article for the full data model)

#### Multiple Results
- Returning `list[Result]` with `label` field
- Each result yields its own row in the results data frame
- Interaction with result set validation (link)

#### Custom Loaders
- When built-in iteration isn't enough (e.g., message pairs)
- `@loader` decorator with `messages`/`events`/`timeline` filters
- Yielding custom content via `AsyncIterator`
- Using `loader=` parameter on `@scanner`

#### Packaging
- Including scanners in Python packages
- `_registry.py` and setuptools entry points
- `scout scan myscanners/reward_hacking`
- Tabset: Setuptools / uv / Poetry

#### Scanners as Scorers
- Using scanners directly in Inspect `Task(scorer=...)`
- `inspect score` CLI
- `as_scorer()` for explicit conversion
- Metrics: default `mean()`/`stderr()`, custom via `@scanner(metrics=...)`
- Result set metrics for multi-label scanners (dict-based, glob shorthand)

---

### Article 2: Scanner Tools (`scanner_tools.qmd`)

*Audience:* Advanced users building custom scanners that need the same answer parsing, generation, segmentation, and message extraction infrastructure that `llm_scanner()` uses internally.

*Sequence:* Start with the highest-value tools (answer generation/parsing), then message presentation and extraction, then segmentation and reduction.

#### Overview
- The scanner tools are the building blocks used internally by `llm_scanner()`
- Use these when `llm_scanner()` is too opinionated but you want its infrastructure
- Motivating example: show a skeleton custom scanner that decomposes `llm_scanner()` into its parts:
  1. `message_numbering()` — format messages with `[M1]`/`[M2]` numbering and extract references
  2. `segment_messages()` — split to fit context windows
  3. **Custom prompt construction** ← your logic here
  4. `generate_answer()` / `parse_answer()` — get a parsed `Result`
  5. `ResultReducer` — combine multi-segment results
- This skeleton shows where each tool fits and where users inject their own prompting logic

#### Answer Generation
- `generate_answer(prompt, answer, ...)` — send a prompt to an LLM and get back a parsed `Result`
- Supports all `AnswerSpec` types (boolean, numeric, string, labels, structured)
- Handles retries for refusals and schema validation

#### Answer Parsing
- `parse_answer(output, answer, ...)` — parse model output into a `Result` without making an LLM call
- Useful for custom generation flows where you handle the model call yourself

#### Answer Types Reference
- `AnswerSpec` type alias — unifies all answer specifications
- `AnswerMultiLabel` — multi-classification
- `AnswerStructured` — tool-based structured output with `answer_tool`, `answer_prompt`, `answer_format`, `max_attempts`

#### Presenting Messages
- `MessagesPreprocessor` options: `exclude_system`, `exclude_reasoning`, `exclude_tool_usage`, `transform`
- Cross-segment numbering: `message_numbering()` maintains consistent `[M1]`...`[Mn]` IDs across multiple segments (counter auto-increments globally so segment 2 continues where segment 1 left off)
- `extract_references()` resolves citations from any prior `messages_as_str()` call within the numbering scope

#### Message Extraction Pipeline
- `transcript_messages(transcript, ...)` — unified entry point; auto-selects strategy (timelines → events → messages)
- `span_messages(source, ...)` — extract from a span/event list with compaction handling
- `segment_messages(source, ...)` — segment messages to fit context windows
- `timeline_messages(timeline, ...)` — walk span tree yielding `TimelineMessages` per non-utility span
- `MessagesSegment`, `TimelineMessages` — return types

#### Segment Scanning
- `scan_segments()` — concurrent scanning of multiple message segments with ordered results
- Use case: scanning long transcripts in parallel chunks

#### Result Reduction
- `ResultReducer` — combining results from multiple segments
- Static reducers: `mean`, `median`, `mode`, `max`, `min`, `any`, `union`, `last`
- `ResultReducer.llm(model, prompt)` — LLM-based synthesis of multi-segment results

---

### Article 3: Timelines (`timelines.qmd`)

*Audience:* Someone working with multi-agent or complex agent transcripts who needs to understand the hierarchical structure of execution traces.

*Sequence:* Conceptual intro, then the data model, then construction/filtering/rendering.

#### Overview
- What a timeline represents: hierarchical tree of spans from agent execution
- Why timelines matter: flat message lists lose agent structure, tool boundaries, and branching
- Built automatically from transcript events
- Available on `Transcript` via the `timelines` field (requires `timeline=True` on `@scanner`)

#### Timeline Data Model
- `Timeline` — root container
- `TimelineSpan` — agent/tool/scorer invocation; fields: `name`, `span_type`, `content`, `branches`, `outline`, token counts
- `TimelineEvent` — individual event within a span
- `TimelineBranch` — re-rolled attempts

#### Building Timelines
- `build_timeline(events)` — converts flat events to hierarchical tree
- What it detects: agent hierarchies, conversation threads, branches, utility agents

#### Filtering Timelines
- `filter_timeline(timeline, predicate)` — prune by span predicate
- Utility spans: what they are, why they're excluded by default

#### Rendering Timelines
- `timeline.render()` — ASCII swimlane diagram
- Example output
