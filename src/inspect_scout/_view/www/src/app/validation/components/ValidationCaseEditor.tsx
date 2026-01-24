import { skipToken } from "@tanstack/react-query";
import { VscodeCollapsible } from "@vscode-elements/react-elements";
import clsx from "clsx";
import { debounce } from "lodash-es";
import { FC, useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import { Field } from "../../project/components/FormFields";
import {
  useUpdateValidationCase,
  useValidationCase,
  useValidationCases,
  useValidationSets,
} from "../../server/useValidations";
import { extractUniqueSplits } from "../utils";

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
  validationCase?: ValidationCase;
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
  const setEditorSelectedValidationSetUri = useStore(
    (state) => state.setEditorSelectedValidationSetUri
  );
  const [, setSearchParams] = useSearchParams();

  // Save status state
  const [saveStatus, setSaveStatus] = useState<
    "idle" | "saving" | "saved" | "error"
  >("idle");
  const [saveError, setSaveError] = useState<string | null>(null);

  // Mutation hook for saving
  const updateValidationCase = useUpdateValidationCase(
    editorValidationSetUri ?? ""
  );

  // Track pending changes to make sure we save all changes in the
  // debounce window
  const pendingChangesRef = useRef<Partial<ValidationCaseRequest>>({});

  // Create debounced save function
  const debouncedSave = useMemo(() => {
    const doSave = () => {
      // No file selected or no case loaded
      if (!editorValidationSetUri || !validationCase) {
        return;
      }

      // Only save if there are pending changes
      const changes = pendingChangesRef.current;
      if (Object.keys(changes).length === 0) {
        return;
      }

      // Build the full request with current values + pending changes
      const request: ValidationCaseRequest = {
        id: validationCase.id,
        predicate:
          "predicate" in changes ? changes.predicate : validationCase.predicate,
        split: "split" in changes ? changes.split : validationCase.split,
        ...(validationCase.labels != null
          ? { labels: validationCase.labels }
          : {
              target:
                "target" in changes ? changes.target : validationCase.target,
            }),
      };

      setSaveStatus("saving");
      setSaveError(null);

      updateValidationCase.mutate(
        { caseId: transcriptId, data: request },
        {
          onSuccess: () => {
            setSaveStatus("saved");
            pendingChangesRef.current = {};
            // Reset to idle after showing "saved" briefly
            setTimeout(() => setSaveStatus("idle"), 1500);
          },
          onError: (error) => {
            setSaveStatus("error");
            setSaveError(error.message);
          },
        }
      );
    };

    return debounce(doSave, 600);
  }, [
    editorValidationSetUri,
    validationCase,
    transcriptId,
    updateValidationCase,
  ]);

  // Cleanup debounce on unmount
  useEffect(() => {
    return () => {
      debouncedSave.cancel();
    };
  }, [debouncedSave]);

  // Handler for field changes
  const handleFieldChange = useCallback(
    (field: keyof ValidationCaseRequest, value: JsonValue | string | null) => {
      pendingChangesRef.current = {
        ...pendingChangesRef.current,
        [field]: value,
      };
      debouncedSave();
    },
    [debouncedSave]
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
              />
            </Field>
            <Field
              label="Split"
              helper='The case that describe the purpose of this validation (e.g., "dev", "test", "train")'
            >
              <ValidationSplitSelector
                value={validationCase?.split || null}
                existingSplits={extractUniqueSplits(validationCases || [])}
                onChange={(split) => handleFieldChange("split", split)}
                disabled={!validationCase}
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
                  target={validationCase?.target}
                  onChange={(target) => handleFieldChange("target", target)}
                />
              </Field>

              <Field
                label="Predicate"
                helper="Specifies the comparison logic for individual cases (by default, comparison is for equality)."
              >
                <ValidationCasePredicateSelector
                  value={validationCase?.predicate || null}
                  onChange={(predicate) =>
                    handleFieldChange("predicate", predicate)
                  }
                  disabled={!validationCase}
                />
              </Field>
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
