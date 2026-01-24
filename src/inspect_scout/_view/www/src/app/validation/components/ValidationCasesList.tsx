import {
  VscodeButton,
  VscodeCheckbox,
} from "@vscode-elements/react-elements";
import { FC, useMemo, useState } from "react";

import { Modal } from "../../../components/Modal";
import { useStore } from "../../../state/store";
import { ValidationCase } from "../../../types/api-types";
import { useTranscriptsByIds } from "../hooks/useTranscriptsByIds";
import { extractUniqueSplits, getCaseKey, getIdText } from "../utils";

import { ValidationCaseCard } from "./ValidationCaseCard";
import styles from "./ValidationCasesList.module.css";
import { ValidationSplitSelector } from "./ValidationSplitSelector";

interface ValidationCasesListProps {
  cases: ValidationCase[];
  transcriptsDir: string | undefined;
  validationSetUri?: string;
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
  validationSetUri,
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
  const searchText = useStore((state) => state.validationSearchText);

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

  // Filter and sort cases based on split, search, and transcript availability
  const filteredCases = useMemo(() => {
    const filtered = cases.filter((c) => {
      // Split filter
      if (splitFilter && c.split !== splitFilter) {
        return false;
      }

      // Filter out cases without transcript data (once loaded)
      if (transcriptMap) {
        const transcriptId = Array.isArray(c.id) ? c.id[0] : c.id;
        if (!transcriptId || !transcriptMap.has(transcriptId)) {
          return false;
        }
      }

      // Search filter (search across multiple fields)
      if (searchText) {
        const search = searchText.toLowerCase();
        const transcriptId = Array.isArray(c.id) ? c.id[0] : c.id;
        const transcript = transcriptId
          ? transcriptMap?.get(transcriptId)
          : undefined;

        // Check ID
        const idText = getIdText(c.id).toLowerCase();
        if (idText.includes(search)) return true;

        // Check transcript details if available
        if (transcript) {
          if (transcript.task_set?.toLowerCase().includes(search)) return true;
          if (transcript.task_id?.toLowerCase().includes(search)) return true;
          if (transcript.model?.toLowerCase().includes(search)) return true;
          if (transcript.agent?.toLowerCase().includes(search)) return true;
        }

        return false;
      }

      return true;
    });

    // Sort by split: no split first, then alphabetically by split name
    return filtered.sort((a, b) => {
      const splitA = a.split;
      const splitB = b.split;

      // No split comes first
      if (!splitA && splitB) return -1;
      if (splitA && !splitB) return 1;
      if (!splitA && !splitB) return 0;

      // Both have splits - sort alphabetically
      return splitA!.localeCompare(splitB!);
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

  // Bulk action modal state
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showSplitModal, setShowSplitModal] = useState(false);
  const [bulkSplitValue, setBulkSplitValue] = useState<string | null>(null);

  const handleAssignSplit = () => {
    handleBulkSplitChange(selectedIds, bulkSplitValue);
    setShowSplitModal(false);
    setBulkSplitValue(null);
  };

  const handleConfirmDelete = () => {
    handleBulkDelete(selectedIds);
    setShowDeleteModal(false);
  };

  const hasSelection = selectedIds.length > 0;
  const hasBulkActions = onBulkSplitChange && onBulkDelete;

  return (
    <div className={styles.container}>
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
          <div className={styles.headerTranscript}>
            <span>Transcript</span>
            {/* Bulk actions inline */}
            {hasSelection && hasBulkActions && (
              <span className={styles.bulkActions}>
                <span className={styles.selectedCount}>
                  {selectedIds.length} selected
                </span>
                <VscodeButton
                  secondary
                  onClick={() => setShowSplitModal(true)}
                  disabled={isUpdating || isDeleting}
                  className={styles.bulkButton}
                >
                  Assign Split
                </VscodeButton>
                <VscodeButton
                  secondary
                  onClick={() => setShowDeleteModal(true)}
                  disabled={isUpdating || isDeleting}
                  className={styles.bulkButton}
                >
                  Delete
                </VscodeButton>
              </span>
            )}
          </div>
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
                  validationSetUri={validationSetUri}
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

      {/* Split Assignment Modal */}
      <Modal
        show={showSplitModal}
        onHide={() => setShowSplitModal(false)}
        title="Assign Split"
        footer={
          <>
            <VscodeButton secondary onClick={() => setShowSplitModal(false)}>
              Cancel
            </VscodeButton>
            <VscodeButton onClick={handleAssignSplit} disabled={isUpdating}>
              {isUpdating ? "Assigning..." : "Assign"}
            </VscodeButton>
          </>
        }
      >
        <div className={styles.modalContent}>
          <p>
            Assign a split to {selectedIds.length} selected{" "}
            {selectedIds.length === 1 ? "case" : "cases"}.
          </p>

          <div className={styles.splitSelector}>
            <ValidationSplitSelector
              value={bulkSplitValue}
              existingSplits={existingSplits}
              onChange={setBulkSplitValue}
              noSplitLabel="Remove split"
            />
          </div>
        </div>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        show={showDeleteModal}
        onHide={() => setShowDeleteModal(false)}
        title="Confirm Delete"
        footer={
          <>
            <VscodeButton secondary onClick={() => setShowDeleteModal(false)}>
              Cancel
            </VscodeButton>
            <VscodeButton onClick={handleConfirmDelete} disabled={isDeleting}>
              {isDeleting ? "Deleting..." : "Delete"}
            </VscodeButton>
          </>
        }
      >
        <div className={styles.modalContent}>
          <p>
            Are you sure you want to delete {selectedIds.length}{" "}
            {selectedIds.length === 1 ? "case" : "cases"}?
          </p>
          <p className={styles.warning}>This action cannot be undone.</p>
        </div>
      </Modal>
    </div>
  );
};
