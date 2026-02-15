# Timeline Implementation Design

Design decisions and architecture for implementing the timeline UI.

## 1. State Management

### URL State (via `replace` navigation)

Structural navigation state lives in URL query params, updated via `navigate(..., { replace: true })` so no browser history entries are created. The timeline's own navigation (breadcrumbs, Escape, chevrons) controls drill-down; browser back controls page-level navigation.

Parameters (all lowercase, snake_case for multi-word):

- `path=build/test` — drill-down breadcrumb path (agent names joined by `/`)
- `selected=code` — which row is selected
- `timeline_view=agents` — which timeline pill is active (only when multiple timelines exist)

Agent names in URL params are **case-insensitive** — resolved against `AgentNode.name` via `toLowerCase()` comparison.

### Zustand State (persisted)

Internal UI state lives in Zustand, persisted for VSCode tab restore:

- Scroll position in the content panel
- Resizable divider position (timeline vs. content panel height)
- Utility agents toggle (shown/hidden)
- Collapsed state within the content panel
- Visible range tracking for virtualized lists

Zustand keys are scoped by transcript ID + drill-down path (e.g., `timeline:${transcriptId}:build/test`) so each drill-down level maintains independent UI state. Multiple scopes coexist simultaneously — drilling into `build`, scrolling, then going back to root preserves the scroll position at both levels.

**Cleanup:** All scoped entries for a transcript ID are cleared when the user navigates away from that transcript. Within a session, entries accumulate freely (bounded by the number of drill-down levels visited, which is small).

### Restoration Priority

On mount (including VSCode tab restore):

1. URL params are the source of truth for structural navigation state
2. Zustand provides fine-grained UI state (scroll, collapse, divider position)

## 2. Data Architecture

### `useTimeline` Hook

A custom hook encapsulates tree building, path resolution, and navigation actions. The container calls the hook and distributes results to the Timeline and ContentPanel components.

```
Container
  ├── const timeline = useTimeline(events)
  ├── passes tree + navigation actions to Timeline
  ├── passes resolved node to ContentPanel
```

**Input:** `TranscriptNodes` (pre-built). Tree building happens upstream — typically a `useMemo` in the container:

```typescript
const tree = useMemo(() => buildTranscriptNodes(events), [events]);
const timeline = useTimeline(tree);
```

For multiple timelines, the container selects which tree to pass:

```typescript
const trees = useMemo(() => buildTimelines(events), [events]);
const activeTree = trees[activeTimelineIndex].transcript;
const timeline = useTimeline(activeTree);
```

**Responsibilities:**
- Reads URL params (`path`, `selected`) to determine navigation state
- Resolves the path to a specific `AgentNode` or `SectionNode` (case-insensitive matching)
- Computes swimlane rows from the resolved node (separate `useMemo`)
- Provides navigation actions that update URL via `replace`

**Return value (sketch):**
```typescript
const timeline = useTimeline(tree);
timeline.node          // resolved AgentNode/SectionNode for current path
timeline.rows          // SwimLaneRow[] for the current drill-down level
timeline.breadcrumbs   // path segments for breadcrumb UI
timeline.selected      // which row is selected
timeline.drillDown(agentName)   // navigate into a child agent/span
timeline.goUp()                 // navigate to parent
timeline.select(agentName)      // select a row
```

**Dependencies:** The hook reads/writes URL params internally (via `useSearchParams` / `useNavigate`). It does not take `transcriptId`, `Timeline[]`, or a navigate function.

**Benefits:**
- Single source of truth for path resolution + swimlane computation
- Plays naturally with URL-based state (hook reads URL params, returns resolved state)
- Both Timeline and ContentPanel become relatively simple renderers
- Independently testable without DOM (hook tests)
- Follows existing patterns (`useTranscript`, `useAdjacentTranscriptIds`)

## 3. Content Panel

### Strategy: Enhance Existing Components

The content panel reuses and enhances the existing `TranscriptView` and `TranscriptOutline` components rather than building new ones.

### Component Composition (Prototype)

The initial prototype composes three components:

```
TimelineContainer
  ├── const timeline = useTimeline(events)
  ├── TranscriptTimeline        ← new (swimlane bars, breadcrumbs)
  ├── resizable divider
  └── ContentPanel
      ├── TranscriptOutline     ← enhanced existing
      └── TranscriptView        ← enhanced existing
```

These are composed as a standalone prototype first, then integrated back into the mainline `TranscriptBody` once stable.

### Enhancements Required

