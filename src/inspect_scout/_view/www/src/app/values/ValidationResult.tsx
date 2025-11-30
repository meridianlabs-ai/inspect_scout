import clsx from "clsx";
import { FC, Fragment } from "react";

import styles from "./ValidationResult.module.css";

interface ValidationResultProps {
  result: boolean | Record<string, boolean>;
}

export const ValidationResult: FC<ValidationResultProps> = ({ result }) => {
  if (typeof result === "boolean") {
    return <Result value={result} />;
  } else if (typeof result === "object") {
    const entries = Object.entries(result);

    return (
      <div className={clsx(styles.validationTable)}>
        {entries.map(([key, value]) => (
          <div>
            <Result value={value} />
          </div>
        ))}
      </div>
    );
  }
};

const Result: FC<{ value: boolean }> = ({ value }) => {
  return (
    <div className={clsx(value ? styles.true : styles.false, styles.result)}>
      {value ? "valid" : "invalid"}
    </div>
  );
};
