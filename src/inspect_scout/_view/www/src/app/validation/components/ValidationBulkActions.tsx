import {
  VscodeButton,
  VscodeOption,
  VscodeSingleSelect,
  VscodeTextfield,
} from "@vscode-elements/react-elements";
import { FC, useMemo, useState } from "react";

import { Modal } from "../../../components/Modal";
import { ValidationCase } from "../../../types/api-types";
import { extractUniqueSplits } from "../utils";

import styles from "./ValidationBulkActions.module.css";

interface ValidationBulkActionsProps {
  cases: ValidationCase[];
  selectedIds: string[];
  onBulkSplitChange: (ids: string[], split: string | null) => void;
  onBulkDelete: (ids: string[]) => void;
  isUpdating?: boolean;
  isDeleting?: boolean;
}

/**
 * Bulk actions for selected validation cases.
 * Includes split assignment and delete functionality.
 */
export const ValidationBulkActions: FC<ValidationBulkActionsProps> = ({
  cases,
  selectedIds,
  onBulkSplitChange,
  onBulkDelete,
  isUpdating,
  isDeleting,
}) => {
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showSplitModal, setShowSplitModal] = useState(false);
  const [selectedSplit, setSelectedSplit] = useState<string>("");
  const [customSplit, setCustomSplit] = useState("");
  const [useCustomSplit, setUseCustomSplit] = useState(false);

  // Extract unique splits from cases
  const existingSplits = useMemo(() => extractUniqueSplits(cases), [cases]);

  const selectedCount = selectedIds.length;

  const handleSplitChange = (e: Event) => {
    const value = (e.target as HTMLSelectElement).value;
    if (value === "__custom__") {
      setUseCustomSplit(true);
      setSelectedSplit("");
    } else {
      setUseCustomSplit(false);
      setSelectedSplit(value);
      setCustomSplit("");
    }
  };

  const handleCustomSplitInput = (e: Event) => {
    const value = (e.target as HTMLInputElement).value;
    setCustomSplit(value);
  };

  const handleAssignSplit = () => {
    const split = useCustomSplit ? customSplit : selectedSplit;
    onBulkSplitChange(selectedIds, split || null);
    setShowSplitModal(false);
    setSelectedSplit("");
    setCustomSplit("");
    setUseCustomSplit(false);
  };

  const handleDelete = () => {
    onBulkDelete(selectedIds);
    setShowDeleteModal(false);
  };

  if (selectedCount === 0) {
    return null;
  }

  return (
    <div className={styles.container}>
      <span className={styles.selectedCount}>{selectedCount} selected</span>

      <VscodeButton
        secondary
        onClick={() => setShowSplitModal(true)}
        disabled={isUpdating || isDeleting}
      >
        Assign Split
      </VscodeButton>

      <VscodeButton
        secondary
        onClick={() => setShowDeleteModal(true)}
        disabled={isUpdating || isDeleting}
      >
        Delete
      </VscodeButton>

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
            <VscodeButton
              onClick={handleAssignSplit}
              disabled={isUpdating || (useCustomSplit && !customSplit)}
            >
              {isUpdating ? "Assigning..." : "Assign"}
            </VscodeButton>
          </>
        }
      >
        <div className={styles.modalContent}>
          <p>
            Assign a split to {selectedCount} selected{" "}
            {selectedCount === 1 ? "case" : "cases"}.
          </p>

          <div className={styles.splitSelector}>
            <VscodeSingleSelect
              value={useCustomSplit ? "__custom__" : selectedSplit}
              onChange={handleSplitChange}
            >
              <VscodeOption value="">Remove split</VscodeOption>
              {existingSplits.map((split) => (
                <VscodeOption key={split} value={split}>
                  {split}
                </VscodeOption>
              ))}
              <VscodeOption value="__custom__">Custom...</VscodeOption>
            </VscodeSingleSelect>

            {useCustomSplit && (
              <VscodeTextfield
                value={customSplit}
                onInput={handleCustomSplitInput}
                placeholder="Enter custom split name"
                className={styles.customInput}
                data-autofocus
              />
            )}
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
            <VscodeButton onClick={handleDelete} disabled={isDeleting}>
              {isDeleting ? "Deleting..." : "Delete"}
            </VscodeButton>
          </>
        }
      >
        <div className={styles.modalContent}>
          <p>
            Are you sure you want to delete {selectedCount}{" "}
            {selectedCount === 1 ? "case" : "cases"}?
          </p>
          <p className={styles.warning}>This action cannot be undone.</p>
        </div>
      </Modal>
    </div>
  );
};
