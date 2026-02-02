import { ColumnSizingState, OnChangeFn } from "@tanstack/react-table";
import { useCallback, useEffect, useMemo, useRef } from "react";

import { useStore } from "../../../state/store";
import {
  clampSize,
  ColumnSizingStrategyKey,
  getColumnConstraints,
  getSizingStrategy,
  SizingStrategy,
} from "../../components/columnSizing";
import { ScanColumn, ScanRow } from "../columns";

interface UseColumnSizingOptions {
  /** Column definitions */
  columns: ScanColumn[];
  /** Reference to the table element for DOM measurement */
  tableRef: React.RefObject<HTMLTableElement | null>;
  /** Current data for content measurement */
  data: ScanRow[];
}

interface UseColumnSizingResult {
  /** Current column sizing state */
  columnSizing: ColumnSizingState;
  /** Handler for column sizing changes with min/max enforcement */
  handleColumnSizingChange: OnChangeFn<ColumnSizingState>;
  /** Current sizing strategy key */
  sizingStrategy: ColumnSizingStrategyKey;
  /** Set the sizing strategy */
  setSizingStrategy: (strategy: ColumnSizingStrategyKey) => void;
  /** Apply auto-sizing based on current strategy (preserves manually resized columns) */
  applyAutoSizing: () => void;
  /** Reset a single column to its auto-calculated size */
  resetColumnSize: (columnId: string) => void;
  /** Reset all column sizing and clear manual resize tracking */
  clearColumnSizing: () => void;
}

/**
 * Hook for managing column sizing with min/max constraints and auto-sizing.
 * Manually resized columns are preserved during auto-sizing operations.
 */
export function useColumnSizing({
  columns,
  tableRef,
  data,
}: UseColumnSizingOptions): UseColumnSizingResult {
  const columnSizing = useStore((state) => state.scansTableState.columnSizing);
  const sizingStrategy = useStore(
    (state) => state.scansTableState.sizingStrategy
  );
  const manuallyResizedColumns = useStore(
    (state) => state.scansTableState.manuallyResizedColumns
  );
  const setTableState = useStore((state) => state.setScansTableState);

  // Track which columns have been manually resized
  const manuallyResizedSet = useMemo(
    () => new Set(manuallyResizedColumns),
    [manuallyResizedColumns]
  );

  // Get constraints for all columns
  const columnConstraints = useMemo(
    () => getColumnConstraints(columns),
    [columns]
  );

  // Track if we're in the middle of an auto-sizing operation
  const isAutoSizingRef = useRef(false);

  // Store latest values in refs for stable callbacks
  const latestRef = useRef({
    sizingStrategy,
    columns,
    data,
    columnConstraints,
    manuallyResizedSet,
    columnSizing,
  });

  // Update refs when values change
  useEffect(() => {
    latestRef.current = {
      sizingStrategy,
      columns,
      data,
      columnConstraints,
      manuallyResizedSet,
      columnSizing,
    };
  });

  // Handle column sizing changes with min/max enforcement
  const handleColumnSizingChange: OnChangeFn<ColumnSizingState> = useCallback(
    (updaterOrValue) => {
      const newSizing =
        typeof updaterOrValue === "function"
          ? updaterOrValue(columnSizing)
          : updaterOrValue;

      // Clamp sizes to min/max constraints
      const clampedSizing: ColumnSizingState = {};
      const newManuallyResized = new Set(manuallyResizedSet);

      for (const [columnId, size] of Object.entries(newSizing)) {
        const constraints = columnConstraints.get(columnId);
        if (constraints) {
          clampedSizing[columnId] = clampSize(size, constraints);
        } else {
          clampedSizing[columnId] = size;
        }

        // Mark this column as manually resized (unless we're auto-sizing)
        if (!isAutoSizingRef.current) {
          newManuallyResized.add(columnId);
        }
      }

      // Include existing sizes that weren't updated
      for (const [columnId, size] of Object.entries(columnSizing)) {
        if (!(columnId in clampedSizing)) {
          clampedSizing[columnId] = size;
        }
      }

      setTableState((prev) => ({
        ...prev,
        columnSizing: clampedSizing,
        manuallyResizedColumns: isAutoSizingRef.current
          ? prev.manuallyResizedColumns
          : Array.from(newManuallyResized),
      }));
    },
    [columnSizing, columnConstraints, manuallyResizedSet, setTableState]
  );

  // Set sizing strategy
  const setSizingStrategy = useCallback(
    (strategy: ColumnSizingStrategyKey) => {
      setTableState((prev) => ({
        ...prev,
        sizingStrategy: strategy,
      }));
    },
    [setTableState]
  );

  // Apply auto-sizing based on current strategy
  // Preserves sizes of manually resized columns
  const applyAutoSizing = useCallback(() => {
    isAutoSizingRef.current = true;

    try {
      const {
        sizingStrategy: strategyKey,
        columns: cols,
        data: rowData,
        columnConstraints: constraints,
        manuallyResizedSet: resizedSet,
        columnSizing: currentSizing,
      } = latestRef.current;

      const strategy = getSizingStrategy(
        strategyKey
      ) as SizingStrategy<ScanRow>;
      const calculatedSizing = strategy.computeSizes({
        tableElement: tableRef.current,
        columns: cols,
        data: rowData,
        constraints,
      });

      // Merge: use calculated sizes for non-manually-resized columns,
      // preserve existing sizes for manually resized columns
      const newSizing: ColumnSizingState = {};
      for (const [columnId, size] of Object.entries(calculatedSizing)) {
        if (resizedSet.has(columnId) && currentSizing[columnId] !== undefined) {
          // Preserve manually resized column's current size
          newSizing[columnId] = currentSizing[columnId];
        } else {
          // Use calculated size
          newSizing[columnId] = size;
        }
      }

      setTableState((prev) => ({
        ...prev,
        columnSizing: newSizing,
      }));
    } finally {
      isAutoSizingRef.current = false;
    }
  }, [tableRef, setTableState]);

  // Reset a single column to its auto-calculated size
  const resetColumnSize = useCallback(
    (columnId: string) => {
      isAutoSizingRef.current = true;

      try {
        const {
          sizingStrategy: strategyKey,
          columns: cols,
          data: rowData,
          columnConstraints: constraints,
        } = latestRef.current;

        const strategy = getSizingStrategy(
          strategyKey
        ) as SizingStrategy<ScanRow>;
        const allSizes = strategy.computeSizes({
          tableElement: tableRef.current,
          columns: cols,
          data: rowData,
          constraints,
        });

        const newSize = allSizes[columnId];
        if (newSize !== undefined) {
          setTableState((prev) => {
            // Remove this column from manually resized list
            const newManuallyResized = prev.manuallyResizedColumns.filter(
              (id) => id !== columnId
            );

            return {
              ...prev,
              columnSizing: {
                ...prev.columnSizing,
                [columnId]: newSize,
              },
              manuallyResizedColumns: newManuallyResized,
            };
          });
        }
      } finally {
        isAutoSizingRef.current = false;
      }
    },
    [tableRef, setTableState]
  );

  // Reset all column sizing and clear manual resize tracking
  const clearColumnSizing = useCallback(() => {
    setTableState((prev) => ({
      ...prev,
      columnSizing: {},
      manuallyResizedColumns: [],
    }));
  }, [setTableState]);

  return {
    columnSizing,
    setSizingStrategy,
    clearColumnSizing,
    sizingStrategy,
    handleColumnSizingChange,
    applyAutoSizing,
    resetColumnSize,
  };
}
