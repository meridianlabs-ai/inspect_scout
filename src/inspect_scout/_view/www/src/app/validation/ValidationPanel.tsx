import { skipToken } from "@tanstack/react-query";
import {
  VscodeButton,
  VscodeOption,
  VscodeSingleSelect,
  VscodeTextfield,
} from "@vscode-elements/react-elements";
import {
  ChangeEvent,
  FC,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import { ApplicationIcons } from "../../components/icons";
import { Modal } from "../../components/Modal";
import { TextInput } from "../../components/TextInput";
import { useStore } from "../../state/store";
import { useConfig } from "../server/useConfig";
import {
  useBulkDeleteValidationCases,
  useDeleteValidationSet,
  useRenameValidationSet,
  useUpdateValidationCase,
  useValidationCases,
  useValidationSets,
} from "../server/useValidations";

import { ValidationCasesList } from "./components/ValidationCasesList";
import { ValidationSetSelector } from "./components/ValidationSetSelector";
import { ValidationSummary } from "./components/ValidationSummary";
import { extractUniqueSplits, getCaseKey, getFilenameFromUri } from "./utils";
import styles from "./ValidationPanel.module.css";

export const ValidationPanel: FC = () => {
  // Config for transcripts directory
  const config = useConfig();
  const transcriptsDir = config.transcripts?.dir ?? undefined;

  // State management
  const selectedUri = useStore((state) => state.selectedValidationSetUri);
  const setSelectedUri = useStore((state) => state.setSelectedValidationSetUri);
  const clearValidationState = useStore((state) => state.clearValidationState);
  const splitFilter = useStore((state) => state.validationSplitFilter);
  const setSplitFilter = useStore((state) => state.setValidationSplitFilter);
  const searchText = useStore((state) => state.validationSearchText);
  const setSearchText = useStore((state) => state.setValidationSearchText);

  // Modal state
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showRenameModal, setShowRenameModal] = useState(false);
  const [newName, setNewName] = useState("");

  // Data fetching
  const {
    data: validationSets,
    loading: setsLoading,
    error: setsError,
  } = useValidationSets();

  const {
    data: cases,
    loading: casesLoading,
    error: casesError,
  } = useValidationCases(selectedUri ?? skipToken);

  // Auto-select first validation set when loaded
  useEffect(() => {
    if (!selectedUri && validationSets && validationSets.length > 0) {
      setSelectedUri(validationSets[0]);
    }
  }, [selectedUri, validationSets, setSelectedUri]);

  // Mutations
  const updateMutation = useUpdateValidationCase(selectedUri ?? "");
  const deleteCasesMutation = useBulkDeleteValidationCases(selectedUri ?? "");
  const deleteSetMutation = useDeleteValidationSet();
  const renameSetMutation = useRenameValidationSet();

  const handleSelectSet = (uri: string | undefined) => {
    // Clear selection and filters when changing sets
    clearValidationState();
    setSelectedUri(uri);
  };

  const handleBulkSplitChange = useCallback(
    (ids: string[], split: string | null) => {
      if (!selectedUri || !cases) return;

      // Build case map at execution time to avoid stale closure
      const caseMap = new Map(cases.map((c) => [getCaseKey(c.id), c]));

      // Update all cases in parallel
      const updateCases = async () => {
        const results = await Promise.allSettled(
          ids.map((id) => {
            const existingCase = caseMap.get(id);
            if (!existingCase) return Promise.resolve();

            return updateMutation.mutateAsync({
              caseId: id,
              data: {
                ...existingCase,
                split: split,
              },
            });
          })
        );

        const failed = results.filter((r) => r.status === "rejected").length;
        if (failed > 0) {
          console.error(
            `Bulk split update: ${failed} of ${ids.length} updates failed`
          );
        }
      };
      void updateCases();
    },
    [selectedUri, cases, updateMutation]
  );

  const handleBulkDelete = useCallback(
    (ids: string[]) => {
      if (!selectedUri) return;
      deleteCasesMutation.mutate(ids);
    },
    [selectedUri, deleteCasesMutation]
  );

  // Handle single case split change
  const handleSingleSplitChange = useCallback(
    (caseId: string, split: string | null) => {
      if (!selectedUri || !cases) return;

      const caseMap = new Map(cases.map((c) => [getCaseKey(c.id), c]));
      const existingCase = caseMap.get(caseId);
      if (!existingCase) return;

      updateMutation.mutate({
        caseId,
        data: {
          ...existingCase,
          split: split,
        },
      });
    },
    [selectedUri, cases, updateMutation]
  );

  // Handle single case delete
  const handleSingleDelete = useCallback(
    (caseId: string) => {
      if (!selectedUri) return;
      deleteCasesMutation.mutate([caseId]);
    },
    [selectedUri, deleteCasesMutation]
  );

  // Delete validation set
  const handleDeleteSet = () => {
    if (!selectedUri) return;
    deleteSetMutation.mutate(selectedUri, {
      onSuccess: () => {
        setShowDeleteModal(false);
        clearValidationState();
        setSelectedUri(undefined);
      },
    });
  };

  // Rename validation set
  const handleOpenRename = () => {
    if (selectedUri) {
      // Get current filename without extension for editing
      const currentName = getFilenameFromUri(selectedUri, true);
      setNewName(currentName);
      setShowRenameModal(true);
    }
  };

  const handleRenameSet = () => {
    if (!selectedUri || !newName.trim()) return;
    renameSetMutation.mutate(
      { uri: selectedUri, newName: newName.trim() },
      {
        onSuccess: (newUri) => {
          setShowRenameModal(false);
          setNewName("");
          // Select the renamed set
          setSelectedUri(newUri);
        },
      }
    );
  };

  const handleNameInput = (e: Event) => {
    const value = (e.target as HTMLInputElement).value;
    setNewName(value);
  };

  const currentFilename = selectedUri ? getFilenameFromUri(selectedUri) : "";

  // Extract unique splits for filter dropdown
  const splits = useMemo(() => extractUniqueSplits(cases ?? []), [cases]);

  // Check for empty state (no validation sets available)
  const hasNoValidationSets =
    !setsLoading && !setsError && validationSets?.length === 0;

  if (hasNoValidationSets) {
    return (
      <div className={styles.container}>
        <div className={styles.noSetsState}>
          <span className={styles.noSetsTitle}>Validation</span>
        </div>
      </div>
    );
  }

  // Filter handlers
  const handleSplitFilterChange = (e: Event) => {
    const value = (e.target as HTMLSelectElement).value;
    setSplitFilter(value || undefined);
  };

  const handleSearchChange = (e: ChangeEvent<HTMLInputElement>) => {
    setSearchText(e.target.value || undefined);
  };

  return (
    <div className={styles.container}>
      {/* Header row: Title + Set Selector + Actions + Summary + Filter */}
      <div className={styles.headerRow}>
        <h2 className={styles.title}>Validation Set:</h2>

        {setsLoading ? (
          <div className={styles.loading}>Loading sets...</div>
        ) : setsError ? (
          <div className={styles.error}>
            Error loading validation sets: {setsError.message}
          </div>
        ) : (
          <ValidationSetSelector
            validationSets={validationSets ?? []}
            selectedUri={selectedUri}
            onSelect={handleSelectSet}
          />
        )}

        {/* Action icons (right after selector) */}
        {selectedUri && (
          <div className={styles.headerActions}>
            <button
              className={styles.iconButton}
              onClick={handleOpenRename}
              title="Rename validation set"
              disabled={renameSetMutation.isPending}
            >
              <i className={ApplicationIcons.rename} />
            </button>
            <button
              className={styles.iconButton}
              onClick={() => setShowDeleteModal(true)}
              title="Delete validation set"
              disabled={deleteSetMutation.isPending}
            >
              <i className={ApplicationIcons.trash} />
            </button>
          </div>
        )}

        {/* Summary (only when cases loaded) */}
        {cases && cases.length > 0 && (
          <div className={styles.summaryWrapper}>
            <ValidationSummary cases={cases} />
          </div>
        )}

        {/* Spacer to push filter to the right */}
        <div className={styles.spacer} />

        {/* Search and split filter (at far right) */}
        {selectedUri && cases && (
          <div className={styles.filterControls}>
            <TextInput
              icon={ApplicationIcons.search}
              value={searchText ?? ""}
              onChange={handleSearchChange}
              placeholder="Search..."
              className={styles.searchInput}
            />
            <div className={styles.splitFilter}>
              <span className={styles.filterLabel}>Split:</span>
              <VscodeSingleSelect
                value={splitFilter ?? ""}
                onChange={handleSplitFilterChange}
                className={styles.splitSelect}
              >
                <VscodeOption value="">All</VscodeOption>
                {splits.map((split) => (
                  <VscodeOption key={split} value={split}>
                    {split}
                  </VscodeOption>
                ))}
              </VscodeSingleSelect>
            </div>
          </div>
        )}
      </div>

      {/* Content */}
      <div className={styles.content}>
        {selectedUri && (
          <>
            {casesLoading ? (
              <div className={styles.loading}>Loading cases...</div>
            ) : casesError ? (
              <div className={styles.error}>
                Error loading cases: {casesError.message}
              </div>
            ) : cases ? (
              <ValidationCasesList
                cases={cases}
                transcriptsDir={transcriptsDir}
                sourceUri={selectedUri}
                onBulkSplitChange={handleBulkSplitChange}
                onBulkDelete={handleBulkDelete}
                onSingleSplitChange={handleSingleSplitChange}
                onSingleDelete={handleSingleDelete}
                isUpdating={updateMutation.isPending}
                isDeleting={deleteCasesMutation.isPending}
              />
            ) : null}
          </>
        )}

        {!selectedUri && !setsLoading && (
          <div className={styles.emptyState}>
            Select a validation set to view its cases.
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      <Modal
        show={showDeleteModal}
        onHide={() => setShowDeleteModal(false)}
        onSubmit={deleteSetMutation.isPending ? undefined : handleDeleteSet}
        title="Delete Validation Set"
        footer={
          <>
            <VscodeButton secondary onClick={() => setShowDeleteModal(false)}>
              Cancel
            </VscodeButton>
            <VscodeButton
              onClick={handleDeleteSet}
              disabled={deleteSetMutation.isPending}
            >
              {deleteSetMutation.isPending ? "Deleting..." : "Delete"}
            </VscodeButton>
          </>
        }
      >
        <div className={styles.modalContent}>
          <p>
            Are you sure you want to delete <strong>{currentFilename}</strong>?
          </p>
          <p className={styles.warning}>This action cannot be undone.</p>
        </div>
      </Modal>

      {/* Rename Modal */}
      <Modal
        show={showRenameModal}
        onHide={() => setShowRenameModal(false)}
        onSubmit={
          renameSetMutation.isPending || !newName.trim()
            ? undefined
            : handleRenameSet
        }
        title="Rename Validation Set"
        footer={
          <>
            <VscodeButton secondary onClick={() => setShowRenameModal(false)}>
              Cancel
            </VscodeButton>
            <VscodeButton
              onClick={handleRenameSet}
              disabled={renameSetMutation.isPending || !newName.trim()}
            >
              {renameSetMutation.isPending ? "Renaming..." : "Rename"}
            </VscodeButton>
          </>
        }
      >
        <div className={styles.modalContent}>
          <p>Enter a new name for the validation set:</p>
          <VscodeTextfield
            value={newName}
            onInput={handleNameInput}
            placeholder="New name"
            className={styles.renameInput}
            data-autofocus
          />
        </div>
      </Modal>
    </div>
  );
};
