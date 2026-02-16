# Timeline UI Spec


## 1. Sequential Sub-Agents

A coding agent that explores the codebase, plans an approach, then builds the solution. The Transcript row spans the full timeline and is selectable (to show the whole trajectory). Solver agents and Scoring are indented beneath it.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Transcript                                                  48.5k tokens │
├──────────────────────────────────────────────────────────────────────────┤
│ Transcript│██████████████████████████████████████████████████████│       │
│  Explore  │ ███████████                                          │  8.1k │
│  Plan     │             ████████                                 │  5.3k │
│  Build    │                      ████████████████████████████    │ 31.8k │
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
│  Build    │                             █████████████████████    │ 34.6k │
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
│  Build    │                      ████████████████████████████    | 31.8k │
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
│  Build       │                       ████████████████████████   │ 27.6k  │
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
{{< pagebreak >}}

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

## 9. Content Panel

The content panel sits below the timeline, separated by the resizable divider (section 8). It shows the selected agent's events and sub-agent launches in chronological order. All events are always expanded. Sub-agent cards appear inline at their launch point and are clickable to drill down.

### Events and Sub-Agent Cards

Build is selected, showing model calls, a tool call, and three sub-agent launches:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ← Transcript › Build                                      31.8k tokens   │
├──────────────────────────────────────────────────────────────────────────┤
│ Build    │██████████████████████████████████████████████████████│        │
│  Code    │ ██████████████████████                               │ 15.2k  │
│  Test    │                       ████████████████               │ 10.4k  │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│ ◆ MODEL                                                          2.1k    │
│ I'll start by reading the existing codebase to understand the            │
│ architecture before making changes.                                      │
│                                                                          │
│ ◇ TOOL read_file                                                 0.3s    │
│ path: "src/main.py"                                                      │
│ ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄               │
│ import os                                                                │
│ from app import create_app                                               │
│ ...                                                                      │
│                                                                          │
│ ◆ MODEL                                                          3.4k    │
│ Based on the code, I need to modify the authentication module.           │
│ Let me delegate the implementation...                                    │
│                                                                          │
│ ┌──────────────────────────────────────────────────────────────┐         │
│ │ Code                                        15.2k · 12.4s    │         │
│ │ "Implement the authentication changes"                       │         │
│ └──────────────────────────────────────────────────────────────┘         │
│                                                                          │
│ ◆ MODEL                                                          1.2k    │
│ Code changes complete. Running tests...                                  │
│                                                                          │
│ ┌──────────────────────────────────────────────────────────────┐         │
│ │ Test                                        10.4k ·  8.2s    │         │
│ │ "Run test suite and verify changes"                          │         │
│ └──────────────────────────────────────────────────────────────┘         │
│                                                                          │
│ ◆ MODEL                                                          0.6k    │
│ All tests passing. Changes complete.                                     │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

{{< pagebreak >}}
### Parallel Sub-Agents

Parallel sub-agents are grouped with a `┃` gutter connecting their cards:

```
│                                                                          │
│ ◆ MODEL                                                          1.8k    │
│ I'll research this from multiple angles...                               │
│                                                                          │
│ ┃ ┌──────────────────────────────────────────────────────────┐           │
│ ┃ │ Explore 1                                8.1k ·  6.2s    │           │
│ ┃ │ "Search for API documentation"                           │           │
│ ┃ └──────────────────────────────────────────────────────────┘           │
│ ┃ ┌──────────────────────────────────────────────────────────┐           │
│ ┃ │ Explore 2                                9.4k ·  7.8s    │           │
│ ┃ │ "Analyze existing codebase"                              │           │
│ ┃ └──────────────────────────────────────────────────────────┘           │
│                                                                          │
│ ◆ MODEL                                                          2.1k    │
│ Research complete. Synthesizing findings...                              │
│                                                                          │
```

### Errors and Compaction

A tool error uses the same `▲` marker as the timeline. Compaction appears as a horizontal divider:

```
│                                                                          │
│ ◇ TOOL web_search                                     ▲ ERROR    0.3s    │
│ query: "solar panel efficiency"                                          │
│ ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄               │
│ Error: Rate limit exceeded                                               │
│                                                                          │
│ ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄ COMPACTION ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄              │
│                                                                          │
│ ◆ MODEL                                                          1.5k    │
│ Continuing after context compression...                                  │
│                                                                          │
```

**Notes:**
- Clicking a sub-agent card drills down (same as double-click or `›` in the timeline)
- `▲ ERROR` and compaction dividers correspond to inline markers in the timeline bars
- `◆` / `◇` distinguish model calls from tool calls

## 10. Utility Agents

Utility agents (bash checkers, safety validators, etc.) can number in the dozens — one per tool call — and are rarely interesting. They never appear in the timeline. In the content panel, they are hidden by default behind a toggle.

### Hidden (Default)

A collapsed toggle indicates their presence:

