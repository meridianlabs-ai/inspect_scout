import clsx from "clsx";
import { FC } from "react";

import styles from "./ValidationCaseEditor.module.css";

interface ValidationCaseEditorProps {
  className?: string | string[];
}

export const ValidationCaseEditor: FC<ValidationCaseEditorProps> = ({
  className,
}) => {
  return (
    <div className={clsx(styles.container, className)}>
      <div className={styles.header}>
        <h3 className={styles.title}>Validation Case</h3>
      </div>
      <div className={styles.content}>
        <p className={styles.placeholder}>
          Select a message to create a validation case
        </p>
      </div>
    </div>
  );
};
