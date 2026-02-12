# Timeline UI Prototype Implementation Plan

## Context

We need to build the visual timeline UI prototype in the existing `src/app/timeline/` directory. The prototype renders swimlane-based timeline bars from synthetic `TranscriptNodes` data, with drill-down navigation, selection, breadcrumbs, and a basic content panel. All 10 synthetic scenarios should work by the end.

The placeholder `TimelinePanel.tsx` already has a scenario dropdown — we'll build the visualization into its `.content` area.

## Phased Implementation

### Phase 1: Swimlane Row Computation (pure data)

Create `swimlane.ts` — types and pure `computeSwimLaneRows()` function.

**Types:**
```typescript
interface SingleSpan { agent: AgentNode }
interface ParallelSpan { agents: AgentNode[] }
type TimelineSpan = SingleSpan | ParallelSpan
interface SwimLaneRow {
  name: string;
  spans: TimelineSpan[];
  totalTokens: number;
  startTime: Date;
  endTime: Date;
  section?: "scoring";
}
```

**Algorithm:**
1. Parent AgentNode → top row (full-width SingleSpan)
2. Collect non-utility child AgentNodes from `content`
3. Group by `name.toLowerCase()`
4. Per group: sort by startTime, detect overlap (100ms tolerance) → SingleSpan (iterative) or ParallelSpan
5. Order rows by earliest start time
6. Append scoring SectionNode as bottom row if present

**Token formatting:** Add `formatTokenCount()` to `src/utils/format.ts` — `48500 → "48.5k"`

**Test file:** `swimlane.test.ts` — data-driven tests using synthetic scenarios (S1: 5 rows, S2: iterative spans, S4: parallel, S7: 1 row, S8: 11 rows, S10: utility filtered)

**Files:**
- `src/app/timeline/swimlane.ts` (new)
- `src/app/timeline/swimlane.test.ts` (new)
- `src/utils/format.ts` (add `formatTokenCount`)

---

### Phase 2: `useTimeline` Hook + Path Resolution

Create `useTimeline.ts` — hook that manages navigation state and computes rows.

**Path resolution** (`resolvePath` — extracted as pure function for testability):
- Split path string on `/`, walk agent tree matching `name.toLowerCase()`
- Handle `-N` suffix for span disambiguation (1-indexed)
- Invalid path → silent fallback to root
- Build breadcrumb segments as we walk

**Hook returns:** `{ node, rows, breadcrumbs, selectedIndex, drillDown(), goUp(), select(), navigateTo() }`

**State:** Local `useState` for `path` and `selectedIndex` (prototype — migrate to URL params later). Reset on scenario change via `useEffect` keyed on `tree`.

**Files:**
- `src/app/timeline/useTimeline.ts` (new)
- `src/app/timeline/useTimeline.test.ts` (new — test `resolvePath` pure function)

---

### Phase 3: Timeline Swimlanes (first visual render)

Create `TimelineSwimlanes.tsx` — CSS Grid with swimlane bars.

**Layout:** Each row is a 3-column CSS Grid: `[label] [bar-area] [tokens]`

**Bar area:** Absolutely positioned `<div>` fills using percentage `left`/`width`:
```
percent = (timestamp - viewStart) / (viewEnd - viewStart) * 100
```

**Rendering:** For each row, for each span, compute and render fill divs. Parent row gets a muted style. Multiple fills per row for iterative agents. Parallel spans get envelope fill + `(N)` badge.

**Wire into TimelinePanel:** Replace the empty `.content` div with the swimlanes component, passing `timeline.rows` and time range.

**Scenarios working after Phase 3:** S1 (Sequential), S2 (Iterative), S4 (Parallel), S7 (Flat), S8 (Many rows)

**Files:**
- `src/app/timeline/TimelineSwimlanes.tsx` (new)
- `src/app/timeline/TimelineSwimlanes.module.css` (new)
- `src/app/timeline/TimelinePanel.tsx` (modify — wire up hook + swimlanes)

---

### Phase 4: Header + Selection + Drill-Down + Keyboard

Create `TimelineHeader.tsx` — breadcrumb bar.

**Header layout:** `[← back] [Transcript › Build › Test] ... [31.8k tokens]`
- Back arrow visible only when drilled in
- Each breadcrumb segment clickable
- Token count right-aligned

**Selection in swimlanes:**
- Click row → `onSelect(index)` → highlights row (▸ indicator, bolder fill)
- Selection updates which content is shown below

**Drill-down:**
- `›` chevron rendered at right edge of drillable fills (agents with children)
- Chevron click → `onDrillDown(agentId)`
- Double-click bar → drill down
- Rows without children (scoring, leaf agents) → no chevron

