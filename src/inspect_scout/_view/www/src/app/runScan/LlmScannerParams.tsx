import {
  VscodeCheckbox,
  VscodeLabel,
  VscodeOption,
  VscodeSingleSelect,
  VscodeTextarea,
} from "@vscode-elements/react-elements";
import { FC } from "react";

import styles from "./RunScanPanel.module.css";

function getInputValue(e: Event): string {
  return (e.target as HTMLInputElement).value;
}

function getSelectValue(e: Event): string {
  return (e.target as HTMLSelectElement).value;
}

export interface LlmScannerParamsValue {
  question: string;
  answerType: "boolean" | "numeric" | "string";
  excludeSystem: boolean;
  excludeReasoning: boolean;
  excludeToolUsage: boolean;
}

interface Props {
  value: LlmScannerParamsValue;
  onChange: (value: LlmScannerParamsValue) => void;
}

const placeholderByAnswerType = {
  boolean: "Enter a yes/no question to ask about each transcript...",
  numeric:
    "Enter a question that yields a numeric answer for each transcript...",
  string: "Enter a question to ask about each transcript...",
} as const;

export const LlmScannerParams: FC<Props> = ({ value, onChange }) => {
  const update = (partial: Partial<LlmScannerParamsValue>) =>
    onChange({ ...value, ...partial });

  return (
    <div className={styles.formRow}>
      <div className={styles.formColumn}>
        <div className={styles.formGroup}>
          <VscodeLabel>Question</VscodeLabel>
          <VscodeTextarea
            rows={4}
            placeholder={placeholderByAnswerType[value.answerType]}
            value={value.question}
            onInput={(e) => update({ question: getInputValue(e) })}
          />
        </div>
      </div>
      <div className={styles.formColumn}>
        <div className={styles.formGroup}>
          <VscodeLabel>Answer type</VscodeLabel>
          <VscodeSingleSelect
            value={value.answerType}
            onChange={(e) =>
              update({
                answerType: getSelectValue(e) as
                  | "boolean"
                  | "numeric"
                  | "string",
              })
            }
          >
            <VscodeOption value="boolean">Boolean</VscodeOption>
            <VscodeOption value="numeric">Numeric</VscodeOption>
            <VscodeOption value="string">String</VscodeOption>
          </VscodeSingleSelect>
        </div>
        <div className={styles.formGroup}>
          <VscodeLabel>Message filter</VscodeLabel>
          <div className={styles.checkboxGroup}>
            <VscodeCheckbox
              checked={value.excludeSystem}
              onChange={(e) =>
                update({
                  excludeSystem: (e.target as HTMLInputElement).checked,
                })
              }
            >
              Exclude system messages
            </VscodeCheckbox>
            <VscodeCheckbox
              checked={value.excludeReasoning}
              onChange={(e) =>
                update({
                  excludeReasoning: (e.target as HTMLInputElement).checked,
                })
              }
            >
              Exclude reasoning content
            </VscodeCheckbox>
            <VscodeCheckbox
              checked={value.excludeToolUsage}
              onChange={(e) =>
                update({
                  excludeToolUsage: (e.target as HTMLInputElement).checked,
                })
              }
            >
              Exclude tool usage
            </VscodeCheckbox>
          </div>
        </div>
      </div>
    </div>
  );
};
