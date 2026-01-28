import { skipToken, useQueryClient } from "@tanstack/react-query";
import {
  VscodeButton,
  VscodeOption,
  VscodeSingleSelect,
  VscodeTextfield,
} from "@vscode-elements/react-elements";
import { FC, useCallback, useMemo, useState } from "react";

import { Modal } from "../../../components/Modal";
import { useApi } from "../../../state/store";
import { ValidationCase } from "../../../types/api-types";
import {
  useBulkDeleteValidationCases,
  useCreateValidationSet,
  useValidationCases,
  useValidationSets,
  validationQueryKeys,
} from "../../server/useValidations";
import {
  extractUniqueSplits,
  generateNewSetUri,
  getCaseKey,
  getFilenameFromUri,
  isValidFilename,
} from "../utils";

import styles from "./CopyMoveCasesModal.module.css";

/** Sentinel value meaning "keep each case's original split" */
const KEEP_ORIGINAL_SPLIT = "__keep__";

/** Sentinel value meaning "remove split (set to null)" */
const NO_SPLIT = "__none__";

interface CopyMoveCasesModalProps {
  /** Whether to show the modal */
  show: boolean;
  /** Copy or move mode */
  mode: "copy" | "move";
  /** Source validation set URI */
  sourceUri: string;
  /** Selected case IDs */
  selectedIds: string[];
  /** Full case data for selected cases */
  selectedCases: ValidationCase[];
  /** Callback when modal is closed */
  onHide: () => void;
  /** Callback on successful operation (used to clear selection) */
  onSuccess: () => void;
}

/**
 * Modal for copying or moving validation cases to another validation set.
 * Supports selecting an existing set or creating a new one.
 */
