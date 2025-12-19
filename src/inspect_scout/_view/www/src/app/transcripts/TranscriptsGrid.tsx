import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  ColumnDef,
  flexRender,
  OnChangeFn,
  ColumnSizingState,
  SortingState,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import clsx from "clsx";
import { FC, useRef, useMemo, useState, DragEvent, useCallback } from "react";

import { useStore } from "../../state/store";
import { TranscriptInfo } from "../../types";
import { printArray } from "../../utils/array";
import { formatNumber, formatPrettyDecimal } from "../../utils/format";
import { printObject } from "../../utils/object";
import { ApplicationIcons } from "../appearance/icons";

import styles from "./TranscriptsGrid.module.css";

type TranscriptColumn = ColumnDef<TranscriptInfo> & {
  meta?: {
    align?: "left" | "center" | "right";
  };
};

// Helper to create strongly-typed columns
function createColumn<K extends keyof TranscriptInfo>(config: {
  accessorKey: K;
  header: string;
  size?: number;
  meta?: { align?: "left" | "center" | "right" };
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

interface TranscriptGridProps {
  transcripts?: TranscriptInfo[];
  className?: string | string[];
}

export const TranscriptsGrid: FC<TranscriptGridProps> = ({
  transcripts = [],
  className,
}) => {
  // The table container which provides the scrollable region
  const containerRef = useRef<HTMLDivElement>(null);

  // Table state
  const columnSizing = useStore(
    (state) => state.transcriptsTableState.columnSizing
  );
  const columnOrder = useStore(
    (state) => state.transcriptsTableState.columnOrder
  );
  const sorting = useStore((state) => state.transcriptsTableState.sorting);
  const setTableState = useStore((state) => state.setTranscriptsTableState);

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

  // Row click handler
  const handleRowClick = useCallback((transcript: TranscriptInfo) => {
    console.log("Row clicked - transcript_id:", transcript.transcript_id);
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
        accessorKey: "task_set",
        header: "Task Set",
        size: 150,
      }),
      createColumn({
        accessorKey: "task_id",
        header: "Task ID",
        size: 150,
      }),
      createColumn({
        accessorKey: "task_repeat",
        header: "Repeat",
        size: 80,
      }),
      createColumn({
        accessorKey: "model",
        header: "Model",
        size: 200,
      }),
      createColumn({
        accessorKey: "score",
        header: "Score",
        size: 100,
        cell: (value) => {
          if (!value) {
            return "-";
          }

          const scoreValue = value.value;
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
        cell: (value) => {
          if (value === undefined) {
            return "-";
          }
          return formatNumber(value);
        },
      }),
      createColumn({
        accessorKey: "total_time",
        header: "Total Time",
        size: 120,
        cell: (value) => {
          if (value === undefined) {
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
    getSortedRowModel: getSortedRowModel(),
    columnResizeMode: "onChange",
    enableColumnResizing: true,
    enableSorting: true,
    enableMultiSort: true,
    enableSortingRemoval: true,
    maxMultiSortColCount: 3,
    state: {
      columnSizing,
      columnOrder,
      sorting,
    },
    onColumnSizingChange: handleColumnSizingChange,
    onColumnOrderChange: handleColumnOrderChange,
    onSortingChange: handleSortingChange,
  });

  const { rows } = table.getRowModel();

  // Create virtualizer
  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => containerRef.current,
    // Estimated row height in pixels
    estimateSize: () => 28,
    // Number of items to render outside visible area
    overscan: 10,
  });

  const virtualItems = rowVirtualizer.getVirtualItems();
  const totalSize = rowVirtualizer.getTotalSize();

  // Render the grid
  return (
    <div ref={containerRef} className={clsx(className, styles.container)}>
      <table className={styles.table}>
        <thead className={styles.thead}>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id} className={styles.headerRow}>
              {headerGroup.headers.map((header) => {
                const align = (header.column.columnDef as TranscriptColumn).meta
                  ?.align;
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
                      style={{ cursor: "pointer" }}
                    >
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
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
                      onDoubleClick={() => header.column.resetSize()}
                    />
                  </th>
                );
              })}
            </tr>
          ))}
        </thead>
        <tbody className={styles.tbody} style={{ height: `${totalSize}px` }}>
          {virtualItems.map((virtualRow) => {
            const row = rows[virtualRow.index];
            if (!row) return null;

            return (
              <tr
                key={row.id}
                className={styles.row}
                style={{ transform: `translateY(${virtualRow.start}px)` }}
                onClick={() => handleRowClick(row.original)}
              >
                {row.getVisibleCells().map((cell) => {
                  const align = (cell.column.columnDef as TranscriptColumn).meta
                    ?.align;
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
          })}
        </tbody>
      </table>
    </div>
  );
};