**TranscriptView:**
- Accept an `AgentNode` (not just raw `Event[]`) as input
- Render child `AgentNode`s inline as sub-agent cards (clickable)
- Render `TimelineBranch` cards with dashed borders at fork points
- Sub-agent card clicks call `timeline.drillDown()` — navigation flows through the `useTimeline` hook
- Error and compaction markers are not needed in the content panel — these are already visible as regular events in the content stream

**TranscriptOutline:**
- Accept an `AgentNode` to build its tree (currently works from raw events)
- Support custom `Outline` attached to an `AgentNode` (replaces the auto-generated outline)
- When a custom outline exists, use its `OutlineNode` tree directly instead of the visitor-based pipeline

### Utility Agent Visibility

The utility agent toggle (`▸ N utility agents hidden` / `▾ N utility agents shown`) lives in the surrounding chrome, not inside the content panel. Utility agent visibility is a Zustand store concern — the content panel simply renders whatever content it receives. Filtering happens upstream before events reach the content panel.

### Navigation Flow

Clicking a sub-agent card in the content panel is a drill-down navigation:

```
User clicks "Build" card in ContentPanel
  → calls timeline.drillDown("build")
  → URL updated via replace: ?path=build
  → useTimeline resolves new path → new AgentNode
  → Timeline re-renders with new breadcrumbs + child rows
  → ContentPanel re-renders with Build's content
```

This unifies navigation — whether the user clicks a swimlane row chevron in the timeline or a sub-agent card in the content panel, the same `useTimeline` hook handles it.

## 4. Swimlane Row Computation

### Data Model

A swimlane row is a sequence of spans sharing an agent name. Each span is either a single agent or a parallel cluster of agents:

```typescript
interface SingleSpan {
  agent: AgentNode;
}

interface ParallelSpan {
  agents: AgentNode[];
}

type TimelineSpan = SingleSpan | ParallelSpan;

interface SwimLaneRow {
  name: string;
  spans: TimelineSpan[];
  totalTokens: number;
  startTime: Date;
  endTime: Date;
}
```

Properties like `kind` (single/iterative/parallel) and `drillable` (has children) are not stored — they are derivable from the data and computed as needed by consumers.

### Grouping Algorithm

1. Collect child `AgentNode`s from the current node's `content` (skip `EventNode`s)
2. Group by name (case-insensitive)
3. Within each name group, cluster into spans:
   - Non-overlapping agents become separate `SingleSpan` entries on the row (iterative pattern)
   - Overlapping agents (within a tolerance of ~100ms to account for spawn skew) become a `ParallelSpan`
   - If any overlap exists within the name group, the entire group is treated as parallel
   - A row can mix single and parallel spans (e.g., a single Explore, then later three Explore in parallel)
4. Order rows by earliest start time across their spans
5. The parent `AgentNode` is always the top row (full-width bar)
6. Scoring (`SectionNode`) is a standard swimlane row at the bottom

### Parallel Count Display

The parallel count badge appears on the bar (span), not the row label. This handles cases where the same agent name has different levels of parallelism across invocations — e.g., the label just says "Explore" while one span shows `(3)` and another shows `(2)`.

### Drill-Down

- Each span has its own chevron for drill-down
- No row-level drill-down — only individual spans are drillable
- For parallel spans, drilling in reveals the individual agent instances (per design doc section 4)
- For single spans, drilling in reveals that agent's children

## 5. Timeline Swimlane Rendering

### Approach: Hybrid DOM + CSS Background

The timeline uses a DOM-based layout with visual fills as separate positioned elements. All elements within a row share one coordinate space (the bar area width), making cross-span positioning (e.g., branch fork markers) straightforward.

### Layout Structure

Each swimlane row is a three-column CSS Grid:

```
┌─────────┬──────────────────────────────────────────┬───────┐
│  label  │              bar area                    │ tokens│
└─────────┴──────────────────────────────────────────┴───────┘
```

Within the bar area, all elements are absolutely positioned using percentage-based `left`/`width` relative to the bar area container:

```html
<div class="bar-area">
  <!-- Visual fills (no interactivity) -->
  <div class="fill" style="left: 5%; width: 25%"></div>
  <div class="fill" style="left: 40%; width: 20%"></div>

  <!-- Markers — all positioned in bar-area coordinates -->
  <span class="marker error" style="left: 30%">▲</span>
  <span class="marker branch" style="left: 35%">↳</span>
  <span class="marker compaction" style="left: 50%">┊</span>

  <!-- Chevrons at span endpoints -->
  <span class="chevron" style="left: 29%">›</span>
  <span class="chevron" style="left: 59%">›</span>
</div>
```

