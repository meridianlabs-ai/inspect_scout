import { useCallback, useMemo } from "react";

import type { SimpleCondition } from "../../query/types";
import { ColumnFilter } from "../../state/store";

/**
 * Base table state interface that filter bar handlers can work with.
 * Both ScansTableState and TranscriptsTableState conform to this.
 */
interface BaseTableState {
  columnFilters: Record<string, ColumnFilter>;
  visibleColumns?: string[];
  columnOrder: string[];
}

interface FilterBarHandlers {
  /**
   * Update a filter's condition or remove it if condition is null
   */
  handleFilterChange: (
    columnId: string,
    condition: SimpleCondition | null
  ) => void;
  /**
   * Remove a filter by column ID
   */
  removeFilter: (column: string) => void;
  /**
   * Add a new filter, ensuring the column is visible
   */
  handleAddFilter: (filter: ColumnFilter) => void;
}

/**
 * Creates filter bar handler functions for a table state.
 * This is the core logic shared between scans and transcripts filter bars.
 *
 * @param setTableState - Store setter function
 * @param defaultVisibleColumns - Default columns when state doesn't have them
 * @returns Object with handler functions
 */
function createFilterBarHandlers<
  TColumnKey extends string,
  TState extends BaseTableState = BaseTableState,
>(
  setTableState: (updater: TState | ((prev: TState) => TState)) => void,
  defaultVisibleColumns: readonly TColumnKey[]
): FilterBarHandlers {
  const handleFilterChange = (
    columnId: string,
    condition: SimpleCondition | null
  ) => {
    setTableState((prevState) => {
      const newFilters = { ...prevState.columnFilters };
      if (condition === null) {
        delete newFilters[columnId];
      } else {
        const existingFilter = newFilters[columnId];
        if (existingFilter) {
          newFilters[columnId] = {
            ...existingFilter,
            condition,
          };
        }
      }
      return {
        ...prevState,
        columnFilters: newFilters,
      };
    });
  };

  const removeFilter = (column: string) => {
    setTableState((prevState) => {
      const newFilters = { ...prevState.columnFilters };
      delete newFilters[column];
      return {
        ...prevState,
        columnFilters: newFilters,
      };
    });
  };

  const handleAddFilter = (filter: ColumnFilter) => {
    setTableState((prevState) => {
      const columnKey = filter.columnId as TColumnKey;

      // Use default visible columns if not set in state
      const currentVisibleColumns =
        (prevState.visibleColumns as TColumnKey[] | undefined) ??
        ([...defaultVisibleColumns] as TColumnKey[]);

      // Check if we need to add this column to visible columns
      const needsColumnVisible = !currentVisibleColumns.includes(columnKey);

      // Check if we need to add this column to column order
      const columnOrder = prevState.columnOrder as TColumnKey[];
      const needsColumnOrder =
        columnOrder.length > 0 && !columnOrder.includes(columnKey);

      return {
        ...prevState,
        columnFilters: {
          ...prevState.columnFilters,
          [filter.columnId]: filter,
        },
        // Add the column to visible columns if it's not already there
        ...(needsColumnVisible && {
          visibleColumns: [...currentVisibleColumns, columnKey],
        }),
        // Add the column to column order if it's not already there
        ...(needsColumnOrder && {
          columnOrder: [...columnOrder, columnKey],
        }),
      };
    });
  };

  return {
    handleFilterChange,
    removeFilter,
    handleAddFilter,
  };
}

interface UseFilterBarHandlersOptions<
  TColumnKey extends string,
  TState extends BaseTableState = BaseTableState,
> {
  /**
   * Store setter function that accepts an updater
   */
  setTableState: (updater: TState | ((prev: TState) => TState)) => void;
  /**
   * Default visible columns to use when state doesn't have them set
   */
  defaultVisibleColumns: readonly TColumnKey[];
}

/**
 * Hook that provides common filter bar handlers for both scans and transcripts tables.
 * Extracts the duplicated logic from ScansFilterBar and TranscriptFilterBar.
 */
export function useFilterBarHandlers<
  TColumnKey extends string,
  TState extends BaseTableState = BaseTableState,
>({
  setTableState,
  defaultVisibleColumns,
}: UseFilterBarHandlersOptions<TColumnKey, TState>): FilterBarHandlers {
  // Memoize the handlers to maintain referential stability
  const handlers = useMemo(
    () => createFilterBarHandlers(setTableState, defaultVisibleColumns),
    [setTableState, defaultVisibleColumns]
  );

  // Wrap in useCallback for consistent return types
  const handleFilterChange = useCallback(
    (columnId: string, condition: SimpleCondition | null) => {
      handlers.handleFilterChange(columnId, condition);
    },
    [handlers]
  );

  const removeFilter = useCallback(
    (column: string) => {
      handlers.removeFilter(column);
    },
    [handlers]
  );

  const handleAddFilter = useCallback(
    (filter: ColumnFilter) => {
      handlers.handleAddFilter(filter);
    },
    [handlers]
  );

  return {
    handleFilterChange,
    removeFilter,
    handleAddFilter,
  };
}
