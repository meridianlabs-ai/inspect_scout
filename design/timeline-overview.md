# Timeline Overview

The Timeline system transforms **flat event streams** from LLM evaluations into a **hierarchical, agent-centric tree** suitable for visualization and navigation. It's implemented as parallel Python/TypeScript codebases that share test fixtures.

## Core Data Structures

| Type | Purpose |
|------|---------|
| **`Timeline`** | Top-level container with `name`, `description`, and a `root` TimelineSpan |
| **`TimelineSpan`** | Hierarchical node representing an agent, scorer, tool, or root. Has `content` (children), `branches`, `spanType` ("agent", "scorer", null), and computed `startTime`/`endTime`/`totalTokens` |
| **`TimelineEvent`** | Leaf node wrapping a single raw `Event` (ModelEvent, ToolEvent, etc.) |
| **`TimelineBranch`** | A discarded alternative execution path, with `forkedAt` UUID pointing to the decision point |

## Build Pipeline (`buildTimeline`)

1. **Span tree parsing** — Python uses `inspect_ai.event_tree()` to pair `span_begin`/`span_end` events; TypeScript has a custom `buildSpanTree()` implementation
2. **Phase detection** — looks for top-level "init", "solvers", "scorers" spans (LLM evaluation phases)
3. **Agent hierarchy building** — explicit `type="agent"` spans become agent nodes; tool spans containing ModelEvents become tool-spawned agents (`spanType=null`)
4. **Init folding** — init events merge into root content
5. **Scoring partition** — scorer span becomes a child with `spanType="scorer"`
6. **Branch detection** — two modes:
   - **Explicit**: `type="branch"` spans in the event stream
   - **Auto-detect**: re-rolled ModelEvents with identical input fingerprints (SHA-256 in Python, plain string in TS)
7. **Utility classification** — single-turn agents with a different system prompt from their parent are marked `utility=true`

## Key Algorithms

### Input Fingerprinting

Hash each message's `role + content` to detect re-rolled model calls (same input, different output). Python uses `hashlib.sha256`; TypeScript uses plain string comparison.

### Fork Point Resolution

Match the last shared input message back to the parent's content:
- Tool messages match by `tool_call_id`
- Assistant messages match by message `id`
- Fallback: match by content text
- User/system messages: fork at beginning

### Swimlane Grouping (`swimlaneRows.ts`)

Groups child spans by name and detects overlap (100ms tolerance) to distinguish sequential vs parallel execution:
- 1 span → SingleSpan
- Multiple spans with overlap → ParallelSpan (grouped)
- Multiple spans without overlap → individual SingleSpans (iterative)

### Content Flattening (`contentItems.ts`)

Inserts branch cards after their fork-point events for sequential vertical rendering. Maps `branch.forkedAt` UUID to event positions in the content list.

### Utility Agent Classification

A span is marked `utility=true` if:
1. Has a parent (not root agent)
2. Has a different system prompt than its parent
3. Is single-turn: exactly 1 ModelEvent, or 2 ModelEvents with ToolEvent(s) between them

## File Map

### Core Implementations

- `src/inspect_scout/_transcript/timeline.py` (~910 lines) — Python implementation using `inspect_ai.event_tree()`
- `src/inspect_scout/_view/www/src/components/transcript/timeline.ts` (~1043 lines) — TypeScript implementation with custom `buildSpanTree()`

### UI Integration (TypeScript)

- `app/timeline/useTimeline.ts` — URL-driven navigation with path resolution and breadcrumbs
- `app/timeline/swimlaneRows.ts` — horizontal row grouping
- `app/timeline/contentItems.ts` — vertical content flattening
- `app/timeline/markers.ts` — error/compaction/branch marker collection

### Tests

- `tests/transcript/nodes/test_timeline.py` (~663 lines) — Python tests
- `src/inspect_scout/_view/www/src/components/transcript/timeline.test.ts` — TypeScript tests
- 37+ shared JSON fixtures in `tests/transcript/nodes/fixtures/events/`

### Design Documents

- `design/timeline-implementation-design.md` — detailed UI/UX spec
- `design/timeline-ui.md` — visual specifications
- `design/timeline-context.md` — architectural context

## Design Patterns

- **Computed properties**: Span timing and tokens are always derived from children — no redundant storage
- **Recursive nesting**: Same algorithms apply at every depth (branch detection, utility classification)
- **Discriminated unions**: TypeScript uses `type: "event" | "span" | "branch"` for type narrowing
- **Cross-language consistency**: Both implementations consume identical JSON fixtures to ensure parity
- **Two-phase branch detection**: Explicit branches take priority; auto-detection via fingerprinting is the fallback
- **Span type disambiguation**: Tool spans containing ModelEvents are treated as tool-spawned agents (`spanType=null`) rather than tool executions
