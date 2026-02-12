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
    "IN",
    "NOT IN",
    "IS NULL",
    "IS NOT NULL",
  ],
  number: [
    "=",
    "!=",
    "<",
    "<=",
    ">",
    ">=",
    "IN",
    "NOT IN",
    "BETWEEN",
    "NOT BETWEEN",
    "IS NULL",
    "IS NOT NULL",
  ],
  boolean: ["=", "!=", "IS NULL", "IS NOT NULL"],
  date: [
    "=",
    "!=",
    "<",
    "<=",
    ">",
    ">=",
    "BETWEEN",
    "NOT BETWEEN",
    "IS NULL",
    "IS NOT NULL",
  ],
  datetime: [
    "=",
    "!=",
    "<",
    "<=",
    ">",
    ">=",
    "BETWEEN",
    "NOT BETWEEN",
    "IS NULL",
    "IS NOT NULL",
  ],
  duration: [
    "=",
    "!=",
    "<",
    "<=",
    ">",
    ">=",
    "BETWEEN",
    "NOT BETWEEN",
    "IS NULL",
    "IS NOT NULL",
  ],
  unknown: [
    "=",
    "!=",
    "LIKE",
    "NOT LIKE",
    "ILIKE",
    "NOT ILIKE",
    "IN",
    "NOT IN",
    "IS NULL",
    "IS NOT NULL",
  ],
};

const OPERATORS_WITHOUT_VALUE = new Set<OperatorModel>([
  "IS NULL",
  "IS NOT NULL",
]);

const OPERATORS_WITH_LIST_VALUE = new Set<OperatorModel>(["IN", "NOT IN"]);

const OPERATORS_WITH_RANGE_VALUE = new Set<OperatorModel>([
  "BETWEEN",
  "NOT BETWEEN",
]);

/**
 * Formats a single scalar value for display in an input field.
 */
const formatScalarValue = (
  value: ScalarValue,
  filterType?: FilterType
): string => {
  if (value === null || value === undefined) {
    return "";
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

/**
 * Formats a filter value (single, array, or tuple) for the primary input field.
 * For BETWEEN operators, this returns only the first value.
 */
const formatFilterValue = (
  value: SimpleCondition["right"] | undefined,
  filterType?: FilterType
): string => {
  if (value === null || value === undefined) {
    return "";
  }
  // For arrays (IN/NOT IN or BETWEEN tuple), join with comma for IN/NOT IN
  // or return first value for BETWEEN
  if (Array.isArray(value)) {
    // Tuple for BETWEEN - return first value only
    if (value.length === 2) {
      return formatScalarValue(value[0], filterType);
    }
    // Array for IN/NOT IN - join with comma
    return value.map((v) => formatScalarValue(v, filterType)).join(", ");
  }
  return formatScalarValue(value, filterType);
};

/**
 * Formats the second value for BETWEEN operators.
 */
const formatFilterValue2 = (
  value: SimpleCondition["right"] | undefined,
  filterType?: FilterType
): string => {
  if (value === null || value === undefined) {
    return "";
  }
  // For BETWEEN tuple, return second value
  if (Array.isArray(value) && value.length === 2) {
    return formatScalarValue(value[1], filterType);
  }
  return "";
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

/**
 * Parses a comma-separated string into an array of scalar values for IN/NOT IN operators.
 */
const parseListValue = (
  filterType: FilterType,
  rawValue: string
): ScalarValue[] | undefined => {
  const parts = rawValue
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s !== "");
  if (parts.length === 0) {
    return undefined;
  }
  const parsed: ScalarValue[] = [];
  for (const part of parts) {
    const value = parseFilterValue(filterType, part);
    if (value === undefined) {
      return undefined;
    }
    parsed.push(value);
  }
  return parsed;
};

/**
 * Parses two values into a tuple for BETWEEN/NOT BETWEEN operators.
 */
const parseRangeValue = (
  filterType: FilterType,
  rawValue1: string,
  rawValue2: string
): [ScalarValue, ScalarValue] | undefined => {
  const parsed1 = parseFilterValue(filterType, rawValue1);
  const parsed2 = parseFilterValue(filterType, rawValue2);
  if (parsed1 === undefined || parsed2 === undefined) {
    return undefined;
  }
  return [parsed1, parsed2];
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
  /** Second value for BETWEEN/NOT BETWEEN operators */
  value2: string;
  setValue2: (value: string) => void;
  /** True if operator requires no value (IS NULL, IS NOT NULL) */
  usesValue: boolean;
  /** True if operator expects a list of values (IN, NOT IN) */
  usesListValue: boolean;
  /** True if operator expects a range with two values (BETWEEN, NOT BETWEEN) */
  usesRangeValue: boolean;
  buildCondition: (
    operator: OperatorModel,
    value: string,
    value2?: string
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

  // value (primary)
  const [value, setValue] = useState<string>(
    formatFilterValue(condition?.right, filterType)
  );
  // value2 (secondary for BETWEEN operators)
  const [value2, setValue2] = useState<string>(
    formatFilterValue2(condition?.right, filterType)
  );

  const isValueDisabled = OPERATORS_WITHOUT_VALUE.has(operator);
  const usesListValue = OPERATORS_WITH_LIST_VALUE.has(operator);
  const usesRangeValue = OPERATORS_WITH_RANGE_VALUE.has(operator);

  const valueSelectRef = useRef<HTMLSelectElement | null>(null);
  const valueInputRef = useRef<HTMLInputElement | null>(null);

  // Track the previous columnId to detect when we switch to a different filter
  const prevColumnIdRef = useRef(columnId);

  // Sync state when closed OR when switching to a different column while opening
  useEffect(() => {
    const columnChanged = prevColumnIdRef.current !== columnId;
    prevColumnIdRef.current = columnId;

    if (!isOpen || columnChanged) {
      // TODO: lint react-hooks/set-state-in-effect - consider if fixing this violation makes sense
      /* eslint-disable react-hooks/set-state-in-effect */
      setOperator(condition?.operator ?? defaultOperator);
      setValue(formatFilterValue(condition?.right, filterType));
      setValue2(formatFilterValue2(condition?.right, filterType));
      /* eslint-enable react-hooks/set-state-in-effect */
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
    (operator: OperatorModel, value: string, value2?: string) => {
      if (OPERATORS_WITHOUT_VALUE.has(operator)) {
        return ConditionBuilder.simple(columnId, operator, null);
      }
      if (value.trim() === "") {
        return null;
      }

      // Handle list operators (IN, NOT IN)
      if (OPERATORS_WITH_LIST_VALUE.has(operator)) {
        const parsed = parseListValue(filterType, value);
        if (parsed === undefined) {
          return undefined;
        }
        return ConditionBuilder.simple(columnId, operator, parsed);
      }

      // Handle range operators (BETWEEN, NOT BETWEEN)
      if (OPERATORS_WITH_RANGE_VALUE.has(operator)) {
        if (!value2 || value2.trim() === "") {
          return null;
        }
        const parsed = parseRangeValue(filterType, value, value2);
        if (parsed === undefined) {
          return undefined;
        }
        return ConditionBuilder.simple(columnId, operator, parsed);
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
    value2,
    setValue2,
    operatorOptions,
    usesValue: isValueDisabled,
    usesListValue,
    usesRangeValue,
    buildCondition,
  };
}
