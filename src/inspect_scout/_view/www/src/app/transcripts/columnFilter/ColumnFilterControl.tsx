import { FC, useCallback, useRef } from "react";

import { ScalarValue } from "../../../api/api";
import { PopOver } from "../../../components/PopOver";
import type { SimpleCondition } from "../../../query/types";
import type { FilterType } from "../../../state/store";

import { ColumnFilterButton } from "./ColumnFilterButton";
import styles from "./ColumnFilterControl.module.css";
import { ColumnFilterEditor } from "./ColumnFilterEditor";
import { useColumnFilterPopover } from "./useColumnFilterPopover";

interface ColumnFilterControlProps {
  columnId: string;
  filterType: FilterType;
  condition: SimpleCondition | null;
  onChange: (condition: SimpleCondition | null) => void;
  /** Autocomplete suggestions for the filter value */
  suggestions?: ScalarValue[];
  /** Called when the popover opens/closes (for fetching suggestions) */
  onOpenChange?: (columnId: string | null) => void;
}

export const ColumnFilterControl: FC<ColumnFilterControlProps> = ({
  columnId,
  filterType,
  condition,
  onChange,
  suggestions = [],
  onOpenChange,
}) => {
  const buttonRef = useRef<HTMLButtonElement | null>(null);

  const {
    isOpen,
    setIsOpen,
    operator,
    setOperator,
    rawValue,
    setRawValue,
    operatorOptions,
    isValueDisabled,
    valueSelectRef,
    valueInputRef,
    commitAndClose,
    cancelAndClose,
  } = useColumnFilterPopover({
    columnId,
    filterType,
    condition,
    onChange,
  });

  const handlePopoverOpenChange = useCallback(
    (nextOpen: boolean) => {
      setIsOpen(nextOpen);
      onOpenChange?.(nextOpen ? columnId : null);
    },
    [setIsOpen, onOpenChange, columnId]
  );

  return (
    <div className={styles.headerActions}>
      <ColumnFilterButton
        ref={buttonRef}
        columnId={columnId}
        isActive={!!condition}
        onClick={(event) => {
          event.stopPropagation();
          handlePopoverOpenChange(!isOpen);
        }}
      />
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
        <ColumnFilterEditor
          columnId={columnId}
          filterType={filterType}
          operator={operator}
          operatorOptions={operatorOptions}
          rawValue={rawValue}
          isValueDisabled={isValueDisabled}
          valueSelectRef={valueSelectRef}
          valueInputRef={valueInputRef}
          onOperatorChange={setOperator}
          onValueChange={setRawValue}
          onCommit={commitAndClose}
          onCancel={cancelAndClose}
          suggestions={suggestions}
        />
      </PopOver>
    </div>
  );
};
