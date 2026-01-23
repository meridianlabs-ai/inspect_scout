import { skipToken } from "@tanstack/react-query";
import { VscodeCollapsible } from "@vscode-elements/react-elements";
import clsx from "clsx";
import { FC, useCallback, useEffect } from "react";
import { useSearchParams } from "react-router-dom";

import { ErrorPanel } from "../../../components/ErrorPanel";
import { ApplicationIcons } from "../../../components/icons";
import { LoadingBar } from "../../../components/LoadingBar";
import { getValidationParam, updateValidationParam } from "../../../router/url";
import { useStore } from "../../../state/store";
import { ValidationCase } from "../../../types/api-types";
import { Field } from "../../project/components/FormFields";
import {
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

  useEffect(() => {
    // By default, select the first validation set if none is selected when loaded
    if (setsData && setsData.length > 0 && !editorValidationSetUri) {
      setEditorSelectedValidationSetUri(setsData[0]);
    }
  }, [setsData, editorValidationSetUri, setEditorSelectedValidationSetUri]);

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
  const onSplitChange = (newSplit: string | null) => {
    // Handle split change logic here
    // This is a placeholder; actual implementation may vary
    console.log("Selected split:", newSplit);
  };
  const [_, setSearchParams] = useSearchParams();

  const closeValidationSidebar = useCallback(() => {
    setSearchParams((prevParams) => {
      const isCurrentlyOpen = getValidationParam(prevParams);
      return updateValidationParam(prevParams, !isCurrentlyOpen);
    });
  }, [setSearchParams]);

  return (
    <div className={clsx(styles.container, className)}>
      <SidebarHeader title="Validation" onClose={closeValidationSidebar} />
      <div className={styles.content}>
        <VscodeCollapsible heading="Validation Set" open>
          <SidebarPanel>
            <Field label="Validation Set">
              <ValidationSetSelector
                validationSets={validationSets || []}
                selectedUri={editorValidationSetUri}
                onSelect={setEditorSelectedValidationSetUri}
              />
            </Field>
            <Field label="Split">
              <ValidationSplitSelector
                value={validationCase?.split || null}
                existingSplits={extractUniqueSplits(validationCases || [])}
                onChange={onSplitChange}
                disabled={!validationCase}
              />
            </Field>
          </SidebarPanel>
        </VscodeCollapsible>

        {editorValidationSetUri && (
          <VscodeCollapsible heading="Validation Case" open>
            <SidebarPanel>
              <SecondaryDisplayValue label="ID" value={transcriptId} />
              <Field label="Target">
                <ValidationCaseTargetEditor
                  target="true"
                  onChange={(target) => {
                    console.log("NEW TARGET:" + target);
                  }}
                />
              </Field>

              <Field label="Predicate">
                <ValidationCasePredicateSelector
                  value={validationCase?.predicate || null}
                  onChange={(predicate) => {
                    console.log("NEW PREDICATE:", predicate);
                  }}
                  disabled={!validationCase}
                />
              </Field>
            </SidebarPanel>
          </VscodeCollapsible>
        )}
      </div>
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
  title?: string;
  secondary?: string;
  onClose?: () => void;
}

export const SidebarHeader: FC<SidebarHeaderProps> = ({
  title,
  secondary,
  onClose,
}) => {
  return (
    <div className={styles.header}>
      <h3 className={styles.headerTitle}>{title}</h3>
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
