import clsx from "clsx";
import { FC } from "react";

import { ErrorPanel } from "../../../components/ErrorPanel";
import { LoadingBar } from "../../../components/LoadingBar";
import { useValidationSets } from "../../server/useValidations";

import styles from "./ValidationCaseEditor.module.css";

interface ValidationCaseEditorProps {
  className?: string | string[];
}

export const ValidationCaseEditor: FC<ValidationCaseEditorProps> = ({
  className,
}) => {
  const { data, loading, error } = useValidationSets();

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
          <ValidationCaseEditorComponent
            validationSets={data}
            className={className}
          />
        </>
      )}
    </>
  );
};

interface ValidationCaseEditorComponentProps {
  validationSets?: string[];
  className?: string | string[];
}

const ValidationCaseEditorComponent: FC<ValidationCaseEditorComponentProps> = ({
  validationSets: _validationSets,
  className,
}) => {
  return (
    <div className={clsx(styles.container, className)}>
      <div className={styles.header}>
        <h3 className={styles.title}>Validation</h3>
      </div>
      <div className={styles.content}>
        <p className={styles.placeholder}>
          Select a message to create a validation case
        </p>
      </div>
    </div>
  );
};
