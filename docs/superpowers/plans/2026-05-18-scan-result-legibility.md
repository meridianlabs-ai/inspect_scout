# Scan Result Legibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve scan result view legibility by promoting the transcript button to the toolbar and enriching the header with all transcript metadata fields.

**Architecture:** Two independent changes to the scan result panel. (1) Move the "View Transcript" action from a hidden icon button inside the Input tab to a labeled toolbar button with shift-click-to-open-in-new-tab support. (2) Replace the custom column-count CSS grid in `ScannerResultHeader` with the flexible `HeadingGrid` component and add all transcript metadata fields (date, agent, limit, error, tokens, time, messages, score).

**Tech Stack:** React, TypeScript, CSS Modules, react-router-dom

**Spec:** `docs/superpowers/specs/2026-05-18-scan-result-legibility-design.md`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `apps/scout/src/app/scannerResult/ScannerResultPanel.tsx` | Modify | Add Transcript `ToolButton` to toolbar with shift-click support |
| `apps/scout/src/app/scannerResult/result/ResultBody.tsx` | Modify | Remove transcript button, remove `transcriptDir`/`hasTranscript` props |
| `apps/scout/src/app/scannerResult/result/ResultPanel.tsx` | Modify | Remove `transcriptDir`/`hasTranscript` prop passthrough |
| `apps/scout/src/app/scannerResult/ScannerResultHeader.tsx` | Modify | Replace custom grid with `HeadingGrid`, add transcript metadata fields |
| `apps/scout/src/app/scannerResult/ScannerResultHeader.module.css` | Modify | Remove column-count classes, keep wrapper styling |

All paths are relative to `src/inspect_scout/_view/ts-mono/`.

---

### Task 1: Add Transcript ToolButton to ScannerResultPanel

**Files:**
- Modify: `apps/scout/src/app/scannerResult/ScannerResultPanel.tsx`

- [ ] **Step 1: Add the Transcript ToolButton to the `tools` useMemo**

In `ScannerResultPanel.tsx`, add a new `ToolButton` for navigating to the transcript. Insert it **before** the Validation button block (before the `if (selectedResult?.transcriptId)` check at line 215). Add the necessary imports and handler.

Add these imports at the top (merge with existing import lines):

```typescript
import { useNavigate } from "react-router-dom";
```

`useNavigate` is already imported indirectly via hooks, but `ScannerResultPanel` doesn't import it yet — however, checking again: it uses `useSearchParams` from `react-router-dom` already. Add `useNavigate` to that import.

Inside the component, add a navigate hook and handler:

```typescript
const navigate = useNavigate();

const handleNavigateToTranscript = useCallback(
  (e: React.MouseEvent) => {
    const route = transcriptRoute(resolvedTranscriptsDir, selectedResult?.transcriptId ?? "");
    if (e.shiftKey) {
      window.open(route, "_blank");
    } else {
      void navigate(route);
    }
  },
  [navigate, resolvedTranscriptsDir, selectedResult?.transcriptId]
);
```

Add the `transcriptRoute` import (merge with existing imports from `../../router/url`):

```typescript
import {
  getScannerParam,
  getValidationParam,
  updateValidationParam,
  transcriptRoute,
} from "../../router/url";
```

Then in the `tools` useMemo, insert this block **before** the existing Validation button block:

```typescript
// Transcript button - navigate to full transcript view
const canNavigateToTranscript =
  !!hasTranscript && resolvedTranscriptsDir.length > 0 && !!selectedResult?.transcriptId;
if (canNavigateToTranscript) {
  toolButtons.push(
    <ToolButton
      key="transcript-navigate"
      label="Transcript"
      icon={ApplicationIcons.transcript}
      onClick={handleNavigateToTranscript}
      title="View complete transcript (Shift+click to open in new tab)"
    />
  );
}
```

Add `handleNavigateToTranscript`, `hasTranscript`, and `resolvedTranscriptsDir` to the `useMemo` dependency array. The updated dependency array:

```typescript
], [
  highlightLabeled,
  toggleHighlightLabeled,
  selectedTab,
  selectedResult,
  toggleValidationSidebar,
  validationSidebarCollapsed,
  handleNavigateToTranscript,
  hasTranscript,
  resolvedTranscriptsDir,
]);
```

