import type { ColumnFilter } from "../../../state/store";
import { TranscriptInfo } from "../../../types/api-types";
import {
  useAddFilterPopover as useAddFilterPopoverBase,
  type AvailableColumn,
} from "../../components/columnFilter";
import {
  COLUMN_LABELS,
  DEFAULT_COLUMN_ORDER,
  getFilterTypeForColumn,
} from "../columns";

interface UseTranscriptAddFilterPopoverParams {
  filters: Record<string, ColumnFilter>;
  onAddFilter: (filter: ColumnFilter) => void;
  onFilterColumnChange?: (columnId: string | null) => void;
}

// Static list of available columns - computed once
const AVAILABLE_COLUMNS: AvailableColumn[] = DEFAULT_COLUMN_ORDER.map(
  (columnId: keyof TranscriptInfo) => ({
    id: columnId,
    label: COLUMN_LABELS[columnId],
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
    availableColumns: AVAILABLE_COLUMNS,
    getFilterTypeForColumn,
    filters,
    onAddFilter,
    onFilterColumnChange,
  });
}
