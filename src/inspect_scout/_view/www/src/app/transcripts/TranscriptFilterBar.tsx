import { clsx } from "clsx";
import { FC, useCallback, useRef, useState } from "react";

import { ScalarValue } from "../../api/api";
import { ApplicationIcons } from "../../components/icons";
import { PopOver } from "../../components/PopOver";
import { ColumnFilter, useStore } from "../../state/store";
import type { TranscriptInfo } from "../../types/api-types";
import { Chip } from "../components/Chip";
import { FilterBar } from "../components/FilterBar";
import { ColumnFilterEditor } from "../components/columnFilter";

import { useAddFilterPopover } from "./columnFilter";
import { DEFAULT_VISIBLE_COLUMNS } from "./columns";
import { TranscriptColumnsButton } from "./TranscriptColumnsButton";
import { TranscriptColumnsPopover } from "./TranscriptColumnsPopover";
import styles from "./TranscriptFilterBar.module.css";

export const TranscriptFilterBar: FC<{
  filterCodeValues?: Record<string, string>;
  filterSuggestions?: ScalarValue[];
  onFilterColumnChange?: (columnId: string | null) => void;
  includeColumnPicker?: boolean;
}> = ({
  filterCodeValues,
  filterSuggestions = [],
  onFilterColumnChange,
  includeColumnPicker = true,
}) => {
  // Transcript Filter State
  const filters = useStore(
    (state) => state.transcriptsTableState.columnFilters
  );
  const setTranscriptsTableState = useStore(
    (state) => state.setTranscriptsTableState
  );

  const handleFilterChange = useCallback(
    (columnId: string, condition: import("../../query/types").SimpleCondition | null) => {
      setTranscriptsTableState((prevState) => {
        const newFilters = { ...prevState.columnFilters };
        if (condition === null) {
          delete newFilters[columnId];
        } else {
          const existingFilter = newFilters[columnId];
          if (existingFilter) {
            newFilters[columnId] = {
              ...existingFilter,
              condition,
            };
          }
        }
        return {
          ...prevState,
          columnFilters: newFilters,
        };
      });
    },
    [setTranscriptsTableState]
  );

  const removeFilter = useCallback(
    (column: string) => {
      setTranscriptsTableState((prevState) => {
        const newFilters = { ...prevState.columnFilters };
        delete newFilters[column];
        return {
          ...prevState,
          columnFilters: newFilters,
        };
      });
    },
    [setTranscriptsTableState]
  );

  // Add filter handler - also ensures the filtered column is visible
  const handleAddFilter = useCallback(
    (filter: ColumnFilter) => {
      setTranscriptsTableState((prevState) => {
        const columnKey = filter.columnId as keyof TranscriptInfo;

        // Use default visible columns if not set in state
        const currentVisibleColumns =
          prevState.visibleColumns ?? DEFAULT_VISIBLE_COLUMNS;

        // Check if we need to add this column to visible columns
        const needsColumnVisible = !currentVisibleColumns.includes(columnKey);

        // Check if we need to add this column to column order
        const needsColumnOrder =
          prevState.columnOrder.length > 0 &&
          !prevState.columnOrder.includes(columnKey);

        return {
          ...prevState,
          columnFilters: {
            ...prevState.columnFilters,
            [filter.columnId]: filter,
          },
          // Add the column to visible columns if it's not already there
          ...(needsColumnVisible && {
            visibleColumns: [...currentVisibleColumns, columnKey],
          }),
          // Add the column to column order if it's not already there
          ...(needsColumnOrder && {
            columnOrder: [...prevState.columnOrder, columnKey],
          }),
        };
      });
    },
    [setTranscriptsTableState]
  );

  // Add filter popover
  const addFilterChipRef = useRef<HTMLDivElement | null>(null);
  const {
    isOpen: isAddFilterOpen,
    setIsOpen: setIsAddFilterOpen,
    selectedColumnId: addFilterColumnId,
    availableColumns,
    filterType: addFilterType,
    operator: addFilterOperator,
    setOperator: setAddFilterOperator,
    operatorOptions: addFilterOperatorOptions,
    value: addFilterValue,
    setValue: setAddFilterValue,
    value2: addFilterValue2,
    setValue2: setAddFilterValue2,
    isValueDisabled: isAddFilterValueDisabled,
    isRangeOperator: isAddFilterRangeOperator,
    commitAndClose: commitAddFilterAndClose,
    cancelAndClose: cancelAddFilterAndClose,
    handleColumnChange: handleAddFilterColumnChange,
  } = useAddFilterPopover({
    filters,
    onAddFilter: handleAddFilter,
    onFilterColumnChange,
  });

  // Column picker state
  const columnButtonRef = useRef<HTMLButtonElement>(null);
  const [showColumnPicker, setShowColumnPicker] = useState(false);

  // Add filter chip slot
  const addFilterSlot = (
    <>
      <Chip
        ref={addFilterChipRef}
        icon={ApplicationIcons.add}
        value="Add"
        title="Add a new filter"
        className={clsx(styles.filterChip, "text-size-smallest")}
        onClick={() => setIsAddFilterOpen(true)}
      />
      {/* Add filter popover */}
      <PopOver
        id="transcript-add-filter-editor"
        isOpen={isAddFilterOpen}
        setIsOpen={setIsAddFilterOpen}
        positionEl={addFilterChipRef.current}
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
          columnId={addFilterColumnId ?? ""}
          filterType={addFilterType}
          operator={addFilterOperator}
          operatorOptions={addFilterOperatorOptions}
          rawValue={addFilterValue}
          rawValue2={addFilterValue2}
          isValueDisabled={isAddFilterValueDisabled}
          isRangeOperator={isAddFilterRangeOperator}
          onOperatorChange={setAddFilterOperator}
          onValueChange={setAddFilterValue}
          onValue2Change={setAddFilterValue2}
          onCommit={commitAddFilterAndClose}
          onCancel={cancelAddFilterAndClose}
          suggestions={filterSuggestions}
          availableColumns={availableColumns}
          onColumnChange={handleAddFilterColumnChange}
        />
      </PopOver>
    </>
  );

  // Column picker content
  const columnPickerContent = includeColumnPicker ? (
    <>
      <TranscriptColumnsButton
        ref={columnButtonRef}
        isOpen={showColumnPicker}
        onClick={() => setShowColumnPicker(!showColumnPicker)}
      />
      <TranscriptColumnsPopover
        positionEl={columnButtonRef.current}
        isOpen={showColumnPicker}
        setIsOpen={setShowColumnPicker}
      />
    </>
  ) : undefined;

  return (
    <FilterBar
      filters={filters}
      onFilterChange={handleFilterChange}
      onRemoveFilter={removeFilter}
      filterCodeValues={filterCodeValues}
      filterSuggestions={filterSuggestions}
      onFilterColumnChange={onFilterColumnChange}
      popoverIdPrefix="transcript-filter"
      addFilterSlot={addFilterSlot}
      rightContent={columnPickerContent}
    />
  );
};