- [ ] **Step 2: Verify the app compiles**

Run from the `ts-mono` directory:

```bash
pnpm typecheck
```

Expected: No type errors.

- [ ] **Step 3: Commit**

```bash
git add apps/scout/src/app/scannerResult/ScannerResultPanel.tsx
git commit -m "feat: add labeled Transcript toolbar button with shift-click"
```

---

### Task 2: Remove transcript button from ResultBody and ResultPanel

**Files:**
- Modify: `apps/scout/src/app/scannerResult/result/ResultBody.tsx`
- Modify: `apps/scout/src/app/scannerResult/result/ResultPanel.tsx`

- [ ] **Step 1: Simplify ResultBody — remove transcript button and related props**

In `ResultBody.tsx`, remove the `transcriptDir` and `hasTranscript` props from the interface and component. Remove the `handleNavigateToTranscript` callback, the `canNavigateToTranscript` variable, and the `transcriptAction` JSX. Remove the now-unused imports.

The updated file should look like this for the relevant sections:

Remove these imports (no longer needed):
- `useNavigate` from `react-router-dom` (line 3)
- `transcriptRoute` from `../../../router/url` (line 10)
- `ColumnHeaderButton` from `../../components/ColumnHeader` (line 16 — keep `ColumnHeader`)
- `ApplicationIcons` from `../../../icons` (line 9)

Updated interface:

```typescript
export interface ResultBodyProps {
  resultData: ScanResultData;
  inputData: ScannerInput;
}
```

