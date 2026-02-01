import { clsx } from "clsx";
import { FC, useCallback, useRef, useState } from "react";

import { ScalarValue } from "../../api/api";
import { ApplicationIcons } from "../../components/icons";
import { PopOver } from "../../components/PopOver";
import { ToolButton } from "../../components/ToolButton";
import { ScansTableState, useStore } from "../../state/store";
import { Chip } from "../components/Chip";
import { ColumnFilterEditor } from "../components/columnFilter";
import { ColumnsPopover, ColumnInfo } from "../components/ColumnsPopover";
import { FilterBar } from "../components/FilterBar";
import { useFilterBarHandlers } from "../components/useFilterBarHandlers";

import { useAddFilterPopover } from "./columnFilter";
import {
  COLUMN_LABELS,
  COLUMN_HEADER_TITLES,
  DEFAULT_COLUMN_ORDER,
  DEFAULT_VISIBLE_COLUMNS,
  ScanColumnKey,
} from "./columns";
import styles from "./ScansFilterBar.module.css";

// Convert column definitions to ColumnInfo array
const COLUMNS_INFO: ColumnInfo[] = DEFAULT_COLUMN_ORDER.map((key) => ({
  id: key,
  label: COLUMN_LABELS[key],
  headerTitle: COLUMN_HEADER_TITLES[key],
}));

export const ScansFilterBar: FC<{
  includeColumnPicker?: boolean;
  filterSuggestions?: ScalarValue[];
  onFilterColumnChange?: (columnId: string | null) => void;
}> = ({
  includeColumnPicker = true,
  filterSuggestions = [],
  onFilterColumnChange,
}) => {
  // Scans Filter State
  const filters = useStore((state) => state.scansTableState.columnFilters);
  const visibleColumns = useStore(
    (state) => state.scansTableState.visibleColumns
  );
  const setScansTableState = useStore((state) => state.setScansTableState);

  // Use shared filter bar handlers
  const { handleFilterChange, removeFilter, handleAddFilter } =
    useFilterBarHandlers<ScanColumnKey, ScansTableState>({
      setTableState: setScansTableState,
      defaultVisibleColumns: DEFAULT_VISIBLE_COLUMNS,
    });

  // Add filter popover
  const addFilterChipRef = useRef<HTMLDivElement | null>(null);
  const {
    isOpen: isAddFilterOpen,
    setIsOpen: setIsAddFilterOpen,
    selectedColumnId: addFilterColumnId,
    columns,
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
          suggestions={filterSuggestions}
          columns={columns}
          onColumnChange={handleAddFilterColumnChange}
        />
      </PopOver>
    </>
  );

  // Column picker content
  const columnPickerContent = includeColumnPicker ? (
    <>
      <ToolButton
        ref={columnButtonRef}
        icon={ApplicationIcons.checkbox.checked}
        label="Choose columns"
        title="Choose columns"
        latched={showColumnPicker}
        onClick={() => setShowColumnPicker(!showColumnPicker)}
        subtle
        className={clsx("text-size-smallest", styles.columnsButton)}
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
      filterSuggestions={filterSuggestions}
      onFilterColumnChange={onFilterColumnChange}
      popoverIdPrefix="scans-filter"
      addFilterSlot={addFilterSlot}
      rightContent={columnPickerContent}
    />
  );
};
