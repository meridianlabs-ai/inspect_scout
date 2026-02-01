import { FC, useCallback } from "react";

import { ScalarValue } from "../../api/api";
import { ScansTableState, useStore } from "../../state/store";
import { AddFilterButton } from "../components/AddFilterButton";
import { ColumnPickerButton } from "../components/ColumnPickerButton";
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

  // Add filter popover state
  const addFilterPopover = useAddFilterPopover({
    filters,
    onAddFilter: handleAddFilter,
    onFilterColumnChange,
  });

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

  return (
    <FilterBar
      filters={filters}
      onFilterChange={handleFilterChange}
      onRemoveFilter={removeFilter}
      filterSuggestions={filterSuggestions}
      onFilterColumnChange={onFilterColumnChange}
      popoverIdPrefix="scans-filter"
      addFilterSlot={
        <AddFilterButton
          idPrefix="scans"
          popoverState={addFilterPopover}
          suggestions={filterSuggestions}
        />
      }
      rightContent={
        includeColumnPicker ? (
          <ColumnPickerButton>
            {({ positionEl, isOpen, setIsOpen }) => (
              <ColumnsPopover
                positionEl={positionEl}
                isOpen={isOpen}
                setIsOpen={setIsOpen}
                columns={COLUMNS_INFO}
                visibleColumns={visibleColumns ?? DEFAULT_VISIBLE_COLUMNS}
                defaultVisibleColumns={DEFAULT_VISIBLE_COLUMNS}
                onVisibleColumnsChange={handleVisibleColumnsChange}
                popoverId="scans-columns"
              />
            )}
          </ColumnPickerButton>
        ) : undefined
      }
    />
  );
};
