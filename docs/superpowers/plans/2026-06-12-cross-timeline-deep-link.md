# Cross-Timeline Deep-Link Auto-Switch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When a `?event=` / `?message=` deep link targets an event in a non-visible root timeline, automatically switch the active timeline so the link resolves and scrolls (fixes dead cite clicks in the transcript search panel).

**Architecture:** New pure lookup helpers in `inspect-components` find which root timeline contains a deep-link target. `TranscriptLayout` gains a memo + effect that calls the existing `setActiveTimeline` when the target lives in a different timeline; the existing resolution/scroll machinery then completes navigation against the new root.

**Tech Stack:** TypeScript (strict, no `any`, no type assertions outside established test-factory patterns), React 19, vitest, pnpm + Turborepo monorepo consumed as a git submodule.

**Spec:** `docs/superpowers/specs/2026-06-12-cross-timeline-deep-link-design.md`

---

## Critical context for the implementer

- **All frontend work happens inside the git submodule** at `src/inspect_scout/_view/ts-mono/`. It has its own git repo. Run all pnpm commands from inside it. Use **pnpm, never npm**.
- The submodule is normally on a **detached HEAD** (pinned commit). Task 1 creates a branch.
- The key background facts (verified, don't re-derive):
  - `?event=<id>` params hold **event uuids** — `treeify.ts:134` keys event nodes by `event.uuid`. They can also hold **span ids** (agent-card targets like `agent-<toolCallId>` — see `resolveMessageToEvent.ts` PRIORITY_AGENT_CARD_RESULT), so containment checks must match both.
  - `TranscriptLayout` already holds `timelines`, `activeTimelineIndex`, `setActiveTimeline` from `useTranscriptTimeline` (lines ~359-386).
  - In scout, `setActiveTimeline(i)` flows to `useActiveTimelineSearchParams.onActiveChange`, which sets/deletes the `timeline_view` URL param and deletes `selected`, leaving `event`/`message` params intact (`apps/scout/src/app/timeline/hooks/useActiveTimeline.ts:44-64`).
  - The imperative scroll effect (`TranscriptViewNodes.tsx:474-497`) does **not** consume its dedup key when the event isn't in `flattenedNodes` (`if (idx === -1) return;` before the ref write), so after the timeline switch recomputes `flattenedNodes`, it re-fires and scrolls. No changes needed there.
  - The existing message side-effect (`TranscriptLayout.tsx:651-664`) consumes `prevMessageIdRef` even when resolution failed. Task 3 adds a guard so a pending cross-timeline switch defers that consumption (otherwise swimlane-row selection for cross-timeline message links would never fire).

---

### Task 1: Branch setup

**Files:** none (git only)

- [ ] **Step 1: Create a branch in the submodule**

```bash
cd src/inspect_scout/_view/ts-mono
git checkout -b feature/cross-timeline-deep-link
```

- [ ] **Step 2: Create a matching branch in the parent repo**

```bash
cd ../../../..   # back to inspect_scout root
git checkout -b feature/cross-timeline-deep-link
```

Expected: both repos report the new branch via `git status -sb`.

---

### Task 2: Timeline containment helpers (TDD)

**Files:**
- Create: `src/inspect_scout/_view/ts-mono/packages/inspect-components/src/transcript/findTimelineForDeepLink.ts`
- Create: `src/inspect_scout/_view/ts-mono/packages/inspect-components/src/transcript/findTimelineForDeepLink.test.ts`
- Modify: `src/inspect_scout/_view/ts-mono/packages/inspect-components/src/transcript/index.ts` (add exports next to the existing `resolveMessageToEvent` exports at ~line 55)

- [ ] **Step 1: Write the failing tests**

Create `packages/inspect-components/src/transcript/findTimelineForDeepLink.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import type { Event } from "@tsmono/inspect-common/types";

import {
  findTimelineIndexForEvent,
  findTimelineIndexForMessage,
  timelineContainsEvent,
} from "./findTimelineForDeepLink";
import { TimelineEvent, TimelineSpan, type Timeline } from "./timeline/core";

// Minimal model-event factory; mirrors the `as unknown as Event` pattern in
// timeline/testHelpers.ts (only the fields the lookup reads are populated).
function modelEvent(
  uuid: string,
  opts?: { inputId?: string; outputId?: string }
): Event {
  return {
    event: "model",
    uuid,
    timestamp: "2025-01-01T00:00:00Z",
    input: opts?.inputId
      ? [{ id: opts.inputId, role: "user", content: "hi" }]
      : [],
    output: {
      choices: opts?.outputId
        ? [
            {
              message: { id: opts.outputId, role: "assistant", content: "ok" },
            },
          ]
        : [],
    },
  } as unknown as Event;
}

function span(
  id: string,
  content: (TimelineEvent | TimelineSpan)[],
  opts?: { branches?: TimelineSpan[]; spanType?: string | null }
): TimelineSpan {
  return new TimelineSpan({
    id,
    name: id,
    spanType: opts?.spanType ?? null,
    content,
    branches: opts?.branches,
  });
}

function timeline(name: string, root: TimelineSpan): Timeline {
  return { name, description: "", root };
}

const targetTl = timeline(
  "target",
  span("root-target", [new TimelineEvent(modelEvent("ev-t1"))])
);
const auditorTl = timeline(
  "auditor",
  span("root-auditor", [
    new TimelineEvent(modelEvent("ev-a1", { outputId: "msg-a1" })),
    span("agent-call1", [new TimelineEvent(modelEvent("ev-a2"))], {
      spanType: "agent",
    }),
  ])
);
const timelines: Timeline[] = [targetTl, auditorTl];

describe("timelineContainsEvent", () => {
  it("matches event uuids in nested spans", () => {
    expect(timelineContainsEvent("ev-a2", auditorTl)).toBe(true);
    expect(timelineContainsEvent("ev-a2", targetTl)).toBe(false);
  });

  it("matches span ids (agent-card deep-link targets)", () => {
    expect(timelineContainsEvent("agent-call1", auditorTl)).toBe(true);
    expect(timelineContainsEvent("agent-call1", targetTl)).toBe(false);
  });

  it("matches events inside branches", () => {
    const branched = timeline(
      "branched",
      span("root-b", [], {
        branches: [span("b1", [new TimelineEvent(modelEvent("ev-br1"))])],
      })
    );
    expect(timelineContainsEvent("ev-br1", branched)).toBe(true);
  });
});

describe("findTimelineIndexForEvent", () => {
  it("returns the index of the containing timeline", () => {
    expect(findTimelineIndexForEvent("ev-a1", timelines)).toBe(1);
    expect(findTimelineIndexForEvent("ev-t1", timelines)).toBe(0);
  });

  it("returns the first match when present in multiple timelines", () => {
    const dup = timeline(
      "dup",
      span("root-dup", [new TimelineEvent(modelEvent("ev-t1"))])
    );
    expect(findTimelineIndexForEvent("ev-t1", [targetTl, dup])).toBe(0);
  });

  it("returns -1 when no timeline contains the event", () => {
    expect(findTimelineIndexForEvent("ev-missing", timelines)).toBe(-1);
  });
});

describe("findTimelineIndexForMessage", () => {
  it("returns the index of the timeline whose events carry the message", () => {
    expect(findTimelineIndexForMessage("msg-a1", timelines)).toBe(1);
  });

  it("returns -1 when no timeline carries the message", () => {
    expect(findTimelineIndexForMessage("msg-missing", timelines)).toBe(-1);
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd src/inspect_scout/_view/ts-mono/packages/inspect-components
pnpm vitest run src/transcript/findTimelineForDeepLink.test.ts
```

Expected: FAIL — cannot resolve `./findTimelineForDeepLink`.

- [ ] **Step 3: Implement the helpers**

Create `packages/inspect-components/src/transcript/findTimelineForDeepLink.ts`:

```ts
/**
 * Locates which root timeline contains a deep-link target (`?event=` /
 * `?message=`), so the view can auto-switch to it when the target is not in
 * the active timeline.
 */

import {
  resolveMessageInBranches,
  resolveMessageToEvent,
} from "./resolveMessageToEvent";
import type { Timeline, TimelineEvent, TimelineSpan } from "./timeline/core";

function itemsContainEvent(
  eventId: string,
  items: ReadonlyArray<TimelineEvent | TimelineSpan>
): boolean {
  for (const item of items) {
    if (item.type === "event") {
      // Not every Event union member declares `uuid`; same access pattern as
      // collectReferencedIds in timeline/hooks/useTimelinesArray.ts.
      const uuid = (item.event as { uuid?: string | null }).uuid;
      if (uuid === eventId) return true;
    } else {
      // `?event=` can also target span nodes (agent-card results use the
      // span id as the scroll target), so match span ids too.
      if (item.id === eventId) return true;
      if (itemsContainEvent(eventId, item.content)) return true;
      if (itemsContainEvent(eventId, item.branches)) return true;
    }
  }
  return false;
}

/** True if the timeline's tree (content and branches) contains the target. */
export function timelineContainsEvent(
  eventId: string,
  timeline: Timeline
): boolean {
  return (
    timeline.root.id === eventId ||
    itemsContainEvent(eventId, timeline.root.content) ||
    itemsContainEvent(eventId, timeline.root.branches)
  );
}

/** Index of the first timeline containing the event/span id, or -1. */
export function findTimelineIndexForEvent(
  eventId: string,
  timelines: ReadonlyArray<Timeline>
): number {
  return timelines.findIndex((tl) => timelineContainsEvent(eventId, tl));
}

/** Index of the first timeline whose events resolve the message id, or -1. */
export function findTimelineIndexForMessage(
  messageId: string,
  timelines: ReadonlyArray<Timeline>
): number {
  return timelines.findIndex(
    (tl) =>
      resolveMessageToEvent(messageId, tl.root) !== undefined ||
      resolveMessageInBranches(messageId, tl.root) !== undefined
  );
}
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
pnpm vitest run src/transcript/findTimelineForDeepLink.test.ts
```

Expected: PASS (8 tests).

If the branch-containment test fails because `TimelineSpan`'s constructor doesn't default `branches`, check `timeline/core.ts` — the constructor accepts `branches?:` and defaults to `[]`; pass `branches: opts?.branches` exactly as written above.

- [ ] **Step 5: Export from the transcript barrel**

In `packages/inspect-components/src/transcript/index.ts`, next to the existing `resolveMessageToEvent` export block (~line 55), add:

```ts
export {
  findTimelineIndexForEvent,
  findTimelineIndexForMessage,
  timelineContainsEvent,
} from "./findTimelineForDeepLink";
```

- [ ] **Step 6: Typecheck and lint the package**

```bash
pnpm typecheck && pnpm lint
```

Expected: clean.

- [ ] **Step 7: Commit (in the submodule)**

```bash
cd src/inspect_scout/_view/ts-mono
git add packages/inspect-components/src/transcript/findTimelineForDeepLink.ts \
        packages/inspect-components/src/transcript/findTimelineForDeepLink.test.ts \
        packages/inspect-components/src/transcript/index.ts
git commit -m "feat: add cross-timeline deep-link containment helpers

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Auto-switch in TranscriptLayout

**Files:**
- Modify: `src/inspect_scout/_view/ts-mono/packages/inspect-components/src/transcript/TranscriptLayout.tsx` (imports; new memo + effect around lines 637-665; one guard line added to the existing message side-effect)

- [ ] **Step 1: Add the import**

In `TranscriptLayout.tsx`, alongside the existing import of `resolveMessageToEvent` / `resolveMessageInBranches`, add:

```ts
import {
  findTimelineIndexForEvent,
  findTimelineIndexForMessage,
  timelineContainsEvent,
} from "./findTimelineForDeepLink";
```

- [ ] **Step 2: Add the switch-target memo**

Insert immediately after the `const resolved = resolvedLocal ?? resolvedRoot;` line (~line 637) and **before** the existing `prevMessageIdRef` effect:

```tsx
  // Cross-timeline deep links: if the target lives in a different root
  // timeline, find it so the effect below can switch to it. -1 = no switch.
  const deepLinkTimelineIndex = useMemo(() => {
    if (timelines.length <= 1) return -1;
    if (initialEventId) {
      const active = timelines[activeTimelineIndex];
      if (!active || timelineContainsEvent(initialEventId, active)) return -1;
      return findTimelineIndexForEvent(initialEventId, timelines);
    }
    if (initialMessageId && !resolvedLocal && !resolvedRoot) {
      return findTimelineIndexForMessage(initialMessageId, timelines);
    }
    return -1;
  }, [
    initialEventId,
    initialMessageId,
    resolvedLocal,
    resolvedRoot,
    timelines,
    activeTimelineIndex,
  ]);
```

Note: when `deepLinkTimelineIndex` resolves to the active index (possible only in the message branch, and only transiently), the effect below ignores it.

- [ ] **Step 3: Guard the existing message side-effect**

In the existing effect that starts `if (prevMessageIdRef.current === initialMessageId) return;` (~line 652), add one guard line **before** the ref write, and add `deepLinkTimelineIndex` to the dep array:

```tsx
  const prevMessageIdRef = useRef<string | null | undefined>(undefined);
  useEffect(() => {
    if (prevMessageIdRef.current === initialMessageId) return;
    // A cross-timeline switch is pending: don't consume the message id yet —
    // this effect must re-evaluate after the switch lands and resolution
    // re-runs against the new root.
    if (deepLinkTimelineIndex >= 0) return;
    prevMessageIdRef.current = initialMessageId;
    if (!resolvedRoot) return;
    let targetKey: string | null = null;
    if (resolvedRoot.branchRowKey) {
      targetKey = resolvedRoot.branchRowKey;
    } else if (resolvedRoot.agentSpanId) {
      targetKey = spanSelectKeys.get(resolvedRoot.agentSpanId)?.key ?? null;
    }
    if (timelineState.selected === targetKey) return;
    timelineState.select(targetKey, { preserveDeepLink: true });
  }, [
    initialMessageId,
    deepLinkTimelineIndex,
    resolvedRoot,
    spanSelectKeys,
    timelineState,
  ]);
```

(The body between the ref write and the dep array is unchanged — only the guard line and the dep are new. Keep the existing block comment above the effect as is.)

- [ ] **Step 4: Add the switch effect**

Insert immediately after the effect modified in Step 3, before `const effectiveInitialEventId = ...`:

```tsx
  // Fire the timeline switch once per deep-link change — a stale `?event=` /
  // `?message=` param left in the URL must not snap the user back after they
  // manually switch timelines away.
  const prevDeepLinkRef = useRef<string | null>(null);
  useEffect(() => {
    if (timelines.length <= 1) return;
    const key = initialEventId ?? initialMessageId ?? null;
    if (prevDeepLinkRef.current === key) return;
    prevDeepLinkRef.current = key;
    if (key === null || deepLinkTimelineIndex < 0) return;
    if (deepLinkTimelineIndex === activeTimelineIndex) return;
    setActiveTimeline(deepLinkTimelineIndex);
  }, [
    initialEventId,
    initialMessageId,
    deepLinkTimelineIndex,
    activeTimelineIndex,
    setActiveTimeline,
    timelines.length,
  ]);
```

The `timelines.length <= 1` early return happens **before** consuming the key: if timelines haven't been built yet (transient empty render), the deep link stays unconsumed until real data arrives.

- [ ] **Step 5: Typecheck, lint, and run package tests**

```bash
cd src/inspect_scout/_view/ts-mono/packages/inspect-components
pnpm typecheck && pnpm lint && pnpm test
```

Expected: all clean/pass. Do not suppress `react-hooks/exhaustive-deps` — if the lint complains, fix the dep array.

- [ ] **Step 6: Commit (in the submodule)**

```bash
cd src/inspect_scout/_view/ts-mono
git add packages/inspect-components/src/transcript/TranscriptLayout.tsx
git commit -m "feat: auto-switch root timeline for cross-timeline deep links

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Full verification

- [ ] **Step 1: Monorepo-wide checks and tests**

```bash
cd src/inspect_scout/_view/ts-mono
pnpm check && pnpm test
```

Expected: all packages pass.

- [ ] **Step 2: Production build**

```bash
pnpm build
```

Expected: succeeds; writes the bundle to the parent repo's `src/inspect_scout/_view/www/dist/` path. (The dist commit and submodule-pointer bump in the parent repo happen at PR-merge time per `docs/submodule-guide.md` — do not commit dist to the parent's feature branch yet unless asked.)