```
│                                                                          │
│ ▸ 12 utility agents hidden                                               │
│                                                                          │
│ ◆ MODEL                                                          2.1k    │
│ I'll start by reading the codebase...                                    │
│                                                                          │
│ ◇ TOOL bash                                                     0.8s     │
│ command: "npm test"                                                      │
│ ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄               │
│ Tests passed: 42/42                                                      │
│                                                                          │
```

### Revealed

Toggling shows utility agents as single-line entries with `⚙`, inline where they ran:

```
│                                                                          │
│ ▾ 12 utility agents shown                                                │
│                                                                          │
│ ◆ MODEL                                                          2.1k    │
│ I'll start by reading the codebase...                                    │
│                                                                          │
│ ◇ TOOL bash                                                      0.8s    │
│ command: "npm test"                                                      │
│ ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄               │
│ Tests passed: 42/42                                                      │
│                                                                          │
│ ⚙ bash_checker                                            0.3k · 0.1s    │
│ ⚙ safety_validator                                        0.2k · 0.2s    │
│                                                                          │
```

**Notes:**
- `⚙` entries are single-line — no box, no task description
- Utility agents are never shown in the timeline, only in the content panel
- The toggle count reflects the selected agent's utility agents, not the whole trace

## 11. Branches

Branches represent alternative execution paths forked from a point in an agent's trajectory. They appear when an agent retries, backtracks, or explores multiple strategies. Each branch shares the same events up to the fork point, then diverges.

### Timeline: Inline Branch Marker

Branches don't get their own swimlane rows. Instead, a `↳` marker appears inline on the parent agent's bar at each fork point. Clicking the marker opens a popover listing the branches at that point. Selecting a branch from the popover drills down.

#### Branch Markers on Timeline Bars

Build has two child agents and a fork point with two branches:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ← Transcript › Build                                      31.8k tokens   │
├──────────────────────────────────────────────────────────────────────────┤
│ Build    │████████████↳████████████████████████████████████████████│     │
│  Code    │ ██████████████████████                                  │15.2k│
│  Test    │                       ████████████████                  │10.4k│
└──────────────────────────────────────────────────────────────────────────┘
```

#### Multiple Fork Points

Each fork point gets its own `↳` marker:

```
│ Build    │████████████↳████████████↳██████████████████████████████│      │
```

#### Branch Popover

Clicking a `↳` marker opens a popover listing the branches at that fork point. Each entry shows label, tokens, and duration:

```
┌──────────────────────────────────┐
│ ↳ branch 1        8.7k ·  6.1s   │
│ ↳ branch 2        5.1k ·  4.3s   │
└──────────────────────────────────┘
```

Clicking a branch entry drills down:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ← Transcript › Build › ↳ branch 1                          8.7k tokens   │
├──────────────────────────────────────────────────────────────────────────┤
│ ↳ branch 1 │██████████████████████████████████████████████████████│      │
│  Refactor  │ ████████████████████                                 │ 5.2k │
│  Validate  │                      ██████████████████████████████  │ 3.5k │
└──────────────────────────────────────────────────────────────────────────┘
```

**Notes:**
- `↳` markers replace a single `█` character — same pattern as error/compaction markers (section 5)
- The popover is lightweight — just a list, not a full panel
- Keeps the timeline compact; branches don't consume swimlane rows

### Content Panel: Branch Cards

Branch cards use dashed borders (`╌`) to distinguish from child agent cards (`─`). They appear inline at the fork point — after the `forkedAt` event — and show label, tokens, duration, and first model output preview. Clicking a branch card drills down.

#### Branch Cards at Fork Point

```
│                                                                          │
│ ◆ MODEL                                                          3.4k    │
│ The current approach isn't working. Let me try a different               │
│ strategy...                                                              │
│                                                                          │
│ ┌──────────────────────────────────────────────────────────────┐         │
│ │ Code                                        15.2k · 12.4s    │         │
│ │ "Implement the authentication changes"                       │         │
│ └──────────────────────────────────────────────────────────────┘         │
│                                                                          │
│ ┌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌┐             │
│ ╎ ↳ branch 1                                   8.7k ·  6.1 ╎             │
│ ╎ "Let me try a recursive approach instead"                ╎             │
│ └╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌┘             │
│ ┌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌┐             │
│ ╎ ↳ branch 2                                   5.1k ·  4.3 ╎             │
│ ╎ "Attempting a greedy algorithm approach"                 ╎             │
│ └╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌┘             │
│                                                                          │
│ ◆ MODEL                                                          1.2k    │
│ Tests passing. Changes complete.                                         │
│                                                                          │
```

**Notes:**
- Dashed borders (`╌` / `╎`) visually separate branch cards from child agent cards (`─` / `│`)
- Multiple branches at the same fork point appear consecutively
- Branch cards show the first model output as a preview, same as child agent cards
- Clicking a branch card drills down (same as selecting from the `↳` popover)

