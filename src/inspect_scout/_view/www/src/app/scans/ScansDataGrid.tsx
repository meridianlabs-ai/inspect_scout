import {
  flexRender,
  getCoreRowModel,
  OnChangeFn,
  SortingState,
  useReactTable,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import clsx from "clsx";
import { FC, useCallback, useEffect, useMemo, useRef } from "react";

import { ApplicationIcons } from "../../components/icons";
import { useLoggingNavigate } from "../../debugging/navigationDebugging";
import { scanRoute } from "../../router/url";
import { useStore } from "../../state/store";
import type { ScanStatusWithActiveInfo } from "../../types/api-types";
import { toRelativePath } from "../../utils/path";

import {
  DEFAULT_COLUMN_ORDER,
  getScanColumns,
  ScanColumn,
  ScanRow,
} from "./columns";
import styles from "./ScansDataGrid.module.css";

// Generate a stable key for a scan item
function scanItemKey(index: number, item?: ScanRow): string {
  if (!item) {
    return String(index);
  }
  return item.spec.scan_id;
}

interface ScansDataGridProps {
  scans: ScanStatusWithActiveInfo[];
  resultsDir: string | undefined;
  className?: string | string[];
  loading?: boolean;
  /** Called when scroll position nears end */
  onScrollNearEnd?: () => void;
  /** Whether more data is available to fetch */
  hasMore?: boolean;
  /** Distance from bottom (in px) at which to trigger callback */
  fetchThreshold?: number;
}

export const ScansDataGrid: FC<ScansDataGridProps> = ({
  scans,
  resultsDir,
  className,
  loading,
  onScrollNearEnd,
  hasMore = false,
  fetchThreshold = 500,
}) => {
  // The table container which provides the scrollable region
  const containerRef = useRef<HTMLDivElement>(null);
  const tableRef = useRef<HTMLTableElement>(null);
  const navigate = useLoggingNavigate("ScansDataGrid");

  // Table state from store
  const sorting = useStore((state) => state.scansTableState.sorting);
  const columnOrder = useStore((state) => state.scansTableState.columnOrder);
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
    () => getScanColumns(visibleColumns ?? undefined),
    [visibleColumns]
  );

  // Compute effective column order
  const effectiveColumnOrder = useMemo(() => {
    if (columnOrder && columnOrder.length > 0) {
      return columnOrder;
    }
    return DEFAULT_COLUMN_ORDER;
  }, [columnOrder]);

  // Sorting
  const handleSortingChange: OnChangeFn<SortingState> = useCallback(
    (updaterOrValue) => {
      const newValue =
        typeof updaterOrValue === "function"
          ? updaterOrValue(sorting)
          : updaterOrValue;
      setTableState((prev) => ({ ...prev, sorting: newValue }));
    },
    [sorting, setTableState]
  );

  // Create table instance
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualSorting: true,
    columnResizeMode: "onChange",
    enableColumnResizing: true,
    enableSorting: true,
    enableMultiSort: true,
    enableSortingRemoval: true,
    maxMultiSortColCount: 3,
    getRowId: (row) => row.spec.scan_id,
    state: {
      columnOrder: effectiveColumnOrder,
      sorting,
    },
    onSortingChange: handleSortingChange,
  });

  const { rows } = table.getRowModel();

  // Row click handler - navigate to scan
  const handleRowClick = useCallback(
    (row: ScanRow) => {
      if (resultsDir) {
        void navigate(scanRoute(resultsDir, row.relativeLocation));
      }
    },
    [navigate, resultsDir]
  );

  // Create virtualizer
  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => containerRef.current,
    // Estimated row height in pixels
    estimateSize: () => 29,
    // Number of items to render outside visible area
    overscan: 10,
    // Item keys
    getItemKey: (index) => scanItemKey(index, rows[index]?.original),
  });

  const virtualItems = rowVirtualizer.getVirtualItems();
  const totalSize = rowVirtualizer.getTotalSize();

  // Infinite scroll: notify parent when scrolled near bottom
  const checkScrollNearEnd = useCallback(
    (containerRefElement?: HTMLDivElement | null) => {
      if (!containerRefElement || !hasMore || !onScrollNearEnd) return;

      const { scrollHeight, scrollTop, clientHeight } = containerRefElement;
      const distanceFromBottom = scrollHeight - scrollTop - clientHeight;

      if (distanceFromBottom < fetchThreshold) {
        onScrollNearEnd();
      }
    },
    [onScrollNearEnd, hasMore, fetchThreshold]
  );

  // Check on mount if we need to fetch more
  useEffect(() => {
    checkScrollNearEnd(containerRef.current);
  }, [checkScrollNearEnd]);

  const onScroll = useCallback(
    (e: React.UIEvent<HTMLDivElement>) =>
      checkScrollNearEnd(e.currentTarget as HTMLDivElement),
    [checkScrollNearEnd]
  );

  return (
    <div
      ref={containerRef}
      className={clsx(className, styles.container)}
      onScroll={onScroll}
    >
      <table ref={tableRef} className={styles.table}>
        <thead className={styles.thead}>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id} className={styles.headerRow}>
              {headerGroup.headers.map((header) => {
                const columnMeta = (header.column.columnDef as ScanColumn).meta;
                const align = columnMeta?.align;
                return (
                  <th
                    key={header.id}
                    className={styles.headerCell}
                    style={{ width: header.getSize() }}
                    title={(header.column.columnDef as ScanColumn).headerTitle}
                  >
                    <div
                      className={clsx(
                        styles.headerContent,
                        align === "center" && styles.headerCellCenter
                      )}
                      onClick={header.column.getToggleSortingHandler()}
                      style={{ cursor: "pointer" }}
                    >
                      <span className={styles.headerText}>
                        {header.isPlaceholder
                          ? null
                          : flexRender(
                              header.column.columnDef.header,
                              header.getContext()
                            )}
                      </span>
                      {{
                        asc: (
                          <i
                            className={clsx(
                              ApplicationIcons.arrows.up,
                              styles.sortIcon
                            )}
                          />
                        ),
                        desc: (
                          <i
                            className={clsx(
                              ApplicationIcons.arrows.down,
                              styles.sortIcon
                            )}
                          />
                        ),
                      }[header.column.getIsSorted() as string] ?? null}
                    </div>
                    <div
                      className={clsx(
                        styles.resizer,
                        header.column.getIsResizing() && styles.resizerActive
                      )}
                      onMouseDown={header.getResizeHandler()}
                      onTouchStart={header.getResizeHandler()}
                    />
                  </th>
                );
              })}
            </tr>
          ))}
        </thead>
        <tbody className={styles.tbody} style={{ height: `${totalSize}px` }}>
          {virtualItems.length > 0 ? (
            virtualItems.map((virtualRow) => {
              const row = rows[virtualRow.index];
              if (!row) return null;

              const rowKey = scanItemKey(virtualRow.index, row.original);

              return (
                <tr
                  key={rowKey}
                  className={styles.row}
                  style={{ transform: `translateY(${virtualRow.start}px)` }}
                  onClick={() => handleRowClick(row.original)}
                >
                  {row.getVisibleCells().map((cell) => {
                    const columnDef = cell.column.columnDef as ScanColumn;
                    const align = columnDef.meta?.align;
                    return (
                      <td
                        key={cell.id}
                        className={clsx(
                          styles.cell,
                          align === "center" && styles.cellCenter
                        )}
                        style={{ width: cell.column.getSize() }}
                      >
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext()
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })
          ) : (
            <tr className={clsx(styles.noMatching, "text-size-smaller")}>
              <td>
                {loading
                  ? "Loading..."
                  : !resultsDir
                    ? "No scans directory configured."
                    : "No matching scans"}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
};
