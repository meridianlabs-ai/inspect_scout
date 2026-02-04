import { useCallback, useEffect, useRef, useState } from "react";

import type { OperatorModel } from "../../../query";
import type { ColumnFilter } from "../../../state/store";

import type { AvailableColumn } from "./ColumnFilterEditor";
import { useColumnFilter } from "./useColumnFilter";

export interface UseAddFilterPopoverParams {
  /** Columns available for filtering */
  columns: AvailableColumn[];
  /** Current filters */
  filters: Record<string, ColumnFilter>;
  /** Callback when a filter is added */
  onAddFilter: (filter: ColumnFilter) => void;
  /** Callback when the selected column changes (for fetching suggestions) */
  onFilterColumnChange?: (columnId: string | null) => void;
}

/**
 * Generic hook for managing the "Add Filter" popover state.
 * Wraps useColumnFilter with column selection and open/close logic.
 */
export function useAddFilterPopover({
  columns,
  filters,
  onAddFilter,
  onFilterColumnChange,
}: UseAddFilterPopoverParams) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedColumnId, setSelectedColumnId] = useState<string | null>(null);
  const prevOpenRef = useRef(false);

  const selectedColumn = selectedColumnId
    ? columns.find((c) => c.id === selectedColumnId)
    : null;
  const filterType = selectedColumn?.filterType ?? "string";

  const existingFilter = selectedColumnId ? filters[selectedColumnId] : null;

  const {
    operator,
    setOperator,
    value,
    setValue,
    value2,
    setValue2,
    operatorOptions,
    usesValue: isValueDisabled,
    usesRangeValue: isRangeOperator,
    buildCondition,
  } = useColumnFilter({
    columnId: selectedColumnId ?? "",
    filterType,
    condition: existingFilter?.condition ?? null,
    isOpen,
  });

  // Reset column selection when popover opens
  useEffect(() => {
    if (isOpen && !prevOpenRef.current) {
      setSelectedColumnId(null);
    }
    prevOpenRef.current = isOpen;
  }, [isOpen]);

  // Notify parent when popover closes
  useEffect(() => {
    if (prevOpenRef.current && !isOpen) {
      onFilterColumnChange?.(null);
    }
  }, [isOpen, onFilterColumnChange]);

  const handleColumnChange = useCallback(
    (newColumnId: string) => {
      setSelectedColumnId(newColumnId || null);
      if (newColumnId) {
        onFilterColumnChange?.(newColumnId);
      }
    },
    [onFilterColumnChange]
  );

  const commitAndClose = useCallback(() => {
    if (!selectedColumnId) return;

    const condition = buildCondition(operator, value, value2);
    if (condition === undefined) return;

    onAddFilter({ columnId: selectedColumnId, filterType, condition });
    setIsOpen(false);
  }, [
    selectedColumnId,
    buildCondition,
    operator,
    value,
    value2,
    onAddFilter,
    filterType,
  ]);

  const cancelAndClose = useCallback(() => setIsOpen(false), []);

  return {
    isOpen,
    setIsOpen,
    selectedColumnId,
    columns,
    filterType,
    operator,
    setOperator: setOperator as (op: OperatorModel) => void,
    operatorOptions,
    value,
    setValue,
    value2,
    setValue2,
    isValueDisabled,
    isRangeOperator,
    handleColumnChange,
    commitAndClose,
    cancelAndClose,
  };
}
