# React Component Dependency Graph

## Mermaid Graph

```mermaid
flowchart TD
    subgraph "Feature Panels"
        ScansPanel
        ScanJobsPanel
        ScanResultPanel
    end

    subgraph "Scans Feature"
        ScansPanelBody
        ScansPanelTitle
        ScanInfo
        ScanResultsPanel
        ScanResultsSearch
        ScanResultsFilter
        ScanResultsGroup
        ScanDataframeWrapTextButton
        ScanDataframeFilterColumnsButton
        ScanDataframeClearFiltersButton
        ScanDataframeColumnsPopover
        ScanResultsOutline
        ScanResultsBody
        ScanResultsList
        ScanResultsRow
        ScanResultGroup
        ScanHeader
    end

    subgraph "ScanJobs Feature"
        ScanJobGrid
    end

    subgraph "ScanResults Feature"
        ResultPanel
        ResultSidebar
        ResultBody
        InfoPanel
        MetadataPanel
        TranscriptPanel
        ErrorPanel
        ScanResultHeader
        ScanResultNav
    end

    subgraph "Shared Components"
        Navbar
        Footer
        Pager
        ToolButton
        ColumnHeader
        Value
        Explanation
        ValidationResult
        Identifier
        Error
        TaskName
    end

    %% ScansPanel dependencies
    ScansPanel --> Navbar
    ScansPanel --> ScansPanelBody
    ScansPanel --> ScansPanelTitle

    %% ScansPanelBody dependencies
    ScansPanelBody --> ScanInfo
    ScansPanelBody --> ScanResultsPanel
    ScansPanelBody --> ScanResultsSearch
    ScansPanelBody --> ScanResultsFilter
    ScansPanelBody --> ScanResultsGroup
    ScansPanelBody --> ScanDataframeWrapTextButton
    ScansPanelBody --> ScanDataframeFilterColumnsButton
    ScansPanelBody --> ScanDataframeClearFiltersButton
    ScansPanelBody --> ScanDataframeColumnsPopover

    %% ScanResultsPanel dependencies
    ScanResultsPanel --> Footer
    ScanResultsPanel --> ScanResultsBody
    ScanResultsPanel --> ScanResultsOutline

    %% ScanResultsBody dependencies
    ScanResultsBody --> ScanResultsList

    %% ScanResultsList dependencies
    ScanResultsList --> ScanHeader
    ScanResultsList --> ScanResultGroup
    ScanResultsList --> ScanResultsRow

    %% ScanResultsRow dependencies
    ScanResultsRow --> Error
    ScanResultsRow --> Explanation
    ScanResultsRow --> Identifier
    ScanResultsRow --> ValidationResult
    ScanResultsRow --> Value
    ScanResultsRow --> TaskName

    %% ScanResultHeader dependencies
    ScanResultHeader --> TaskName

    %% Dataframe buttons
    ScanDataframeWrapTextButton --> ToolButton
    ScanDataframeFilterColumnsButton --> ToolButton
    ScanDataframeClearFiltersButton --> ToolButton

    %% ScanJobsPanel dependencies
    ScanJobsPanel --> Footer
    ScanJobsPanel --> Navbar
    ScanJobsPanel --> ScanJobGrid

    %% Footer dependencies
    Footer --> Pager

    %% ScanResultPanel dependencies
    ScanResultPanel --> Navbar
    ScanResultPanel --> ToolButton
    ScanResultPanel --> InfoPanel
    ScanResultPanel --> MetadataPanel
    ScanResultPanel --> ResultPanel
    ScanResultPanel --> TranscriptPanel
    ScanResultPanel --> ScanResultHeader
    ScanResultPanel --> ScanResultNav

    %% ResultPanel dependencies
    ResultPanel --> ResultBody
    ResultPanel --> ResultSidebar

    %% ResultSidebar dependencies
    ResultSidebar --> Explanation
    ResultSidebar --> ValidationResult
    ResultSidebar --> Value

    %% ResultBody dependencies
    ResultBody --> ColumnHeader
```

## Adjacency List (app/ components)