### Naming

- **Explicit branches**: use the span `name` from the transcript (e.g., `↳ retry`, `↳ backtrack`)
- **Auto-detected branches**: numbered sequentially — `↳ branch 1`, `↳ branch 2`, etc.
- The `↳` prefix is always shown to distinguish branches from child agents

## 12. Multiple Timelines

A single transcript can have multiple timeline interpretations. Each timeline is a named view with its own `TimelineSpan` tree — the same event stream parsed with different groupings, filters, or analytical lenses. For example, a default agent-centric timeline alongside a phase-based or domain-specific grouping.

### Data Model

A `Timeline` is a lightweight container:

- **name** — short label shown in the pill (e.g., "Agents", "Phases", "Tools")
- **description** — tooltip or subtitle explaining the view
- **root** — a `TimelineSpan` tree (init events folded into root, scoring as a child span)

### UI: Timeline Pills

When multiple timelines are available, a row of pills appears above the timeline panel. Clicking a pill switches the entire timeline and content panel to that view. Only one timeline is active at a time.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  [ Agents ]  [ Phases ]  [ Tools ]                                       │
├──────────────────────────────────────────────────────────────────────────┤
│ Transcript                                                  48.5k tokens │
├──────────────────────────────────────────────────────────────────────────┤
│ Transcript│██████████████████████████████████████████████████████│       │
│  Explore  │ ███████████                                          │  8.1k │
│  Plan     │             ████████                                 │  5.3k │
│  Build    │                      ████████████████████████████    │ 31.8k │
│  Scoring  │                                                   ███│  3.2k │
└──────────────────────────────────────────────────────────────────────────┘
```

### Behavior

- **Single timeline**: pills are hidden — no UI change from current design
- **Multiple timelines**: pills appear; the first timeline is selected by default
- Switching timelines resets drill-down, selection, and branch navigation to the new tree's root
- Each timeline maintains independent navigation state while active
- The active timeline pill is visually highlighted (filled background vs outline)

## 13. Custom Outline

By default, the content panel shows events in a flat chronological list. When a `TimelineSpan` has an `outline` attached, a sidebar appears on the left side of the content panel providing hierarchical navigation. This is primarily useful for custom timelines where the author wants to impose a meaningful structure on the event stream.

### Data Model

An `Outline` is a tree of `OutlineNode` entries, each referencing an event by UUID:

- **event** — UUID of an event in the agent's content
- **children** — optional nested `OutlineNode` list

### Layout

The outline sidebar sits to the left of the content panel, separated by a vertical divider. Outline entries are shown as a collapsible tree. Clicking an entry scrolls the content panel to that event.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ← Transcript › Build                                      31.8k tokens   │
├──────────────────────────────────────────────────────────────────────────┤
│ Build    │██████████████████████████████████████████████████████│        │
│  Code    │ ██████████████████████                               │ 15.2k  │
│  Test    │                       ████████████████               │ 10.4k  │
├──────────────────────────────────────────────────────────────────────────┤
│          │                                                               │
│ Outline  │  ◆ MODEL                                         2.1k        │
│          │  I'll start by reading the existing codebase...              │
│ ▾ Setup  │                                                               │
│   Read   │  ◇ TOOL read_file                                0.3s        │
│   Config │  path: "src/main.py"                                         │
│ ▾ Impl   │  ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄              │
│   Code   │  import os                                                    │
│   Test   │  from app import create_app                                   │
│ ▸ Review │  ...                                                          │
│          │                                                               │
│          │  ◆ MODEL                                         3.4k        │
│          │  Based on the code, I need to modify the auth...             │
│          │                                                               │
└──────────────────────────────────────────────────────────────────────────┘
```

### Behavior

- **No outline**: sidebar is hidden — content panel uses full width (default)
- **With outline**: sidebar appears; entries are collapsible tree nodes
- Clicking an outline entry scrolls the content panel to the referenced event and highlights it
- The currently visible event is highlighted in the outline (scroll tracking)
- Outline entries display the event's label (model output preview, tool name, etc.)

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
- Each timeline has its own `Timeline` with a root `TimelineSpan` tree.
- Switching resets drill-down, selection, and branch navigation.

### Custom Outline

- Optional sidebar in the content panel when a `TimelineSpan` has an `outline`.
- Collapsible tree with scroll-tracking and click-to-scroll.

## 2. Data Model (timeline.ts)

The TypeScript data model that powers the timeline:

### Core Types