**Keyboard** (timeline container gets `tabIndex={0}`):
- `↑`/`↓` → move selection between rows
- `Enter` → drill down into selected
- `Escape` → go up one level, or deselect at root

**Scenarios working after Phase 4:** S3 (Deep Nesting — drill 3 levels), all selection/navigation scenarios

**Files:**
- `src/app/timeline/TimelineHeader.tsx` (new)
- `src/app/timeline/TimelineHeader.module.css` (new)
- `src/app/timeline/TimelineSwimlanes.tsx` (modify — add selection, chevrons, keyboard, double-click)
- `src/app/timeline/TimelineSwimlanes.module.css` (modify — selection + chevron styles)

---

### Phase 5: Content Panel + Resizable Divider

Create `ContentPanel.tsx` — shows selected agent's content.

**Content items** built from `AgentNode.content`:
- `EventNode` → minimal event card (type badge + summary)
- Child `AgentNode` → sub-agent card (name, tokens, duration) in solid border box, clickable → drill down
- `Branch` → branch card with dashed border, `↳` prefix, clickable → drill into branch

**Resizable divider:** Simple drag handle between timeline and content panel. Parent maintains `timelineHeight` state. CSS `cursor: row-resize`.

**Utility agents:** When selected agent has utility children, show toggle (`▸ N utility agents hidden` / `▾ shown`). Hidden by default. Component-local state.

**Scenarios working after Phase 5:** S10 (Utility toggle), S11a/S11b (Branch cards in content)

**Files:**
- `src/app/timeline/ContentPanel.tsx` (new)
- `src/app/timeline/ContentPanel.module.css` (new)
- `src/app/timeline/ResizableDivider.tsx` (new)
- `src/app/timeline/ResizableDivider.module.css` (new)
- `src/app/timeline/TimelinePanel.tsx` (modify — compose header + swimlanes + divider + content)

---

### Phase 6: Polish

- **Inline markers:** `↳` branch fork markers on parent bars (resolve `forkedAt` to timestamp → position at %)
- **Adaptive height:** Timeline section grows to fit up to 6 rows, scrolls internally beyond that
- **Spacing and visual refinement** based on visual testing across all 10 scenarios

**Scenarios working after Phase 6:** S5 (Inline markers), S11b (multiple fork markers)

---

## Key Files Modified/Created

| File | Action | Phase |
|------|--------|-------|
| `src/app/timeline/swimlane.ts` | Create | 1 |
| `src/app/timeline/swimlane.test.ts` | Create | 1 |
| `src/utils/format.ts` | Modify (add formatTokenCount) | 1 |
| `src/app/timeline/useTimeline.ts` | Create | 2 |
| `src/app/timeline/useTimeline.test.ts` | Create | 2 |
| `src/app/timeline/TimelineSwimlanes.tsx` | Create | 3 |
| `src/app/timeline/TimelineSwimlanes.module.css` | Create | 3 |
| `src/app/timeline/TimelinePanel.tsx` | Modify | 3, 4, 5 |
| `src/app/timeline/TimelineHeader.tsx` | Create | 4 |
| `src/app/timeline/TimelineHeader.module.css` | Create | 4 |
| `src/app/timeline/ContentPanel.tsx` | Create | 5 |
| `src/app/timeline/ContentPanel.module.css` | Create | 5 |
| `src/app/timeline/ResizableDivider.tsx` | Create | 5 |
| `src/app/timeline/ResizableDivider.module.css` | Create | 5 |

All new files in `src/inspect_scout/_view/www/src/app/timeline/` (paths above are relative to `www/src/`).

## Reusable Existing Code

- `formatPrettyDecimal()` from `src/utils/format.ts` — for token formatting
- `formatDuration()` from `src/utils/format.ts` — for duration display on cards
- `clsx` — for CSS class composition (used throughout codebase)
- CSS variables: `--vscode-foreground`, `--vscode-descriptionForeground`, `--vscode-panel-border`, `--vscode-progressBar-background`, `--vscode-list-hoverBackground`, `--vscode-textLink-foreground`
- `AgentNode`, `SectionNode`, `Branch`, `TranscriptNodes` types from `src/components/transcript/nodes.ts`

## Verification & Commits

After each phase:
1. `pnpm check` (lint + format + typecheck)
2. `pnpm test` (unit tests for swimlane + path resolution)
3. Visual verification at `http://127.0.0.1:7576/#/timeline` — cycle through all 10 scenarios in the dropdown
4. `pnpm build` before committing
5. **Git commit** with a descriptive message summarizing the phase
