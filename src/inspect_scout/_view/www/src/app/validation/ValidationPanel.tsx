import { skipToken } from "@tanstack/react-query";
import { FC, useCallback } from "react";

import { useStore } from "../../state/store";
import { useConfig } from "../server/useConfig";
import {
  useBulkDeleteValidationCases,
  useUpdateValidationCase,
  useValidationCases,
  useValidationSets,
} from "../server/useValidations";

import { ValidationCasesList } from "./components/ValidationCasesList";
import { ValidationSetSelector } from "./components/ValidationSetSelector";
import { ValidationSummary } from "./components/ValidationSummary";
import { getCaseKey } from "./utils";
import styles from "./ValidationPanel.module.css";

export const ValidationPanel: FC = () => {
  // Config for transcripts directory
  const config = useConfig();
  const transcriptsDir = config.transcripts?.dir ?? undefined;

  // State management
  const selectedUri = useStore((state) => state.selectedValidationSetUri);
  const setSelectedUri = useStore((state) => state.setSelectedValidationSetUri);
  const clearValidationState = useStore((state) => state.clearValidationState);

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

  // Mutations
  const updateMutation = useUpdateValidationCase(selectedUri ?? "");
  const deleteMutation = useBulkDeleteValidationCases(selectedUri ?? "");

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
        try {
          await Promise.all(
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
        } catch (error) {
          console.error("Error updating validation cases:", error);
        }
      };
      void updateCases();
    },
    [selectedUri, cases, updateMutation]
  );

  const handleBulkDelete = useCallback(
    (ids: string[]) => {
      if (!selectedUri) return;
      deleteMutation.mutate(ids);
    },
    [selectedUri, deleteMutation]
  );

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <h2 className={styles.title}>Validation</h2>
      </div>

      {/* Selector */}
      <div className={styles.selectorSection}>
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
              <>
                {/* Summary */}
                <ValidationSummary uri={selectedUri} cases={cases} />

                {/* Cases List */}
                <ValidationCasesList
                  cases={cases}
                  transcriptsDir={transcriptsDir}
                  onBulkSplitChange={handleBulkSplitChange}
                  onBulkDelete={handleBulkDelete}
                  isUpdating={updateMutation.isPending}
                  isDeleting={deleteMutation.isPending}
                />
              </>
            ) : null}
          </>
        )}

        {!selectedUri && !setsLoading && (
          <div className={styles.emptyState}>
            Select a validation set to view its cases.
          </div>
        )}
      </div>
    </div>
  );
};
