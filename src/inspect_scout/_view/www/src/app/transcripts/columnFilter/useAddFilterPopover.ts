import { useCallback, useEffect, useRef, useState } from "react";

import type { OperatorModel } from "../../../query";
import type { ColumnFilter } from "../../../state/store";
import { TranscriptInfo } from "../../../types/api-types";
import {
  COLUMN_LABELS,
  DEFAULT_COLUMN_ORDER,
  getFilterTypeForColumn,
} from "../columns";

import { useColumnFilter } from "./useColumnFilter";

export interface AvailableColumn {
  id: string;
  label: string;
}

interface UseAddFilterPopoverParams {
  filters: Record<string, ColumnFilter>;
  onAddFilter: (filter: ColumnFilter) => void;
  onFilterColumnChange?: (columnId: string | null) => void;
}

// Static list of available columns - computed once
const AVAILABLE_COLUMNS: AvailableColumn[] = DEFAULT_COLUMN_ORDER.map(
  (columnId: keyof TranscriptInfo) => ({
    id: columnId,
    label: COLUMN_LABELS[columnId],
  })
);

/**
 * Hook for managing the "Add Filter" popover state.
 * Wraps useColumnFilter with column selection and open/close logic.
 */
export function useAddFilterPopover({
  filters,
  onAddFilter,
  onFilterColumnChange,
}: UseAddFilterPopoverParams) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedColumnId, setSelectedColumnId] = useState<string | null>(null);
  const prevOpenRef = useRef(false);

  const filterType = selectedColumnId
    ? getFilterTypeForColumn(selectedColumnId)
    : "string";

  const existingFilter = selectedColumnId ? filters[selectedColumnId] : null;

  const {
    operator,
    setOperator,
    value,
    setValue,
    operatorOptions,
    usesValue: isValueDisabled,
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

    const condition = buildCondition(operator, value);
    if (condition === undefined) return;

    onAddFilter({ columnId: selectedColumnId, filterType, condition });
    setIsOpen(false);
  }, [
    selectedColumnId,
    buildCondition,
    operator,
    value,
    onAddFilter,
    filterType,
  ]);

  const cancelAndClose = useCallback(() => setIsOpen(false), []);

  return {
    isOpen,
    setIsOpen,
    selectedColumnId,
    availableColumns: AVAILABLE_COLUMNS,
    operator,
    setOperator: setOperator as (op: OperatorModel) => void,
    operatorOptions,
    value,
    setValue,
    isValueDisabled,
    handleColumnChange,
    commitAndClose,
    cancelAndClose,
  };
}
