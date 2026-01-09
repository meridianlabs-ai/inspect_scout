import clsx from "clsx";
import { FC } from "react";

import { ApplicationIcons } from "../../components/icons";
import { JsonValue } from "../../types/json-value";

import styles from "./ValidationResult.module.css";

interface ValidationResultProps {
  result: boolean | Record<string, boolean>;
  target?: JsonValue;
  label?: string;
}

export const ValidationResult: FC<ValidationResultProps> = ({
  result,
  target,
  label,
}) => {
  // TODO: stringify the target value properly
  if (typeof result === "boolean") {
    return (
      <Result
        value={result}
        targetValue={valueStr(resolveTargetValue(target, label))}
      />
    );
  } else if (typeof result === "object") {
    const entries = Object.entries(result);

    return (
      <div className={clsx(styles.validationTable)}>
        {entries.map(([key, value]) => (
          <div key={`validation-result-${key}`}>
            <Result
              value={value}
              targetValue={valueStr(resolveTargetValue(target, key))}
            />
          </div>
        ))}
      </div>
    );
  }
};

const Result: FC<{ value: boolean; targetValue?: string }> = ({
  value,
  targetValue,
}) => {
  return (
    <div>
      <div className={clsx(value ? styles.true : styles.false, styles.result)}>
        {value ? (
          <i className={clsx(ApplicationIcons.check)} />
        ) : (
          <i className={clsx(ApplicationIcons.x)} />
        )}
      </div>
      <span
        className={clsx(
          styles.targetValue,
          "text-size-smallestest",
          "text-style-secondary"
        )}
        title={targetValue}
      >
        {targetValue}
      </span>
    </div>
  );
};

const resolveTargetValue = (target?: JsonValue, key?: string): JsonValue => {
  if (target === undefined) {
    return "";
  }

  if (key === undefined) {
    return target;
  }

  if (target && typeof target === "object" && !Array.isArray(target)) {
    return (target as Record<string, JsonValue>)[key] || false;
  }
  return target;
};

const valueStr = (target?: JsonValue): string => {
  if (target === null) {
    return "null";
  } else if (typeof target === "string") {
    return target;
  } else if (typeof target === "number" || typeof target === "boolean") {
    return target.toString();
  } else if (Array.isArray(target)) {
    return `[Array(${target.length})]`;
  } else if (typeof target === "object") {
    return "{Object}";
  } else {
    return "undefined";
  }
};
