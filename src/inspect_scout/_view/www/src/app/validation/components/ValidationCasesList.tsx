import { VscodeCheckbox } from "@vscode-elements/react-elements";
import { FC, useMemo } from "react";

import { useStore } from "../../../state/store";
import { ValidationCase } from "../../../types/api-types";
import { useTranscriptsByIds } from "../hooks/useTranscriptsByIds";
import { extractUniqueSplits, getCaseKey, getIdText } from "../utils";

import { ValidationBulkActions } from "./ValidationBulkActions";
import { ValidationCaseCard } from "./ValidationCaseCard";
import styles from "./ValidationCasesList.module.css";
import { ValidationFilterBar } from "./ValidationFilterBar";

interface ValidationCasesListProps {
  cases: ValidationCase[];
  transcriptsDir: string | undefined;
  onBulkSplitChange?: (ids: string[], split: string | null) => void;
  onBulkDelete?: (ids: string[]) => void;
  onSingleSplitChange?: (caseId: string, split: string | null) => void;
  onSingleDelete?: (caseId: string) => void;
  isUpdating?: boolean;
  isDeleting?: boolean;
}

/**
 * List component for displaying and managing validation cases.
 * Includes filtering, selection, and individual case cards.
 */
export const ValidationCasesList: FC<ValidationCasesListProps> = ({
  cases,
  transcriptsDir,
  onBulkSplitChange,
  onBulkDelete,
  onSingleSplitChange,
  onSingleDelete,
  isUpdating,
  isDeleting,
}) => {
  // State from store
  const selection = useStore((state) => state.validationCaseSelection);
  const setSelection = useStore((state) => state.setValidationCaseSelection);
  const toggleSelection = useStore(
    (state) => state.toggleValidationCaseSelection
  );
  const splitFilter = useStore((state) => state.validationSplitFilter);
  const setSplitFilter = useStore((state) => state.setValidationSplitFilter);
  const searchText = useStore((state) => state.validationSearchText);
  const setSearchText = useStore((state) => state.setValidationSearchText);

  // Extract all transcript IDs from cases (use first ID for composite IDs)
  const transcriptIds = useMemo(() => {
    return cases
      .map((c) => (Array.isArray(c.id) ? c.id[0] : c.id))
      .filter((id): id is string => id !== undefined);
  }, [cases]);

  // Extract unique splits from all cases
  const existingSplits = useMemo(() => extractUniqueSplits(cases), [cases]);

  // Fetch transcript data for all cases
  const { data: transcriptMap, loading: transcriptsLoading } =
    useTranscriptsByIds(transcriptsDir, transcriptIds);

  // Filter cases based on split, search, and transcript availability
  const filteredCases = useMemo(() => {
    return cases.filter((c) => {
      // Split filter
      if (splitFilter && c.split !== splitFilter) {
        return false;
      }
      // Search filter (case-insensitive ID search)
      if (searchText) {
        const idText = getIdText(c.id).toLowerCase();
        if (!idText.includes(searchText.toLowerCase())) {
          return false;
        }
      }
      // Filter out cases without transcript data (once loaded)
      if (transcriptMap) {
        const transcriptId = Array.isArray(c.id) ? c.id[0] : c.id;
        if (!transcriptId || !transcriptMap.has(transcriptId)) {
          return false;
        }
      }
      return true;
    });
  }, [cases, splitFilter, searchText, transcriptMap]);

  // Get filtered case keys for select all logic
  const filteredCaseKeys = useMemo(() => {
    return filteredCases.map((c) => getCaseKey(c.id));
  }, [filteredCases]);

  // Get selected IDs
  const selectedIds = useMemo(() => {
    return Object.entries(selection)
      .filter(([, selected]) => selected)
      .map(([id]) => id);
  }, [selection]);

  // Check if all filtered cases are selected
  const allSelected =
    filteredCaseKeys.length > 0 &&
    filteredCaseKeys.every((key) => selection[key]);

  // Check if some (but not all) filtered cases are selected
  const someSelected =
    filteredCaseKeys.some((key) => selection[key]) && !allSelected;

  // Handle select all / deselect all
  const handleSelectAllChange = () => {
    if (allSelected) {
      // Deselect all filtered cases
      const newSelection = { ...selection };
      filteredCaseKeys.forEach((key) => {
        delete newSelection[key];
      });
      setSelection(newSelection);
    } else {
      // Select all filtered cases
      const newSelection = { ...selection };
      filteredCaseKeys.forEach((key) => {
        newSelection[key] = true;
      });
      setSelection(newSelection);
    }
  };

  // Handle bulk split change - clear selection after
  const handleBulkSplitChange = (ids: string[], split: string | null) => {
    onBulkSplitChange?.(ids, split);
    setSelection({});
  };

  // Handle bulk delete - clear selection after
  const handleBulkDelete = (ids: string[]) => {
    onBulkDelete?.(ids);
    setSelection({});
  };

  return (
    <div className={styles.container}>
      {/* Filter bar */}
      <ValidationFilterBar
        cases={cases}
        splitFilter={splitFilter}
        onSplitFilterChange={setSplitFilter}
        searchText={searchText}
        onSearchTextChange={setSearchText}
      />

      {/* Bulk actions (shown when items selected) */}
      {selectedIds.length > 0 && onBulkSplitChange && onBulkDelete && (
        <ValidationBulkActions
          cases={cases}
          selectedIds={selectedIds}
          onBulkSplitChange={handleBulkSplitChange}
          onBulkDelete={handleBulkDelete}
          isUpdating={isUpdating}
          isDeleting={isDeleting}
        />
      )}

      {/* Grid container with sticky header */}
      <div className={styles.gridContainer}>
        {/* Header row */}
        <div className={styles.header}>
          <div className={styles.headerCheckbox}>
            <VscodeCheckbox
              checked={allSelected}
              indeterminate={someSelected}
              onChange={handleSelectAllChange}
              title={allSelected ? "Deselect all" : "Select all"}
            />
          </div>
          <div className={styles.headerTranscript}>Transcript</div>
          <div className={styles.headerTarget}>Target</div>
          <div className={styles.headerSplit}>Split</div>
          <div className={styles.headerActions}>Actions</div>
        </div>

        {/* Scrollable list */}
        <div className={styles.list}>
          {transcriptsLoading ? (
            <div className={styles.emptyState}>
              Loading transcript details...
            </div>
          ) : filteredCases.length === 0 ? (
            <div className={styles.emptyState}>
              {cases.length === 0
                ? "No validation cases in this set."
                : "No cases match the current filters."}
            </div>
          ) : (
            filteredCases.map((c) => {
              const caseKey = getCaseKey(c.id);
              const transcriptId = Array.isArray(c.id) ? c.id[0] : c.id;
              const transcript = transcriptId
                ? transcriptMap?.get(transcriptId)
                : undefined;
              return (
                <ValidationCaseCard
                  key={caseKey}
                  validationCase={c}
                  transcript={transcript}
                  transcriptsDir={transcriptsDir}
                  isSelected={selection[caseKey] ?? false}
                  onSelectionChange={() => toggleSelection(caseKey)}
                  existingSplits={existingSplits}
                  onSplitChange={
                    onSingleSplitChange
                      ? (split) => onSingleSplitChange(caseKey, split)
                      : undefined
                  }
                  onDelete={
                    onSingleDelete ? () => onSingleDelete(caseKey) : undefined
                  }
                  isUpdating={isUpdating}
                  isDeleting={isDeleting}
                />
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
