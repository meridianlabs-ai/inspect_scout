import { FC, useState } from "react";

import { ApplicationIcons } from "../../components/icons";
import { useStartScan } from "../server/useStartScan";

import styles from "./RunScanPanel.module.css";

interface Props {
  onScanStarted: (scanId: string) => void;
}

export const DefineScannerSection: FC<Props> = ({ onScanStarted }) => {
  const [question, setQuestion] = useState("");
  const [answerType, setAnswerType] = useState<
    "boolean" | "numeric" | "string"
  >("boolean");
  const [excludeSystem, setExcludeSystem] = useState(true);
  const [excludeReasoning, setExcludeReasoning] = useState(false);
  const [excludeToolUsage, setExcludeToolUsage] = useState(false);
  const mutation = useStartScan();

  const canRunScan = question.trim().length > 0 && !mutation.isPending;

  const placeholderByAnswerType = {
    boolean: "Enter a yes/no question to ask about each transcript...",
    numeric:
      "Enter a question that yields a numeric answer for each transcript...",
    string: "Enter a question to ask about each transcript...",
  } as const;

  const handleRunScan = () => {
    mutation.mutate(
      {
        name: "llm_scanner",
        filter: [],
        scanners: [
          {
            name: "llm_scanner",
            version: 0,
            params: {
              question,
              answer: answerType,
              preprocessor: {
                exclude_system: excludeSystem,
                exclude_reasoning: excludeReasoning,
                exclude_tool_usage: excludeToolUsage,
              },
            },
          },
        ],
      },
      { onSuccess: (data) => onScanStarted(data.spec.scan_id) }
    );
  };

  return (
    <div className={styles.defineScannerSection}>
      <h2 className={styles.sectionTitle}>Define Scanner</h2>
      <div className={styles.formRow}>
        <div className={styles.formColumn}>
          <div className={styles.formGroup}>
            <label className={styles.label}>Type</label>
            <select className={styles.select} disabled>
              <option>llm_scanner</option>
            </select>
          </div>
          <div className={styles.formGroup}>
            <label className={styles.label}>Question</label>
            <textarea
              className={styles.textarea}
              rows={4}
              placeholder={placeholderByAnswerType[answerType]}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
            />
          </div>
          <button
            className={styles.runScanButton}
            disabled={!canRunScan}
            onClick={handleRunScan}
          >
            <i className={ApplicationIcons.play} />
            Run Scan
          </button>
          <div className={styles.mutationStatus}>
            start scan status: {mutation.status}
          </div>
        </div>
        <div className={styles.formColumn}>
          <div className={styles.formGroup}>
            <label className={styles.label}>Answer type</label>
            <select
              className={styles.select}
              value={answerType}
              onChange={(e) =>
                setAnswerType(
                  e.target.value as "boolean" | "numeric" | "string"
                )
              }
            >
              <option value="boolean">Boolean</option>
              <option value="numeric">Numeric</option>
              <option value="string">String</option>
            </select>
          </div>
          <div className={styles.formGroup}>
            <label className={styles.label}>Message filter</label>
            <div className={styles.checkboxGroup}>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={excludeSystem}
                  onChange={(e) => setExcludeSystem(e.target.checked)}
                />
                Exclude system messages
              </label>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={excludeReasoning}
                  onChange={(e) => setExcludeReasoning(e.target.checked)}
                />
                Exclude reasoning content
              </label>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={excludeToolUsage}
                  onChange={(e) => setExcludeToolUsage(e.target.checked)}
                />
                Exclude tool usage
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