```typescript
interface TimelineEvent {
  type: "event";
  event: Event;
  startTime: Date;
  endTime: Date;
  totalTokens: number;
}

interface TimelineSpan {
  type: "span";
  id: string;
  name: string;
  spanType: string | null;        // "agent", "scorer", "tool", or null
  content: (TimelineEvent | TimelineSpan)[];
  branches: TimelineBranch[];
  utility: boolean;
  outline?: Outline;
  startTime: Date;
  endTime: Date;
  totalTokens: number;
}

interface TimelineBranch {
  type: "branch";
  forkedAt: string;              // UUID of the fork-point event
  content: (TimelineEvent | TimelineSpan)[];
  startTime: Date;
  endTime: Date;
  totalTokens: number;
}

interface Timeline {
  name: string;
  description: string;
  root: TimelineSpan;
}

interface Outline {
  nodes: OutlineNode[];
}

interface OutlineNode {
  event: string;                 // UUID reference
  children?: OutlineNode[];
}
```

### Processing Pipeline

`buildTimeline(events: Event[]) -> Timeline`:

1. Build span tree from flat events (span_begin/span_end pairing)
2. Find phase spans (init/solvers/scorers) or treat entire stream as agent
3. Init events are folded into the root `TimelineSpan.content` as early events
4. Build agent hierarchy from explicit `type='agent'` spans or tool-spawned agents
5. Scoring spans become `TimelineSpan` children with `spanType: "scorer"`
6. Classify utility agents (single-turn + different system prompt from parent)
7. Detect branches (explicit `type='branch'` spans or auto-detected via duplicate input fingerprints)

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
│   ├── transcript/   # Rendering engine: timeline.ts, outline, event viewers, transforms
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
2. `buildTimeline()` builds the semantic tree as a `Timeline` with root `TimelineSpan`
3. `transform()` / `flatten()` / `treeify()` prepare the display tree
4. `TranscriptVirtualList` renders via Virtuoso with event-specific viewers
5. `TranscriptOutline` provides tree sidebar navigation

### Timeline Current State

- `TimelinePanel` at `/timeline` route — placeholder with scenario dropdown
- `syntheticNodes.ts` provides 10 mock `Timeline` scenarios (sequential, iterative, parallel, branches, utilities, deep nesting, etc.)
- No visual implementation yet

### Key Patterns

- Module CSS for component scoping
- `AsyncData<T>` discriminated union for loading/data/error
- VSCode Elements for form controls and split layouts
- Bootstrap for grid/layout utilities
- Virtualized rendering for large datasets

# Timeline Implementation Design

Design decisions and architecture for implementing the timeline UI.

## 1. State Management

### URL State (via `replace` navigation)

Structural navigation state lives in URL query params, updated via `navigate(..., { replace: true })` so no browser history entries are created. The timeline's own navigation (breadcrumbs, Escape, chevrons) controls drill-down; browser back controls page-level navigation.

Parameters (all lowercase, snake_case for multi-word):

- `path=build/test` — drill-down breadcrumb path (agent names joined by `/`)
- `selected=code` — which row is selected
- `timeline_view=agents` — which timeline pill is active (only when multiple timelines exist)

Agent names in URL params are **case-insensitive** — resolved against `TimelineSpan.name` via `toLowerCase()` comparison.

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

**Input:** `Timeline` (pre-built). Tree building happens upstream — typically a `useMemo` in the container:

```typescript
const tl = useMemo(() => buildTimeline(events), [events]);
const timeline = useTimeline(tl);
```

For multiple timelines, the container selects which one to pass:

```typescript
const timelines = useMemo(() => buildTimelines(events), [events]);
const timeline = useTimeline(timelines[activeIndex]);
```

**Responsibilities:**
- Reads URL params (`path`, `selected`) to determine navigation state
- Resolves the path to a specific `TimelineSpan` (case-insensitive matching)
- Computes swimlane rows from the resolved node (separate `useMemo`)
- Provides navigation actions that update URL via `replace`

**Return value (sketch):**
```typescript
const timeline = useTimeline(tl);
timeline.node          // resolved TimelineSpan for current path
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
- Accept a `TimelineSpan` (not just raw `Event[]`) as input
- Render child `TimelineSpan`s inline as sub-agent cards (clickable)
- Render `TimelineBranch` cards with dashed borders at fork points
- Sub-agent card clicks call `timeline.drillDown()` — navigation flows through the `useTimeline` hook
- Error and compaction markers are not needed in the content panel — these are already visible as regular events in the content stream

**TranscriptOutline:**
- Accept a `TimelineSpan` to build its tree (currently works from raw events)
- Support custom `Outline` attached to a `TimelineSpan` (replaces the auto-generated outline)
- When a custom outline exists, use its `OutlineNode` tree directly instead of the visitor-based pipeline

### Utility Agent Visibility

The utility agent toggle (`▸ N utility agents hidden` / `▾ N utility agents shown`) lives in the surrounding chrome, not inside the content panel. Utility agent visibility is a Zustand store concern — the content panel simply renders whatever content it receives. Filtering happens upstream before events reach the content panel.

### Navigation Flow

Clicking a sub-agent card in the content panel is a drill-down navigation:

```
User clicks "Build" card in ContentPanel
  → calls timeline.drillDown("build")
  → URL updated via replace: ?path=build
  → useTimeline resolves new path → new TimelineSpan
  → Timeline re-renders with new breadcrumbs + child rows
  → ContentPanel re-renders with Build's content
