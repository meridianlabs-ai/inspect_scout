# Timeline UI Design

## 1. Sequential Sub-Agents

A coding agent that explores the codebase, plans an approach, then builds the solution. The Transcript row spans the full timeline and is selectable (to show the whole trajectory). Solver agents and Scoring are indented beneath it.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Transcript                                                  48.5k tokens │
├──────────────────────────────────────────────────────────────────────────┤
│ Transcript│██████████████████████████████████████████████████████│       │
│  Explore  │ ███████████                                          │  8.1k │
│  Plan     │             ████████                                 │  5.3k │
│  Build    │                      ████████████████████████████████│ 31.8k │
│  Scoring  │                                                   ███│  3.2k │
└──────────────────────────────────────────────────────────────────────────┘
```

**Notes:**
- Transcript row spans the full timeline — selecting it shows the whole trajectory
- Solver agents (Explore, Plan, Build) and Scoring are indented beneath
- Init phase is hidden by default
- Token counts are right-aligned for quick scanning
- Small gaps between agents represent the orchestrator's own model calls

## 2. Iterative Sub-Agents (Multiple Spans)

An agent that iterates between exploring and planning before building. When a named sub-agent has multiple spans, they appear on the same swimlane row. Token counts show the total across all spans.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Transcript                                                  61.5k tokens │
├──────────────────────────────────────────────────────────────────────────┤
│ Transcript│██████████████████████████████████████████████████████│       │
│  Explore  │ ███████        ██████                                │ 14.5k │
│  Plan     │         ██████        █████                          │  9.2k │
│  Build    │                             ███████████████████████  │ 34.6k │
│  Scoring  │                                                   ███│  3.2k │
└──────────────────────────────────────────────────────────────────────────┘
```

**Notes:**
- Explore and Plan each appear twice, with both spans on the same row
- The sequence reads left-to-right: Explore → Plan → Explore → Plan → Build → Scoring
- Token counts are aggregated across all spans for each agent
- Gaps between spans on the same row show when that agent was not active

## 3. Agent Navigation

Agents can nest to arbitrary depth. Rather than showing all levels at once (which exhausts horizontal space), the timeline uses drill-down navigation. Clicking a sub-agent zooms in: its timeline rescales to fill the full width, revealing its children. A breadcrumb and back arrow provide navigation.

### Top Level

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Transcript                                                  48.5k tokens │
├──────────────────────────────────────────────────────────────────────────┤
│ Transcript│██████████████████████████████████████████████████████│       │
│  Explore  │ ███████████                                          │  8.1k │
│  Plan     │             ████████                                 │  5.3k │
│  Build    │                      ████████████████████████████████ 31.8k  │
│  Scoring  │                                                   ███│  3.2k │
└──────────────────────────────────────────────────────────────────────────┘
```

Clicking Build zooms into it:

### Zoomed into Build

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ← Transcript › Build                                        31.8k tokens │
├──────────────────────────────────────────────────────────────────────────┤
│ Build    │██████████████████████████████████████████████████████│        │
│  Code    │ ██████████████████████                               │ 15.2k  │
│  Test    │                       ████████████████               │ 10.4k  │
│  Fix     │                                       ███████████████│  6.2k  │
└──────────────────────────────────────────────────────────────────────────┘
```

**Notes:**
- `←` back arrow returns to the parent level; `Escape` key does the same
- Breadcrumb shows path: `Transcript › Build` — each segment is clickable
- Build's bar rescales to fill the full width, revealing its sub-agents (Code, Test, Fix)
- Token count updates to show Build's total (31.8k)
- The pattern repeats for deeper nesting — clicking Test zooms in further:

### Zoomed into Test

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ← Transcript › Build › Test                                 10.4k tokens │
├──────────────────────────────────────────────────────────────────────────┤
│ Test     │██████████████████████████████████████████████████████│        │
│  Generate│ ████████████████                                     │  5.8k  │
│  Run     │                  ██████████                          │  0.4k  │
│  Evaluate│                            ██████████████████████████│  4.2k  │
└──────────────────────────────────────────────────────────────────────────┘
```

**Notes:**
- Breadcrumb extends: `Transcript › Build › Test` — all segments clickable
- `←` returns to Build level; clicking `Transcript` jumps straight to the top
- Test's timeline rescales to full width, revealing its own sub-agents
- Each level of nesting works identically — no limit on depth

## 4. Parallel Sub-Agents

Multiple Explore agents run in parallel, followed by sequential Plan and Build. Parallel agents of the same type are shown as a single row with a `(3)` count badge. The envelope bar spans from the earliest start to the latest end. Clicking the group row drills down (same pattern as section 3) to reveal individual instances.

### Top Level

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Transcript                                                  60.4k tokens │
├──────────────────────────────────────────────────────────────────────────┤
│ Transcript   │██████████████████████████████████████████████████│        │
│  Explore (3) │ █████████████                                    │ 24.3k  │
│  Plan        │               ███████                            │  5.3k  │
│  Build       │                       ██████████████████████████ │ 27.6k  │
│  Scoring     │                                                ██│  3.2k  │
└──────────────────────────────────────────────────────────────────────────┘
```

Clicking Explore (3) drills into the parallel group:

### Zoomed into Explore (3)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ← Transcript › Explore (3)                                  24.3k tokens │
├──────────────────────────────────────────────────────────────────────────┤
│ Explore (3)│██████████████████████████████████████████████████████│      │
│  Explore 1 │ ██████████████████████████████████████████           │ 8.1k │
│  Explore 2 │   ███████████████████████████████████████████████████│ 9.4k │
│  Explore 3 │ ████████████████████████████████████                 │ 6.8k │
└──────────────────────────────────────────────────────────────────────────┘
```

**Notes:**
- `(3)` badge on the group row indicates multiple parallel instances
- Envelope bar at the top level spans earliest start to latest end of all instances
- Drill-down uses the same breadcrumb navigation pattern as section 3
- Individual bars overlap in time, clearly showing concurrent execution
- At full width, timing differences between instances are much easier to see
- Token count on the group row is the sum of all instances

## 5. Inline Markers

Errors and compaction events are shown as subtle inline markers within timeline bars. These provide positional context — you can see *where* in the execution something happened without leaving the timeline view.

### Marker Characters

- `▲` — Error (tool error, model error, etc.)
- `┊` — Compaction (context window was compressed at this point)

### Example

A single Transcript bar showing two errors and one compaction:

```
│ Transcript│██████████████▲██████████┊██████████▲████████████████│       │
```

Multiple agents with markers on different rows:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Transcript                                                  48.5k tokens │
├──────────────────────────────────────────────────────────────────────────┤
│ Transcript│██████████████▲██████████┊██████████▲█████████████████│       │
│  Explore  │ ███████████                                          │  8.1k │
│  Plan     │             ████████                                 │  5.3k │
│  Build    │                      ████████▲███████┊██▲████████████│ 31.8k │
│  Scoring  │                                                   ███│  3.2k │
└──────────────────────────────────────────────────────────────────────────┘
```

**Notes:**
- Markers appear at the position within the bar corresponding to when the event occurred
- `▲` errors are positioned where the error happened in time
- `┊` compaction markers show where the context window was compressed
- The Transcript row aggregates all markers from its children
- Markers replace a single `█` character — they don't widen the bar
- Both marker types are visually distinct from the bar fill while remaining subtle
