import { ChangeEvent, FC, KeyboardEvent, useCallback } from "react";

import type { OperatorModel } from "../../../query";
import type { FilterType } from "../../../state/store";

import styles from "./ColumnFilterEditor.module.css";

export interface ColumnFilterEditorProps {
  columnId: string;
  filterType: FilterType;
  operator: OperatorModel;
  operatorOptions: OperatorModel[];
  rawValue: string;
  isValueDisabled: boolean;
  valueSelectRef: React.RefObject<HTMLSelectElement | null>;
  valueInputRef: React.RefObject<HTMLInputElement | null>;
  onOperatorChange: (operator: OperatorModel) => void;
  onValueChange: (value: string) => void;
  onCommit?: () => void;
  onCancel?: () => void;
}

export const ColumnFilterEditor: FC<ColumnFilterEditorProps> = ({
  columnId,
  filterType,
  operator,
  operatorOptions,
  rawValue,
  isValueDisabled,
  valueSelectRef,
  valueInputRef,
  onOperatorChange,
  onValueChange,
  onCommit,
  onCancel,
}) => {
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

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        onCancel?.();
      }
      if (event.key === "Enter") {
        event.preventDefault();
        event.stopPropagation();
        onCommit?.();
      }
    },
    [onCancel, onCommit]
  );

  return (
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
  );
};