```

This unifies navigation — whether the user clicks a swimlane row chevron in the timeline or a sub-agent card in the content panel, the same `useTimeline` hook handles it.

## 4. Swimlane Row Computation

### Data Model

A swimlane row is a sequence of spans sharing an agent name. Each span is either a single agent or a parallel cluster of agents:

```typescript
interface SingleSpan {
  agent: TimelineSpan;
}

interface ParallelSpan {
  agents: TimelineSpan[];
}

type RowSpan = SingleSpan | ParallelSpan;

interface SwimLaneRow {
  name: string;
  spans: RowSpan[];
  totalTokens: number;
  startTime: Date;
  endTime: Date;
}
```

Properties like `kind` (single/iterative/parallel) and `drillable` (has children) are not stored — they are derivable from the data and computed as needed by consumers.

### Grouping Algorithm

1. Collect child `TimelineSpan`s from the current node's `content` (skip `TimelineEvent`s and utility spans)
2. Group by name (case-insensitive)
3. Within each name group, cluster into spans:
   - Non-overlapping spans become separate `SingleSpan` entries on the row (iterative pattern)
   - Overlapping spans (within a tolerance of ~100ms to account for spawn skew) become a `ParallelSpan`
   - If any overlap exists within the name group, the entire group is treated as parallel
   - A row can mix single and parallel spans (e.g., a single Explore, then later three Explore in parallel)
4. Order rows by earliest start time across their spans
5. The parent `TimelineSpan` is always the top row (full-width bar)
6. Scoring is a standard child `TimelineSpan` with `spanType: "scorer"` — appears as a regular swimlane row

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

Where `viewStart`/`viewEnd` come from the current drill-down level's `TimelineSpan` time range.

### Theming

Fills, markers, and selection highlighting use CSS custom properties (VSCode theme variables) for light/dark mode compatibility.

## 6. `useTimeline` Hook — Detailed Behavior

### Edge Cases

- **Invalid path**: If the URL `path` param doesn't resolve to a valid node (e.g., stale URL from a different transcript), fall back to the root. No error state — just silently reset.
- **Flat transcript** (no agents): The single root `TimelineSpan` is the parent row and the content source. Timeline shows one bar.

### Selection Semantics

Selecting a row **fully replaces** the content panel with that node's content. It does not scroll within the parent's events — the selected node's `TimelineSpan` becomes the content panel's data source.

### Init and Scoring

Init events are folded into the root `TimelineSpan.content` as early events — there is no separate init section. Scoring is a child `TimelineSpan` with `spanType: "scorer"` that appears naturally in the root's content and as a swimlane row.

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

- `buildTimeline(events)` — memoized via `useMemo` keyed on `events`
- Swimlane row computation — separate `useMemo` keyed on the resolved `TimelineSpan`, deferred from the tree build
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

## 9. Content Panel ↔ TimelineSpan Integration

### Approach: Direct rendering from TimelineSpan content

The content panel builds a flat rendering list directly from `TimelineSpan.content`, bypassing the existing transform pipeline (no fixups, treeify, transform, flatten). The `TimelineSpan` is already the structured form — the transform pipeline exists to build structure from raw events, which is unnecessary here.

However, the existing pipeline encodes implicit rules and behaviors (e.g., collapsing pending events, sandbox event grouping, `sample_init` injection, default collapse decisions, span unwrapping). These rules must be audited during implementation — some are irrelevant in the TimelineSpan context (the tree is already structured), but others may need to be reflected in the new rendering path. Document each rule as it's encountered.

### Content Item Types

A discriminated union for the virtual list:

```typescript
type ContentItem =
  | { type: "event"; eventNode: TimelineEvent }
  | { type: "agent_card"; agentNode: TimelineSpan }
  | { type: "branch_card"; branch: TimelineBranch }
  | { type: "parallel_group"; agents: TimelineSpan[] }
```

### Building the Content List

Walk `TimelineSpan.content` chronologically:

1. **TimelineEvent** items → `{ type: "event", eventNode }`
2. **Child TimelineSpan** items → `{ type: "agent_card", agentNode }` (or `parallel_group` if consecutive same-name spans overlap)
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
- **`↳` Branch** — from `TimelineSpan.branches`. Each branch's `forkedAt` UUID is resolved to a timestamp.

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
  () => collectMarkers(node, depth),
  [node, depth]
);
```

No pre-computation on swimlane rows — avoids computing multiple depth variants and keeps the row data model simple. The scan is cheap (small number of events per view level).

### Positioning

Each marker has a timestamp, mapped to a percentage position using the same formula as bar fills:

```
percent = (marker.timestamp - viewStart) / (viewEnd - viewStart) * 100
```

### Branch Markers