### Why Hybrid Over Pure DOM

In pure DOM, each bar segment is both the visual fill and the interactive container, with markers positioned relative to their segment. This creates problems for elements that aren't scoped to a single segment — e.g., a `↳` branch marker on the parent bar at a time position between child spans. The hybrid approach puts everything in one coordinate space, so positioning any element is just `left: <percent>` regardless of which fill it overlaps.

Click targets for bar segments use either click handlers on the fill divs or invisible overlay divs — the visual and interactive layers are separate.

### Proportional Positioning

All `left`/`width` percentages are computed from timestamps relative to the current view's time range:

```
percent = (timestamp - viewStart) / (viewEnd - viewStart) * 100
```

Where `viewStart`/`viewEnd` come from the current drill-down level's `AgentNode` time range.

### Theming

Fills, markers, and selection highlighting use CSS custom properties (VSCode theme variables) for light/dark mode compatibility.

## 6. `useTimeline` Hook — Detailed Behavior

### Edge Cases

- **Invalid path**: If the URL `path` param doesn't resolve to a valid node (e.g., stale URL from a different transcript), fall back to the root. No error state — just silently reset.
- **Empty events**: Return null/empty tree. No timeline or content panel to render.
- **Flat transcript** (no agents): The single root `AgentNode` (named "main") is the parent row and the content source. Timeline shows one bar.

### Selection Semantics

Selecting a row **fully replaces** the content panel with that node's content. It does not scroll within the parent's events — the selected node's `AgentNode` (or `SectionNode`) becomes the content panel's data source.

### Section Nodes

`SectionNode` types (init, scoring) are treated uniformly alongside `AgentNode` in the timeline. Init, scoring, and agent nodes all appear as standard swimlane rows and are all selectable.

### Span Numbering for Drill-Down

When an agent name has multiple spans (iterative or parallel), spans are numbered with a `-N` suffix for disambiguation in URL paths:

- `?path=build` — single Build agent, no suffix needed
- `?path=explore-2` — second span of Explore
- `?path=explore-2/test` — drill into Test within the second Explore invocation

Resolution rules:
- Find all agents/spans matching the name (case-insensitive)
- If a `-N` suffix is present, select the Nth span (1-indexed)
- If no suffix and only one match, use it
- If no suffix and multiple matches, default to the first

This numbering applies uniformly to both iterative spans (sequential invocations) and parallel spans (individual instances within a parallel group).

### Memoization Strategy

- `buildTranscriptNodes(events)` — memoized via `useMemo` keyed on `events`
- Swimlane row computation — separate `useMemo` keyed on the resolved `AgentNode`, deferred from the tree build
- Navigation actions (`drillDown`, `goUp`, `select`) — stable callbacks via `useCallback`

## 7. Header Bar

### Structure

A `TimelineHeader` component composed of two sub-components:

```
TimelineHeader
  ├── TimelinePills       ← conditional (only when multiple timelines)
  └── TimelineBreadcrumb  ← always present
```

### TimelinePills

A row of pill buttons for switching between named timeline views. Only rendered when multiple timelines exist — single-timeline transcripts show no pills.

### TimelineBreadcrumb

A single row with three elements:

```
← Transcript › Build › Test                            31.8k tokens
```

- **Back arrow** (`←`): Visible when drilled in (not at root). Goes up one level (same as Escape).
- **Breadcrumb segments**: Each segment is clickable, jumping directly to that level. Allows skipping levels (e.g., from `Build > Test` directly to root by clicking `Transcript`).
- **Token count**: Right-aligned. Shows the current drill-down node's total tokens (not the full transcript total).

At root level, just the name and total:

```
Transcript                                              48.5k tokens
```

### Data Flow

- `TimelinePills` receives the `Timeline[]` array and active index from the container
- `TimelineBreadcrumb` receives `timeline.breadcrumbs`, `timeline.node.totalTokens`, and `timeline.goUp` from the `useTimeline` hook
- Breadcrumb segment clicks call `timeline.drillDown` or navigate to a specific path level

## 8. Keyboard Navigation

### Focus Model

The timeline panel is a focusable container (`tabIndex={0}`). Keyboard events are only handled when the timeline has focus — no global key handlers. Clicking a row or tabbing into the timeline gives it focus.

### Key Bindings

| Key | Effect |
|-----|--------|
| `↑` / `↓` | Move selection between rows (including the parent row at top) |
| `Enter` | Drill down into selected row |
| `Escape` | Go up one level; if at root with selection, deselect; if at root with no selection, no-op |

### Behavior Details

