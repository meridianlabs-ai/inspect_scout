import type { ColumnFilter } from "../../../state/store";
import { TranscriptInfo } from "../../../types/api-types";
import {
  useAddFilterPopover as useAddFilterPopoverBase,
  type AvailableColumn,
} from "../../components/columnFilter";
import { ALL_COLUMNS, COLUMN_LABELS, DEFAULT_COLUMN_ORDER } from "../columns";

interface UseTranscriptAddFilterPopoverParams {
  filters: Record<string, ColumnFilter>;
  onAddFilter: (filter: ColumnFilter) => void;
  onFilterColumnChange?: (columnId: string | null) => void;
}

// Static list of columns for filtering - computed once
const COLUMNS: AvailableColumn[] = DEFAULT_COLUMN_ORDER.map(
  (columnId: keyof TranscriptInfo) => ({
    id: columnId,
    label: COLUMN_LABELS[columnId],
    filterType: ALL_COLUMNS[columnId].meta?.filterType ?? "string",
  })
);

/**
 * Transcript-specific hook for the "Add Filter" popover.
 * Pre-configures useAddFilterPopover with transcript column definitions.
 */
export function useAddFilterPopover({
  filters,
  onAddFilter,
  onFilterColumnChange,
}: UseTranscriptAddFilterPopoverParams) {
  return useAddFilterPopoverBase({
    columns: COLUMNS,
    filters,
    onAddFilter,
    onFilterColumnChange,
  });
}