Branch markers (`↳`) are separate from error/compaction markers. They come from `TimelineSpan.branches` — each branch's `forkedAt` UUID is resolved to the corresponding event's timestamp. Branch markers only appear on the row that owns the branches, not aggregated upward.

## 11. Resizable Divider

### Layout

The timeline panel and content panel are separated by a VSCode Elements split layout divider (`VscodeSplitLayout`). The timeline panel sits above, the content panel below.

### Default Height

The timeline panel shows up to **5 rows** by default (parent row + up to 4 child rows). If there are more rows, the timeline area scrolls internally. The divider allows the user to customize the split.

### Persistence

The divider position is stored in Zustand (persisted) so it survives VSCode tab switches and session restarts.


# Phased Implementation

All new files go in `src/inspect_scout/_view/www/src/app/timeline/`.

## Working Guidelines

1. **One phase at a time.** Implement, test, and verify each phase before moving to the next.
2. **Review before commit.** After tests pass, pause and review the code together before committing. Do not auto-commit.
3. **Full tests at each step.** Every phase produces both an implementation file and a test file. Run `pnpm test` and `pnpm check` to verify.
4. **Use synthetic scenarios.** Import `timelineScenarios` from `syntheticNodes.ts` for realistic test data. Build minimal inline helpers for edge cases.
5. **Pure logic first.** Phases 1–3 are pure functions with no DOM or React dependencies. Phase 4 introduces the hook layer.
6. **Mirror Python changes.** If a phase touches `timeline.ts`, the corresponding changes must be mirrored in `timeline.py` and both test suites must pass.

## Phase 1: Swimlane Row Computation (Complete)

**Files:** `swimlaneRows.ts`, `swimlaneRows.test.ts`
**Commit:** `b8b384ed`

### What was done

Implemented `computeSwimLaneRows(node: TimelineSpan): SwimLaneRow[]` which transforms a TimelineSpan's children into rows for rendering as horizontal swimlane bars.

**Types:**
- `SingleSpan { agent: TimelineSpan }` — one span occupying a time range
- `ParallelSpan { agents: TimelineSpan[] }` — overlapping spans on the same row
- `RowSpan = SingleSpan | ParallelSpan` — with `isSingleSpan()` / `isParallelSpan()` guards
- `SwimLaneRow { name, spans, totalTokens, startTime, endTime }`

**Algorithm:**
1. Parent row first (the node itself as a SingleSpan)
2. Filter children to non-utility TimelineSpans
3. Group by name (case-insensitive, display name from first encountered)
4. Cluster spans: check pairwise overlap with 100ms tolerance — any overlap makes the entire group a ParallelSpan, otherwise each span is a separate SingleSpan
5. Order rows by earliest start time
6. Scoring is a regular child TimelineSpan with `spanType: "scorer"` — no special handling needed

### Non-nullable times

`startTime`/`endTime` are non-nullable across both Python (`timeline.py`) and TypeScript (`timeline.ts`), since every Event has a required timestamp field. Container nodes use an epoch sentinel (`new Date(0)` / `datetime(1970, 1, 1, tzinfo=timezone.utc)`) for the degenerate empty-content case.

**Tests:** 20 tests covering sequential (S1), iterative (S2), parallel (S4), flat (S7), many-rows (S8), utility filtering (S10), custom edge cases (case-insensitive grouping, no children, token aggregation, time ranges).

## Phase 2: Content Item Building (Complete)

**Files:** `contentItems.ts`, `contentItems.test.ts`
**Commit:** `3401bfca`

### What was done

Implemented `buildContentItems(node: TimelineSpan): ContentItem[]` which transforms a TimelineSpan into a flat list of items for the detail panel.

**Types:**
- `EventItem { type: "event", eventNode }` — a single event
- `AgentCardItem { type: "agent_card", agentNode }` — a child agent rendered as a card
- `BranchCardItem { type: "branch_card", branch }` — a branch fork point
- `ContentItem` — discriminated union of the above

**Algorithm:**
1. Walk `node.content` chronologically: TimelineEvent → EventItem, TimelineSpan → AgentCardItem
2. Insert branch cards: for each branch, find the event matching `forkedAt` UUID and insert a BranchCardItem after it. Multiple branches at the same fork point appear consecutively. Unresolvable UUIDs → append at end.

No parallel grouping type — parallel agents appear as consecutive AgentCardItems. The UI layer detects adjacency and renders visual grouping. Utility agents are always included; filtering is a UI concern.

**Tests:** 16 tests covering sequential (S1), flat (S7), parallel (S4), iterative (S2), utility agents (S10, drilled into Build), deep nesting (S3), branches with unmatched UUIDs (S11a, S11b), matched UUID insertion, multiple branches at same fork point, branches at different positions, mixed matched/unmatched, edge cases.

## Phase 3: Marker Computation (Complete)

**Files:** `markers.ts`, `markers.test.ts`
**Commit:** `4c4b84d5`

