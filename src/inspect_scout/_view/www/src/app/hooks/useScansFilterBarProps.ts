import { skipToken } from "@tanstack/react-query";
import { useCallback, useState } from "react";

import { ScalarValue } from "../../api/api";
import { useScansColumnValues } from "../server/useScansColumnValues";

import { useScanFilterConditions } from "./useScanFilterConditions";

interface ScansFilterBarProps {
  /** Autocomplete suggestions for the currently edited column. */
  filterSuggestions: ScalarValue[];
  /** Callback when filter column selection changes. */
  onFilterColumnChange: (columnId: string | null) => void;
}

/**
 * Hook providing autocomplete props needed for ScansFilterBar.
 * Manages filter editing state and fetches autocomplete suggestions.
 */
export const useScansFilterBarProps = (
  scansDir: string | undefined
): ScansFilterBarProps => {
  const [editingColumnId, setEditingColumnId] = useState<string | null>(null);

  // Get filter condition excluding the currently editing column
  const otherColumnsFilter = useScanFilterConditions(
    editingColumnId ?? undefined
  );

  // Fetch autocomplete suggestions for editing column
  const { data: filterSuggestions } = useScansColumnValues(
    editingColumnId && scansDir
      ? {
          location: scansDir,
          column: editingColumnId,
          filter: otherColumnsFilter,
        }
      : skipToken
  );

  const onFilterColumnChange = useCallback(
    (columnId: string | null) => setEditingColumnId(columnId),
    []
  );

  return {
    filterSuggestions: filterSuggestions ?? [],
    onFilterColumnChange,
  };
};
