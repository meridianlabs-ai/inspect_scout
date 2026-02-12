# Timeline Implementation Briefing

Reference material for implementing the timeline UI. Captures the design spec, data model, and application architecture context.

## 1. Design Spec Summary (timeline-ui.md)

Please read the timeline-ui.md as required for more details.

The timeline UI visualizes transcript execution as a swimlane-based timeline with a content panel below. Key concepts:

### Timeline Panel

- **Swimlane rows** for agents, each showing a proportional bar with token count. A full-width Transcript bar spans the top.
- **Iterative agents** appear as multiple non-contiguous spans on one row, with aggregated token counts.
- **Parallel agents** of the same type collapse into a single row with a count badge (e.g., `Explore (3)`).
- **Drill-down navigation** instead of showing all nesting levels. Clicking a sub-agent rescales the timeline to fill full width, with breadcrumb navigation (`← Transcript > Build > Test`). Escape goes up.
- **Inline markers**: `▲` for errors, `┊` for compaction, `↳` for branch fork points — placed inline within bars.
- **Selection vs. drill-down**: Single-click selects a row (drives the content panel). `›` chevron or double-click drills down. Arrow keys move between rows.
- **Adaptive height**: Grows to fit rows up to a cap of 6, then scrolls internally. Resizable divider between timeline and content panel.

### Content Panel

- Shows the selected agent's events chronologically: `◆ MODEL` calls, `◇ TOOL` calls, and sub-agent launch cards.
- **Sub-agent cards** appear inline at launch points, showing name, tokens, duration, and task description preview. Clickable to drill down.
- **Parallel sub-agents** grouped with a `┃` gutter connecting their cards.
- **Errors**: `▲ ERROR` badge on tool events. **Compaction**: horizontal divider.
- **Utility agents**: Hidden by default behind a toggle (`▸ 12 utility agents hidden`), shown as single-line `⚙` entries when revealed.
- **Branch cards**: Dashed borders to distinguish from child agent cards, appearing at fork points.

### Multiple Timelines

- Pill selector above the timeline for switching between named views (e.g., "Agents", "Phases", "Tools").
- Each timeline has its own `TranscriptNodes` tree.
- Switching resets drill-down, selection, and branch navigation.

### Custom Outline

- Optional sidebar in the content panel when an `AgentNode` has an `outline`.
- Collapsible tree with scroll-tracking and click-to-scroll.

## 2. Data Model (nodes.ts)

The TypeScript data model that powers the timeline:

### Core Types

```typescript
interface EventNode {
  type: "event";
  event: Event;
  startTime: Date | null;
  endTime: Date | null;
  totalTokens: number;
}

interface AgentNode {
  type: "agent";
  id: string;
  name: string;
  source: AgentSource;           // "span" or "tool"
  content: (EventNode | AgentNode)[];
  branches: Branch[];
  taskDescription?: string;
  utility: boolean;
  outline?: Outline;
  startTime: Date | null;
  endTime: Date | null;
  totalTokens: number;
}

interface Branch {
  type: "branch";
  forkedAt: string;              // UUID of the fork-point event
  content: (EventNode | AgentNode)[];
  startTime: Date | null;
  endTime: Date | null;
  totalTokens: number;
}

interface SectionNode {
  type: "section";
  section: "init" | "scoring";
  content: EventNode[];
  startTime: Date | null;
  endTime: Date | null;
  totalTokens: number;
}

interface TranscriptNodes {
  init: SectionNode | null;
  agent: AgentNode | null;
  scoring: SectionNode | null;
  startTime: Date | null;
  endTime: Date | null;
  totalTokens: number;
}

interface Timeline {
  name: string;
  description: string;
  transcript: TranscriptNodes;
}

interface Outline {
  nodes: OutlineNode[];
}

interface OutlineNode {
  event: string;                 // UUID reference
  children?: OutlineNode[];
}
```

### Agent Source Types

```typescript
interface AgentSourceSpan {
  source: "span";
  spanId: string;
}

interface AgentSourceTool {
  source: "tool";
  toolEvent?: ToolEvent;
}
```

### Processing Pipeline

`buildTranscriptNodes(events: Event[]) -> TranscriptNodes`:

1. Build span tree from flat events (span_begin/span_end pairing)
2. Find phase spans (init/solvers/scorers) or treat entire stream as agent
3. Build agent hierarchy from explicit `type='agent'` spans or tool-spawned agents
4. Classify utility agents (single-turn + different system prompt from parent)
5. Detect branches (explicit `type='branch'` spans or auto-detected via duplicate input fingerprints)

## 3. Application Architecture

### Stack

- **React 19** + React Router 7 (hash-based routing)
- **VSCode Elements** for native VSCode-like controls
- **Bootstrap 5** (themed for VSCode appearance) for layout/utilities
- **Zustand 5** with immer + persist for state management
- **React Query v5** for server state with `AsyncData<T>` wrapper
- **Virtuoso** / TanStack Virtual for virtualized lists
- **CSS Modules** for component-scoped styling

### Directory Structure

```
src/
├── api/              # ScoutApiV2 interface + HTTP/JSON-RPC implementations
├── app/
│   ├── transcript/   # TranscriptPanel, TranscriptBody (tabs: Messages, Events, Metadata, Info)
│   ├── timeline/     # TimelinePanel (placeholder) + syntheticNodes.ts (10 test scenarios)
│   └── server/       # React Query hooks (useTranscript, useScans, etc.)
├── components/
│   ├── transcript/   # Rendering engine: nodes.ts, outline, event viewers, transforms
│   └── chat/         # Chat message rendering
├── state/            # Zustand store (single store, multiple slices)
├── router/           # URL helpers, route definitions
└── types/            # TypeScript types (including generated.ts from OpenAPI)
```

### State Management

Single Zustand store with slices for: app status, scans, transcripts, UI state (scroll positions, collapsed events, grid states), validation. Uses immer for immutable updates and persist for localStorage.

### Data Flow

- `ApiProvider` exposes `ScoutApiV2` interface (server HTTP or VSCode JSON-RPC)
- React Query hooks wrap API calls in `AsyncData<T>` (loading | data | error)
- WebSocket topic-based invalidation for real-time updates
- `staleTime: Infinity` for static data like transcripts

### Existing Transcript Rendering

1. Raw events fetched via API
2. `buildTranscriptNodes()` builds the semantic tree
3. `transform()` / `flatten()` / `treeify()` prepare the display tree
4. `TranscriptVirtualList` renders via Virtuoso with event-specific viewers
5. `TranscriptOutline` provides tree sidebar navigation

### Timeline Current State

- `TimelinePanel` at `/timeline` route — placeholder with scenario dropdown
- `syntheticNodes.ts` provides 10 mock `TranscriptNodes` scenarios (sequential, iterative, parallel, branches, utilities, deep nesting, etc.)
- No visual implementation yet

### Key Patterns

- Module CSS for component scoping
- `AsyncData<T>` discriminated union for loading/data/error
- VSCode Elements for form controls and split layouts
- Bootstrap for grid/layout utilities
- Virtualized rendering for large datasets