- [ ] **Step 3: Manual verification against the repro**

Requires the dev server (the user typically has `pnpm dev` running on `localhost:5173` — don't start one without checking). Using the Playwright MCP tools:

1. Navigate to the repro transcript:
   `http://localhost:5173/#/transcripts/ZmlsZTovLy9Vc2Vycy9jaGFybGVzdGVhZ3VlL0RldmVsb3BtZW50L3Rlc3RfZXZhbHMvbG9ncw/YhnkALeSmrCAMWL7pXY7vB?search=1&tab=transcript-events`
2. With the **target** timeline visible, run a grep search in the search panel that produces cites into the **auditor** timeline.
3. Click such a cite. Expected: the timeline selector switches to auditor (`timeline_view=auditor` appears in the URL) and the view scrolls to the cited event.
4. Click a cite into the currently visible timeline. Expected: scrolls without switching.
5. After a cross-timeline jump, manually switch back to target via the timeline selector. Expected: the view stays on target (no snap-back), because the deep-link key was already consumed.
6. Paste a URL with `?event=<uuid-from-auditor>` while `timeline_view` is absent/target. Expected: lands on auditor and scrolls.

Note: hot-reload via Playwright can show stale code — reload the page after the build/watch picks up changes.

- [ ] **Step 4: Report results**

Report pass/fail for each manual check to the user before any merge/PR steps (use superpowers:finishing-a-development-branch for integration).