### What was done

Implemented `collectMarkers(node: TimelineSpan, depth: MarkerDepth): TimelineMarker[]` which finds error, compaction, and branch markers at configurable depth.

**Types:**
- `MarkerKind = "error" | "compaction" | "branch"`
- `TimelineMarker { kind, timestamp, reference }` — reference is event UUID or forkedAt ID
- `MarkerDepth = "direct" | "children" | "recursive"`

**Exported helpers:**
- `isErrorEvent(event)` — ToolEvent with `.error !== null`, or ModelEvent with `.error !== null` or `.output.error !== null`
- `isCompactionEvent(event)` — `event.event === "compaction"`

**Algorithm:**
- Recursion controlled by `shouldDescend(depth, currentLevel)`: direct = never descend, children = descend at level 0 only, recursive = always descend
- Branch markers resolved by scanning `node.content` for the event matching `forkedAt` UUID → timestamp. Unresolvable branches silently dropped.
- All markers sorted by timestamp.

**Tests:** 23 tests covering isErrorEvent (6 cases: ToolEvent with/without error, ModelEvent with event.error, output.error, clean, CompactionEvent), isCompactionEvent (3 cases), S5 inline markers (error + compaction from child agent), S7 flat (empty), depth modes (direct/children/recursive with parent-child-grandchild), branch markers (matched UUID, unmatched, empty forkedAt, S11a synthetic), sort order (unsorted input, mixed types), edge cases (empty agent, normal-only events).

## Phase 4: `useTimeline` Hook (Complete)

**Files:** `useTimeline.ts`, `useTimeline.test.ts`

### What was done

Implemented the `useTimeline` hook and three pure helper functions that drive URL-based drill-down navigation through the transcript node tree.

**Pure functions** (exported, testable without DOM):

- `parsePathSegment(segment)` — splits `"my-agent-3"` into `{ name: "my-agent", spanIndex: 3 }`. Only the trailing `-N` is consumed (N must be >= 1). `-0` is treated as part of the name.
- `resolvePath(timeline, pathString)` — walks the tree from `timeline.root`, splitting path on `/`, matching child spans case-insensitively. `-N` suffix selects the Nth same-named child (1-indexed). Returns `null` for invalid paths.
- `buildBreadcrumbs(pathString, timeline)` — builds `BreadcrumbSegment[]` starting with root. Each segment resolves its label from the actual span name when possible, falls back to the raw segment string.

**Hook:** `useTimeline(timeline: Timeline): TimelineState`

- Reads `path` and `selected` from `useSearchParams()`
- Resolves path → `TimelineSpan`
- Falls back to root on invalid path
- Init events are already in root content; scoring is a child `TimelineSpan` with `spanType: "scorer"` — no special folding needed
- Computes `rows` via `computeSwimLaneRows()`, `breadcrumbs` via `buildBreadcrumbs()`
- Navigation: `drillDown(name, spanIndex?)`, `goUp()`, `select(name | null)` — all update URL via `setSearchParams(..., { replace: true })`

**Tests:** Pure function tests (no jsdom): parsePathSegment (7 cases), resolvePath (12 cases including root, named, case-insensitive, nested S3, span index S2, invalid, scoring, init, out-of-range), buildBreadcrumbs (5 cases). Hook tests (jsdom + `MemoryRouter` wrapper): S1 root resolution, drill-down, S7 flat, S4 parallel, selected param, nested breadcrumbs, invalid fallback, scoring as child span, drillDown/goUp/select navigation, span index drill-down, S2 iterative spans.

## Phase 5: Timeline UI Components (Complete)

### Phase 5a: Swimlane Layout

**Files:** `swimlaneLayout.ts`, `swimlaneLayout.test.ts`

Implemented `computeRowLayouts(rows, viewStart, viewEnd)` which positions swimlane bars as percentage-based rectangles within a time range.

**Types:**
- `PositionedBar { left, width, agent, drillable }` — a bar with percentage position, the source `TimelineSpan`, and whether it has children to drill into
- `PositionedMarker { left, kind, reference }` — a marker glyph at a percentage position. `reference` carries the event UUID (for error/compaction) or `forkedAt` UUID (for branch markers), enabling click handlers to look up related data.
- `RowLayout { name, bars, markers, tokenLabel }` — complete layout for one swimlane row

**Algorithm:**
- `computeBarPosition(start, end, viewStart, viewEnd)` — clamps to `[0, 100]` percentage range
- Drillability: a span is drillable if it has child spans (`content.some(c => c.type === "span")`)
- Token labels use `formatTokenCount()` (e.g., `"8.1k"`, `"1.2M"`)
- Markers collected via `collectMarkers(parentSpan, "children")` and positioned using the same percentage formula

**Tests:** 15 tests covering S1 sequential (positions, drillability, token labels, markers), S2 iterative (multiple bars per row), S4 parallel, S7 flat, marker positioning, edge cases.

