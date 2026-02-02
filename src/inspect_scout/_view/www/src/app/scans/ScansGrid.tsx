import { FC, useEffect, useMemo, useRef } from "react";

import { ScalarValue } from "../../api/api";
import { scanRoute } from "../../router/url";
import { useStore } from "../../state/store";
import type { ScanStatusWithActiveInfo } from "../../types/api-types";
import { toRelativePath } from "../../utils/path";
import { DataGrid } from "../components/dataGrid";

import {
  DEFAULT_COLUMN_ORDER,
  getScanColumns,
  ScanColumn,
  ScanRow,
} from "./columns";
import { useColumnSizing } from "./columnSizing";

// Generate a stable key for a scan item
function scanItemKey(index: number, item?: ScanRow): string {
  if (!item) {
    return String(index);
  }
  return item.spec.scan_id;
}

interface ScansGridProps {
  scans: ScanStatusWithActiveInfo[];
  resultsDir: string | undefined;
  className?: string | string[];
  loading?: boolean;
  /** Called when scroll position nears end */
  onScrollNearEnd?: (distanceFromBottom?: number) => void;
  /** Whether more data is available to fetch */
  hasMore?: boolean;
  /** Distance from bottom (in px) at which to trigger callback */
  fetchThreshold?: number;
  /** Autocomplete suggestions for the currently editing filter column */
  filterSuggestions?: ScalarValue[];
  /** Called when a filter column starts/stops being edited */
  onFilterColumnChange?: (columnId: string | null) => void;
}

export const ScansGrid: FC<ScansGridProps> = ({
  scans,
  resultsDir,
  className,
  loading,
  onScrollNearEnd,
  hasMore = false,
  fetchThreshold = 500,
  filterSuggestions = [],
  onFilterColumnChange,
}) => {
  // Table ref for DOM measurement (used by column sizing)
  const tableRef = useRef<HTMLTableElement>(null);

  // Table state from store
  const sorting = useStore((state) => state.scansTableState.sorting);
  const columnOrder = useStore((state) => state.scansTableState.columnOrder);
  const columnFilters = useStore(
    (state) => state.scansTableState.columnFilters
  );
  const rowSelection = useStore((state) => state.scansTableState.rowSelection);
  const focusedRowId = useStore((state) => state.scansTableState.focusedRowId);
  const visibleColumns = useStore(
    (state) => state.scansTableState.visibleColumns
  );
  const setTableState = useStore((state) => state.setScansTableState);
  const setVisibleScanJobCount = useStore(
    (state) => state.setVisibleScanJobCount
  );

  // Add computed relativeLocation to each scan
  const data = useMemo(
    (): ScanRow[] =>
      scans.map((scan) => ({
        ...scan,
        relativeLocation: toRelativePath(scan.location, resultsDir),
      })),
    [scans, resultsDir]
  );

  // Update visible count
  useEffect(() => {
    setVisibleScanJobCount(data.length);
  }, [data.length, setVisibleScanJobCount]);

  // Define table columns based on visible columns from store
  const columns = useMemo<ScanColumn[]>(
    () => getScanColumns(visibleColumns),
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
    data,
  });

  // Track if we've done initial auto-sizing
  const hasInitializedRef = useRef(false);

  // Track previous visible columns to detect changes
  const previousVisibleColumnsRef = useRef<typeof visibleColumns | null>(null);

  // Auto-size columns on initial load when data is available
  useEffect(() => {
    if (!hasInitializedRef.current && data.length > 0) {
      hasInitializedRef.current = true;
      applyAutoSizing();
    }
  }, [data.length, applyAutoSizing]);

  // Auto-size when visible columns change
  // (applyAutoSizing preserves manually resized columns)
  useEffect(() => {
    const previousVisibleColumns = previousVisibleColumnsRef.current;
    previousVisibleColumnsRef.current = visibleColumns;

    if (previousVisibleColumns && previousVisibleColumns !== visibleColumns) {
      applyAutoSizing();
    }
  }, [visibleColumns, applyAutoSizing]);

  // Compute effective column order
  const effectiveColumnOrder = useMemo(() => {
    if (columnOrder && columnOrder.length > 0) {
      return columnOrder;
    }
    return DEFAULT_COLUMN_ORDER;
  }, [columnOrder]);

  // Get row ID
  const getRowId = (row: ScanRow): string => row.spec.scan_id;

  // Get route for navigation
  const getRowRoute = (row: ScanRow): string => {
    if (!resultsDir) return "";
    return scanRoute(resultsDir, row.relativeLocation);
  };

  return (
    <DataGrid
      data={data}
      columns={columns}
      getRowId={getRowId}
      getRowKey={scanItemKey}
      state={{
        sorting,
        columnOrder: effectiveColumnOrder,
        columnFilters,
        columnSizing,
        rowSelection,
        focusedRowId,
      }}
      onStateChange={setTableState}
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
      emptyMessage="No matching scans"
      noConfigMessage="No scans directory configured."
    />
  );
};
