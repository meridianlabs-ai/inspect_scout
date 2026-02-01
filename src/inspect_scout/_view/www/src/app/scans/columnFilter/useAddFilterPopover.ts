import type { ColumnFilter } from "../../../state/store";
import {
  useAddFilterPopover as useAddFilterPopoverBase,
  type AvailableColumn,
} from "../../components/columnFilter";
import {
  ALL_COLUMNS,
  COLUMN_LABELS,
  DEFAULT_COLUMN_ORDER,
  ScanColumnKey,
} from "../columns";

interface UseScanAddFilterPopoverParams {
  filters: Record<string, ColumnFilter>;
  onAddFilter: (filter: ColumnFilter) => void;
  onFilterColumnChange?: (columnId: string | null) => void;
}

// Static list of columns for filtering - computed once
const COLUMNS: AvailableColumn[] = DEFAULT_COLUMN_ORDER.map(
  (columnId: ScanColumnKey) => ({
    id: columnId,
    label: COLUMN_LABELS[columnId],
    filterType: ALL_COLUMNS[columnId].meta?.filterType ?? "string",
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
    columns: COLUMNS,
    filters,
    onAddFilter,
    onFilterColumnChange,
  });
}
