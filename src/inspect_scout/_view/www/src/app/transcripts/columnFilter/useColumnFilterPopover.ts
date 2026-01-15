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
  isValueDisabled: ReturnType<typeof useColumnFilter>["usesValue"];

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
    operatorOptions,
    usesValue: isValueDisabled,
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
    const nextCondition = buildCondition(operator, value);
    if (nextCondition === undefined) {
      return;
    }
    setIsOpen(false);
  }, [buildCondition, operator, value]);

  // commit changes when popover closes (unless cancelled)
  useEffect(() => {
    if (prevOpenRef.current && !isOpen) {
      if (cancelRef.current) {
        cancelRef.current = false;
      } else {
        const nextCondition = buildCondition(operator, value);
        if (nextCondition !== undefined) {
          onChange(nextCondition);
        }
      }
    }
    prevOpenRef.current = isOpen;
  }, [buildCondition, isOpen, onChange, operator, value]);

  return {
    isOpen,
    setIsOpen,
    operator,
    setOperator,
    value,
    setValue,
    operatorOptions,
    isValueDisabled,
    commitAndClose,
    cancelAndClose,
  };
}
