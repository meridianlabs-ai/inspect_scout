import { VscodeCheckbox } from "@vscode-elements/react-elements";
import { FC, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ValidationCase } from "../../../types/api-types";
import { encodeBase64Url } from "../../../utils/base64url";
import { getIdText } from "../utils";

import styles from "./ValidationCaseCard.module.css";

interface ValidationCaseCardProps {
  validationCase: ValidationCase;
  transcriptsDir: string | undefined;
  isSelected: boolean;
  onSelectionChange: (selected: boolean) => void;
}

/**
 * Card component for displaying a single validation case.
 */
export const ValidationCaseCard: FC<ValidationCaseCardProps> = ({
  validationCase,
  transcriptsDir,
  isSelected,
  onSelectionChange,
}) => {
  const navigate = useNavigate();
  const [isTargetExpanded, setIsTargetExpanded] = useState(false);

  const { id, target, split, predicate } = validationCase;

  // Get display text for the ID
  const idText = getIdText(id);

  // Extract target text from the validation case
  const getTargetText = (): string => {
    if (typeof target === "string") {
      return target;
    }
    if (Array.isArray(target)) {
      // Labels array - show as comma-separated
      return target.map(String).join(", ");
    }
    if (target === null || target === undefined) {
      return "";
    }
    return JSON.stringify(target);
  };

  const targetText = getTargetText();
  const isTargetLong = targetText.length > 100;
  const displayTarget =
    isTargetLong && !isTargetExpanded
      ? targetText.slice(0, 100) + "..."
      : targetText;

  // Handle navigation to transcript (only works for single string IDs)
  const handleIdClick = () => {
    const singleId = Array.isArray(id) ? id[0] : id;
    if (transcriptsDir && singleId) {
      // Navigate to the transcript detail view using base64url encoding
      void navigate(
        `/transcripts/${encodeBase64Url(transcriptsDir)}/${singleId}`
      );
    }
  };

  const handleCheckboxChange = (e: Event) => {
    const checked = (e.target as HTMLInputElement).checked;
    onSelectionChange(checked);
  };

  return (
    <div className={`${styles.card} ${isSelected ? styles.selected : ""}`}>
      <div className={styles.cardHeader}>
        <VscodeCheckbox
          checked={isSelected}
          onChange={handleCheckboxChange}
          className={styles.checkbox}
        />
        <button
          className={styles.idLink}
          onClick={handleIdClick}
          disabled={!transcriptsDir}
          title={
            transcriptsDir ? "View transcript" : "No transcripts directory"
          }
        >
          {idText}
        </button>
        {split && <span className={styles.splitBadge}>{split}</span>}
      </div>

      <div className={styles.cardBody}>
        {/* Target */}
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Target:</span>
          <span
            className={`${styles.fieldValue} ${isTargetLong ? styles.clickable : ""}`}
            onClick={() =>
              isTargetLong && setIsTargetExpanded(!isTargetExpanded)
            }
          >
            {displayTarget}
          </span>
        </div>

        {/* Predicate */}
        {predicate && (
          <div className={styles.field}>
            <span className={styles.fieldLabel}>Predicate:</span>
            <span className={styles.fieldValue}>{predicate}</span>
          </div>
        )}
      </div>
    </div>
  );
};
