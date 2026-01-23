import { skipToken } from "@tanstack/react-query";
import {
  VscodeCollapsible,
  VscodeLabel,
  VscodeTextfield,
} from "@vscode-elements/react-elements";
import clsx from "clsx";
import { FC, useEffect } from "react";

import { ErrorPanel } from "../../../components/ErrorPanel";
import { LoadingBar } from "../../../components/LoadingBar";
import { useStore } from "../../../state/store";
import { ValidationCase } from "../../../types/api-types";
import {
  useValidationCase,
  useValidationCases,
  useValidationSets,
} from "../../server/useValidations";
import { extractUniqueSplits } from "../utils";

import styles from "./ValidationCaseEditor.module.css";
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

  return (
    <div className={clsx(styles.container, className)}>
      <SidebarHeader title="Validation" secondary={transcriptId} />
      <div className={styles.content}>
        <VscodeCollapsible heading="Validation Set" open>
          <SidebarPanel>
            <VscodeLabel>Validation Set</VscodeLabel>
            <ValidationSetSelector
              validationSets={validationSets || []}
              selectedUri={editorValidationSetUri}
              onSelect={setEditorSelectedValidationSetUri}
            />
            <VscodeLabel>Split</VscodeLabel>
            <ValidationSplitSelector
              value={validationCase?.split || null}
              existingSplits={extractUniqueSplits(validationCases || [])}
              onChange={onSplitChange}
              disabled={!validationCase}
            />
          </SidebarPanel>
        </VscodeCollapsible>

        {editorValidationSetUri && (
          <VscodeCollapsible heading="Validation Case" open>
            <SidebarPanel>
              <VscodeLabel>Predicate</VscodeLabel>
              {validationCase?.predicate || "eq"}

              <VscodeLabel>Target</VscodeLabel>
              <VscodeTextfield
                id="field-target"
                value={String(validationCase?.target)}
                placeholder="Target"
                spellCheck={false}
                autocomplete="off"
              ></VscodeTextfield>

              <VscodeLabel>Split</VscodeLabel>
              {validationCase?.split || "N/A"}
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
}

export const SidebarHeader: FC<SidebarHeaderProps> = ({ title, secondary }) => {
  return (
    <div className={styles.header}>
      <h3 className={styles.headerTitle}>{title}</h3>
      {secondary && <div className={styles.headerSecondary}>{secondary}</div>}
    </div>
  );
};
