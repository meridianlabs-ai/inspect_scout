import { useCallback, useEffect, useRef, useState } from "react";

import { ConditionBuilder } from "../../../query";
import type { OperatorModel, ScalarValue } from "../../../query";
import type { SimpleCondition } from "../../../query/types";
import type { FilterType } from "../../../state/store";
import {
  formatDateForInput,
  formatDateTimeForInput,
  parseDateFromInput,
} from "../../../utils/date";

const OPERATORS_BY_TYPE: Record<FilterType, OperatorModel[]> = {
  string: [
    "=",
    "!=",
    "LIKE",
    "NOT LIKE",
    "ILIKE",
    "NOT ILIKE",
    "IS NULL",
    "IS NOT NULL",
  ],
  number: ["=", "!=", "<", "<=", ">", ">=", "IS NULL", "IS NOT NULL"],
  boolean: ["=", "!=", "IS NULL", "IS NOT NULL"],
  date: ["=", "!=", "<", "<=", ">", ">=", "IS NULL", "IS NOT NULL"],
  datetime: ["=", "!=", "<", "<=", ">", ">=", "IS NULL", "IS NOT NULL"],
  duration: ["=", "!=", "<", "<=", ">", ">=", "IS NULL", "IS NOT NULL"],
  unknown: [
    "=",
    "!=",
    "LIKE",
    "NOT LIKE",
    "ILIKE",
    "NOT ILIKE",
    "IS NULL",
    "IS NOT NULL",
  ],
};

const OPERATORS_WITHOUT_VALUE = new Set<OperatorModel>([
  "IS NULL",
  "IS NOT NULL",
]);

const formatFilterValue = (
  value: SimpleCondition["right"] | undefined,
  filterType?: FilterType
): string => {
  if (value === null || value === undefined) {
    return "";
  }
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  // For date/datetime types, ensure ISO format for native inputs
  if (filterType === "date" && typeof value !== "boolean") {
    return formatDateForInput(value);
  }
  if (filterType === "datetime" && typeof value !== "boolean") {
    return formatDateTimeForInput(value);
  }
  return String(value);
};

const parseFilterValue = (
  filterType: FilterType,
  rawValue: string
): ScalarValue | undefined => {
  switch (filterType) {
    case "number":
    case "duration": {
      const parsed = Number(rawValue);
      return Number.isFinite(parsed) ? parsed : undefined;
    }
    case "boolean":
      if (rawValue === "true") return true;
      if (rawValue === "false") return false;
      return undefined;
    case "date":
    case "datetime":
      return parseDateFromInput(rawValue);
    case "unknown":
    case "string":
    default:
      return rawValue;
  }
};

export interface UseColumnFilterParams {
  columnId: string;
  filterType: FilterType;
  condition: SimpleCondition | null;
  isOpen: boolean;
}

export interface UseColumnFilterReturn {
  operator: OperatorModel;
  setOperator: (operator: OperatorModel) => void;
  operatorOptions: OperatorModel[];
  value: string;
  setValue: (value: string) => void;
  usesValue: boolean;
  buildCondition: (
    operator: OperatorModel,
    value: string
  ) => SimpleCondition | null | undefined;
}

export function useColumnFilter({
  columnId,
  filterType,
  condition,
  isOpen,
}: UseColumnFilterParams): UseColumnFilterReturn {
  // operators
  const operatorOptions = OPERATORS_BY_TYPE[filterType];
  const defaultOperator: OperatorModel = operatorOptions[0] ?? "=";
  const [operator, setOperator] = useState<OperatorModel>(
    condition?.operator ?? defaultOperator
  );

  // value
  const [value, setValue] = useState<string>(
    formatFilterValue(condition?.right, filterType)
  );
  const isValueDisabled = OPERATORS_WITHOUT_VALUE.has(operator);
  const valueSelectRef = useRef<HTMLSelectElement | null>(null);
  const valueInputRef = useRef<HTMLInputElement | null>(null);

  // Track the previous columnId to detect when we switch to a different filter
  const prevColumnIdRef = useRef(columnId);

  // Sync state when closed OR when switching to a different column while opening
  useEffect(() => {
    const columnChanged = prevColumnIdRef.current !== columnId;
    prevColumnIdRef.current = columnId;

    if (!isOpen || columnChanged) {
      setOperator(condition?.operator ?? defaultOperator);
      setValue(formatFilterValue(condition?.right, filterType));
    }
  }, [condition, defaultOperator, filterType, isOpen, columnId, setValue]);

  // auto-focus value input when opened
  useEffect(() => {
    if (!isOpen || isValueDisabled) {
      return;
    }
    const timer = window.setTimeout(() => {
      if (filterType === "boolean") {
        valueSelectRef.current?.focus();
      } else {
        valueInputRef.current?.focus();
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, [filterType, isOpen, isValueDisabled]);

  const buildCondition = useCallback(
    (operator: OperatorModel, value: string) => {
      if (OPERATORS_WITHOUT_VALUE.has(operator)) {
        return ConditionBuilder.simple(columnId, operator, null);
      }
      if (value.trim() === "") {
        return null;
      }
      const parsed = parseFilterValue(filterType, value);
      if (parsed === undefined) {
        return undefined;
      }

      // Special case - inject wildcards if not specified
      if (
        operator === "LIKE" ||
        operator === "NOT LIKE" ||
        operator === "ILIKE" ||
        operator === "NOT ILIKE"
      ) {
        let modified = String(parsed);
        if (!modified.includes("%")) {
          modified = `%${modified}%`;
        }
        return ConditionBuilder.simple(columnId, operator, modified);
      } else {
        return ConditionBuilder.simple(columnId, operator, parsed);
      }
    },
    [columnId, filterType]
  );

  return {
    operator,
    setOperator,
    value,
    setValue,
    operatorOptions,
    usesValue: isValueDisabled,
    buildCondition,
  };
}
