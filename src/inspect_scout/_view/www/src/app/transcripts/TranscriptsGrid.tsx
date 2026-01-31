import { FC, useEffect, useMemo, useRef } from "react";

import { ScalarValue } from "../../api/api";
import { transcriptRoute } from "../../router/url";
import { useStore } from "../../state/store";
import { TranscriptInfo } from "../../types/api-types";
import { DataGrid } from "../components/dataGrid";

import { TranscriptColumn, getTranscriptColumns, DEFAULT_COLUMN_ORDER } from "./columns";
import { useColumnSizing } from "./columnSizing";

// Default visible columns (stable reference)
const DEFAULT_VISIBLE_COLUMNS: Array<keyof TranscriptInfo> = [
  "success",
  "date",
  "task_set",
  "task_id",
  "task_repeat",
  "model",
  "score",
  "message_count",
  "total_time",
  "total_tokens",
];

// Generate a stable key for a transcript item
function transcriptItemKey(index: number, item?: TranscriptInfo): string {
  if (!item) {
    return String(index);
  }
  return `${item.source_uri}/${item.transcript_id}`;
}

interface TranscriptGridProps {
  transcripts: TranscriptInfo[];
  transcriptsDir?: string | null;
  className?: string | string[];
  /** Called when scroll position nears end; receives distance from bottom in px. */
  onScrollNearEnd: (distanceFromBottom: number) => void;
  /** Whether more data is available to fetch. */
  hasMore: boolean;
  /** Distance from bottom (in px) at which to trigger callback. */
  fetchThreshold: number;
  loading?: boolean;
  /** Autocomplete suggestions for the currently editing filter column */
  filterSuggestions?: ScalarValue[];
  /** Called when a filter column starts/stops being edited */
  onFilterColumnChange?: (columnId: string | null) => void;
}

export const TranscriptsGrid: FC<TranscriptGridProps> = ({
  transcripts,
  transcriptsDir,
  className,
  onScrollNearEnd,
  hasMore,
  fetchThreshold,
  loading,
  filterSuggestions = [],
  onFilterColumnChange,
}) => {
  // Table ref for DOM measurement (used by column sizing)
  const tableRef = useRef<HTMLTableElement>(null);

  // Table state from store
  const columnOrder = useStore((state) => state.transcriptsTableState.columnOrder);
  const sorting = useStore((state) => state.transcriptsTableState.sorting);
  const rowSelection = useStore((state) => state.transcriptsTableState.rowSelection);
  const columnFilters = useStore((state) => state.transcriptsTableState.columnFilters) ?? {};
  const focusedRowId = useStore((state) => state.transcriptsTableState.focusedRowId);
  const visibleColumns =
    useStore((state) => state.transcriptsTableState.visibleColumns) ?? DEFAULT_VISIBLE_COLUMNS;
  const setTableState = useStore((state) => state.setTranscriptsTableState);

  // Define table columns based on visible columns from store
  const columns = useMemo<TranscriptColumn[]>(
    () => getTranscriptColumns(visibleColumns),
    [visibleColumns]
  );

  // Column sizing with min/max constraints and auto-sizing
  const {
    columnSizing,
    handleColumnSizingChange,
    applyAutoSizing,
    resetColumnSize,
  } = useColumnSizing({
    columns,
    tableRef,
    data: transcripts,
  });

  // Track if we've done initial auto-sizing
  const hasInitializedRef = useRef(false);

  // Track previous visible columns to detect changes
  const previousVisibleColumnsRef = useRef<typeof visibleColumns | null>(null);

  // Auto-size columns on initial load when data is available
  useEffect(() => {
    if (!hasInitializedRef.current && transcripts.length > 0) {
      hasInitializedRef.current = true;
      applyAutoSizing();
    }
  }, [transcripts.length, applyAutoSizing]);

  // Auto-size when visible columns change
  // (applyAutoSizing preserves manually resized columns)
  useEffect(() => {
    const previousVisibleColumns = previousVisibleColumnsRef.current;
    previousVisibleColumnsRef.current = visibleColumns;

    if (previousVisibleColumns && previousVisibleColumns !== visibleColumns) {
      applyAutoSizing();
    }
  }, [visibleColumns, applyAutoSizing]);

  // Compute effective column order: use explicit order if set, otherwise derive from DEFAULT_COLUMN_ORDER
  const effectiveColumnOrder = useMemo(() => {
    if (columnOrder && columnOrder.length > 0) {
      return columnOrder;
    }
    // Filter DEFAULT_COLUMN_ORDER to only include visible columns
    return DEFAULT_COLUMN_ORDER.filter((col) => visibleColumns.includes(col));
  }, [columnOrder, visibleColumns]);

  // Get row ID
  const getRowId = (row: TranscriptInfo): string => String(row.transcript_id);

  // Get route for navigation
  const getRowRoute = (row: TranscriptInfo): string => {
    if (!transcriptsDir) return "";
    return transcriptRoute(transcriptsDir, String(row.transcript_id));
  };

  return (
    <DataGrid
      data={transcripts}
      columns={columns}
      getRowId={getRowId}
      getRowKey={transcriptItemKey}
      sorting={sorting}
      columnOrder={effectiveColumnOrder}
      columnFilters={columnFilters}
      columnSizing={columnSizing}
      rowSelection={rowSelection}
      focusedRowId={focusedRowId}
      setTableState={setTableState}
      getRowRoute={getRowRoute}
      onScrollNearEnd={onScrollNearEnd}
      hasMore={hasMore}
      fetchThreshold={fetchThreshold}
      filterSuggestions={filterSuggestions}
      onFilterColumnChange={onFilterColumnChange}
      onColumnSizingChange={handleColumnSizingChange}
      onResetColumnSize={resetColumnSize}
      className={className}
      loading={loading}
      emptyMessage="No matching transcripts"
      noConfigMessage="No transcripts directory configured."
    />
  );
};
