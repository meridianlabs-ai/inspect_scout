import {
  flexRender,
  getCoreRowModel,
  OnChangeFn,
  RowSelectionState,
  SortingState,
  ColumnSizingState,
  useReactTable,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import clsx from "clsx";
import {
  DragEvent,
  KeyboardEvent,
  MouseEvent,
  ReactElement,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { ApplicationIcons } from "../../../components/icons";
import { useLoggingNavigate } from "../../../debugging/navigationDebugging";
import type { SimpleCondition } from "../../../query/types";
import { openRouteInNewTab } from "../../../router/url";
import { FilterType } from "../../../state/store";
import { ColumnFilterControl } from "../columnFilter";
import {
  getCellTitleValue,
  ExtendedColumnDef,
  BaseColumnMeta,
} from "../columnTypes";

import styles from "./DataGrid.module.css";
import type { DataGridProps, DataGridTableState } from "./types";

/**
 * Shared DataGrid component with virtual scrolling, sorting, filtering,
 * row selection, keyboard navigation, and column reordering.
 */
export function DataGrid<
  TData,
  TColumn extends ExtendedColumnDef<TData, BaseColumnMeta>,
  TState extends DataGridTableState = DataGridTableState,
>({
  // Data
  data,
  columns,
  getRowId,
  getRowKey,

  // State (consolidated)
  state,

  // State setter
  onStateChange,

  // Navigation
  getRowRoute,

  // Infinite scroll
  onScrollNearEnd,
  hasMore = false,
  fetchThreshold = 500,

  // Filtering
  filterSuggestions = [],
  onFilterColumnChange,

  // Column sizing
  onColumnSizingChange,
  onResetColumnSize,

  // UI
  className,
  loading = false,
  emptyMessage = "No matching items",
  noConfigMessage = "No directory configured.",
}: DataGridProps<TData, TColumn, TState>): ReactElement {
  // Destructure state for convenience
  const {
    sorting,
    columnOrder,
    columnFilters,
    columnSizing,
    rowSelection,
    focusedRowId,
  } = state;

  // Refs
  const containerRef = useRef<HTMLDivElement>(null);
  const tableRef = useRef<HTMLTableElement>(null);
  const navigate = useLoggingNavigate("DataGrid");

  // Default getRowKey to getRowId if not provided
  const effectiveGetRowKey = useCallback(
    (index: number, row?: TData): string => {
      if (getRowKey) {
        return getRowKey(index, row);
      }
      if (row) {
        return getRowId(row);
      }
      return String(index);
    },
    [getRowKey, getRowId]
  );

  // Column filter change handler
  const handleColumnFilterChange = useCallback(
    (
      columnId: string,
      filterType: FilterType,
      condition: SimpleCondition | null
    ) => {
      onStateChange((prev) => {
        if (condition === null) {
          // Remove the filter entirely
          const newFilters = { ...prev.columnFilters };
          delete newFilters[columnId];
          return {
            ...prev,
            columnFilters: newFilters,
          };
        }
        // Add or update the filter
        return {
          ...prev,
          columnFilters: {
            ...prev.columnFilters,
            [columnId]: {
              columnId,
              filterType,
              condition,
            },
          },
        };
      });
    },
    [onStateChange]
  );

  // Column ordering handler
  const handleColumnOrderChange: OnChangeFn<string[]> = useCallback(
    (updaterOrValue) => {
      onStateChange((prev) => {
        const newValue =
          typeof updaterOrValue === "function"
            ? updaterOrValue(prev.columnOrder)
            : updaterOrValue;
        return { ...prev, columnOrder: newValue };
      });
    },
    [onStateChange]
  );

  // Sorting handler
  const handleSortingChange: OnChangeFn<SortingState> = useCallback(
    (updaterOrValue) => {
      onStateChange((prev) => {
        const newValue =
          typeof updaterOrValue === "function"
            ? updaterOrValue(prev.sorting)
            : updaterOrValue;
        return { ...prev, sorting: newValue };
      });
    },
    [onStateChange]
  );

  // Row selection handler
  const handleRowSelectionChange: OnChangeFn<RowSelectionState> = useCallback(
    (updaterOrValue) => {
      onStateChange((prev) => {
        const newValue =
          typeof updaterOrValue === "function"
            ? updaterOrValue(prev.rowSelection)
            : updaterOrValue;
        return { ...prev, rowSelection: newValue };
      });
    },
    [onStateChange]
  );

  // Column sizing handler
  const handleColumnSizingChange: OnChangeFn<ColumnSizingState> = useCallback(
    (updaterOrValue) => {
      onStateChange((prev) => {
        const newValue =
          typeof updaterOrValue === "function"
            ? updaterOrValue(prev.columnSizing)
            : updaterOrValue;
        return { ...prev, columnSizing: newValue };
      });

      // Also call external handler if provided
      if (onColumnSizingChange) {
        const newValue =
          typeof updaterOrValue === "function"
            ? updaterOrValue(columnSizing)
            : updaterOrValue;
        onColumnSizingChange(newValue);
      }
    },
    [onStateChange, onColumnSizingChange, columnSizing]
  );

  // Compute effective column order
  const effectiveColumnOrder = useMemo(() => {
    if (columnOrder && columnOrder.length > 0) {
      return columnOrder;
    }
    // Default to column order from column definitions
    return columns.map(
      (col) =>
        (col.id ?? (col as { accessorKey?: string }).accessorKey) as string
    );
  }, [columnOrder, columns]);

  // Drag and drop state
  const [draggedColumn, setDraggedColumn] = useState<string | null>(null);
  const [dragOverColumn, setDragOverColumn] = useState<string | null>(null);
  const [dropPosition, setDropPosition] = useState<"left" | "right" | null>(
    null
  );

  const resetDragState = useCallback(() => {
    setDraggedColumn(null);
    setDragOverColumn(null);
    setDropPosition(null);
  }, []);

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

        // Determine which side to show the drop indicator
        const draggedIndex = effectiveColumnOrder.indexOf(draggedColumn);
        const targetIndex = effectiveColumnOrder.indexOf(columnId);

        // If dragging from left to right, show indicator on right side
        setDropPosition(draggedIndex < targetIndex ? "right" : "left");
      }
    },
    [draggedColumn, effectiveColumnOrder]
  );

  const handleDragLeave = useCallback(() => {
    setDragOverColumn(null);
    setDropPosition(null);
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent<HTMLElement>, targetColumnId: string) => {
      e.preventDefault();

      if (!draggedColumn || draggedColumn === targetColumnId) {
        resetDragState();
        return;
      }

      const draggedIndex = effectiveColumnOrder.indexOf(draggedColumn);
      const targetIndex = effectiveColumnOrder.indexOf(targetColumnId);

      if (draggedIndex === -1 || targetIndex === -1) {
        resetDragState();
        return;
      }

      // Create new order by moving dragged column to target position
      const newOrder = [...effectiveColumnOrder];
      newOrder.splice(draggedIndex, 1);
      newOrder.splice(targetIndex, 0, draggedColumn);

      onStateChange((prev) => ({ ...prev, columnOrder: newOrder }));
      resetDragState();
    },
    [draggedColumn, effectiveColumnOrder, onStateChange, resetDragState]
  );

  const handleDragEnd = useCallback(() => {
    resetDragState();
  }, [resetDragState]);

  // Create table instance
  // useReactTable returns unmemoizable functions
  // https://github.com/TanStack/table/issues/5567
  // https://github.com/facebook/react/issues/33057
  // eslint-disable-next-line react-hooks/incompatible-library
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
    enableRowSelection: true,
    getRowId,
    state: {
      columnSizing,
      columnOrder: effectiveColumnOrder,
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
      onStateChange((prev) => ({ ...prev, focusedRowId: rowId }));

      const row = rows[rowIndex];
      if (!row) return;

      if (e.metaKey || e.ctrlKey) {
        // Cmd/Ctrl + Click: Open in new tab
        openRouteInNewTab(getRowRoute(row.original));
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
              const r = rows[i];
              if (r) {
                newSelection[r.id] = true;
              }
            }

            onStateChange((prev) => ({
              ...prev,
              rowSelection: newSelection,
            }));
          }
        } else {
          // No previous selection, just select this row
          onStateChange((prev) => ({
            ...prev,
            rowSelection: { [rowId]: true },
          }));
        }
      } else {
        // Normal click: Navigate to row
        void navigate(getRowRoute(row.original));
      }
    },
    [rows, rowSelection, onStateChange, navigate, getRowRoute]
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
              void navigate(getRowRoute(row.original));
            }
          }
          return;

        case " ":
          e.preventDefault();
          if (focusedIndex !== -1) {
            const row = rows[focusedIndex];
            if (row) {
              onStateChange((prev) => ({
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
            onStateChange((prev) => ({
              ...prev,
              rowSelection: allSelected,
            }));
          }
          return;

        case "Escape":
          e.preventDefault();
          // Clear selection
          onStateChange((prev) => ({
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

        onStateChange((prev) => ({
          ...prev,
          focusedRowId: newRow.id,
        }));

        if (shouldUpdateSelection) {
          // Normal arrow: move selection
          onStateChange((prev) => ({
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
                const r = rows[i];
                if (r) {
                  newSelection[r.id] = true;
                }
              }

              onStateChange((prev) => ({
                ...prev,
                rowSelection: newSelection,
              }));
            }
          } else {
            // No selection, start new one
            onStateChange((prev) => ({
              ...prev,
              rowSelection: { [newRow.id]: true },
            }));
          }
        }
      }
    },
    [rows, focusedRowId, rowSelection, onStateChange, navigate, getRowRoute]
  );

  // Create virtualizer
  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => containerRef.current,
    estimateSize: () => 29,
    overscan: 10,
    getItemKey: (index) => effectiveGetRowKey(index, rows[index]?.original),
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
    (e: React.UIEvent<HTMLDivElement>) => checkScrollNearEnd(e.currentTarget),
    [checkScrollNearEnd]
  );

  // Get empty state message
  const getEmptyMessage = (): string => {
    if (loading) return "Loading...";
    if (!data.length && noConfigMessage) return noConfigMessage;
    return emptyMessage;
  };

  return (
    <div
      ref={containerRef}
      className={clsx(className, styles.container)}
      tabIndex={0}
      onKeyDown={handleKeyDown}
      onScroll={onScroll}
    >
      <table ref={tableRef} className={styles.table}>
        <thead className={styles.thead}>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id} className={styles.headerRow}>
              {headerGroup.headers.map((header) => {
                const columnDef = header.column.columnDef as TColumn;
                const columnMeta = columnDef.meta;
                const align = columnMeta?.align;
                const filterType = columnMeta?.filterType;
                return (
                  <th
                    key={header.id}
                    className={clsx(
                      styles.headerCell,
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
                    title={[header.column.id, columnDef.headerTitle]
                      .filter(Boolean)
                      .join("\n")}
                  >
                    <div
                      className={clsx(
                        styles.headerContent,
                        align === "center" && styles.headerCellCenter
                      )}
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
                        condition={
                          columnFilters[header.column.id]?.condition ?? null
                        }
                        onChange={(condition) =>
                          handleColumnFilterChange(
                            header.column.id,
                            filterType,
                            condition
                          )
                        }
                        suggestions={filterSuggestions}
                        onOpenChange={onFilterColumnChange}
                      />
                    ) : null}
                    <div
                      className={clsx(
                        styles.resizer,
                        header.column.getIsResizing() && styles.resizerActive
                      )}
                      onMouseDown={header.getResizeHandler()}
                      onTouchStart={header.getResizeHandler()}
                      onDoubleClick={() =>
                        onResetColumnSize?.(header.column.id)
                      }
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
              const rowKey = effectiveGetRowKey(virtualRow.index, row.original);

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
                    const cellColumnDef = cell.column.columnDef as TColumn;
                    const cellAlign = cellColumnDef.meta?.align;
                    const titleValue = getCellTitleValue(
                      cell.getValue(),
                      cellColumnDef
                    );
                    return (
                      <td
                        key={cell.id}
                        className={clsx(
                          styles.cell,
                          cellAlign === "center" && styles.cellCenter
                        )}
                        style={{ width: cell.column.getSize() }}
                        title={titleValue}
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
              <td>{getEmptyMessage()}</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