- **Arrow keys stop at boundaries** — pressing `↓` on the last row or `↑` on the first row does nothing (no wrapping).
- **Parent row is included** in the arrow key cycle — `↑` from the first child selects the parent.
- **No-ops are silent** — Enter on a non-drillable row (e.g., Scoring with no children) does nothing. No visual feedback.
- **Escape does not cross boundaries** — Escape in the content panel does not move focus back to the timeline. The two panels have independent focus scopes.

## 9. Content Panel ↔ AgentNode Integration

### Approach: Direct rendering from AgentNode content

The content panel builds a flat rendering list directly from `AgentNode.content`, bypassing the existing transform pipeline (no fixups, treeify, transform, flatten). The `AgentNode` is already the structured form — the transform pipeline exists to build structure from raw events, which is unnecessary here.

However, the existing pipeline encodes implicit rules and behaviors (e.g., collapsing pending events, sandbox event grouping, `sample_init` injection, default collapse decisions, span unwrapping). These rules must be audited during implementation — some are irrelevant in the AgentNode context (the tree is already structured), but others may need to be reflected in the new rendering path. Document each rule as it's encountered.

### Content Item Types

A discriminated union for the virtual list:

```typescript
type ContentItem =
  | { type: "event"; eventNode: EventNode }
  | { type: "agent_card"; agentNode: AgentNode }
  | { type: "branch_card"; branch: TimelineBranch }
  | { type: "parallel_group"; agents: AgentNode[] }
```

### Building the Content List

Walk `AgentNode.content` chronologically:

1. **EventNode** items → `{ type: "event", eventNode }`
2. **Child AgentNode** items → `{ type: "agent_card", agentNode }` (or `parallel_group` if consecutive same-name agents overlap)
3. **Branches** → insert `{ type: "branch_card", branch }` at each branch's `forkedAt` position

### Rendering Dispatch

The virtual list dispatches on `ContentItem.type`:

- `"event"` → delegates to existing event viewers (`ModelEventView`, `ToolEventView`, etc.) via `RenderedEventNode`, passing `eventNode.event`. No changes to existing viewers needed.
- `"agent_card"` → new component: sub-agent card with name, tokens, duration, task description preview. Solid border. Clickable — calls `timeline.drillDown()`.
- `"branch_card"` → new component: branch card with `↳` prefix, dashed border. Clickable — drills into the branch.
- `"parallel_group"` → new component: stacked agent cards connected with `┃` gutter. Each card individually clickable.

## 10. Inline Marker Computation

### Marker Types

- **`▲` Error** — `ToolEvent` with error result, `ModelEvent` with error output. Classified by a function `isErrorEvent(event: Event) => boolean`.
- **`┊` Compaction** — `CompactionEvent` (explicit event type in the inspect event stream).
- **`↳` Branch** — from `AgentNode.branches`. Each branch's `forkedAt` UUID is resolved to a timestamp.

### Scanning Depth

The depth of marker collection is a user-configurable option:

| Setting | Behavior |
|---------|----------|
| `"direct"` | Only events in the node's own `content` |
| `"children"` | Direct content + one level of child agents (default) |
| `"recursive"` | Full subtree scan |

Default is `"children"` — shows that an error happened in a direct child without flooding markers from deeply nested sub-agents.

The depth preference is stored in Zustand (persisted display preference), not in the URL.

### Computation

Markers are computed on render via `useMemo`, keyed on the agent node and depth setting:

```typescript
const markers = useMemo(
  () => collectMarkers(agentNode, depth),
  [agentNode, depth]
);
```

No pre-computation on swimlane rows — avoids computing multiple depth variants and keeps the row data model simple. The scan is cheap (small number of events per view level).

### Positioning

Each marker has a timestamp, mapped to a percentage position using the same formula as bar fills:

```
percent = (marker.timestamp - viewStart) / (viewEnd - viewStart) * 100
```

### Branch Markers

Branch markers (`↳`) are separate from error/compaction markers. They come from `AgentNode.branches` — each branch's `forkedAt` UUID is resolved to the corresponding event's timestamp. Branch markers only appear on the row that owns the branches, not aggregated upward.

## 11. Resizable Divider

### Layout

The timeline panel and content panel are separated by a VSCode Elements split layout divider (`VscodeSplitLayout`). The timeline panel sits above, the content panel below.

### Default Height

The timeline panel shows up to **5 rows** by default (parent row + up to 4 child rows). If there are more rows, the timeline area scrolls internally. The divider allows the user to customize the split.

### Persistence

The divider position is stored in Zustand (persisted) so it survives VSCode tab switches and session restarts.
