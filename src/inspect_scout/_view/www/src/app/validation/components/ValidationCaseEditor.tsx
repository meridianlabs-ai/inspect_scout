import { skipToken, useQueryClient } from "@tanstack/react-query";
import { VscodeDivider } from "@vscode-elements/react-elements";
import clsx from "clsx";
import React, { FC, ReactNode, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { ConfirmationDialog } from "../../../components/ConfirmationDialog";
import { ErrorPanel } from "../../../components/ErrorPanel";
import { ApplicationIcons } from "../../../components/icons";
import { LoadingBar } from "../../../components/LoadingBar";
import { MenuActionButton } from "../../../components/MenuActionButton";
import {
  getValidationParam,
  getValidationSetParam,
  updateValidationParam,
  updateValidationSetParam,
} from "../../../router/url";
import { useStore } from "../../../state/store";
import {
  JsonValue,
  ValidationCase,
  ValidationCaseRequest,
} from "../../../types/api-types";
import { Field } from "../../project/components/FormFields";
import { useAppConfig } from "../../server/useAppConfig";
import {
  useCreateValidationSet,
  useDeleteValidationCase,
  useUpdateValidationCase,
  useValidationCase,
  useValidationCases,
  useValidationSets,
  validationQueryKeys,
} from "../../server/useValidations";
import {
  extractUniqueLabels,
  extractUniqueSplits,
  hasValidationSetExtension,
  isValidFilename,
} from "../utils";

import styles from "./ValidationCaseEditor.module.css";
import { ValidationCaseLabelsEditor } from "./ValidationCaseLabelsEditor";
import {
  extractUniquePredicates,
  ValidationCasePredicateSelector,
} from "./ValidationCasePredicateSelector";
import { ValidationCaseTargetEditor } from "./ValidationCaseTargetEditor";
import { ValidationSetSelector } from "./ValidationSetSelector";
import { ValidationSplitSelector } from "./ValidationSplitSelector";

interface ValidationCaseEditorProps {
  transcriptId: string;
  className?: string | string[];
}

export const ValidationCaseEditor: FC<ValidationCaseEditorProps> = ({
  transcriptId,
  className,
}) => {
  const [searchParams] = useSearchParams();
  const editorValidationSetUri = useStore(
    (state) => state.editorSelectedValidationSetUri
  );
  const setEditorSelectedValidationSetUri = useStore(
    (state) => state.setEditorSelectedValidationSetUri
  );
  const {
    data: setsData,
    loading: setsLoading,
    error: setsError,
  } = useValidationSets();

  const {
    data: caseData,
    loading: caseLoading,
    error: caseError,
  } = useValidationCase(
    !editorValidationSetUri
      ? skipToken
      : {
          url: editorValidationSetUri,
          caseId: transcriptId,
        }
  );

  const {
    data: casesData,
    loading: casesLoading,
    error: casesError,
  } = useValidationCases(
    editorValidationSetUri ? editorValidationSetUri : skipToken
  );

  // Initialize from URL param or fall back to first available set
  // URL param always takes precedence when present and valid
  useEffect(() => {
    if (!setsData || setsData.length === 0) return;

    const validationSetParam = getValidationSetParam(searchParams);
    if (validationSetParam && setsData.includes(validationSetParam)) {
      // URL param is valid - use it (even if store has a different value)
      if (editorValidationSetUri !== validationSetParam) {
        setEditorSelectedValidationSetUri(validationSetParam);
      }
    } else if (!editorValidationSetUri) {
      // No URL param and no store value - fall back to first set
      setEditorSelectedValidationSetUri(setsData[0]);
    }
  }, [
    setsData,
    searchParams,
    editorValidationSetUri,
    setEditorSelectedValidationSetUri,
  ]);

  const error = setsError || casesError || caseError;
  const loading =
    setsLoading || casesLoading || (!!editorValidationSetUri && caseLoading);
  const showPanel = !setsLoading;

  return (
    <>
      {error && (
        <ErrorPanel
          title="Error Loading Validation Sets"
          error={{ message: error.message }}
        />
      )}
      {!error && (
        <>
          <LoadingBar loading={loading} />
          {showPanel && setsData && (
            <ValidationCaseEditorComponent
              transcriptId={transcriptId}
              validationSets={setsData}
              editorValidationSetUri={editorValidationSetUri}
              validationCase={caseData}
              validationCases={casesData}
              className={className}
            />
          )}
        </>
      )}
    </>
  );
};

interface ValidationCaseEditorComponentProps {
  transcriptId: string;
  validationSets: string[];
  editorValidationSetUri?: string;
  validationCase?: ValidationCase | null;
  validationCases?: ValidationCase[];
  className?: string | string[];
}

const ValidationCaseEditorComponent: FC<ValidationCaseEditorComponentProps> = ({
  transcriptId,
  validationSets,
  editorValidationSetUri,
  validationCase: caseData,
  validationCases,
  className,
}) => {
  const config = useAppConfig();
  const queryClient = useQueryClient();
  const setEditorSelectedValidationSetUri = useStore(
    (state) => state.setEditorSelectedValidationSetUri
  );
  const [, setSearchParams] = useSearchParams();

  // Save status state
  const [saveStatus, setSaveStatus] = useState<
    "idle" | "saving" | "saved" | "error"
  >("idle");
  const [saveError, setSaveError] = useState<string | null>(null);

  // Create set status state
  const [createError, setCreateError] = useState<string | null>(null);
  const createSetMutation = useCreateValidationSet();

  // Delete case state
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  // Track when "other" mode is selected in the target editor
  const [isOtherModeSelected, setIsOtherModeSelected] = useState(false);
  const deleteCaseMutation = useDeleteValidationCase(
    editorValidationSetUri ?? ""
  );

  const updateValidationCaseMutation = useUpdateValidationCase(
    editorValidationSetUri ?? ""
  );

  // Handler for field changes - updates cache immediately, fires mutation for non-empty values
  const handleFieldChange = useCallback(
    (field: keyof ValidationCaseRequest, value: JsonValue | string | null) => {
      if (!editorValidationSetUri) return;

      // Build the updated case
      const updatedCase: ValidationCase = caseData
        ? { ...caseData, [field]: value }
        : {
            id: transcriptId,
            labels: null,
            predicate: null,
            split: null,
            target: null,
            [field]: value,
          };

      // Skip save if this is a NEW case with empty target (user selected "Other" but hasn't typed a value yet).
      // But allow saving empty target if there was a previous value (user is clearing it).
      const hasEmptyTarget =
        updatedCase.target == null || updatedCase.target === "";
      const hadPreviousTarget =
        caseData?.target != null && caseData.target !== "";
      const isNewEmptyCase =
        hasEmptyTarget && updatedCase.labels == null && !hadPreviousTarget;

      if (isNewEmptyCase) {
        // Update cache for UI but don't save to server yet
        queryClient.setQueryData(
          validationQueryKeys.case({
            url: editorValidationSetUri,
            caseId: transcriptId,
          }),
          updatedCase
        );
        return;
      }

      // Fire mutation immediately - optimistic updates handle UI
      const request: ValidationCaseRequest = {
        id: updatedCase.id,
        predicate: updatedCase.predicate,
        split: updatedCase.split,
        ...(updatedCase.labels != null
          ? { labels: updatedCase.labels }
          : { target: updatedCase.target }),
      };

      setSaveStatus("saving");
      setSaveError(null);

      updateValidationCaseMutation.mutate(
        { caseId: transcriptId, data: request },
        {
          onSuccess: () => {
            setSaveStatus("saved");
            setTimeout(() => setSaveStatus("idle"), 1500);
          },
          onError: (error) => {
            setSaveStatus("error");
            setSaveError(error.message);
          },
        }
      );
    },
    [
      editorValidationSetUri,
      transcriptId,
      caseData,
      queryClient,
      updateValidationCaseMutation,
    ]
  );

  const handleValidationSetSelect = useCallback(
    (uri: string | undefined) => {
      setEditorSelectedValidationSetUri(uri);
      setSearchParams(
        (prevParams) => updateValidationSetParam(prevParams, uri),
        { replace: true }
      );
    },
    [setEditorSelectedValidationSetUri, setSearchParams]
  );

  const closeValidationSidebar = useCallback(() => {
    setSearchParams((prevParams) => {
      const isCurrentlyOpen = getValidationParam(prevParams);
      return updateValidationParam(prevParams, !isCurrentlyOpen);
    });
  }, [setSearchParams]);

  // Handler for creating a new validation set
  const handleCreateSet = useCallback(
    async (name: string) => {
      setCreateError(null);

      // Validate filename
      const validation = isValidFilename(name);
      if (!validation.isValid) {
        setCreateError(validation.error ?? "Invalid filename");
        return;
      }

      // Always use project directory (as URI) for new validation sets
      // Only add .csv extension if the user didn't already include a valid extension
      const filename = hasValidationSetExtension(name) ? name : `${name}.csv`;
      const newUri = `${config.project_dir}/${filename}`;

      // Check for duplicates
      if (validationSets?.includes(newUri)) {
        setCreateError("A validation set with this name already exists");
        return;
      }

      try {
        await createSetMutation.mutateAsync({ path: newUri, cases: [] });
        setCreateError(null);
        handleValidationSetSelect(newUri); // Select the new set
      } catch (err) {
        setCreateError(
          err instanceof Error ? err.message : "Failed to create set"
        );
      }
    },
    [
      config.project_dir,
      validationSets,
      createSetMutation,
      handleValidationSetSelect,
    ]
  );

  // Handler for deleting the current validation case
  const handleDeleteCase = useCallback(async () => {
    if (!transcriptId || !editorValidationSetUri) return;
    try {
      await deleteCaseMutation.mutateAsync(transcriptId);
      setShowDeleteModal(false);
      // Reset cache to null after deletion (keeps panel open)
      queryClient.setQueryData(
        validationQueryKeys.case({
          url: editorValidationSetUri,
          caseId: transcriptId,
        }),
        null
      );
    } catch {
      // Error is handled by mutation state - modal stays open
    }
  }, [transcriptId, editorValidationSetUri, deleteCaseMutation, queryClient]);

  const isEditable =
    caseData?.target === undefined ||
    caseData?.target === null ||
    (!Array.isArray(caseData.target) && typeof caseData.target !== "object");

  const actions: ReactNode =
    caseData?.target != null && caseData.target !== "" ? (
      <MenuActionButton
        items={[
          {
            icon: ApplicationIcons.trash,
            label: "Delete validation case",
            value: "delete",
            disabled: deleteCaseMutation.isPending,
          },
        ]}
        onSelect={(value) => {
          if (value === "delete") setShowDeleteModal(true);
        }}
        title="More actions"
      />
    ) : undefined;

  return (
    <div className={clsx(styles.container, className)}>
      <SidebarHeader
        title="Validation Case"
        icon={ApplicationIcons.validation}
        actions={actions}
        onClose={closeValidationSidebar}
      />
      <div className={styles.content}>
        <SidebarPanel>
          <SecondaryDisplayValue label="ID" value={transcriptId} />
          <Field label="Validation Set">
            <ValidationSetSelector
              validationSets={validationSets || []}
              selectedUri={editorValidationSetUri}
              onSelect={handleValidationSetSelect}
              allowCreate={true}
              onCreate={(name) => void handleCreateSet(name)}
              appConfig={config}
            />
            {createError && (
              <div className={styles.createError}>{createError}</div>
            )}
          </Field>

          {!isEditable && (
            <>
              <VscodeDivider />
              <InfoBox>
                Validation sets with dictionary or list targets aren't editable
                using this UI.
              </InfoBox>
            </>
          )}
          {editorValidationSetUri && isEditable && (
            <>
              <Field label="Target" helper="The expected value for this case.">
                <ValidationCaseTargetEditor
                  target={caseData?.target}
                  onChange={(target) => {
                    if (!isOtherTarget(target)) {
                      // Set predicate to "eq" for boolean targets
                      handleFieldChange("predicate", "eq");
                    }
                    handleFieldChange("target", target);
                  }}
                  onModeChange={setIsOtherModeSelected}
                />
              </Field>

              {isOtherModeSelected && (
                <Field
                  label="Predicate"
                  helper="Specifies the comparison logic for individual cases (by default, comparison is for equality)."
                >
                  <ValidationCasePredicateSelector
                    value={caseData?.predicate || null}
                    onChange={(predicate) =>
                      handleFieldChange("predicate", predicate)
                    }
                    existingPredicates={extractUniquePredicates(
                      validationCases || []
                    )}
                  />
                </Field>
              )}

              <Field
                label="Labels"
                helper="Labels that must be present or absent."
              >
                <ValidationCaseLabelsEditor
                  labels={caseData?.labels ?? null}
                  availableLabels={extractUniqueLabels(validationCases || [])}
                  onChange={(labels) => handleFieldChange("labels", labels)}
                />
              </Field>

              <Field
                label="Split"
                helper='Split for this case (e.g., "dev", "test").'
              >
                <ValidationSplitSelector
                  value={caseData?.split || null}
                  existingSplits={extractUniqueSplits(validationCases || [])}
                  onChange={(split) => handleFieldChange("split", split)}
                />
              </Field>

              <ConfirmationDialog
                show={showDeleteModal}
                onHide={() => setShowDeleteModal(false)}
                onConfirm={() => void handleDeleteCase()}
                title="Delete Case"
                message="Are you sure you want to delete this validation case?"
                confirmLabel="Delete"
                confirmingLabel="Deleting..."
                isConfirming={deleteCaseMutation.isPending}
              />
            </>
          )}
        </SidebarPanel>
      </div>
      <SaveStatus status={saveStatus} error={saveError} />
    </div>
  );
};

interface SidebarPanelProps {
  children: React.ReactNode;
}

export const SidebarPanel: FC<SidebarPanelProps> = ({ children }) => {
  return <div className={styles.panel}>{children}</div>;
};

interface SidebarHeaderProps {
  icon?: string;
  title?: string;
  secondary?: string;
  actions?: React.ReactNode;
  onClose?: () => void;
}

export const SidebarHeader: FC<SidebarHeaderProps> = ({
  icon,
  title,
  secondary,
  actions,
  onClose,
}) => {
  return (
    <div className={styles.header}>
      <h3 className={styles.headerTitle}>
        {icon && <i className={clsx(icon, styles.headerIcon)} />}
        {title}
      </h3>
      {secondary && <div className={styles.headerSecondary}>{secondary}</div>}

      {(actions || onClose) && (
        <div className={styles.headerActions}>
          {actions}
          {onClose && (
            <i
              className={clsx(ApplicationIcons.close, styles.clickable)}
              onClick={onClose}
            />
          )}
        </div>
      )}
    </div>
  );
};

export const SecondaryDisplayValue: FC<{ label: string; value: string }> = ({
  label,
  value,
}) => {
  return (
    <div
      className={clsx(
        styles.idField,
        "text-size-smaller",
        "text-style-secondary"
      )}
    >
      <span className={styles.idLabel}>{label}:</span>
      <span className={styles.idValue}>{value}</span>
    </div>
  );
};

const InfoBox: FC<{ children: ReactNode }> = ({ children }) => (
  <div className={clsx("text-size-smaller", styles.infoBox)}>
    <i className={clsx(ApplicationIcons.info, styles.infoIcon)} />
    <div>{children}</div>
  </div>
);

type SaveStatusType = "idle" | "saving" | "saved" | "error";

interface SaveStatusProps {
  status: SaveStatusType;
  error: string | null;
}

const SaveStatus: FC<SaveStatusProps> = ({ status, error }) => {
  return (
    <div
      className={clsx(
        styles.saveStatusContainer,
        status === "error" && styles.saveStatusError,
        status === "idle" && styles.saveStatusHidden
      )}
    >
      <span className={styles.saveStatus}>
        {status === "saving"
          ? "Saving..."
          : status === "saved"
            ? "Saved"
            : status === "error"
              ? error || "Error saving changes"
              : ""}
      </span>
    </div>
  );
};

/**
 * Returns true if the target is an "other" value (not a boolean or boolean string).
 * "Other" targets include numbers, objects, arrays, non-boolean strings, and empty string
 * (which indicates the user selected "Other" mode but hasn't typed a value yet).
 */
const isOtherTarget = (target?: JsonValue): boolean => {
  if (target === null || target === undefined) {
    return false;
  }

  // Empty string means "other" was selected but no value typed yet
  if (target === "") {
    return true;
  }

  if (typeof target === "boolean") {
    return false;
  }

  if (typeof target === "string") {
    const lower = target.toLowerCase();
    // "true" and "false" strings are treated as boolean targets
    return lower !== "true" && lower !== "false";
  }

  // Numbers, objects, arrays are all "other" targets
  return true;
};
