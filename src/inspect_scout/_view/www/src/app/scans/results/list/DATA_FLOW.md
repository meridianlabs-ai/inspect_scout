# ScanResultsList Data Flow

## Overview

```
Parquet files → Python API → Arrow IPC (LZ4) → JS client → ColumnTable → ScanResultSummary[] → UI
```

## Chain

### 0. Server Endpoint (Python)

**Endpoint**: `GET /scanjobs/{scan}/{scanner}` ([_api_v2.py](../../../../../../../_view/_api_v2.py):349)

1. `scan_results_arrow_async(scan_path)` → `ScanResultsArrow`
2. `FileRecorder.results_arrow()` ([file.py](../../../../../../../_recorder/file.py):237)
   - Reads `{scanner}.parquet` from scan directory
   - Returns `pa.RecordBatchReader` over parquet batches
3. Streams Arrow IPC with LZ4 compression
   - Excludes `input` column for efficiency
   - Media type: `application/vnd.apache.arrow.stream; codecs=lz4`

### 1. Client Fetch
`useServerScanDataframe` ([server/hooks.ts](../../server/hooks.ts))
- Calls `api.getScannerDataframe(location, scanner)`
- Returns LZ4-compressed Arrow IPC bytes

### 2. Decode & Expand
- `decodeArrowBytes` — decompress, convert to Arquero ColumnTable
- `expandResultsetRows` ([utils/arrow.ts](../../utils/arrow.ts)) — explode `value_type="resultset"` rows into individual result rows

### 3. Component Receives Data
`ScanResultsList` receives `columnTable: ColumnTable` prop

### 4. Parse to Summaries
`useScanResultSummaries` ([hooks.ts](../../hooks.ts))
- Extracts row objects via `columnTable.objects()`
- Calls `parseScanResultSummaries` ([arrowHelpers.ts](../../arrowHelpers.ts))
- Async parses JSON fields (validation_result, transcript_metadata, etc.)
- Returns `ScanResultSummary[]`

### 5. Filter/Sort/Group
Component applies:
- Text search filter
- Positive/all results filter
- Sort by columns
- Group by (source, label, id, epoch, model, none)

### 6. Render
`LiveVirtualList` renders virtualized rows

## Key Types

| Type | Location | Purpose |
|------|----------|---------|
| `ColumnTable` | arquero | In-memory columnar table |
| `ScanResultSummary` | [types.ts](../../types.ts) | Row data for list display |
| `ScanResultData` | [types.ts](../../types.ts) | Full detail (extends Summary) |