Updated component signature and body (remove lines 42-71, keeping only what's needed):

```typescript
export const ResultBody: FC<ResultBodyProps> = ({
  resultData,
  inputData,
}) => {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [searchParams] = useSearchParams();

  // Headroom: collapse swimlanes on scroll-down, expand on scroll-up.
  const { hidden: headroomHidden, resetAnchor: headroomResetAnchor } =
    useScrollDirection(scrollRef);

  // Get message or event ID from query params
  const initialMessageId = searchParams.get("message");
  const initialEventId = searchParams.get("event");

  const highlightLabeled = useStore((state) => state.highlightLabeled);

  return (
    <div className={clsx(styles.container, containerClass(inputData))}>
      <ColumnHeader label="Input" />
      <div ref={scrollRef} className={clsx(styles.scrollable)}>
        <InputRenderer
          resultData={resultData}
          inputData={inputData}
          scrollRef={scrollRef}
          initialMessageId={initialMessageId}
          initialEventId={initialEventId}
          highlightLabeled={highlightLabeled}
          headroomHidden={headroomHidden}
          onHeadroomResetAnchor={headroomResetAnchor}
        />
      </div>
    </div>
  );
};
```

Also remove `useCallback` from the React import (line 2) since it's no longer used — keep `FC`, `useRef`.

- [ ] **Step 2: Simplify ResultPanel — remove transcript-related props**

In `ResultPanel.tsx`, remove `transcriptDir` and `hasTranscript` from the interface and stop passing them to `ResultBody`:

```typescript
interface ResultPanelProps {
  resultData: ScanResultData;
  inputData: ScannerInput | undefined;
}

export const ResultPanel: FC<ResultPanelProps> = ({
  resultData,
  inputData,
}) => (
  <div className={clsx(styles.container, "text-size-base")}>
    <ResultSidebar inputData={inputData} resultData={resultData} />
    {inputData ? (
      <ResultBody
        resultData={resultData}
        inputData={inputData}
      />
    ) : (
      <div>No Input Available</div>
    )}
  </div>
);
```

- [ ] **Step 3: Update ScannerResultPanel to stop passing removed props**

In `ScannerResultPanel.tsx`, update the `ResultPanel` usage (around line 281) to stop passing `transcriptDir` and `hasTranscript`:

```typescript
<ResultPanel
  resultData={resultData}
  inputData={inputData}
/>
```

- [ ] **Step 4: Verify the app compiles**

```bash
pnpm typecheck
```

Expected: No type errors.

- [ ] **Step 5: Commit**

```bash
git add apps/scout/src/app/scannerResult/result/ResultBody.tsx \
       apps/scout/src/app/scannerResult/result/ResultPanel.tsx \
       apps/scout/src/app/scannerResult/ScannerResultPanel.tsx
git commit -m "refactor: remove transcript button from ResultBody/ResultPanel"
```

---

### Task 3: Replace ScannerResultHeader with HeadingGrid and add transcript fields

**Files:**
- Modify: `apps/scout/src/app/scannerResult/ScannerResultHeader.tsx`
- Modify: `apps/scout/src/app/scannerResult/ScannerResultHeader.module.css`

- [ ] **Step 1: Rewrite ScannerResultHeader to use HeadingGrid**

Replace the entire contents of `ScannerResultHeader.tsx`:

```typescript
import clsx from "clsx";
import { FC } from "react";

import type { ChatMessage, Event } from "@tsmono/inspect-common/types";
import type { EventType } from "@tsmono/inspect-components/transcript";
import {
  formatDateTime,
  formatNumber,
  formatTime,
  isRecord,
} from "@tsmono/util";

import {
  AppConfig,
  ScannerInput,
  Status,
  Transcript,
} from "../../types/api-types";
import { HeadingGrid, HeadingValue } from "../components/HeadingGrid";
import { ScoreValue } from "../components/ScoreValue";
import { TaskName } from "../components/TaskName";
import { projectOrAppAliasedPath } from "../server/useAppConfig";
import {
  isEventInput,
  isEventsInput,
  isMessageInput,
  isMessagesInput,
  isTranscriptInput,
} from "../types";

import styles from "./ScannerResultHeader.module.css";

interface ScannerResultHeaderProps {
  scan?: Status;
  inputData?: ScannerInput;
  appConfig: AppConfig;
}

const labelClassName = clsx(
  "text-style-label",
  "text-size-smallestest",
  "text-style-secondary"
);
const valueClassName = clsx("text-size-small");

export const ScannerResultHeader: FC<ScannerResultHeaderProps> = ({
  scan,
  inputData,
  appConfig,
}) => {
  const headings = headingsForResult(appConfig, inputData, scan) ?? [];
  if (headings.length === 0) return null;

  // Tabular scores get their own region (same pattern as TranscriptTitle)
  const transcript =
    inputData && isTranscriptInput(inputData) ? inputData.input : undefined;
  const tabularScore =
    transcript?.score != null && isRecord(transcript.score);

  return (
    <div
      className={clsx(
        styles.header,
        tabularScore && styles.headerWithScore
      )}
    >
      <HeadingGrid
        headings={headings}
        className={tabularScore ? styles.metadataRegion : undefined}
        labelClassName={labelClassName}
        valueClassName={valueClassName}
      />
      {tabularScore && (
        <div className={styles.scoreRegion}>
          <span className={labelClassName}>Score</span>
          <span className={valueClassName}>
            <ScoreValue score={transcript.score} maxRows={5} />
          </span>
        </div>
      )}
    </div>
  );
};

const headingsForResult = (
  appConfig: AppConfig,
  inputData?: ScannerInput,
  status?: Status
): HeadingValue[] | undefined => {
  if (!inputData) return [];
  if (isTranscriptInput(inputData))
    return transcriptHeadings(appConfig, inputData.input, status);
  if (isMessageInput(inputData))
    return messageHeadings(inputData.input, status);
  if (isMessagesInput(inputData))
    return messagesHeadings(inputData.input);
  if (isEventInput(inputData))
    return eventHeadings(inputData.input);
  if (isEventsInput(inputData))
    return eventsHeadings(inputData.input);
  return [];
};

const transcriptHeadings = (
  appConfig: AppConfig,
  transcript: Transcript,
  status?: Status
): HeadingValue[] => {
  // Source info — backwards compat with metadata
  const sourceUri =
    transcript.source_uri ||
    (transcript.metadata?.log as string | undefined) ||
    "";
  let resolvedSourceUrl = sourceUri;
  if (resolvedSourceUrl && resolvedSourceUrl.startsWith("/")) {
    resolvedSourceUrl = `file://${resolvedSourceUrl}`;
  }
  const displaySourceUri = projectOrAppAliasedPath(appConfig, resolvedSourceUrl);

  // Model — backwards compat with metadata
  const transcriptModel =
    transcript.model ||
    (transcript.metadata?.model as string | undefined) ||
    "";

  // Task — backwards compat with metadata
  const taskSet =
    transcript.task_set ||
    (transcript.metadata?.task_name as string | undefined) ||
    "";
  const taskId =
    transcript.task_id || (transcript.metadata?.id as string | undefined) || "";
  const taskRepeat =
    transcript.task_repeat || (transcript.metadata?.epoch as number) || -1;

  const scanningModel = status?.spec.model?.model;

  const headings: HeadingValue[] = [
    {
      label: "Task",
      value: (
        <TaskName taskSet={taskSet} taskId={taskId} taskRepeat={taskRepeat} />
      ),
    },
  ];

  if (displaySourceUri) {
    headings.push({ label: "Source", value: displaySourceUri });
  }

  if (transcript.date) {
    headings.push({
      label: "Date",
      value: formatDateTime(new Date(transcript.date)),
    });
  }

  if (transcript.agent) {
    headings.push({ label: "Agent", value: transcript.agent });
  }

  if (transcriptModel) {
    headings.push({ label: "Model", value: transcriptModel });
  }

  if (scanningModel) {
    headings.push({ label: "Scanning Model", value: scanningModel });
  }

  if (transcript.limit) {
    headings.push({ label: "Limit", value: transcript.limit });
  }

  if (transcript.error) {
    headings.push({ label: "Error", value: transcript.error });
  }

  if (transcript.total_tokens) {
    headings.push({
      label: "Tokens",
      value: formatNumber(transcript.total_tokens),
    });
  }

  if (transcript.total_time) {
    headings.push({
      label: "Time",
      value: formatTime(transcript.total_time),
    });
  }

  if (transcript.message_count) {
    headings.push({
      label: "Messages",
      value: transcript.message_count.toString(),
    });
  }

  // Simple (non-tabular) scores go inline; tabular scores are handled by the parent
  if (transcript.score != null && !isRecord(transcript.score)) {
    headings.push({
      label: "Score",
      value: <ScoreValue score={transcript.score} />,
    });
  }

  return headings;
};

