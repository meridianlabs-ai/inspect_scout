import { FC } from "react";

import { ScalarValue } from "../../api/api";
import { TranscriptsTableState, useStore } from "../../state/store";
import type { TranscriptInfo } from "../../types/api-types";
import { AddFilterButton } from "../components/AddFilterButton";
import { ColumnPickerButton } from "../components/ColumnPickerButton";
import { FilterBar } from "../components/FilterBar";
import { useFilterBarHandlers } from "../components/useFilterBarHandlers";

import { useAddFilterPopover } from "./columnFilter";
import { DEFAULT_VISIBLE_COLUMNS } from "./columns";
import { TranscriptColumnsPopover } from "./TranscriptColumnsPopover";

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
              <TranscriptColumnsPopover
                positionEl={positionEl}
                isOpen={isOpen}
                setIsOpen={setIsOpen}
              />
            )}
          </ColumnPickerButton>
        ) : undefined
      }
    />
  );
};
