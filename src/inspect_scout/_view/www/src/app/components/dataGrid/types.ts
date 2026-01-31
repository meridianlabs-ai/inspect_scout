import {
  ColumnSizingState,
  RowSelectionState,
  SortingState,
} from "@tanstack/react-table";

import type { ScalarValue } from "../../../api/api";
import type { SimpleCondition } from "../../../query/types";
import type { ColumnFilter, FilterType } from "../../../state/store";
import type { ExtendedColumnDef, BaseColumnMeta } from "../columnTypes";

/**
 * Props for the shared DataGrid component.
 * Designed to work with any data type and column configuration.
 *
 * @template TData - The row data type
 * @template TColumn - The column definition type
 * @template TState - The table state type (must extend DataGridTableState)
 */
export interface DataGridProps<
  TData,
  TColumn extends ExtendedColumnDef<TData>,
  TState extends DataGridTableState = DataGridTableState,
> {
  // Data
  /** Array of row data to display */
  data: TData[];
  /** Column definitions for the grid */
  columns: TColumn[];
  /** Get unique ID for a row */
  getRowId: (row: TData) => string;
  /** Get stable key for virtualizer (defaults to getRowId) */
  getRowKey?: (index: number, row?: TData) => string;

  // State (from parent's store)
  /** Current sorting state */
  sorting: SortingState;
  /** Column order (array of column IDs) */
  columnOrder: string[];
  /** Active column filters */
  columnFilters: Record<string, ColumnFilter>;
  /** Column sizing state */
  columnSizing: ColumnSizingState;
  /** Selected rows */
  rowSelection: RowSelectionState;
  /** Currently focused row ID */
  focusedRowId: string | null;

  // State setter (single update function for all state)
  // Uses generic TState to allow specific store types
  setTableState: (updater: TState | ((prev: TState) => TState)) => void;

  // Navigation
  /** Get the route for a row (for navigation) */
  getRowRoute: (row: TData) => string;

  // Infinite scroll (optional)
  /** Called when scroll position nears end. Receives distance from bottom in px. */
  onScrollNearEnd?: (distanceFromBottom: number) => void;
  /** Whether more data is available to fetch */
  hasMore?: boolean;
  /** Distance from bottom (in px) at which to trigger callback */
  fetchThreshold?: number;

  // Filtering (optional)
  /** Autocomplete suggestions for the currently editing filter column */
  filterSuggestions?: ScalarValue[];
  /** Called when a filter column starts/stops being edited */
  onFilterColumnChange?: (columnId: string | null) => void;

  // Column sizing (optional)
  /** Handler for column sizing changes */
  onColumnSizingChange?: (sizing: ColumnSizingState) => void;
  /** Reset a single column to its auto-calculated size */
  onResetColumnSize?: (columnId: string) => void;

  // UI
  /** Additional CSS class names */
  className?: string | string[];
  /** Whether data is loading */
  loading?: boolean;
  /** Message to show when there's no data */
  emptyMessage?: string;
  /** Message to show when there's no configuration (e.g., no directory) */
  noConfigMessage?: string;
}

/**
 * Table state managed by parent store.
 * This is the shape of state that setTableState updater receives.
 */
export interface DataGridTableState {
  columnSizing: ColumnSizingState;
  columnOrder: string[];
  sorting: SortingState;
  rowSelection: RowSelectionState;
  focusedRowId: string | null;
  columnFilters: Record<string, ColumnFilter>;
}

/**
 * Handler for column filter changes.
 */
export type ColumnFilterChangeHandler = (
  columnId: string,
  filterType: FilterType,
  condition: SimpleCondition | null
) => void;

/**
 * Re-export column types for convenience
 */
export type { ExtendedColumnDef, BaseColumnMeta };
