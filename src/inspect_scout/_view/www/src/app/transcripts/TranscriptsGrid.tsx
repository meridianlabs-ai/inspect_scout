import {
  ColumnDef,
  ColumnSizingState,
  flexRender,
  getCoreRowModel,
  OnChangeFn,
  RowSelectionState,
  SortingState,
  useReactTable,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import clsx from "clsx";
import {
  DragEvent,
  FC,
  KeyboardEvent,
  MouseEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useNavigate } from "react-router-dom";

import type { SimpleCondition } from "../../query/types";
import { transcriptRoute } from "../../router/url";
import { useStore } from "../../state/store";
import { TranscriptInfo } from "../../types/api-types";
import { Score } from "../../types/api-types";
import { printArray } from "../../utils/array";
import { formatNumber, formatPrettyDecimal } from "../../utils/format";
import { printObject } from "../../utils/object";
import { ApplicationIcons } from "../appearance/icons";

import { ColumnFilterControl, FilterType } from "./ColumnFilterControl";
import styles from "./TranscriptsGrid.module.css";

type TranscriptColumn = ColumnDef<TranscriptInfo> & {
  meta?: {
    align?: "left" | "center" | "right";
    filterable?: boolean;
    filterType?: FilterType;
  };
};

// Helper to create strongly-typed columns
function createColumn<K extends keyof TranscriptInfo>(config: {
  accessorKey: K;
  header: string;
  size?: number;
  meta?: {
    align?: "left" | "center" | "right";
    filterable?: boolean;
    filterType?: FilterType;
  };
  cell?: (value: TranscriptInfo[K]) => React.ReactNode;
}): TranscriptColumn {
  return {
    accessorKey: config.accessorKey as string,
    header: config.header,
    size: config.size,
    meta: config.meta,
    cell: (info) => {
      const value = info.getValue() as TranscriptInfo[K];
      if (config.cell) {
        return config.cell(value);
      }
      if (value === undefined || value === null) {
        return "-";
      }
      return String(value);
    },
  };
}

// Generate a stable key for a transcript item
function transcriptItemKey(index: number, item?: TranscriptInfo): string {
  if (!item) {
    return String(index);
  }
  return `${item.source_uri}/${item.transcript_id}`;
}

interface TranscriptGridProps {
  transcripts: TranscriptInfo[];
  transcriptsDir: string;
  className?: string | string[];
  /** Called when scroll position nears end; receives distance from bottom in px. */
  onScrollNearEnd: (distanceFromBottom: number) => void;
  /** Whether more data is available to fetch. */
  hasMore: boolean;
  /** Distance from bottom (in px) at which to trigger callback. */
  fetchThreshold: number;
}

export const TranscriptsGrid: FC<TranscriptGridProps> = ({
  transcripts,
  transcriptsDir,
  className,
  onScrollNearEnd,
  hasMore,
  fetchThreshold,
}) => {
  // The table container which provides the scrollable region
  const containerRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  // Table state
  const columnSizing = useStore(
    (state) => state.transcriptsTableState.columnSizing
  );
  const columnOrder = useStore(
    (state) => state.transcriptsTableState.columnOrder
  );
  const sorting = useStore((state) => state.transcriptsTableState.sorting);
  const rowSelection = useStore(
    (state) => state.transcriptsTableState.rowSelection
  );
  const columnFilters =
    useStore((state) => state.transcriptsTableState.columnFilters) ?? {};
  const focusedRowId = useStore(
    (state) => state.transcriptsTableState.focusedRowId
  );
  const setTableState = useStore((state) => state.setTranscriptsTableState);
  const handleColumnFilterChange = useCallback(
    (columnId: string, condition: SimpleCondition | null) => {
      setTableState((prev) => ({
        ...prev,
        columnFilters: {
          ...(prev.columnFilters ?? {}),
          [columnId]: condition,
        },
      }));
    },
    [setTableState]
  );

  // Column sizing
  const handleColumnSizingChange: OnChangeFn<ColumnSizingState> = useCallback(
    (updaterOrValue) => {
      const newValue =
        typeof updaterOrValue === "function"
          ? updaterOrValue(columnSizing)
          : updaterOrValue;
      setTableState((prev) => ({ ...prev, columnSizing: newValue }));
    },
    [columnSizing, setTableState]
  );

  // Column ordering
  const handleColumnOrderChange: OnChangeFn<string[]> = useCallback(
    (updaterOrValue) => {
      const newValue =
        typeof updaterOrValue === "function"
          ? updaterOrValue(columnOrder)
          : updaterOrValue;
      setTableState((prev) => ({ ...prev, columnOrder: newValue }));
    },
    [columnOrder, setTableState]
  );

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

  // Row selection
  const handleRowSelectionChange: OnChangeFn<RowSelectionState> = useCallback(
    (updaterOrValue) => {
      const newValue =
        typeof updaterOrValue === "function"
          ? updaterOrValue(rowSelection)
          : updaterOrValue;
      setTableState((prev) => ({ ...prev, rowSelection: newValue }));
    },
    [rowSelection, setTableState]
  );

  // Drag and drop state
  const [draggedColumn, setDraggedColumn] = useState<string | null>(null);
  const [dragOverColumn, setDragOverColumn] = useState<string | null>(null);
  const [dropPosition, setDropPosition] = useState<"left" | "right" | null>(
    null
  );

  const handleDragStart = useCallback(
    (e: DragEvent<HTMLElement>, columnId: string) => {
      setDraggedColumn(columnId);
      e.dataTransfer.effectAllowed = "move";
    },
    []
  );

  const handleDragOver = useCallback(
    (e: DragEvent<HTMLElement>, columnId: string) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";

      // Only set drag over if it's a different column than the one being dragged
      if (draggedColumn && draggedColumn !== columnId) {
        setDragOverColumn(columnId);

        // Determine which side to show the drop indicator based on current column order
        const draggedIndex = columnOrder.indexOf(draggedColumn);
        const targetIndex = columnOrder.indexOf(columnId);

        // If dragging from left to right, show indicator on right side
        // If dragging from right to left, show indicator on left side
        setDropPosition(draggedIndex < targetIndex ? "right" : "left");
      }
    },
    [draggedColumn, columnOrder]
  );

  const handleDragLeave = useCallback(() => {
    setDragOverColumn(null);
    setDropPosition(null);
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent<HTMLElement>, targetColumnId: string) => {
      e.preventDefault();

      if (!draggedColumn || draggedColumn === targetColumnId) {
        setDraggedColumn(null);
        setDragOverColumn(null);
        setDropPosition(null);
        return;
      }

      const draggedIndex = columnOrder.indexOf(draggedColumn);
      const targetIndex = columnOrder.indexOf(targetColumnId);

      if (draggedIndex === -1 || targetIndex === -1) {
        setDraggedColumn(null);
        setDragOverColumn(null);
        setDropPosition(null);
        return;
      }

      // Create new order by moving dragged column to target position
      const newOrder = [...columnOrder];
      newOrder.splice(draggedIndex, 1);
      newOrder.splice(targetIndex, 0, draggedColumn);

      setTableState((prev) => ({ ...prev, columnOrder: newOrder }));
      setDraggedColumn(null);
      setDragOverColumn(null);
      setDropPosition(null);
    },
    [draggedColumn, columnOrder, setTableState]
  );

  const handleDragEnd = useCallback(() => {
    setDraggedColumn(null);
    setDragOverColumn(null);
    setDropPosition(null);
  }, []);

  // Define table columns
  const columns = useMemo<TranscriptColumn[]>(
    () => [
      createColumn({
        accessorKey: "success",
        header: "Success",
        size: 68,
        meta: {
          align: "center",
          filterable: true,
          filterType: "boolean",
        },
        cell: (value) => {
          // value is now strongly typed as boolean | undefined
          if (value === undefined) {
            return "-";
          }

          const icon = value
            ? ApplicationIcons.success
            : ApplicationIcons.error;
          const colorCls = value ? styles.green : styles.red;

          return <i className={clsx(icon, colorCls)} />;
        },
      }),
      createColumn({
        accessorKey: "date",
        header: "date",
        size: 180,
        meta: {
          filterable: true,
          filterType: "unknown",
        },
        cell: (value) => {
          if (!value) {
            return "-";
          }
          const date = new Date(value);
          return date.toLocaleString();
        },
      }),
      createColumn({
        accessorKey: "task_set",
        header: "Task Set",
        size: 150,
        meta: {
          filterable: true,
          filterType: "string",
        },
      }),
      createColumn({
        accessorKey: "task_id",
        header: "Task ID",
        size: 150,
        meta: {
          filterable: true,
          filterType: "string",
        },
      }),
      createColumn({
        accessorKey: "task_repeat",
        header: "Repeat",
        size: 80,
        meta: {
          filterable: true,
          filterType: "number",
        },
      }),
      createColumn({
        accessorKey: "model",
        header: "Model",
        size: 200,
        meta: {
          filterable: true,
          filterType: "string",
        },
      }),
      createColumn({
        accessorKey: "score",
        header: "Score",
        size: 100,
        meta: {
          filterable: true,
          filterType: "string",
        },
        cell: (value) => {
          if (!value) {
            return "-";
          }

          // TODO: Fixme
          const scoreValue = (value as unknown as Score).value;
          if (Array.isArray(scoreValue)) {
            return printArray(scoreValue, 1000);
          } else if (typeof scoreValue === "object") {
            return printObject(scoreValue, 1000);
          } else if (typeof scoreValue === "number") {
            return formatPrettyDecimal(scoreValue);
          } else {
            return String(scoreValue);
          }
        },
      }),
      createColumn({
        accessorKey: "total_tokens",
        header: "Total Tokens",
        size: 120,
        meta: {
          filterable: true,
          filterType: "number",
        },
        cell: (value) => {
          if (value == null) {
            return "-";
          }
          return formatNumber(value);
        },
      }),
      createColumn({
        accessorKey: "total_time",
        header: "Total Time",
        size: 120,
        meta: {
          filterable: true,
          filterType: "number",
        },
        cell: (value) => {
          if (value == null) {
            return "-";
          }
          return formatPrettyDecimal(value);
        },
      }),
    ],
    []
  );

  // Create table instance
  const table = useReactTable({
    data: transcripts,
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualSorting: true,
    columnResizeMode: "onChange",
    enableColumnResizing: true,
    enableSorting: true,
    enableMultiSort: true,
    enableSortingRemoval: true,
    maxMultiSortColCount: 3,
    enableRowSelection: true,
    getRowId: (row) => String(row.transcript_id),
    state: {
      columnSizing,
      columnOrder,
      sorting,
      rowSelection,
    },
    onColumnSizingChange: handleColumnSizingChange,
    onColumnOrderChange: handleColumnOrderChange,
    onSortingChange: handleSortingChange,
    onRowSelectionChange: handleRowSelectionChange,
  });

  const { rows } = table.getRowModel();

  // Row click handler with selection support
  const handleRowClick = useCallback(
    (e: MouseEvent<HTMLTableRowElement>, rowId: string, rowIndex: number) => {
      // Focus the container to enable keyboard navigation
      if (containerRef.current) {
        containerRef.current.focus();
      }

      // Update focused row
      setTableState((prev) => ({ ...prev, focusedRowId: rowId }));

      if (e.metaKey || e.ctrlKey) {
        // Cmd/Ctrl + Click: Toggle individual row selection
        setTableState((prev) => ({
          ...prev,
          rowSelection: {
            ...prev.rowSelection,
            [rowId]: !prev.rowSelection[rowId],
          },
        }));
      } else if (e.shiftKey) {
        // Shift + Click: Range selection
        const currentSelectedRows = Object.keys(rowSelection).filter(
          (id) => rowSelection[id]
        );
        if (currentSelectedRows.length > 0) {
          // Find the last selected row
          const lastSelectedId =
            currentSelectedRows[currentSelectedRows.length - 1];
          const lastSelectedIndex = rows.findIndex(
            (r) => r.id === lastSelectedId
          );

          if (lastSelectedIndex !== -1) {
            const start = Math.min(lastSelectedIndex, rowIndex);
            const end = Math.max(lastSelectedIndex, rowIndex);
            const newSelection: RowSelectionState = {};

            for (let i = start; i <= end; i++) {
              const row = rows[i];
              if (row) {
                newSelection[row.id] = true;
              }
            }

            setTableState((prev) => ({
              ...prev,
              rowSelection: newSelection,
            }));
          }
        } else {
          // No previous selection, just select this row
          setTableState((prev) => ({
            ...prev,
            rowSelection: { [rowId]: true },
          }));
        }
      } else {
        // Normal click: Navigate to transcript
        void navigate(transcriptRoute(transcriptsDir, rowId));
      }
    },
    [rows, rowSelection, setTableState, navigate, transcriptsDir]
  );

  // Keyboard navigation handler
  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLDivElement>) => {
      if (rows.length === 0) return;

      // Find the currently focused row index
      const focusedIndex = focusedRowId
        ? rows.findIndex((r) => r.id === focusedRowId)
        : -1;

      let newFocusedIndex = focusedIndex;
      let shouldUpdateSelection = false;
      let shouldExtendSelection = false;

      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          if (e.metaKey || e.ctrlKey) {
            // Cmd/Ctrl + Arrow Down: Jump to bottom
            newFocusedIndex = rows.length - 1;
          } else {
            newFocusedIndex = Math.min(focusedIndex + 1, rows.length - 1);
          }
          shouldUpdateSelection = !e.shiftKey;
          shouldExtendSelection = e.shiftKey;
          break;

        case "ArrowUp":
          e.preventDefault();
          if (e.metaKey || e.ctrlKey) {
            // Cmd/Ctrl + Arrow Up: Jump to top
            newFocusedIndex = 0;
          } else {
            newFocusedIndex = Math.max(focusedIndex - 1, 0);
          }
          shouldUpdateSelection = !e.shiftKey;
          shouldExtendSelection = e.shiftKey;
          break;

        case "Enter":
          e.preventDefault();
          if (focusedIndex !== -1) {
            const row = rows[focusedIndex];
            if (row) {
              if (!transcriptsDir) {
                return;
              }
              // Navigate to transcript
              void navigate(transcriptRoute(transcriptsDir, row.id));
            }
          }
          return;

        case " ":
          e.preventDefault();
          if (focusedIndex !== -1) {
            const row = rows[focusedIndex];
            if (row) {
              setTableState((prev) => ({
                ...prev,
                rowSelection: {
                  ...prev.rowSelection,
                  [row.id]: !prev.rowSelection[row.id],
                },
              }));
            }
          }
          return;

        case "a":
          if (e.metaKey || e.ctrlKey) {
            e.preventDefault();
            // Select all
            const allSelected: RowSelectionState = {};
            rows.forEach((row) => {
              allSelected[row.id] = true;
            });
            setTableState((prev) => ({
              ...prev,
              rowSelection: allSelected,
            }));
          }
          return;

        case "Escape":
          e.preventDefault();
          // Clear selection
          setTableState((prev) => ({
            ...prev,
            rowSelection: {},
          }));
          return;

        default:
          return;
      }

      // Handle arrow key navigation
      if (newFocusedIndex !== focusedIndex && newFocusedIndex !== -1) {
        const newRow = rows[newFocusedIndex];
        if (!newRow) return;

        setTableState((prev) => ({
          ...prev,
          focusedRowId: newRow.id,
        }));

        if (shouldUpdateSelection) {
          // Normal arrow: move selection
          setTableState((prev) => ({
            ...prev,
            rowSelection: { [newRow.id]: true },
          }));
        } else if (shouldExtendSelection) {
          // Shift + arrow: extend selection
          const currentSelectedRows = Object.keys(rowSelection).filter(
            (id) => rowSelection[id]
          );
          if (currentSelectedRows.length > 0) {
            // Find the anchor (first selected row)
            const anchorId = currentSelectedRows[0];
            const anchorIndex = rows.findIndex((r) => r.id === anchorId);

            if (anchorIndex !== -1) {
              const start = Math.min(anchorIndex, newFocusedIndex);
              const end = Math.max(anchorIndex, newFocusedIndex);
              const newSelection: RowSelectionState = {};

              for (let i = start; i <= end; i++) {
                const row = rows[i];
                if (row) {
                  newSelection[row.id] = true;
                }
              }

              setTableState((prev) => ({
                ...prev,
                rowSelection: newSelection,
              }));
            }
          } else {
            // No selection, start new one
            setTableState((prev) => ({
              ...prev,
              rowSelection: { [newRow.id]: true },
            }));
          }
        }
      }
    },
    [rows, focusedRowId, rowSelection, setTableState, navigate, transcriptsDir]
  );

  // Create virtualizer
  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => containerRef.current,
    // Estimated row height in pixels (padding + content + border)
    estimateSize: () => 29,
    // Number of items to render outside visible area
    overscan: 10,
    // Item keys
    getItemKey: (index) => transcriptItemKey(index, rows[index]?.original),
  });

  const virtualItems = rowVirtualizer.getVirtualItems();
  const totalSize = rowVirtualizer.getTotalSize();

  // Infinite scroll: notify parent when scrolled near bottom
  const checkScrollNearEnd = useCallback(
    (containerRefElement?: HTMLDivElement | null) => {
      if (!containerRefElement || !hasMore) return;

      const { scrollHeight, scrollTop, clientHeight } = containerRefElement;
      const distanceFromBottom = scrollHeight - scrollTop - clientHeight;

      if (distanceFromBottom < fetchThreshold) {
        onScrollNearEnd(distanceFromBottom);
      }
    },
    [onScrollNearEnd, hasMore, fetchThreshold]
  );

  // Check on mount if we need to fetch more
  useEffect(() => {
    checkScrollNearEnd(containerRef.current);
  }, [checkScrollNearEnd]);

  // Scroll focused row into view when it changes
  useEffect(() => {
    if (focusedRowId && containerRef.current) {
      const focusedIndex = rows.findIndex((r) => r.id === focusedRowId);
      if (focusedIndex !== -1) {
        // For the last item, scroll to the very bottom
        if (focusedIndex === rows.length - 1) {
          containerRef.current.scrollTop = containerRef.current.scrollHeight;
        } else {
          rowVirtualizer.scrollToIndex(focusedIndex, {
            align: "center",
            behavior: "auto",
          });
        }
      }
    }
  }, [focusedRowId, rows, rowVirtualizer]);

  const onScroll = useCallback(
    (e) => checkScrollNearEnd(e.currentTarget),
    [checkScrollNearEnd]
  );

  // Render the grid
  return (
    <div
      ref={containerRef}
      className={clsx(className, styles.container)}
      tabIndex={0}
      onKeyDown={handleKeyDown}
      onScroll={onScroll}
    >
      <table className={styles.table}>
        <thead className={styles.thead}>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id} className={styles.headerRow}>
              {headerGroup.headers.map((header) => {
                const columnMeta = (header.column.columnDef as TranscriptColumn)
                  .meta;
                const align = columnMeta?.align;
                const filterType = columnMeta?.filterType;
                return (
                  <th
                    key={header.id}
                    className={clsx(
                      styles.headerCell,
                      align === "center" && styles.headerCellCenter,
                      draggedColumn === header.column.id &&
                        styles.headerCellDragging,
                      dragOverColumn === header.column.id &&
                        dropPosition === "left" &&
                        styles.headerCellDragOverLeft,
                      dragOverColumn === header.column.id &&
                        dropPosition === "right" &&
                        styles.headerCellDragOverRight
                    )}
                    style={{ width: header.getSize() }}
                    onDragOver={(e) => handleDragOver(e, header.column.id)}
                    onDragLeave={handleDragLeave}
                    onDrop={(e) => handleDrop(e, header.column.id)}
                  >
                    <div
                      className={styles.headerContent}
                      draggable
                      onDragStart={(e) => handleDragStart(e, header.column.id)}
                      onDragEnd={handleDragEnd}
                      onClick={header.column.getToggleSortingHandler()}
                      style={{
                        cursor: "pointer",
                        maxWidth: `calc(${header.getSize()}px - 32px)`,
                      }}
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
                    {columnMeta?.filterable && filterType ? (
                      <ColumnFilterControl
                        columnId={header.column.id}
                        filterType={filterType}
                        condition={columnFilters[header.column.id] ?? null}
                        onChange={(condition) =>
                          handleColumnFilterChange(header.column.id, condition)
                        }
                      />
                    ) : null}
                    <div
                      className={clsx(
                        styles.resizer,
                        header.column.getIsResizing() && styles.resizerActive
                      )}
                      onMouseDown={header.getResizeHandler()}
                      onTouchStart={header.getResizeHandler()}
                      onDoubleClick={() => header.column.resetSize()}
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

              const isSelected = row.getIsSelected();
              const isFocused = focusedRowId === row.id;
              const rowKey = transcriptItemKey(virtualRow.index, row.original);

              return (
                <tr
                  key={rowKey}
                  className={clsx(
                    styles.row,
                    isSelected && styles.rowSelected,
                    isFocused && styles.rowFocused
                  )}
                  style={{ transform: `translateY(${virtualRow.start}px)` }}
                  onClick={(e) => handleRowClick(e, row.id, virtualRow.index)}
                >
                  {row.getVisibleCells().map((cell) => {
                    const align = (cell.column.columnDef as TranscriptColumn)
                      .meta?.align;
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
              <td>No matching transcripts</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
};
