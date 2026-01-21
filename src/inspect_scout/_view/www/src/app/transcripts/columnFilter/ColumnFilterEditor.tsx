import clsx from "clsx";
import { ChangeEvent, FC, KeyboardEvent, useCallback } from "react";

import { ScalarValue } from "../../../api/api";
import { AutocompleteInput } from "../../../components/AutocompleteInput";
import type { OperatorModel } from "../../../query";
import type { FilterType } from "../../../state/store";

import styles from "./ColumnFilterEditor.module.css";
import { DurationInput } from "./DurationInput";

export interface AvailableColumn {
  id: string;
  label: string;
}

export interface ColumnFilterEditorProps {
  columnId: string;
  filterType: FilterType;
  operator: OperatorModel;
  operatorOptions: OperatorModel[];
  rawValue: string;
  /** Second value for BETWEEN/NOT BETWEEN operators */
  rawValue2?: string;
  isValueDisabled: boolean;
  /** True if operator expects a range with two values (BETWEEN, NOT BETWEEN) */
  isRangeOperator?: boolean;
  onOperatorChange: (operator: OperatorModel) => void;
  onValueChange: (value: string) => void;
  /** Handler for second value changes (BETWEEN operators) */
  onValue2Change?: (value: string) => void;
  onCommit?: () => void;
  onCancel?: () => void;
  suggestions?: ScalarValue[];
  // Add mode props
  mode?: "add" | "edit";
  availableColumns?: AvailableColumn[];
  onColumnChange?: (columnId: string) => void;
}

export const ColumnFilterEditor: FC<ColumnFilterEditorProps> = ({
  columnId,
  filterType,
  operator,
  operatorOptions,
  rawValue,
  rawValue2 = "",
  isValueDisabled,
  isRangeOperator = false,
  onOperatorChange,
  onValueChange,
  onValue2Change,
  onCommit,
  onCancel,
  suggestions = [],
  mode = "edit",
  availableColumns,
  onColumnChange,
}) => {
  const isAddMode = mode === "add";
  const hasColumnSelected = isAddMode ? !!columnId : true;
  // In add mode, show dropdown only until a column is selected
  const showColumnDropdown = isAddMode && !columnId;

  // Get the display label for the selected column
  const selectedColumnLabel = columnId
    ? (availableColumns?.find((col) => col.id === columnId)?.label ?? columnId)
    : "";

  const handleColumnSelectChange = useCallback(
    (event: ChangeEvent<HTMLSelectElement>) => {
      onColumnChange?.(event.target.value);
    },
    [onColumnChange]
  );
  const handleOperatorChange = useCallback(
    (event: ChangeEvent<HTMLSelectElement>) => {
      const operator = event.target.value as OperatorModel;
      onOperatorChange(operator);
    },
    [onOperatorChange]
  );

  const handleValueChange = useCallback(
    (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      const value = event.target.value;
      onValueChange(value);
    },
    [onValueChange]
  );

  const handleValue2Change = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      const value = event.target.value;
      onValue2Change?.(value);
    },
    [onValue2Change]
  );

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // Prevent parent bubbling
      event.stopPropagation();

      if (event.key === "Escape") {
        event.preventDefault();
        onCancel?.();
      }
      if (event.key === "Enter") {
        event.preventDefault();
        onCommit?.();
      }
    },
    [onCancel, onCommit]
  );

  return (
    <div className={styles.filterContent} onKeyDown={handleKeyDown}>
      {/* Column row - dropdown until selected, then static text */}
      <div
        className={clsx(
          styles.filterRow,
          styles.columnId,
          !showColumnDropdown && styles.columnIdText,
          "text-size-small"
        )}
      >
        {showColumnDropdown ? (
          <select
            id="column-select"
            className={styles.filterSelect}
            value={columnId}
            onChange={handleColumnSelectChange}
            autoFocus
          >
            <option value="">Select column...</option>
            {availableColumns?.map((col) => (
              <option key={col.id} value={col.id}>
                {col.label}
              </option>
            ))}
          </select>
        ) : (
          selectedColumnLabel
        )}
      </div>

      {/* Operator and value rows - only show when column is selected */}
      {hasColumnSelected && (
        <>
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
          {isRangeOperator && <span className={styles.rangeLabel}>Start</span>}
          <div className={styles.filterRow}>
            {filterType === "boolean" ? (
              <select
                id={`${columnId}-val`}
                className={styles.filterSelect}
                value={rawValue}
                onChange={handleValueChange}
                disabled={isValueDisabled}
                autoFocus={!isAddMode}
              >
                <option value="">(not set)</option>
                <option value="true">true</option>
                <option value="false">false</option>
              </select>
            ) : filterType === "string" || filterType === "unknown" ? (
              <AutocompleteInput
                id={`${columnId}-val`}
                value={rawValue}
                onChange={onValueChange}
                onCommit={onCommit}
                onCancel={onCancel}
                disabled={isValueDisabled}
                placeholder="Filter"
                suggestions={suggestions}
                className={styles.filterInput}
                autoFocus={!isAddMode}
                allowBrowse={true}
              />
            ) : filterType === "duration" ? (
              <DurationInput
                id={`${columnId}-val`}
                value={rawValue}
                onChange={handleValueChange}
                disabled={isValueDisabled}
                autoFocus={!isAddMode}
              />
            ) : (
              <input
                id={`${columnId}-val`}
                className={styles.filterInput}
                type={
                  filterType === "number"
                    ? "number"
                    : filterType === "date"
                      ? "date"
                      : "datetime-local"
                }
                spellCheck="false"
                value={rawValue}
                onChange={handleValueChange}
                placeholder="Filter"
                disabled={isValueDisabled}
                step={filterType === "number" ? "any" : undefined}
                autoFocus={!isAddMode}
              />
            )}
          </div>
          {/* Second input for BETWEEN/NOT BETWEEN operators */}
          {isRangeOperator && (
            <>
              <span className={styles.rangeLabel}>End</span>
              <div className={styles.filterRow}>
                {filterType === "duration" ? (
                  <DurationInput
                    id={`${columnId}-val2`}
                    value={rawValue2}
                    onChange={handleValue2Change}
                    disabled={isValueDisabled}
                  />
                ) : (
                  <input
                    id={`${columnId}-val2`}
                    className={styles.filterInput}
                    type={
                      filterType === "number"
                        ? "number"
                        : filterType === "date"
                          ? "date"
                          : "datetime-local"
                    }
                    spellCheck="false"
                    value={rawValue2}
                    onChange={handleValue2Change}
                    placeholder="Filter"
                    disabled={isValueDisabled}
                    step={filterType === "number" ? "any" : undefined}
                  />
                )}
              </div>
            </>
          )}
        </>
      )}

      <div className={styles.filterRow}>
        <button
          className={clsx(
            "btn",
            "btn-outline-primary",
            styles.filterButton,
            "text-size-small"
          )}
          onClick={onCommit}
          disabled={!hasColumnSelected}
        >
          Apply
        </button>
      </div>
    </div>
  );
};