```json
{
  "ScansPanel": ["Navbar", "ScansPanelBody", "ScansPanelTitle"],
  "ScansPanelBody": ["ScanInfo", "ScanDataframeClearFiltersButton", "ScanDataframeColumnsPopover", "ScanDataframeFilterColumnsButton", "ScanDataframeWrapTextButton", "ScanResultsFilter", "ScanResultsGroup", "ScanResultsPanel", "ScanResultsSearch"],
  "ScansPanelTitle": [],
  "ScanInfo": [],
  "ScanResultsPanel": ["Footer", "ScanResultsBody", "ScanResultsOutline"],
  "ScanResultsSearch": [],
  "ScanResultsOutline": [],
  "ScanResultsBody": ["ScanResultsList"],
  "ScanDataframeWrapTextButton": ["ToolButton"],
  "ScanDataframeFilterColumnsButton": ["ToolButton"],
  "ScanDataframeClearFiltersButton": ["ToolButton"],
  "ScanDataframeColumnsPopover": [],
  "ScanResultsGroup": [],
  "ScanResultsFilter": [],
  "ScanResultsList": ["ScanHeader", "ScanResultGroup", "ScanResultsRow"],
  "ScanResultsRow": ["Error", "Explanation", "Identifier", "TaskName", "ValidationResult", "Value"],
  "ScanResultGroup": [],
  "ScanHeader": [],
  "ScanJobGrid": [],
  "ScanJobsPanel": ["Footer", "Navbar", "ScanJobGrid"],
  "Navbar": [],
  "ValidationResult": [],
  "ColumnHeader": [],
  "Explanation": [],
  "Identifier": [],
  "Value": [],
  "Footer": ["Pager"],
  "ToolButton": [],
  "Error": [],
  "Pager": [],
  "ResultSidebar": ["Explanation", "ValidationResult", "Value"],
  "ResultBody": ["ColumnHeader"],
  "ResultPanel": ["ResultBody", "ResultSidebar"],
  "TranscriptPanel": [],
  "InfoPanel": [],
  "ScanResultPanel": ["InfoPanel", "MetadataPanel", "Navbar", "ResultPanel", "ScanResultHeader", "ScanResultNav", "ToolButton", "TranscriptPanel"],
  "ErrorPanel": [],
  "ScanResultHeader": ["TaskName"],
  "ScanResultNav": [],
  "MetadataPanel": [],
  "TaskName": []
}
```

## Derived: Leaf Nodes

Components with no dependencies on other app/ components:
```
Navbar, ScansPanelTitle, ScanInfo, ScanResultsSearch, ScanResultsOutline,
ScanDataframeColumnsPopover, ScanResultsGroup, ScanResultsFilter, ScanResultGroup,
ScanHeader, ScanJobGrid, ValidationResult, ColumnHeader, Explanation, Identifier,
Value, ToolButton, Error, Pager, TranscriptPanel, InfoPanel, ErrorPanel,
ScanResultNav, MetadataPanel, TaskName
```

## Derived: Consumers (Reverse Graph)

```json
{
  "Navbar": ["ScansPanel", "ScanJobsPanel", "ScanResultPanel"],
  "ScansPanelBody": ["ScansPanel"],
  "ScansPanelTitle": ["ScansPanel"],
  "ScanInfo": ["ScansPanelBody"],
  "ScanDataframeClearFiltersButton": ["ScansPanelBody"],
  "ScanDataframeColumnsPopover": ["ScansPanelBody"],
  "ScanDataframeFilterColumnsButton": ["ScansPanelBody"],
  "ScanDataframeWrapTextButton": ["ScansPanelBody"],
  "ScanResultsFilter": ["ScansPanelBody"],
  "ScanResultsGroup": ["ScansPanelBody"],
  "ScanResultsPanel": ["ScansPanelBody"],
  "ScanResultsSearch": ["ScansPanelBody"],
  "Footer": ["ScanResultsPanel", "ScanJobsPanel"],
  "ScanResultsBody": ["ScanResultsPanel"],
  "ScanResultsOutline": ["ScanResultsPanel"],
  "ScanResultsList": ["ScanResultsBody"],
  "ToolButton": ["ScanDataframeWrapTextButton", "ScanDataframeFilterColumnsButton", "ScanDataframeClearFiltersButton", "ScanResultPanel"],
  "ScanHeader": ["ScanResultsList"],
  "ScanResultGroup": ["ScanResultsList"],
  "ScanResultsRow": ["ScanResultsList"],
  "Error": ["ScanResultsRow"],
  "Explanation": ["ScanResultsRow", "ResultSidebar"],
  "Identifier": ["ScanResultsRow"],
  "TaskName": ["ScanResultHeader", "ScanResultsRow"],
  "ValidationResult": ["ScanResultsRow", "ResultSidebar"],
  "Value": ["ScanResultsRow", "ResultSidebar"],
  "Pager": ["Footer"],
  "ScanJobGrid": ["ScanJobsPanel"],
  "InfoPanel": ["ScanResultPanel"],
  "MetadataPanel": ["ScanResultPanel"],
  "ResultPanel": ["ScanResultPanel"],
  "ScanResultHeader": ["ScanResultPanel"],
  "ScanResultNav": ["ScanResultPanel"],
  "TranscriptPanel": ["ScanResultPanel"],
  "ResultBody": ["ResultPanel"],
  "ResultSidebar": ["ResultPanel"],
  "ColumnHeader": ["ResultBody"]
}
```

## External Dependencies (outside app/)

These are imported from sibling directories, not app/:
- `/components/`: Card, ErrorPanel, NoContentsPanel, ANSIDisplay, LiveVirtualList, LabeledValue, PopOver, DataframeView, SegmentedControl, TabSet, TabPanel, TextInput, CopyButton, ActivityBar, ExtendedFindProvider
- `/content/`: MetaDataGrid, RecordTree, MarkdownDivWithReferences, MarkdownReference
- `/chat/`: ChatView, ChatViewVirtualList
- `/transcript/`: TranscriptView
- `/usage/`: ModelTokenTable

## Notes

- Graph includes only app/ → app/ component references
- External deps (components/, content/, etc.) excluded from adjacency list
- AgGridReact excluded (3rd party library)
- Branch: `main`

