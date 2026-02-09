---
title: Timeline UI Design
format: typst
---

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
