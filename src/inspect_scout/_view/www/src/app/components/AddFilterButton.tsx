import { clsx } from "clsx";
import { FC, useRef } from "react";

import { ScalarValue } from "../../api/api";
import { ApplicationIcons } from "../../components/icons";
import { PopOver } from "../../components/PopOver";
import type { OperatorModel } from "../../query";

import { Chip } from "./Chip";
import {
  ColumnFilterEditor,
  type AvailableColumn,
} from "./columnFilter/ColumnFilterEditor";
import styles from "./FilterBar.module.css";

/** Props accepted by AddFilterButton - subset of useAddFilterPopover return */
export interface AddFilterPopoverState {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  selectedColumnId: string | null;
  columns: AvailableColumn[];
  filterType:
    | "string"
    | "number"
    | "date"
    | "datetime"
    | "boolean"
    | "duration"
    | "unknown";
  operator: OperatorModel;
  setOperator: (op: OperatorModel) => void;
  operatorOptions: OperatorModel[];
  value: string;
  setValue: (v: string) => void;
  value2: string;
  setValue2: (v: string) => void;
  isValueDisabled: boolean;
  isRangeOperator: boolean;
  handleColumnChange: (columnId: string) => void;
  commitAndClose: () => void;
  cancelAndClose: () => void;
}

export interface AddFilterButtonProps {
  /** Unique prefix for popover IDs */
  idPrefix: string;
  /** Popover state from useAddFilterPopover hook */
  popoverState: AddFilterPopoverState;
  /** Suggestions for autocomplete */
  suggestions?: ScalarValue[];
}

/**
 * "Add filter" chip + popover pattern extracted for reuse.
 * Accepts popover state from useAddFilterPopover hook.
 */
export const AddFilterButton: FC<AddFilterButtonProps> = ({
  idPrefix,
  popoverState,
  suggestions = [],
}) => {
  const chipRef = useRef<HTMLDivElement | null>(null);

  const {
    isOpen,
    setIsOpen,
    selectedColumnId,
    columns,
    filterType,
    operator,
    setOperator,
    operatorOptions,
    value,
    setValue,
    value2,
    setValue2,
    isValueDisabled,
    isRangeOperator,
    handleColumnChange,
    commitAndClose,
    cancelAndClose,
  } = popoverState;

  return (
    <>
      <Chip
        ref={chipRef}
        icon={ApplicationIcons.add}
        value="Add"
        title="Add a new filter"
        className={clsx(styles.filterChip, "text-size-smallest")}
        onClick={() => setIsOpen(true)}
      />
      <PopOver
        id={`${idPrefix}-add-filter-editor`}
        isOpen={isOpen}
        setIsOpen={setIsOpen}
        // eslint-disable-next-line react-hooks/refs -- positionEl accepts null; PopOver/Popper handles this in effects and updates when ref is populated
        positionEl={chipRef.current}
        placement="bottom-start"
        showArrow={true}
        hoverDelay={-1}
        closeOnMouseLeave={false}
        styles={{
          padding: "0.4rem",
          backgroundColor: "var(--bs-light)",
        }}
      >
        <ColumnFilterEditor
          mode="add"
          columnId={selectedColumnId ?? ""}
          filterType={filterType}
          operator={operator}
          operatorOptions={operatorOptions}
          rawValue={value}
          rawValue2={value2}
          isValueDisabled={isValueDisabled}
          isRangeOperator={isRangeOperator}
          onOperatorChange={setOperator}
          onValueChange={setValue}
          onValue2Change={setValue2}
          onCommit={commitAndClose}
          onCancel={cancelAndClose}
          suggestions={suggestions}
          columns={columns}
          onColumnChange={handleColumnChange}
        />
      </PopOver>
    </>
  );
};
