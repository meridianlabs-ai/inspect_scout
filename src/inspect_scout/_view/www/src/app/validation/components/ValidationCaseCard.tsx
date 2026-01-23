import { VscodeCheckbox } from "@vscode-elements/react-elements";
import { FC, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApplicationIcons } from "../../../components/icons";
import { Modal } from "../../../components/Modal";
import { transcriptRoute } from "../../../router/url";
import { TranscriptInfo, ValidationCase } from "../../../types/api-types";
import { getIdText } from "../utils";

import styles from "./ValidationCaseCard.module.css";
import { ValidationSplitSelector } from "./ValidationSplitSelector";

interface ValidationCaseCardProps {
  validationCase: ValidationCase;
  transcript?: TranscriptInfo;
  transcriptsDir: string | undefined;
  isSelected: boolean;
  onSelectionChange: (selected: boolean) => void;
  existingSplits: string[];
  onSplitChange?: (split: string | null) => void;
  onDelete?: () => void;
  isUpdating?: boolean;
  isDeleting?: boolean;
}

/**
 * Format the target value for display.
 */
const formatTarget = (target: ValidationCase["target"]): string => {
  if (typeof target === "string") {
    return target;
  }
  if (typeof target === "boolean") {
    return target ? "true" : "false";
  }
  if (typeof target === "number") {
    return String(target);
  }
  if (Array.isArray(target)) {
    return target.map(String).join(", ");
  }
  if (target === null || target === undefined) {
    return "";
  }
  return JSON.stringify(target);
};

/**
 * Format the score value for display.
 */
const formatScore = (score: TranscriptInfo["score"]): string => {
  if (score === null || score === undefined) {
    return "—";
  }
  if (typeof score === "number") {
    return String(score);
  }
  if (typeof score === "boolean") {
    return score ? "1" : "0";
  }
  if (typeof score === "string") {
    return score;
  }
  return JSON.stringify(score);
};

/**
 * Build the transcript details line.
 * Format: <task_set>/<task_id> (<repeat>) - <agent> - <model> (score: <score>)
 */
const buildTranscriptDetails = (transcript: TranscriptInfo): string => {
  const parts: string[] = [];

  // Task info: task_set/task_id (repeat)
  if (transcript.task_set || transcript.task_id) {
    let taskPart = "";
    if (transcript.task_set && transcript.task_id) {
      taskPart = `${transcript.task_set}/${transcript.task_id}`;
    } else if (transcript.task_set) {
      taskPart = transcript.task_set;
    } else if (transcript.task_id) {
      taskPart = transcript.task_id;
    }
    if (
      transcript.task_repeat !== null &&
      transcript.task_repeat !== undefined
    ) {
      taskPart += ` (${transcript.task_repeat})`;
    }
    parts.push(taskPart);
  }

  // Agent
  if (transcript.agent) {
    parts.push(transcript.agent);
  }

  // Model
  if (transcript.model) {
    parts.push(transcript.model);
  }

  // Score
  const scoreStr = formatScore(transcript.score);
  parts.push(`score: ${scoreStr}`);

  return parts.join(" - ");
};

/**
 * Card component for displaying a single validation case.
 */
export const ValidationCaseCard: FC<ValidationCaseCardProps> = ({
  validationCase,
  transcript,
  transcriptsDir,
  isSelected,
  onSelectionChange,
  existingSplits,
  onSplitChange,
  onDelete,
  isUpdating,
  isDeleting,
}) => {
  const navigate = useNavigate();

  const { id, target, split, predicate } = validationCase;

  // Modal state
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  // Get display text for the ID
  const idText = getIdText(id);

  // Format target for display
  const targetText = formatTarget(target);

  // Show predicate if it's not the default "eq"
  const showPredicate = predicate && predicate !== "eq";

  // Handle navigation to transcript (only works for single string IDs)
  const handleNavigateToTranscript = () => {
    const singleId = Array.isArray(id) ? id[0] : id;
    if (transcriptsDir && singleId) {
      void navigate(transcriptRoute(transcriptsDir, singleId));
    }
  };

  const handleCheckboxChange = (e: Event) => {
    const checked = (e.target as HTMLInputElement).checked;
    onSelectionChange(checked);
  };

  const handleDelete = () => {
    onDelete?.();
    setShowDeleteModal(false);
  };

  return (
    <div className={`${styles.card} ${isSelected ? styles.selected : ""}`}>
      {/* First row: grid layout matching header */}
      <div className={styles.row}>
        {/* Checkbox column */}
        <div className={styles.checkbox}>
          <VscodeCheckbox
            checked={isSelected}
            onChange={handleCheckboxChange}
          />
        </div>

        {/* Transcript column */}
        <div className={styles.transcriptCell}>
          <button
            className={styles.idLink}
            onClick={handleNavigateToTranscript}
            disabled={!transcriptsDir}
            title={
              transcriptsDir ? "View transcript" : "No transcripts directory"
            }
          >
            {idText}
          </button>
        </div>

        {/* Target column */}
        <div className={styles.targetCell}>
          {targetText && (
            <span className={styles.target}>
              {showPredicate ? `(${predicate}) ` : ""}{targetText}
            </span>
          )}
        </div>

        {/* Split column */}
        {onSplitChange ? (
          <ValidationSplitSelector
            value={split}
            existingSplits={existingSplits}
            onChange={onSplitChange}
            disabled={isUpdating}
            className={styles.splitSelect}
          />
        ) : (
          <span className={styles.target}>{split ?? "—"}</span>
        )}

        {/* Actions column */}
        <div className={styles.actions}>
          <button
            className={styles.actionButton}
            onClick={handleNavigateToTranscript}
            disabled={!transcriptsDir}
            title="View transcript"
          >
            <i className={ApplicationIcons.edit} />
          </button>
          {onDelete && (
            <button
              className={styles.actionButton}
              onClick={() => setShowDeleteModal(true)}
              disabled={isDeleting}
              title="Delete case"
            >
              <i className={ApplicationIcons.trash} />
            </button>
          )}
        </div>
      </div>

      {/* Second row: Transcript details */}
      {transcript && (
        <div className={styles.detailsRow}>
          {buildTranscriptDetails(transcript)}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <Modal
        show={showDeleteModal}
        onHide={() => setShowDeleteModal(false)}
        onSubmit={handleDelete}
        title="Delete Case"
        footer={
          <>
            <button
              className={styles.modalButton}
              onClick={() => setShowDeleteModal(false)}
            >
              Cancel
            </button>
            <button
              className={`${styles.modalButton} ${styles.modalButtonPrimary}`}
              onClick={handleDelete}
              disabled={isDeleting}
            >
              {isDeleting ? "Deleting..." : "Delete"}
            </button>
          </>
        }
      >
        <div className={styles.modalContent}>
          <p>Are you sure you want to delete this validation case?</p>
          <p className={styles.warning}>This action cannot be undone.</p>
        </div>
      </Modal>
    </div>
  );
};
