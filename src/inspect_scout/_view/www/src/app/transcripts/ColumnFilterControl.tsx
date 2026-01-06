import clsx from "clsx";
import {
  ChangeEvent,
  FC,
  KeyboardEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import { ApplicationIcons } from "../../components/icons";
import { PopOver } from "../../components/PopOver";
import { ConditionBuilder } from "../../query";
import type { OperatorModel, ScalarValue } from "../../query";
import type { SimpleCondition } from "../../query/types";
import {
  formatDateForInput,
  formatDateTimeForInput,
  parseDateFromInput,
} from "../../utils/date";

import styles from "./ColumnFilterControl.module.css";

export type FilterType =
  | "string"
  | "number"
  | "boolean"
  | "date"
  | "datetime"
  | "unknown";

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
    case "number": {
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

interface ColumnFilterControlProps {
  columnId: string;
  filterType: FilterType;
  condition: SimpleCondition | null;
  onChange: (condition: SimpleCondition | null) => void;
}

export const ColumnFilterControl: FC<ColumnFilterControlProps> = ({
  columnId,
  filterType,
  condition,
  onChange,
}) => {
  // operators
  const operatorOptions = OPERATORS_BY_TYPE[filterType];
  const defaultOperator: OperatorModel = operatorOptions[0] ?? "=";
  const [operator, setOperator] = useState<OperatorModel>(
    condition?.operator ?? defaultOperator
  );

  // value
  const [rawValue, setRawValue] = useState<string>(
    formatFilterValue(condition?.right, filterType)
  );
  const isValueDisabled = OPERATORS_WITHOUT_VALUE.has(operator);
  const valueSelectRef = useRef<HTMLSelectElement | null>(null);
  const valueInputRef = useRef<HTMLInputElement | null>(null);

  // popover
  const buttonRef = useRef<HTMLButtonElement | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const cancelRef = useRef(false);
  const prevOpenRef = useRef(false);

  // keep state in sync with props when closed
  useEffect(() => {
    if (!isOpen) {
      setOperator(condition?.operator ?? defaultOperator);
      setRawValue(formatFilterValue(condition?.right, filterType));
    }
  }, [condition, defaultOperator, filterType, isOpen]);

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

  const handleOperatorChange = useCallback(
    (event: ChangeEvent<HTMLSelectElement>) => {
      const operator = event.target.value as OperatorModel;
      setOperator(operator);
    },
    []
  );

  const handleValueChange = useCallback(
    (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      const value = event.target.value;
      setRawValue(value);
    },
    []
  );

  const handlePopoverOpenChange = useCallback((nextOpen: boolean) => {
    setIsOpen(nextOpen);
  }, []);

  const cancelAndClose = useCallback(() => {
    cancelRef.current = true;
    setOperator(condition?.operator ?? defaultOperator);
    setRawValue(formatFilterValue(condition?.right, filterType));
    handlePopoverOpenChange(false);
  }, [condition, defaultOperator, filterType, handlePopoverOpenChange]);

  const commitAndClose = useCallback(() => {
    const nextCondition = buildCondition(operator, rawValue);
    if (nextCondition === undefined) {
      return;
    }
    handlePopoverOpenChange(false);
  }, [buildCondition, handlePopoverOpenChange, operator, rawValue]);

  useEffect(() => {
    if (prevOpenRef.current && !isOpen) {
      if (cancelRef.current) {
        cancelRef.current = false;
      } else {
        const nextCondition = buildCondition(operator, rawValue);
        if (nextCondition !== undefined) {
          onChange(nextCondition);
        }
      }
    }
    prevOpenRef.current = isOpen;
  }, [buildCondition, isOpen, onChange, operator, rawValue]);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        cancelAndClose();
      }
      if (event.key === "Enter") {
        event.preventDefault();
        commitAndClose();
      }
    },
    [cancelAndClose, commitAndClose]
  );

  return (
    <div className={styles.headerActions}>
      <button
        ref={buttonRef}
        type="button"
        className={clsx(
          styles.filterButton,
          condition && styles.filterButtonActive
        )}
        onClick={(event) => {
          event.stopPropagation();
          if (isOpen) {
            handlePopoverOpenChange(false);
          } else {
            handlePopoverOpenChange(true);
          }
        }}
        aria-label={`Filter ${columnId}`}
      >
        <i className={ApplicationIcons.filter} />
      </button>
      <PopOver
        id={`transcripts-filter-${columnId}`}
        isOpen={isOpen}
        setIsOpen={handlePopoverOpenChange}
        positionEl={buttonRef.current}
        placement="bottom-end"
        showArrow={true}
        hoverDelay={-1}
        className={styles.filterPopover}
        closeOnMouseLeave={false}
        styles={{
          padding: "0.4rem",
          backgroundColor: "var(--bs-light)",
        }}
      >
        <div className={styles.filterContent} onKeyDown={handleKeyDown}>
          <div className={styles.filterRow}>
            <select
              id={`${columnId}-op`}
              className={styles.filterSelect}
              value={operator}
              onChange={handleOperatorChange}
            >
              {operatorOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>
          <div className={styles.filterRow}>
            {filterType === "boolean" ? (
              <select
                id={`${columnId}-val`}
                className={styles.filterSelect}
                value={rawValue}
                onChange={handleValueChange}
                disabled={isValueDisabled}
                ref={valueSelectRef}
              >
                <option value="">(clear)</option>
                <option value="true">true</option>
                <option value="false">false</option>
              </select>
            ) : (
              <input
                id={`${columnId}-val`}
                className={styles.filterInput}
                type={
                  filterType === "number"
                    ? "number"
                    : filterType === "date"
                      ? "date"
                      : filterType === "datetime"
                        ? "datetime-local"
                        : "text"
                }
                value={rawValue}
                onChange={handleValueChange}
                placeholder="Filter"
                disabled={isValueDisabled}
                step={filterType === "number" ? "any" : undefined}
                ref={valueInputRef}
              />
            )}
          </div>
        </div>
      </PopOver>
    </div>
  );
};