const messageHeadings = (
  message: ChatMessage,
  status?: Status
): HeadingValue[] => {
  const headings: HeadingValue[] = [
    { label: "Message ID", value: message.id },
  ];

  if (message.role === "assistant") {
    headings.push({ label: "Model", value: message.model });
    headings.push({
      label: "Tool Calls",
      value: ((message.tool_calls as []) || []).length,
    });
  } else {
    headings.push({ label: "Role", value: message.role });
  }

  if (status?.spec.model?.model) {
    headings.push({
      label: "Scanning Model",
      value: status.spec.model.model,
    });
  }

  return headings;
};

const messagesHeadings = (messages: ChatMessage[]): HeadingValue[] => [
  { label: "Message Count", value: messages.length },
];

const eventHeadings = (event: EventType): HeadingValue[] => [
  { label: "Event Type", value: event.event },
  {
    label: "Timestamp",
    value: event.timestamp
      ? new Date(event.timestamp).toLocaleString()
      : undefined,
  },
];

const eventsHeadings = (events: Event[]): HeadingValue[] => [
  { label: "Event Count", value: events.length },
];
```

- [ ] **Step 2: Replace ScannerResultHeader.module.css**

Replace the CSS module contents — remove the column-count classes, keep the wrapper, add score layout support (matching `TranscriptTitle.module.css` pattern):

```css
.header {
  padding: 1rem 1rem;
  border-top: solid var(--bs-light-border-subtle) 1px;
}

.headerWithScore {
  display: grid;
  grid-template-columns: 1fr minmax(10rem, 45%);
  gap: 1rem;
}

.metadataRegion {
  min-width: 0;
}

.scoreRegion {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}
```

Check the `TranscriptTitle.module.css` to confirm the score layout pattern is consistent:

The `TranscriptTitle.module.css` uses `titleWithScore` with a similar 2-column grid split. We replicate the same approach here.

- [ ] **Step 3: Verify the app compiles**

```bash
pnpm typecheck
```

Expected: No type errors.

- [ ] **Step 4: Verify the app builds**

```bash
pnpm build
```

Expected: Build succeeds. This is important because we ship the built JS.

- [ ] **Step 5: Commit**

```bash
git add apps/scout/src/app/scannerResult/ScannerResultHeader.tsx \
       apps/scout/src/app/scannerResult/ScannerResultHeader.module.css
git commit -m "feat: enrich scan result header with transcript metadata fields"
```
