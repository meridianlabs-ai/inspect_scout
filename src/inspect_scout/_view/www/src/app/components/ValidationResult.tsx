import clsx from "clsx";
import { FC } from "react";

import { ApplicationIcons } from "../appearance/icons";

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
          <div key={`validation-result-${key}`}>
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
      {value ? (
        <i className={clsx(ApplicationIcons.check)} />
      ) : (
        <i className={clsx(ApplicationIcons.x)} />
      )}
    </div>
  );
};