export const CopyMoveCasesModal: FC<CopyMoveCasesModalProps> = ({
  show,
  mode,
  sourceUri,
  selectedIds,
  selectedCases,
  onHide,
  onSuccess,
}) => {
  const api = useApi();
  const queryClient = useQueryClient();

  // Target selection state
  const [targetUri, setTargetUri] = useState<string | undefined>(undefined);
  // Default to keeping original splits
  const [targetSplit, setTargetSplit] = useState<string>(KEEP_ORIGINAL_SPLIT);

  // New set creation state
  const [showNewSetInput, setShowNewSetInput] = useState(false);
  const [newSetName, setNewSetName] = useState("");

  // Operation state
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch all validation sets
  const { data: validationSets } = useValidationSets();

  // Filter out the source set from available targets
  const availableTargets = useMemo(() => {
    return (validationSets ?? []).filter((uri) => uri !== sourceUri);
  }, [validationSets, sourceUri]);

  // Fetch target set's cases to extract splits
  const { data: targetCases } = useValidationCases(targetUri ?? skipToken);

  // Extract splits from target set
  const targetSplits = useMemo(() => {
    return extractUniqueSplits(targetCases ?? []);
  }, [targetCases]);

  // Mutations
  const createSetMutation = useCreateValidationSet();
  const deleteCasesMutation = useBulkDeleteValidationCases(sourceUri);

  // Reset state when modal opens/closes
  const handleHide = useCallback(() => {
    if (isProcessing) {
      return; // Don't allow closing during processing
    }
    setTargetUri(undefined);
    setTargetSplit(KEEP_ORIGINAL_SPLIT);
    setShowNewSetInput(false);
    setNewSetName("");
    setError(null);
    onHide();
  }, [onHide, isProcessing]);

  // Handle target set selection
  const handleTargetChange = (e: Event) => {
    const value = (e.target as HTMLSelectElement).value;
    if (value === "__new__") {
      setShowNewSetInput(true);
      setNewSetName("");
      setTargetUri(undefined);
    } else {
      setShowNewSetInput(false);
      setTargetUri(value || undefined);
    }
    setTargetSplit(KEEP_ORIGINAL_SPLIT); // Reset split when target changes
    setError(null);
  };

  // Handle new set name input
  const handleNewSetNameInput = (e: Event) => {
    setNewSetName((e.target as HTMLInputElement).value);
    setError(null);
  };

  // Handle split selection change
  const handleSplitChange = (e: Event) => {
    const value = (e.target as HTMLSelectElement).value;
    setTargetSplit(value);
  };

  // Create new validation set
  const handleCreateNewSet = async (): Promise<string | undefined> => {
    const trimmedName = newSetName.trim();

    // Validate filename
    const validation = isValidFilename(trimmedName);
    if (!validation.isValid) {
      setError(validation.error ?? "Invalid filename");
      return undefined;
    }

    const newUri = generateNewSetUri(sourceUri, trimmedName);

    // Check if this would be the same as source
    if (newUri === sourceUri) {
      setError("Cannot copy/move to the same validation set");
      return undefined;
    }

    // Check if a set with this name already exists
    if (validationSets?.includes(newUri)) {
      setError("A validation set with this name already exists");
      return undefined;
    }

    try {
      await createSetMutation.mutateAsync({ path: newUri, cases: [] });
      return newUri;
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to create validation set";
      setError(message);
      return undefined;
    }
  };

  // Get the split value to use for a case
  const getSplitForCase = (originalCase: ValidationCase): string | null => {
    if (targetSplit === KEEP_ORIGINAL_SPLIT) {
      return originalCase.split ?? null;
    }
    if (targetSplit === NO_SPLIT) {
      return null;
    }
    return targetSplit;
  };

  // Copy cases to target
  const copyCasesToTarget = async (destUri: string): Promise<boolean> => {
    const results = await Promise.allSettled(
      selectedCases.map((c) =>
        api.upsertValidationCase(destUri, getCaseKey(c.id), {
          id: c.id,
          target: c.target,
          labels: c.labels,
          split: getSplitForCase(c),
          predicate: c.predicate ?? undefined,
        })
      )
    );

    const succeeded = results.filter((r) => r.status === "fulfilled").length;
    const failed = results.filter((r) => r.status === "rejected").length;

    if (failed > 0 && succeeded === 0) {
      setError(`All ${failed} copy operations failed`);
      return false;
    }

    if (failed > 0) {
      // Partial success - show warning but continue
      setError(
        `Warning: ${failed} of ${selectedIds.length} cases failed to copy. ${succeeded} succeeded.`
      );
      // Still return true to proceed with move deletion if applicable
    }

    return true;
  };

  // Handle form submission
  const handleSubmit = async () => {
    setIsProcessing(true);
    setError(null);

    try {
      // Determine final target URI
      let finalTargetUri = targetUri;

      if (showNewSetInput) {
        finalTargetUri = await handleCreateNewSet();
        if (!finalTargetUri) {
          setIsProcessing(false);
          return;
        }
      }

      if (!finalTargetUri) {
        setError("Please select a target validation set");
        setIsProcessing(false);
        return;
      }

      // Copy cases to target
      const copySuccess = await copyCasesToTarget(finalTargetUri);
      if (!copySuccess) {
        setIsProcessing(false);
        return;
      }

      // Invalidate target set cache to show new cases
      void queryClient.invalidateQueries({
        queryKey: validationQueryKeys.cases(finalTargetUri),
      });

      // If move mode, delete from source
      if (mode === "move") {
        try {
          await deleteCasesMutation.mutateAsync(selectedIds);
        } catch (err) {
          // Cases were copied but deletion failed - inform user
          const message = err instanceof Error ? err.message : "Unknown error";
          setError(
            `Cases copied successfully, but failed to delete from source: ${message}`
          );
          setIsProcessing(false);
          return;
        }
      }

      // Success!
      onSuccess();
      handleHide();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Operation failed";
      setError(message);
    } finally {
      setIsProcessing(false);
    }
  };

  const title = mode === "copy" ? "Copy Cases" : "Move Cases";
  const actionLabel = mode === "copy" ? "Copy" : "Move";
  const processingLabel = mode === "copy" ? "Copying..." : "Moving...";

  const canSubmit =
    !isProcessing && (targetUri || (showNewSetInput && newSetName.trim()));

  return (
    <Modal
      show={show}
      onHide={handleHide}
      onSubmit={canSubmit ? () => void handleSubmit() : undefined}
      title={title}
      footer={
        <>
          <VscodeButton secondary onClick={handleHide} disabled={isProcessing}>
            Cancel
          </VscodeButton>
          <VscodeButton
            onClick={() => void handleSubmit()}
            disabled={!canSubmit}
          >
            {isProcessing ? processingLabel : actionLabel}
          </VscodeButton>
        </>
      }
    >
      <div className={styles.modalContent}>
        <p>
          {actionLabel} {selectedIds.length}{" "}
          {selectedIds.length === 1 ? "case" : "cases"} to another validation
          set.
        </p>

        {/* Target set selector */}
        <div className={styles.fieldGroup}>
          <label className={styles.label}>Target validation set:</label>
          <VscodeSingleSelect
            value={showNewSetInput ? "__new__" : (targetUri ?? "")}
            onChange={handleTargetChange}
            disabled={isProcessing}
            className={styles.select}
          >
            <VscodeOption value="">Select a validation set...</VscodeOption>
            {availableTargets.map((uri) => (
              <VscodeOption key={uri} value={uri}>
                {getFilenameFromUri(uri)}
              </VscodeOption>
            ))}
            <VscodeOption value="__new__">Create new set...</VscodeOption>
          </VscodeSingleSelect>
        </div>

        {/* New set name input */}
        {showNewSetInput && (
          <div className={styles.fieldGroup}>
            <label className={styles.label}>New set name:</label>
            <VscodeTextfield
              value={newSetName}
              onInput={handleNewSetNameInput}
              placeholder="Enter name (without extension)"
              disabled={isProcessing}
              data-autofocus
              className={styles.textInput}
            />
            <span className={styles.hint}>
              Will be created as {newSetName.trim() || "name"}.csv
            </span>
          </div>
        )}

        {/* Split selector for target */}
        {(targetUri || (showNewSetInput && newSetName.trim())) && (
          <div className={styles.fieldGroup}>
            <label className={styles.label}>Split assignment:</label>
            <VscodeSingleSelect
              value={targetSplit}
              onChange={handleSplitChange}
              disabled={isProcessing}
              className={styles.select}
            >
              <VscodeOption value={KEEP_ORIGINAL_SPLIT}>
                Keep original splits
              </VscodeOption>
              <VscodeOption value={NO_SPLIT}>No split</VscodeOption>
              {targetSplits.map((split) => (
                <VscodeOption key={split} value={split}>
                  {split}
                </VscodeOption>
              ))}
            </VscodeSingleSelect>
          </div>
        )}

        {/* Error message */}
        {error && <p className={styles.error}>{error}</p>}
      </div>
    </Modal>
  );
};