### Phase 5b: Timeline Header Components

**Files:** `TimelineBreadcrumb.tsx`, `TimelineBreadcrumb.module.css`, `TimelinePills.tsx`, `TimelinePills.module.css`, `TimelineMinimap.tsx`, `TimelineMinimap.module.css`

**TimelineBreadcrumb:** Renders `← Transcript › Build › Refactor` with clickable segments. Uses `BreadcrumbSegment[]` from `buildBreadcrumbs()`. The `←` back button navigates up one level. Duration displayed on the right via `formatDuration()` from `utils/format.ts`.

**TimelinePills:** Shows aggregate stats (total tokens, duration, model name) as small pill badges in the header area.

**TimelineMinimap:** A thin horizontal strip showing the current zoom position within the root timeline when drilled into a child span. Rendered inside the swimlane grid using `display: contents` to participate in the 3-column layout. Shows a 2px rail track with two vertical blue bar markers at the zoom boundaries (the drilled-into span's start/end relative to the root). Uses `computeBarPosition()` for percentage positioning. Hidden at root level (when the view spans the full timeline).

### Phase 5c: SwimLane Panel

**Files:** `SwimLanePanel.tsx`, `SwimLanePanel.module.css`

The main swimlane visualization component rendering a CSS grid with three columns: labels (left), bars (center), token counts (right).

**Features:**
- **Row rendering:** Each `RowLayout` renders as a grid row. Parent row has a distinct background. Child rows show bar fills with percentage-based `left`/`width` styling.
- **Selection:** Clicking a row sets `selected` in URL search params. Selected row gets a highlight ring. Clicking the selected row deselects it.
- **Keyboard navigation:** Arrow keys (`↑`/`↓`) cycle through rows, `Enter` drills into a drillable row, `Escape` clears selection. Parent row is included in the arrow key cycle.
- **Marker glyphs:** Inline markers (`▲` error, `┊` compaction, `↳` branch) rendered at their percentage positions on the bar area.
- **Branch popover:** Clicking a `↳` branch marker opens a popover listing branches at that fork point. Uses the existing `PopOver` component with `hoverDelay={-1}` (click-to-open pattern). Each entry shows branch label, token count, and duration. Clicking an entry drills into the branch.
- **Branch lookup:** `findBranchesByForkedAt(content, forkedAt)` recursively searches the span tree for branches matching a `forkedAt` UUID, returning both the branches and the owner span's path. This is necessary because branches may be on deeply nested child spans, not the currently viewed node.
- **Max height:** CSS variable `--swimlane-minimap-height: 14px` accounts for the minimap in the max-height calculation, preventing scrolling when 5 rows plus minimap are displayed.

### Phase 5d: Timeline Panel

**Files:** `TimelinePanel.tsx`

Top-level panel wiring `useTimeline` state to the UI components. Passes `node`, `rows`, `breadcrumbs`, and navigation callbacks (`drillDown`, `goUp`, `select`) to child components. Connects `onBranchDrillDown` from SwimLanePanel to `state.drillDown`. Passes root timeline start/end times to the minimap for zoom position calculation.

### Phase 5e: Branch Navigation

**Files:** `useTimeline.ts` (extended), `useTimeline.test.ts` (extended)

Extended the path system to support drilling into branches via `@branch-N` path segments, where N is the 1-indexed branch index among branches sharing the same `forkedAt` UUID.

**Path resolution:** `resolveBranchSegment(segment, parent)` detects `@branch-` prefix, parses the index, looks up `parent.branches`, and returns a synthetic span wrapping the branch content via `createBranchSpan`.

**`createBranchSpan` optimization:** For single-span branches (branch content contains exactly one child span), returns the child span directly with a `↳` prefix on its name. This avoids double-rendering where both a synthetic wrapper and the single child would appear as separate swimlane rows.

**`deriveBranchLabel`:** Uses the first child span's name if one exists (e.g., "Refactor"), otherwise falls back to "Branch N".

**Breadcrumb support:** `buildBreadcrumbs` handles `@branch-N` segments by calling `resolveBranchSegment` to get the resolved label (e.g., `↳ Refactor`) instead of showing the raw path segment.

**Tests:** 5 new tests: branch path resolution (valid index, out-of-range), breadcrumb labels for branch paths, single-branch and multi-branch drill-down scenarios. Uses `S11A_BRANCHES` constant extracted from synthetic node data for stable test assertions.

### Supporting Changes

**`syntheticNodes.ts`:** Added optional `uuid` parameter to `makeModelEventNode()`. Set UUIDs on fork-point events in S11a/S11b so branch markers resolve correctly. Added Explore span to S3 for more realistic timeline proportions.

**`utils/format.ts`:** `formatDuration(start, end)` extracted as a shared utility (was previously defined locally in `TimelineBreadcrumb.tsx`). Takes two `Date` objects and returns a human-readable duration string.


