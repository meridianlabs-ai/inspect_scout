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
- Init phase is hidden by default
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
- Token counts are aggregated across all spans for each agent

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
- `Escape` key also returns to parent level
- Each breadcrumb segment is clickable

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
- Clicking any breadcrumb segment jumps directly to that level
- No limit on nesting depth

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
- Token count on the group row is the sum of all instances
- At full width, timing differences between instances are much easier to see

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
- The Transcript row aggregates all markers from its children
- Markers replace a single `█` character — they don't widen the bar

## 6. Selection and Navigation

Single click selects a row (driving the content panel below). Drill-down is a separate action via a `›` chevron attached to each bar, or double-click. This preserves browsing — you can click between sibling agents to compare their events without navigating in and out.

### Selected State (Sequential)

Build is selected. Chevrons on each bar indicate drillable agents:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Transcript                                                  48.5k tokens │
├──────────────────────────────────────────────────────────────────────────┤
│ Transcript│██████████████████████████████████████████████████████│       │
│  Explore  │ ██████████›                                          │  8.1k │
│  Plan     │             ███████›                                 │  5.3k │
│▸ Build    │                      ███████████████████████████████›│ 31.8k │
│  Scoring  │                                                   ███│  3.2k │
└──────────────────────────────────────────────────────────────────────────┘
```

### Selected State (Iterative)

Each span gets its own chevron — you can drill into a specific invocation:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Transcript                                                  61.5k tokens │
├──────────────────────────────────────────────────────────────────────────┤
│ Transcript│██████████████████████████████████████████████████████│       │
│▸ Explore  │ ██████›        █████›                                │ 14.5k │
│  Plan     │         █████›        ████›                          │  9.2k │
│  Build    │                             ██████████████████████›  │ 34.6k │
│  Scoring  │                                                   ███│  3.2k │
└──────────────────────────────────────────────────────────────────────────┘
```

### Interactions

| Action | Effect |
|--------|--------|
| Click row | Select — highlights row, shows its events in content panel |
| Click `›` on bar | Drill down into that specific agent span |
| Double-click bar | Drill down (shortcut) |
| `Enter` | Drill down into selected row |
| `Escape` | Zoom out one level (or deselect if at top) |
| `↑` / `↓` | Move selection between rows |

**Notes:**
- Leaf agents (Scoring) and the Transcript row have no chevron
- In the iterative case, clicking `›` on a specific span drills into just that invocation
- Selection changes only update the content panel — the timeline stays stable

## 7. Flat Transcript (No Sub-Agents)

A simple eval with no agent hierarchy — just model calls and tool calls. The timeline shows a single Transcript bar. Inline markers provide landmarks for navigating the execution.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Transcript                                                  12.4k tokens │
├──────────────────────────────────────────────────────────────────────────┤
│ Transcript│████████████████████▲█████████┊███████████████████████│       │
└──────────────────────────────────────────────────────────────────────────┘
```

**Notes:**
- Compact timeline leaves maximum vertical space for the content panel

## 8. Timeline Height

The timeline panel height adapts to content, up to a cap of 6 rows. A resizable divider between the timeline and content panel lets users override the default.

### Behavior

- **Adaptive**: timeline grows to fit its rows — 2 agents = 2 rows, no wasted space
- **Cap at 6 rows**: beyond 6, the swimlane area scrolls internally
- **Resizable divider**: draggable border between timeline and content panel

**Notes:**
- When scrolled, the Transcript parent row could optionally stay pinned at the top
