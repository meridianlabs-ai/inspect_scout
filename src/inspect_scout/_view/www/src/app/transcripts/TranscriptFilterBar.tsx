import { clsx } from "clsx";
import { FC, useRef, useState } from "react";

import { ScalarValue } from "../../api/api";
import { ApplicationIcons } from "../../components/icons";
import { PopOver } from "../../components/PopOver";
import { TranscriptsTableState, useStore } from "../../state/store";
import type { TranscriptInfo } from "../../types/api-types";
import { Chip } from "../components/Chip";
import { ColumnFilterEditor } from "../components/columnFilter";
import { FilterBar } from "../components/FilterBar";
import { useFilterBarHandlers } from "../components/useFilterBarHandlers";

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

  // Use shared filter bar handlers
  const { handleFilterChange, removeFilter, handleAddFilter } =
    useFilterBarHandlers<keyof TranscriptInfo, TranscriptsTableState>({
      setTableState: setTranscriptsTableState,
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
          columns={columns}
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
      filterCodeValues={filterCodeValues ?? {}}
      filterSuggestions={filterSuggestions}
      onFilterColumnChange={onFilterColumnChange}
      popoverIdPrefix="transcript-filter"
      addFilterSlot={addFilterSlot}
      rightContent={columnPickerContent}
    />
  );
};
