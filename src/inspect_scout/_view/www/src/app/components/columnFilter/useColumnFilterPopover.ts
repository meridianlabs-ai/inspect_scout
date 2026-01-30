import { useCallback, useEffect, useRef, useState } from "react";

import type { SimpleCondition } from "../../../query/types";
import type { FilterType } from "../../../state/store";

import { useColumnFilter } from "./useColumnFilter";

export interface UseColumnFilterPopoverParams {
  columnId: string;
  filterType: FilterType;
  condition: SimpleCondition | null;
  onChange: (condition: SimpleCondition | null) => void;
}

export interface UseColumnFilterPopoverReturn {
  // Popover state
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;

  // Filter state from useColumnFilter
  operator: ReturnType<typeof useColumnFilter>["operator"];
  setOperator: ReturnType<typeof useColumnFilter>["setOperator"];
  operatorOptions: ReturnType<typeof useColumnFilter>["operatorOptions"];

  // Value
  value: ReturnType<typeof useColumnFilter>["value"];
  setValue: ReturnType<typeof useColumnFilter>["setValue"];
  value2: ReturnType<typeof useColumnFilter>["value2"];
  setValue2: ReturnType<typeof useColumnFilter>["setValue2"];
  isValueDisabled: ReturnType<typeof useColumnFilter>["usesValue"];
  isRangeOperator: ReturnType<typeof useColumnFilter>["usesRangeValue"];

  // Actions
  commitAndClose: () => void;
  cancelAndClose: () => void;
}

export function useColumnFilterPopover({
  columnId,
  filterType,
  condition,
  onChange,
}: UseColumnFilterPopoverParams): UseColumnFilterPopoverReturn {
  const [isOpen, setIsOpen] = useState(false);
  const cancelRef = useRef(false);
  const prevOpenRef = useRef(false);

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
    columnId,
    filterType,
    condition,
    isOpen,
  });

  const cancelAndClose = useCallback(() => {
    cancelRef.current = true;
    setIsOpen(false);
  }, []);

  const commitAndClose = useCallback(() => {
    const nextCondition = buildCondition(operator, value, value2);
    if (nextCondition === undefined) {
      return;
    }
    setIsOpen(false);
  }, [buildCondition, operator, value, value2]);

  // commit changes when popover closes (unless cancelled)
  useEffect(() => {
    if (prevOpenRef.current && !isOpen) {
      if (cancelRef.current) {
        cancelRef.current = false;
      } else {
        const nextCondition = buildCondition(operator, value, value2);
        if (nextCondition !== undefined) {
          onChange(nextCondition);
        }
      }
    }
    prevOpenRef.current = isOpen;
  }, [buildCondition, isOpen, onChange, operator, value, value2]);

  return {
    isOpen,
    setIsOpen,
    operator,
    setOperator,
    value,
    setValue,
    value2,
    setValue2,
    operatorOptions,
    isValueDisabled,
    isRangeOperator,
    commitAndClose,
    cancelAndClose,
  };
}
