import { FC, useCallback } from "react";

import { ScalarValue } from "../../api/api";
import { TranscriptsTableState, useStore } from "../../state/store";
import type { TranscriptInfo } from "../../types/api-types";
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
} from "./columns";

// Convert column definitions to ColumnInfo array
const COLUMNS_INFO: ColumnInfo[] = DEFAULT_COLUMN_ORDER.map((key) => ({
  id: key,
  label: COLUMN_LABELS[key],
  headerTitle: COLUMN_HEADER_TITLES[key],
}));

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
  const visibleColumns = useStore(
    (state) => state.transcriptsTableState.visibleColumns
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

  // Handle visible columns change
  const handleVisibleColumnsChange = useCallback(
    (newVisibleColumns: string[]) => {
      setTranscriptsTableState((prevState) => ({
        ...prevState,
        visibleColumns: newVisibleColumns as Array<keyof TranscriptInfo>,
      }));
    },
    [setTranscriptsTableState]
  );

  // Add filter popover state
  const addFilterPopover = useAddFilterPopover({
    filters,
    onAddFilter: handleAddFilter,
    onFilterColumnChange,
  });

  return (
    <FilterBar
      filters={filters}
      onFilterChange={handleFilterChange}
      onRemoveFilter={removeFilter}
      filterCodeValues={filterCodeValues ?? {}}
      filterSuggestions={filterSuggestions}
      onFilterColumnChange={onFilterColumnChange}
      popoverIdPrefix="transcript-filter"
      addFilterSlot={
        <AddFilterButton
          idPrefix="transcript"
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
                popoverId="transcript-columns"
              />
            )}
          </ColumnPickerButton>
        ) : undefined
      }
    />
  );
};
