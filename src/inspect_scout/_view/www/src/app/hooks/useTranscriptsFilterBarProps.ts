import { skipToken } from "@tanstack/react-query";
import { useCallback, useState } from "react";

import { ScalarValue } from "../../api/api";
import { Condition } from "../../query/types";
import { useCode } from "../server/useCode";
import { useTranscriptsColumnValues } from "../server/useTranscriptsColumnValues";

import { useFilterConditions } from "./useFilterConditions";

interface TranscriptsFilterBarProps {
  /** Code representations of current filters (Python, SQL). */
  filterCodeValues: Record<string, string> | undefined;
  /** Autocomplete suggestions for the currently edited column. */
  filterSuggestions: ScalarValue[];
  /** Callback when filter column selection changes. */
  onFilterColumnChange: (columnId: string | null) => void;
  /** Combined filter condition from all column filters. */
  condition: Condition | undefined;
}

/**
 * Hook providing all props needed for TranscriptFilterBar.
 * Manages filter editing state, code generation, and autocomplete suggestions.
 */
export const useTranscriptsFilterBarProps = (
  transcriptsDir: string | undefined
): TranscriptsFilterBarProps => {
  const [editingColumnId, setEditingColumnId] = useState<string | null>(null);

  const condition = useFilterConditions();
  const otherColumnsFilter = useFilterConditions(editingColumnId ?? undefined);

  const { data: filterCodeValues } = useCode(condition ?? skipToken);

  const { data: filterSuggestions } = useTranscriptsColumnValues(
    editingColumnId && transcriptsDir
      ? {
          location: transcriptsDir,
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
    filterCodeValues,
    filterSuggestions: filterSuggestions ?? [],
    onFilterColumnChange,
    condition,
  };
};