### Name Clarification

Two similarly-named components exist:
| Export Name | File | Purpose | Used By |
|-------------|------|---------|---------|
| `ScanResultsGroup` | `scans/results/ScanResultsGroup.tsx` | Dropdown to select grouping | ScansPanelBody |
| `ScanResultGroup` | `scans/results/list/ScanResultsGroup.tsx` | Group header display in list | ScanResultsList |

## Server Data

Data retrieved by `server/hooks.ts`:

**Zustand State (direct):**
| Item | Type | Source Hook | Source API |
|------|------|-------------|------------|
| `resultsDir` | `string` | `useServerScans` | `api.getScans()` |
| `scans` | `Status[]` | `useServerScans` | `api.getScans()` |
| `selectedScanStatus` | `Status` | `useServerScan` | `api.getScan()` |
| `selectedScanLocation` | `string` | `useServerScan` | derived from URL |

**External Ref Data (`selectedScanResultDataRef`):**

This data is stored outside zustand in a plain object ref for three reasons:

1. **Lazy Loading** (primary) - This data is not required for Feature Panels to render. Panels display their skeleton (header, nav, controls) using zustand state, then show loading indicators while ref data fetches. This enables progressive rendering.
2. **Serialization** - zustand's `persist` middleware would attempt to serialize this data to localStorage; `ColumnTable` (arquero) doesn't serialize properly
3. **Performance** - large dataframes in zustand state would trigger unnecessary re-renders and deep equality checks

The ref is accessed through getter functions exposed on the store.

| Ref Field | Type | Source Hook | Source API |
|-----------|------|-------------|------------|
| `data` | `ColumnTable` | `useServerScanDataframe` | `api.getScannerDataframe()` |
| `previews` | `ScanResultSummary[]` | `useServerScanDataframe` | derived from data |
| `input` | `Input` | `useServerScanDataframeInput` | `api.getScannerDataframeInput()` |
| `inputUuid` | `string` | `useServerScanDataframeInput` | derived from URL |
| `inputType` | `string` | `useServerScanDataframeInput` | `api.getScannerDataframeInput()` |

**Getter Functions (access external ref):**
| Function | Returns |
|----------|---------|
| `getSelectedScanResultData()` | `ColumnTable` |
| `getSelectedScanResultInputData()` | `ScanResultInputData` |
| `getSelectedScanResultSummaries()` | `ScanResultSummary[]` |

## Deep Dive: `selectedScanStatus`

This item warrants special attention because it combines client state (selection) with server data (Status object).

**Two related store items:**
| Item | Type | Nature |
|------|------|--------|
| `selectedScanLocation` | `string` | Client state - which scan URL is selected |
| `selectedScanStatus` | `Status` | Server data - fetched for that location |

**Selection flow:**
```
URL navigation
  → parseScanResultPath(relativePath) extracts scanPath
  → setSelectedScanLocation(scanPath)           [client choice stored]
  → join(scanPath, resultsDir) = absolute location
  → Check scans[] cache OR api.getScan(location) [server fetch]
  → setSelectedScanStatus(status)               [server data stored]
```

**Key characteristics:**
- `Status` is **purely server data** - never modified client-side
- **Caching**: First checks if Status exists in `scans[]` list before fetching
- **Persistence**: Persisted to localStorage via zustand (useful for page refresh)
- Components only **read** from Status (display-only)

**Status type structure:**
```typescript
interface Status {
  complete: boolean;      // Scan finished?
  spec: ScanSpec;         // Scan metadata (name, model, scanners, transcripts)
  location: string;       // Absolute path to scan results
  summary: Summary;       // Aggregated results (tokens, metrics, validations)
  errors: Error[];        // Scan-level errors
}
```

## Components Outside Feature Panels Consuming Server Data

Feature Panels = `ScansPanel`, `ScanJobsPanel`, `ScanResultPanel`

| Component | Server Data Consumed | Layer | Usage | Status |
|-----------|---------------------|-------|-------|-------|
| Navbar | `resultsDir` | Shared | Builds breadcrumb navigation path | FIXED |
| ScanJobGrid | `resultsDir` | ScanJobs Feature | computes relative paths | FIXED |
| ScanJobGrid | `scans`| ScanJobs Feature | Transforms scans to grid rows| FIXED |
| ScansPanelBody | `selectedScanStatus` | Scans Feature | Passes to JSON panel; determines tab content | |
| ScansPanelTitle | `resultsDir` | Scans Feature | computes relative paths | FIXED |
| ScansPanelTitle | `selectedScanStatus` | Scans Feature | Displays name, model, transcript count, timestamp | |
| ScanInfo | `selectedScanStatus` | Scans Feature | Shows scan ID, args, source, origin, commit | |
| ScanResultsOutline | `selectedScanStatus` | Scans Feature | Builds scanner summary with metrics/errors | |
| ScanResultsBody | `getSelectedScanResultData()` | Scans Feature | Powers list/dataframe views with ColumnTable | |
| ScanResultsList | `selectedScanStatus` | Scans Feature | Uses completion state for initial filter | |
