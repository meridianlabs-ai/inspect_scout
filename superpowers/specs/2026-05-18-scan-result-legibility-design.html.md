# scan-result-legibility-design – Inspect Scout

## Goal

Improve legibility of the scan result view by (1) promoting the “View Transcript” action to a toolbar button and (2) enriching the header to show the same metadata fields as the transcript view.

## 1. View Transcript Button

### Current State

A small icon-only `ColumnHeaderButton` in the Input tab’s `ColumnHeader` actions area (`ResultBody.tsx`). Easy to miss.

### Change

Move to the `ScannerResultPanel` toolbar as a labeled `ToolButton`, placed **before** the Validation button.

- **Icon:** `ApplicationIcons.transcript`
- **Label:** “Transcript”
- **Visibility:** Only when all conditions are met:
  - `hasTranscript` is true (transcript exists in the transcript database)
  - `transcriptDir.length > 0`
  - `selectedResult.transcriptId` is defined
- **Normal click:** `navigate(transcriptRoute(transcriptDir, transcriptId))`
- **Shift+click:** `window.open(transcriptRoute(transcriptDir, transcriptId), '_blank')` — opens in a new browser tab

### Cleanup

- Remove the `ColumnHeaderButton` transcript action from `ResultBody.tsx`
- Remove `transcriptDir`, `hasTranscript`, and `handleNavigateToTranscript` from `ResultBody` (these are no longer needed there)
- Propagate removal through `ResultPanel` if it only passes these props through

## 2. Scan Result Header Enrichment

### Current State

`ScannerResultHeader` uses a custom 2-row grid layout (label row, value row) with CSS column-count classes (`oneCol` through `sixCol`). For transcript inputs it shows: Task, Source, Model, Scanning Model.

### Change

Replace the custom grid with `HeadingGrid` (from `../components/HeadingGrid`). For transcript inputs, show these fields **only when they have values**:

| Field | Source | Formatter |
|----|----|----|
| Task | `task_set`, `task_id`, `task_repeat` | `TaskName` component |
| Source | `source_uri` (aliased via `projectOrAppAliasedPath`) | plain text |
| Date | `transcript.date` | `formatDateTime` |
| Agent | `transcript.agent` | plain text |
| Model | `transcript.model` | plain text |
| Scanning Model | `status.spec.model.model` | plain text |
| Limit | `transcript.limit` | plain text |
| Error | `transcript.error` | plain text |
| Tokens | `transcript.total_tokens` | `formatNumber` |
| Time | `transcript.total_time` | `formatTime` |
| Messages | `transcript.message_count` | `.toString()` |
| Score | `transcript.score` | `ScoreValue` component |

Task is always present; all others are conditional on having a value.

Non-transcript input types (message, messages, event, events) keep their existing field sets but also switch to `HeadingGrid` for layout consistency.

### Styling

Use the same label/value class pattern as `TranscriptTitle`: - Labels: `text-style-label text-size-smallestest text-style-secondary` - Values: `text-size-small`

This ensures visual consistency between the scan result header and the transcript title.

### Cleanup

- Remove `classForCols` function and the `oneCol`-`sixCol` CSS classes from `ScannerResultHeader.module.css`
- Remove the old 2-row grid rendering logic
- The [Column](../../reference/transcript.html.md#column) interface is replaced by `HeadingValue` from `HeadingGrid`

## Files Modified

| File | Change |
|----|----|
| `ScannerResultPanel.tsx` | Add Transcript `ToolButton` to toolbar; pass `transcriptDir`/`hasTranscript` handling here |
| `ResultBody.tsx` | Remove transcript button, simplify props |
| `ResultPanel.tsx` | Remove transcript-related prop passthrough (if applicable) |
| `ScannerResultHeader.tsx` | Replace custom grid with `HeadingGrid`; add new fields for transcript inputs |
| `ScannerResultHeader.module.css` | Remove column-count classes; simplify to wrapper styling |
