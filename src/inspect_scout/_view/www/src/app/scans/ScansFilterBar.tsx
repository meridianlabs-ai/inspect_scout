import { clsx } from "clsx";
import { FC, useCallback, useRef, useState } from "react";

import { ApplicationIcons } from "../../components/icons";
import { PopOver } from "../../components/PopOver";
import { ColumnFilter, useStore } from "../../state/store";
import type { SimpleCondition } from "../../query/types";
import { Chip } from "../components/Chip";
import { FilterBar } from "../components/FilterBar";
import { ColumnFilterEditor } from "../components/columnFilter";
import { ColumnsButton } from "../components/ColumnsButton";
import { ColumnsPopover, ColumnInfo } from "../components/ColumnsPopover";

import {
  COLUMN_LABELS,
  COLUMN_HEADER_TITLES,
  DEFAULT_COLUMN_ORDER,
  DEFAULT_VISIBLE_COLUMNS,
  ScanColumnKey,
} from "./columns";
import { useAddFilterPopover } from "./columnFilter";
import styles from "./ScansFilterBar.module.css";

// Convert column definitions to ColumnInfo array
const COLUMNS_INFO: ColumnInfo[] = DEFAULT_COLUMN_ORDER.map((key) => ({
  id: key,
  label: COLUMN_LABELS[key],
  headerTitle: COLUMN_HEADER_TITLES[key],
}));

export const ScansFilterBar: FC<{
  includeColumnPicker?: boolean;
}> = ({ includeColumnPicker = true }) => {
  // Scans Filter State
  const filters = useStore((state) => state.scansTableState.columnFilters);
  const visibleColumns = useStore(
    (state) => state.scansTableState.visibleColumns
  );
  const setScansTableState = useStore((state) => state.setScansTableState);

  const handleFilterChange = useCallback(
    (columnId: string, condition: SimpleCondition | null) => {
      setScansTableState((prevState) => {
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
    [setScansTableState]
  );

  const removeFilter = useCallback(
    (column: string) => {
      setScansTableState((prevState) => {
        const newFilters = { ...prevState.columnFilters };
        delete newFilters[column];
        return {
          ...prevState,
          columnFilters: newFilters,
        };
      });
    },
    [setScansTableState]
  );

  // Add filter handler - also ensures the filtered column is visible
  const handleAddFilter = useCallback(
    (filter: ColumnFilter) => {
      setScansTableState((prevState) => {
        const columnKey = filter.columnId as ScanColumnKey;

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
    [setScansTableState]
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
  });

  // Column picker state
  const columnButtonRef = useRef<HTMLButtonElement>(null);
  const [showColumnPicker, setShowColumnPicker] = useState(false);

  // Handle visible columns change
  const handleVisibleColumnsChange = useCallback(
    (newVisibleColumns: string[]) => {
      setScansTableState((prevState) => ({
        ...prevState,
        visibleColumns: newVisibleColumns as ScanColumnKey[],
      }));
    },
    [setScansTableState]
  );

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
        id="scans-add-filter-editor"
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
          availableColumns={availableColumns}
          onColumnChange={handleAddFilterColumnChange}
        />
      </PopOver>
    </>
  );

  // Column picker content
  const columnPickerContent = includeColumnPicker ? (
    <>
      <ColumnsButton
        ref={columnButtonRef}
        isOpen={showColumnPicker}
        onClick={() => setShowColumnPicker(!showColumnPicker)}
      />
      <ColumnsPopover
        positionEl={columnButtonRef.current}
        isOpen={showColumnPicker}
        setIsOpen={setShowColumnPicker}
        columns={COLUMNS_INFO}
        visibleColumns={visibleColumns ?? DEFAULT_VISIBLE_COLUMNS}
        defaultVisibleColumns={DEFAULT_VISIBLE_COLUMNS}
        onVisibleColumnsChange={handleVisibleColumnsChange}
        popoverId="scans-columns"
      />
    </>
  ) : undefined;

  return (
    <FilterBar
      filters={filters}
      onFilterChange={handleFilterChange}
      onRemoveFilter={removeFilter}
      popoverIdPrefix="scans-filter"
      addFilterSlot={addFilterSlot}
      rightContent={columnPickerContent}
    />
  );
};
