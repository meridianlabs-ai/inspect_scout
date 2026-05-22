# scan-result-header-redesign – Inspect Scout

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the ScannerResultHeader to match the “Direction A — Refined Grid” design: source path with middle-truncation + copy button, score always in a right column with “All scores” dialog, monospace for identifiers, and a collapsed sticky bar on scroll.

**Architecture:** The existing `ScannerResultHeader` component is refactored to render two states: expanded (default) and collapsed (sticky bar). The component wraps in `StickyScroll` from `@tsmono/react/components` to detect scroll position and switch between states. A new `SourcePath` sub-component handles middle-truncation with a copy button. Score display always uses a right column (both simple and complex), with an “All scores” link opening a modal wrapping the existing `SampleScoresView`.

**Tech Stack:** React, TypeScript, CSS Modules, existing components: `StickyScroll`, `CopyButton`, `HeadingGrid`, `ScoreValue`, `Modal`, `centerTruncate` from `@tsmono/util`.

------------------------------------------------------------------------

## File Structure

| File | Action | Responsibility |
|----|----|----|
| `apps/scout/src/app/scannerResult/ScannerResultHeader.tsx` | Modify | Add collapsed state rendering, source path truncation, score right column always, monospace values |
| `apps/scout/src/app/scannerResult/ScannerResultHeader.module.css` | Modify | Add collapsed bar styles, score column border-left |
| `apps/scout/src/app/scannerResult/ScannerResultPanel.tsx` | Modify | Move header inside scrollable content area, wrap with StickyScroll |
| `apps/scout/src/app/scannerResult/ScannerResultPanel.module.css` | Modify | Adjust grid to remove header row, add scroller wrapper |
| `apps/scout/src/app/scannerResult/SourcePath.tsx` | Create | Middle-truncated source path with copy button |
| `apps/scout/src/app/scannerResult/ScoreColumn.tsx` | Create | Right-column score rendering (simple + complex) with “All scores” link |
| `apps/scout/src/app/scannerResult/AllScoresDialog.tsx` | Create | Modal wrapping existing ScoreValue/MetaDataGrid for full score view |

All paths are relative to `src/inspect_scout/_view/ts-mono/`.

------------------------------------------------------------------------

## Reference: Design Key Decisions

From the design chat and Direction A prototype:

1.  **Source path**: Always middle-truncated (head 20 / tail 36 expanded, head 18 / tail 28 collapsed) with monospace font and inline copy button. Full path in native tooltip.
2.  **Score**: Always in a standalone right column with `border-left`, whether simple or complex. Simple = plain value. Complex = key/value list (max 5 rows) + “All scores (N)” link.
3.  **Collapsed bar**: ~30px min-height, `background: #fafbfc` (use `var(--bs-tertiary-bg)`), shows: chevron + Task · Source (truncated) · Date · Scanning Model + score affordance. Dot-separated.
4.  **“All scores” dialog**: Both the “All scores (N)” link in expanded and collapsed wire to the same dialog. Use existing `Modal` + `ScoreValue` with `MetaDataGrid`.
5.  **Monospace**: Agent, Model, Scanning Model values use monospace.
6.  **Type**: Labels are 0.6rem uppercase (#8a8f98 → `text-style-label text-size-smallestest text-style-secondary`). Values are 0.8rem (`text-size-small`). These class names already exist and are already used.

------------------------------------------------------------------------

## Task 1: Create `SourcePath` Component

**Files:** - Create: `apps/scout/src/app/scannerResult/SourcePath.tsx` - Create: `apps/scout/src/app/scannerResult/SourcePath.module.css`

**Step 1: Create SourcePath component**

``` tsx
// SourcePath.tsx
import { FC } from "react";

import { CopyButton } from "@tsmono/react/components";
import { centerTruncate } from "@tsmono/util";

import styles from "./SourcePath.module.css";

interface SourcePathProps {
  uri: string;
  /** Maximum display length before truncation. Default 58 (≈ head 20 + ellipsis + tail 36). */
  maxLength?: number;
  className?: string;
}

export const SourcePath: FC<SourcePathProps> = ({
  uri,
  maxLength = 58,
  className,
}) => {
  const display = centerTruncate(uri, maxLength);
  return (
    <span className={className ?? styles.sourcePath} title={uri}>
      <span className={styles.pathText}>{display}</span>
      <CopyButton value={uri} ariaLabel="Copy source path" />
    </span>
  );
};
```

``` css
/* SourcePath.module.css */
.sourcePath {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  min-width: 0;
}

.pathText {
  font-family: var(--bs-font-monospace);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}
```

**Step 2: Verify it builds**

Run from `src/inspect_scout/_view/ts-mono/`:

``` bash
pnpm typecheck
```

Expected: PASS (no type errors)

**Step 3: Commit**

``` bash
git add apps/scout/src/app/scannerResult/SourcePath.tsx apps/scout/src/app/scannerResult/SourcePath.module.css
git commit -m "feat(scanner): add SourcePath component with middle-truncation and copy button"
```

------------------------------------------------------------------------

## Task 2: Create `ScoreColumn` Component

**Files:** - Create: `apps/scout/src/app/scannerResult/ScoreColumn.tsx` - Create: `apps/scout/src/app/scannerResult/ScoreColumn.module.css`

**Step 1: Create ScoreColumn component**

This component renders the score in a right column with a border-left. It handles both simple (scalar) and complex (record) scores. Complex scores show max 5 rows via `ScoreValue` with `maxRows={5}`, plus an “All scores” link.

``` tsx
// ScoreColumn.tsx
import clsx from "clsx";
import { FC, ReactNode } from "react";

import type { JsonValue } from "@tsmono/inspect-common/types";
import { isRecord } from "@tsmono/util";

import { ScoreValue } from "../components/ScoreValue";

import styles from "./ScoreColumn.module.css";

interface ScoreColumnProps {
  score: JsonValue;
  labelClassName?: string;
  valueClassName?: string;
  onShowAllScores?: () => void;
}

export const ScoreColumn: FC<ScoreColumnProps> = ({
  score,
  labelClassName,
  valueClassName,
  onShowAllScores,
}) => {
  const isComplex = isRecord(score);
  const totalScores = isComplex ? Object.keys(score as Record<string, unknown>).length : 0;

  return (
    <div className={styles.scoreColumn}>
      <span className={clsx(labelClassName)}>Score</span>
      <span className={clsx(valueClassName)}>
        <ScoreValue score={score} maxRows={5} />
      </span>
      {isComplex && totalScores > 5 && onShowAllScores && (
        <button
          type="button"
          className={styles.allScoresLink}
          onClick={onShowAllScores}
        >
          All scores ({totalScores})
        </button>
      )}
    </div>
  );
};

/** Compact inline score for the collapsed bar. */
export const CollapsedScore: FC<{
  score: JsonValue;
  onShowAllScores?: () => void;
}> = ({ score, onShowAllScores }) => {
  const isComplex = isRecord(score);

  if (isComplex) {
    const totalScores = Object.keys(score as Record<string, unknown>).length;
    return (
      <button
        type="button"
        className={styles.allScoresLink}
        onClick={onShowAllScores}
      >
        All scores ({totalScores})
      </button>
    );
  }

  return (
    <span className={styles.collapsedSimpleScore}>
      Score: {String(score)}
    </span>
  );
};
```

``` css
/* ScoreColumn.module.css */
.scoreColumn {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  min-width: 0;
  border-left: 1px solid var(--bs-border-color);
  padding-left: 1.25rem;
}

.allScoresLink {
  align-self: flex-start;
  margin-top: 0.3rem;
  color: var(--bs-link-color);
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  font-size: 0.75rem;
  text-decoration: none;
}

.allScoresLink:hover {
  text-decoration: underline;
}

.collapsedSimpleScore {
  font-family: var(--bs-font-monospace);
  font-size: 0.74rem;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
```

**Step 2: Verify it builds**

``` bash
pnpm typecheck
```

Expected: PASS

**Step 3: Commit**

``` bash
git add apps/scout/src/app/scannerResult/ScoreColumn.tsx apps/scout/src/app/scannerResult/ScoreColumn.module.css
git commit -m "feat(scanner): add ScoreColumn and CollapsedScore components"
```

------------------------------------------------------------------------

## Task 3: Create `AllScoresDialog` Component

**Files:** - Create: `apps/scout/src/app/scannerResult/AllScoresDialog.tsx`

**Step 1: Create AllScoresDialog component**

Wraps the existing `Modal` component with `ScoreValue` inside. The design notes say to use the existing `SampleScoresView` from inspect_ai, but that component expects an [EvalSample](https://inspect.aisi.org.uk/reference/inspect_ai.log.html#evalsample) object which we don’t have in the scanner context. Instead, use `ScoreValue` (which already renders `MetaDataGrid` for record scores) without a `maxRows` limit.

``` tsx
// AllScoresDialog.tsx
import { FC } from "react";

import type { JsonValue } from "@tsmono/inspect-common/types";

import { Modal } from "../../../../inspect/src/components/Modal";
import { ScoreValue } from "../components/ScoreValue";

interface AllScoresDialogProps {
  showing: boolean;
  setShowing: (showing: boolean) => void;
  score: JsonValue;
}

export const AllScoresDialog: FC<AllScoresDialogProps> = ({
  showing,
  setShowing,
  score,
}) => {
  return (
    <Modal
      id="all-scores-dialog"
      title="All Scores"
      showing={showing}
      setShowing={setShowing}
      overflow="auto"
    >
      <ScoreValue score={score} />
    </Modal>
  );
};
```

**Important**: Verify the import path for `Modal` — it lives in `apps/inspect/src/components/Modal.tsx`. Check if it’s re-exported from `@tsmono/react/components` or if a direct relative import is needed. The explorer noted it’s “already exported from `@tsmono/react/components`” — verify this and use the package import if available:

``` tsx
import { Modal } from "@tsmono/react/components";
```

If Modal is NOT exported from `@tsmono/react/components`, use the relative path. The agent implementing this task should verify which import works by checking the `@tsmono/react` package exports.

**Step 2: Verify it builds**

``` bash
pnpm typecheck
```

Expected: PASS

**Step 3: Commit**

``` bash
git add apps/scout/src/app/scannerResult/AllScoresDialog.tsx
git commit -m "feat(scanner): add AllScoresDialog modal for viewing all scores"
```

------------------------------------------------------------------------

## Task 4: Refactor `ScannerResultHeader` — Expanded State

**Files:** - Modify: `apps/scout/src/app/scannerResult/ScannerResultHeader.tsx` - Modify: `apps/scout/src/app/scannerResult/ScannerResultHeader.module.css`

This is the core refactor. The expanded state changes: 1. Source uses `SourcePath` with truncation + copy 2. Agent, Model, Scanning Model get monospace via a new `mono` field on `HeadingValue` 3. Score always renders in a right column via `ScoreColumn` (not inline in HeadingGrid) 4. Add `collapsed` prop and `onShowAllScores` callback

**Step 1: Update ScannerResultHeader props and expand rendering**

Add new props to `ScannerResultHeaderProps`:

``` typescript
interface ScannerResultHeaderProps {
  scan?: Status;
  inputData?: ScannerInput;
  resultData?: ScanResultData;
  appConfig: AppConfig;
  collapsed?: boolean;
  onShowAllScores?: () => void;
}
```

Refactor the `transcriptHeadings` function: - Replace the Source heading’s plain `displaySourceUri` value with `<SourcePath uri={displaySourceUri} />` (or the raw sourceUri before aliasing — check which is the right input) - Remove inline Score from the headings array (it’s now always in `ScoreColumn`) - Add `className` with monospace to Agent, Model, Scanning Model values via a wrapper span

Update the JSX in the component: - The `ScoreColumn` replaces the existing `scoreRegion` div - Score column renders whenever `resultData?.transcriptScore != null` (not just for records) - Grid columns: always `1fr` when no score, `minmax(0,1fr) minmax(260px, 38%)` when complex score, `minmax(0,1fr) auto` when simple score

Replace the current score region rendering with `ScoreColumn`:

``` tsx
{score != null && (
  <ScoreColumn
    score={score}
    labelClassName={labelClassName}
    valueClassName={valueClassName}
    onShowAllScores={onShowAllScores}
  />
)}
```

**Step 2: Verify it builds and renders correctly**

``` bash
pnpm typecheck
```

Expected: PASS

**Step 3: Commit**

``` bash
git add apps/scout/src/app/scannerResult/ScannerResultHeader.tsx apps/scout/src/app/scannerResult/ScannerResultHeader.module.css
git commit -m "feat(scanner): refactor expanded header with SourcePath, monospace values, and ScoreColumn"
```

------------------------------------------------------------------------

## Task 5: Add Collapsed State to `ScannerResultHeader`

**Files:** - Modify: `apps/scout/src/app/scannerResult/ScannerResultHeader.tsx` - Modify: `apps/scout/src/app/scannerResult/ScannerResultHeader.module.css`

**Step 1: Add collapsed rendering**

When `collapsed` is true, render a compact single-row bar instead of the expanded grid. The collapsed bar shows: chevron-right icon + Task · Source (shorter truncation) · Date · Scanning Model + score affordance. Fields are separated by dot separators (`·`).

Add a new function `renderCollapsed` inside the component (or a sub-component) that returns:

``` tsx
const renderCollapsed = () => {
  if (!resultData || !inputData || !isTranscriptInput(inputData)) return null;

  const scanningModel = scan?.spec.model?.model;
  const score = resultData.transcriptScore;
  const sourceUri = resultData.transcriptSourceUri ?? "";
  const displaySourceUri = projectOrAppAliasedPath(appConfig, sourceUri.startsWith("/") ? `file://${sourceUri}` : sourceUri);

  return (
    <div className={styles.collapsedBar}>
      <i className="bi bi-chevron-right" style={{ fontSize: "0.65rem" }} />
      <span className={styles.collapsedTask}>
        <TaskName
          taskSet={resultData.transcriptTaskSet}
          taskId={resultData.transcriptTaskId}
          taskRepeat={resultData.transcriptTaskRepeat}
        />
      </span>
      <span className={styles.dot}>·</span>
      {displaySourceUri && (
        <>
          <SourcePath uri={displaySourceUri} maxLength={48} className={styles.collapsedSource} />
          <span className={styles.dot}>·</span>
        </>
      )}
      {resultData.transcriptDate && (
        <>
          <span className={styles.collapsedDate}>
            {formatDateTime(new Date(resultData.transcriptDate))}
          </span>
        </>
      )}
      {scanningModel && (
        <>
          <span className={styles.dot}>·</span>
          <span className={styles.collapsedMono}>{scanningModel}</span>
        </>
      )}
      {score != null && (
        <CollapsedScore score={score} onShowAllScores={onShowAllScores} />
      )}
    </div>
  );
};
```

Update the component’s return to branch on `collapsed`:

``` tsx
if (collapsed) return renderCollapsed();
// ... existing expanded rendering
```

**Step 2: Add collapsed CSS**

``` css
.collapsedBar {
  background: var(--bs-tertiary-bg);
  border-top: 1px solid var(--bs-border-color);
  border-bottom: 1px solid var(--bs-border-color);
  padding: 0.25rem 0.9rem;
  display: flex;
  align-items: center;
  gap: 0.85rem;
  font-size: 0.76rem;
  color: var(--bs-body-color);
  min-height: 30px;
}

.collapsedTask {
  font-weight: 500;
  white-space: nowrap;
}

.collapsedSource {
  flex: 1 1 0;
  min-width: 0;
  display: flex;
}

.collapsedDate {
  color: var(--bs-secondary-color);
  white-space: nowrap;
}

.collapsedMono {
  font-family: var(--bs-font-monospace);
  font-size: 0.72rem;
  white-space: nowrap;
}

.dot {
  color: var(--bs-tertiary-color);
  flex-shrink: 0;
}
```

**Step 3: Verify it builds**

``` bash
pnpm typecheck
```

Expected: PASS

**Step 4: Commit**

``` bash
git add apps/scout/src/app/scannerResult/ScannerResultHeader.tsx apps/scout/src/app/scannerResult/ScannerResultHeader.module.css
git commit -m "feat(scanner): add collapsed sticky bar state to header"
```

------------------------------------------------------------------------

## Task 6: Integrate Sticky Scroll in `ScannerResultPanel`

**Files:** - Modify: `apps/scout/src/app/scannerResult/ScannerResultPanel.tsx` - Modify: `apps/scout/src/app/scannerResult/ScannerResultPanel.module.css`

This task moves the header into the scrollable content area and wraps it with `StickyScroll` so it collapses on scroll.

**Step 1: Restructure the layout**

The current layout is a 4-row grid: - Row 1: ScansNavbar - Row 2: LoadingBar - Row 3: ScannerResultHeader ← currently fixed - Row 4: contentArea

Change to: - Row 1: ScansNavbar - Row 2: LoadingBar - Row 3: scrollable container (header + contentArea together)

Add `useRef` for the scroll container and `useState` for sticky state:

``` tsx
import { StickyScroll } from "@tsmono/react/components";
// ...
const scrollRef = useRef<HTMLDivElement>(null);
const [headerCollapsed, setHeaderCollapsed] = useState(false);
const [showAllScores, setShowAllScores] = useState(false);
```

Restructure the JSX — the header and content area both live inside a new `.scroller` div:

``` tsx
<div className={styles.root}>
  <ScansNavbar ...>...</ScansNavbar>
  <LoadingBar ... />
  <div className={styles.scroller} ref={scrollRef}>
    <StickyScroll
      scrollRef={scrollRef}
      onStickyChange={setHeaderCollapsed}
    >
      <ScannerResultHeader
        inputData={inputData}
        resultData={selectedResult}
        scan={selectedScan}
        appConfig={appConfig}
        collapsed={headerCollapsed}
        onShowAllScores={() => setShowAllScores(true)}
      />
    </StickyScroll>
    {selectedResult && (
      <div className={clsx(styles.contentArea, ...)}>
        {/* existing tab/split layout */}
      </div>
    )}
  </div>
  {selectedResult?.transcriptScore != null && (
    <AllScoresDialog
      showing={showAllScores}
      setShowing={setShowAllScores}
      score={selectedResult.transcriptScore}
    />
  )}
</div>
```

**Step 2: Update CSS grid**

Change `.root` from 4-row to 3-row grid:

``` css
.root {
  height: 100%;
  display: grid;
  grid-template-rows: max-content max-content 1fr;
}
```

The `.scroller` class already exists in the CSS with `overflow-y: auto`. The `.contentArea` needs to no longer have `flex: 1` since it’s now inside a scroller — it should take its natural height. Review this carefully: the content inside needs to expand to fill the scroller. The contentArea’s children (TabSet panels) handle their own scrolling, so the contentArea itself should have a `min-height` that fills the viewport minus the header.

**Critical**: The existing tab panels have `overflow-y: hidden` and rely on being in a flex container with `min-height: 0`. Moving them into a scroller changes the sizing model. The content area needs `min-height: calc(100% - <header-height>)` or similar to ensure the tabs fill the viewport. Alternatively, use `min-height: 100%` on contentArea inside the scroller so it fills at minimum the viewport, allowing the header to scroll away but the content area to remain full-height.

Update `.contentArea`:

``` css
.contentArea {
  display: flex;
  flex-direction: row;
  min-height: calc(100vh - 200px); /* approximate; header + navbar height */
  overflow: hidden;
}
```

A better approach: give `.contentArea` a `min-height: 100%` inside the scroller so it always fills at least the scroll viewport. The `.scroller` provides the scroll context.

``` css
.contentArea {
  display: flex;
  flex-direction: row;
  min-height: 100%;
  overflow: hidden;
}
```

**Note to implementer**: This layout restructuring is the trickiest part. The key constraint is that the tab panels inside contentArea manage their own scrolling (they have `overflow-y: auto` internally). When the header is scrolled away, the contentArea should fill the remaining viewport. Test by verifying: 1. Initially the expanded header is visible above the tabs 2. Scrolling down collapses the header to the sticky bar 3. Tab content panels still scroll independently within their own containers 4. The overall page doesn’t double-scroll

**Step 3: Verify it builds**

``` bash
pnpm typecheck
```

Expected: PASS

**Step 4: Manual verification**

Open the app in a browser, navigate to a scan result with transcript data. Verify: 1. Header shows expanded with all fields 2. Scrolling down within the result collapses header to sticky bar 3. Sticky bar shows Task · Source · Date · Scanning Model 4. Tab panels still function and scroll independently 5. “All scores” link opens the modal dialog 6. Source path shows truncated with copy button 7. Agent/Model/Scanning Model show in monospace

**Step 5: Commit**

``` bash
git add apps/scout/src/app/scannerResult/ScannerResultPanel.tsx apps/scout/src/app/scannerResult/ScannerResultPanel.module.css
git commit -m "feat(scanner): integrate sticky scroll for header collapse on scroll"
```

------------------------------------------------------------------------

## Task 7: Build and Final Check

**Step 1: Run full checks**

``` bash
pnpm check
```

Expected: PASS (lint, typecheck, format all pass)

**Step 2: Run build**

``` bash
pnpm build
```

Expected: PASS — the built bundle must be valid since we ship it.

**Step 3: Fix any issues found**

Address any lint, type, or build errors.

**Step 4: Final commit if needed**

``` bash
git add -A
git commit -m "chore: fix lint/build issues from header redesign"
```
