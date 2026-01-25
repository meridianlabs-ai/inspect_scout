import { skipToken } from "@tanstack/react-query";
import { VscodeCollapsible } from "@vscode-elements/react-elements";
import clsx from "clsx";
import { FC, useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { ErrorPanel } from "../../../components/ErrorPanel";
import { ApplicationIcons } from "../../../components/icons";
import { LoadingBar } from "../../../components/LoadingBar";
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
import { useDebouncedCallback } from "../../../utils/useDebouncedCallback";
import { Field } from "../../project/components/FormFields";
import { useConfig } from "../../server/useConfig";
import {
  useCreateValidationSet,
  useUpdateValidationCase,
  useValidationCase,
  useValidationCases,
  useValidationSets,
} from "../../server/useValidations";
import {
  extractUniqueSplits,
  hasValidationSetExtension,
  isValidFilename,
} from "../utils";

import styles from "./ValidationCaseEditor.module.css";
import { ValidationCasePredicateSelector } from "./ValidationCasePredicateSelector";
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
  validationCase,
  validationCases,
  className,
}) => {
  const config = useConfig();
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

  // Local working copy of the validation case for editing
  // This is the single source of truth for the UI during editing
  // null means the case doesn't exist yet (404), undefined means not loaded
  const [workingCase, setWorkingCase] = useState<
    ValidationCase | null | undefined
  >(validationCase);

  // Sync working copy from server when:
  // 1. Server data changes and we're not in the middle of saving
  // 2. The case identity changes (different transcriptId or validation set)
  const updateValidationCaseMutation = useUpdateValidationCase(
    editorValidationSetUri ?? ""
  );
  const isSaving = updateValidationCaseMutation.isPending;

  useEffect(() => {
    // Sync from server when not saving
    // validationCase is null when case doesn't exist (404), undefined when not loaded
    if (!isSaving && validationCase !== undefined) {
      setWorkingCase(validationCase);
    }
  }, [validationCase, isSaving]);

  // Reset working case when switching to a different case
  const prevTranscriptIdRef = useRef(transcriptId);
  const prevUriRef = useRef(editorValidationSetUri);
  useEffect(() => {
    if (
      transcriptId !== prevTranscriptIdRef.current ||
      editorValidationSetUri !== prevUriRef.current
    ) {
      setWorkingCase(validationCase);
      prevTranscriptIdRef.current = transcriptId;
      prevUriRef.current = editorValidationSetUri;
    }
  }, [transcriptId, editorValidationSetUri, validationCase]);

  // Debounced save function - always has access to current state
  const debouncedSave = useDebouncedCallback(() => {
    // Access current state directly - no refs needed
    if (!editorValidationSetUri || !workingCase) {
      return;
    }

    // Don't save if neither target nor labels is set - silently wait for user to set one
    // Also don't save if target is empty string (user selected "Other" but hasn't typed a value)
    if (
      (workingCase.target == null || workingCase.target === "") &&
      workingCase.labels == null
    ) {
      return;
    }

    const request: ValidationCaseRequest = {
      id: workingCase.id,
      predicate: workingCase.predicate,
      split: workingCase.split,
      ...(workingCase.labels != null
        ? { labels: workingCase.labels }
        : { target: workingCase.target }),
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
  }, 600);

  // Handler for field changes - updates local state immediately, debounces server call
  const handleFieldChange = useCallback(
    (field: keyof ValidationCaseRequest, value: JsonValue | string | null) => {
      if (!editorValidationSetUri) return;

      // Update local working copy immediately for instant UI feedback
      setWorkingCase((prev) => {
        // If no existing case, create a default one with the changed field
        if (!prev) {
          return {
            id: transcriptId,
            labels: null,
            predicate: null,
            split: null,
            target: null,
            [field]: value,
          };
        }
        return { ...prev, [field]: value };
      });

      // Debounce the actual server call
      debouncedSave();
    },
    [editorValidationSetUri, transcriptId, debouncedSave]
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

  return (
    <div className={clsx(styles.container, className)}>
      <SidebarHeader
        title="Validation"
        icon={ApplicationIcons.validation}
        onClose={closeValidationSidebar}
      />
      <div className={styles.content}>
        <VscodeCollapsible heading="Validation Set" open>
          <SidebarPanel>
            <Field
              label="Validation Set"
              helper="The file which contains this validation set."
            >
              <ValidationSetSelector
                validationSets={validationSets || []}
                selectedUri={editorValidationSetUri}
                onSelect={handleValidationSetSelect}
                allowCreate={true}
                onCreate={(name) => void handleCreateSet(name)}
                projectDir={config.project_dir}
              />
              {createError && (
                <div className={styles.createError}>{createError}</div>
              )}
            </Field>
            <Field
              label="Split"
              helper='The case that describe the purpose of this validation (e.g., "dev", "test", "train")'
            >
              <ValidationSplitSelector
                value={workingCase?.split || null}
                existingSplits={extractUniqueSplits(validationCases || [])}
                onChange={(split) => handleFieldChange("split", split)}
              />
            </Field>
          </SidebarPanel>
        </VscodeCollapsible>

        {editorValidationSetUri && (
          <VscodeCollapsible heading="Validation Case" open>
            <SidebarPanel>
              <SecondaryDisplayValue label="ID" value={transcriptId} />
              <Field
                label="Target"
                helper="The expected value for this validation case."
              >
                <ValidationCaseTargetEditor
                  target={workingCase?.target}
                  onChange={(target) => {
                    if (!isOtherTarget(target)) {
                      // Clear the predicate when switching away from boolean target
                      handleFieldChange("predicate", null);
                    }
                    handleFieldChange("target", target);
                  }}
                />
              </Field>

              {isOtherTarget(workingCase?.target) && (
                <Field
                  label="Predicate"
                  helper="Specifies the comparison logic for individual cases (by default, comparison is for equality)."
                >
                  <ValidationCasePredicateSelector
                    value={workingCase?.predicate || null}
                    onChange={(predicate) =>
                      handleFieldChange("predicate", predicate)
                    }
                  />
                </Field>
              )}
            </SidebarPanel>
          </VscodeCollapsible>
        )}
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
  onClose?: () => void;
}

export const SidebarHeader: FC<SidebarHeaderProps> = ({
  icon,
  title,
  secondary,
  onClose,
}) => {
  return (
    <div className={styles.header}>
      <h3 className={styles.headerTitle}>
        {icon && <i className={clsx(icon, styles.headerIcon)} />}
        {title}
      </h3>
      {secondary && <div className={styles.headerSecondary}>{secondary}</div>}
      {onClose && (
        <i
          className={clsx(ApplicationIcons.close, styles.clickable)}
          onClick={onClose}
        />
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
 * "Other" targets include numbers, objects, arrays, and non-boolean strings.
 */
const isOtherTarget = (target?: JsonValue): boolean => {
  if (target === null || target === undefined || target === "") {
    return false;
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
