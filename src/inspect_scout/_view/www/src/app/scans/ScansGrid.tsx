import { FC, useEffect, useMemo } from "react";

import { ScalarValue } from "../../api/api";
import { scanRoute } from "../../router/url";
import { useStore } from "../../state/store";
import type { ScanStatusWithActiveInfo } from "../../types/api-types";
import { toRelativePath } from "../../utils/path";
import { DataGrid } from "../components/dataGrid";

import { DEFAULT_COLUMN_ORDER, getScanColumns, ScanColumn, ScanRow } from "./columns";

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
  // Table state from store
  const sorting = useStore((state) => state.scansTableState.sorting);
  const columnOrder = useStore((state) => state.scansTableState.columnOrder);
  const columnFilters = useStore((state) => state.scansTableState.columnFilters);
  const columnSizing = useStore((state) => state.scansTableState.columnSizing);
  const rowSelection = useStore((state) => state.scansTableState.rowSelection);
  const focusedRowId = useStore((state) => state.scansTableState.focusedRowId);
  const visibleColumns = useStore((state) => state.scansTableState.visibleColumns);
  const setTableState = useStore((state) => state.setScansTableState);
  const setVisibleScanJobCount = useStore((state) => state.setVisibleScanJobCount);

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
      className={className}
      loading={loading}
      emptyMessage="No matching scans"
      noConfigMessage="No scans directory configured."
    />
  );
};
