import { FC, useCallback, useEffect, useRef, useState } from "react";

import { PopOver } from "../../../components/PopOver";
import type { SimpleCondition } from "../../../query/types";
import type { FilterType } from "../../../state/store";

import { ColumnFilterButton } from "./ColumnFilterButton";
import styles from "./ColumnFilterControl.module.css";
import { ColumnFilterEditor } from "./ColumnFilterEditor";
import { useColumnFilter } from "./useColumnFilter";

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
  // popover state
  const buttonRef = useRef<HTMLButtonElement | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const cancelRef = useRef(false);
  const prevOpenRef = useRef(false);

  // filter logic
  const {
    operator,
    setOperator,
    rawValue,
    setRawValue,
    operatorOptions,
    isValueDisabled,
    valueSelectRef,
    valueInputRef,
    buildCondition,
  } = useColumnFilter({
    columnId,
    filterType,
    condition,
    isOpen,
  });

  const handlePopoverOpenChange = useCallback((nextOpen: boolean) => {
    setIsOpen(nextOpen);
  }, []);

  const cancelAndClose = useCallback(() => {
    cancelRef.current = true;
    handlePopoverOpenChange(false);
  }, [handlePopoverOpenChange]);

  const commitAndClose = useCallback(() => {
    const nextCondition = buildCondition(operator, rawValue);
    if (nextCondition === undefined) {
      return;
    }
    handlePopoverOpenChange(false);
  }, [buildCondition, handlePopoverOpenChange, operator, rawValue]);

  // commit changes when popover closes (unless cancelled)
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
        />
      </PopOver>
    </div>
  );
};
