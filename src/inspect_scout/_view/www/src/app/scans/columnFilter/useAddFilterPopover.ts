import type { ColumnFilter } from "../../../state/store";
import {
  useAddFilterPopover as useAddFilterPopoverBase,
  type AvailableColumn,
} from "../../components/columnFilter";
import {
  COLUMN_LABELS,
  DEFAULT_COLUMN_ORDER,
  getFilterTypeForColumn,
  ScanColumnKey,
} from "../columns";

interface UseScanAddFilterPopoverParams {
  filters: Record<string, ColumnFilter>;
  onAddFilter: (filter: ColumnFilter) => void;
  onFilterColumnChange?: (columnId: string | null) => void;
}

// Static list of available columns - computed once
const AVAILABLE_COLUMNS: AvailableColumn[] = DEFAULT_COLUMN_ORDER.map(
  (columnId: ScanColumnKey) => ({
    id: columnId,
    label: COLUMN_LABELS[columnId],
  })
);

/**
 * Scans-specific hook for the "Add Filter" popover.
 * Pre-configures useAddFilterPopover with scan column definitions.
 */
export function useAddFilterPopover({
  filters,
  onAddFilter,
  onFilterColumnChange,
}: UseScanAddFilterPopoverParams) {
  return useAddFilterPopoverBase({
    availableColumns: AVAILABLE_COLUMNS,
    getFilterTypeForColumn,
    filters,
    onAddFilter,
    onFilterColumnChange,
  });
}
