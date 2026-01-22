import { VscodeCheckbox } from "@vscode-elements/react-elements";
import { FC, useMemo } from "react";

import { useStore } from "../../../state/store";
import { ValidationCase } from "../../../types/api-types";
import { getCaseKey, getIdText } from "../utils";

import { ValidationBulkActions } from "./ValidationBulkActions";
import { ValidationCaseCard } from "./ValidationCaseCard";
import styles from "./ValidationCasesList.module.css";
import { ValidationFilterBar } from "./ValidationFilterBar";

interface ValidationCasesListProps {
  cases: ValidationCase[];
  transcriptsDir: string | undefined;
  onBulkSplitChange?: (ids: string[], split: string | null) => void;
  onBulkDelete?: (ids: string[]) => void;
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

  // Filter cases based on split and search
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
      return true;
    });
  }, [cases, splitFilter, searchText]);

  // Get selected IDs
  const selectedIds = useMemo(() => {
    return Object.entries(selection)
      .filter(([, selected]) => selected)
      .map(([id]) => id);
  }, [selection]);

  // Selection state
  const selectedCount = selectedIds.length;
  const allSelected =
    filteredCases.length > 0 &&
    filteredCases.every((c) => selection[getCaseKey(c.id)]);
  const someSelected = selectedCount > 0 && !allSelected;

  // Toggle all selection
  const handleSelectAll = () => {
    if (allSelected) {
      // Deselect all
      setSelection({});
    } else {
      // Select all filtered cases
      const newSelection: Record<string, boolean> = {};
      for (const c of filteredCases) {
        newSelection[getCaseKey(c.id)] = true;
      }
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

      {/* Selection header */}
      <div className={styles.selectionHeader}>
        <VscodeCheckbox
          checked={allSelected}
          indeterminate={someSelected}
          onChange={handleSelectAll}
        >
          {selectedCount > 0
            ? `${selectedCount} selected`
            : `${filteredCases.length} cases`}
        </VscodeCheckbox>
      </div>

      {/* Cases list */}
      <div className={styles.list}>
        {filteredCases.length === 0 ? (
          <div className={styles.emptyState}>
            {cases.length === 0
              ? "No validation cases in this set."
              : "No cases match the current filters."}
          </div>
        ) : (
          filteredCases.map((c) => {
            const caseKey = getCaseKey(c.id);
            return (
              <ValidationCaseCard
                key={caseKey}
                validationCase={c}
                transcriptsDir={transcriptsDir}
                isSelected={selection[caseKey] ?? false}
                onSelectionChange={() => toggleSelection(caseKey)}
              />
            );
          })
        )}
      </div>
    </div>
  );
};
