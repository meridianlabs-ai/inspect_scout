import { VscodeCheckbox } from "@vscode-elements/react-elements";
import React, { CSSProperties, FC, useState } from "react";
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
  showLabels?: boolean;
  showTarget?: boolean;
  gridStyle?: CSSProperties;
}

/**
 * Format the target value for display (non-boolean values).
 */
const formatTarget = (target: ValidationCase["target"]): string => {
  if (typeof target === "string") {
    return target;
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
 * Render the target value with appropriate styling.
 * Boolean targets get styled badges, others get plain text.
 */
const renderTarget = (
  target: ValidationCase["target"],
  predicate: string | null | undefined
): React.ReactNode => {
  const showPredicate = predicate && predicate !== "eq";
  const predicatePrefix = showPredicate ? `(${predicate}) ` : "";

  if (typeof target === "boolean") {
    return (
      <>
        {predicatePrefix}
        <span className={target ? styles.targetTrue : styles.targetFalse}>
          {String(target)}
        </span>
      </>
    );
  }

  const targetText = formatTarget(target);
  if (!targetText) return null;

  return (
    <span className={styles.target}>
      {predicatePrefix}
      {targetText}
    </span>
  );
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
 * Format labels for display.
 * Shows comma-separated label: true/false pairs, with true values first.
 */
const formatLabels = (
  labels: Record<string, boolean> | null | undefined
): string => {
  if (!labels) return "";
  const entries = Object.entries(labels);
  // Sort: true values first, then false
  entries.sort(([, a], [, b]) => (b ? 1 : 0) - (a ? 1 : 0));
  return entries.map(([k, v]) => `${k}: ${v}`).join(", ");
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
  showLabels,
  showTarget,
  gridStyle,
}) => {
  const navigate = useNavigate();

  const { id, target, split, predicate, labels } = validationCase;

  // Modal state
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  // Get display text for the ID
  const idText = getIdText(id);

  // Render target with appropriate styling
  const targetElement = renderTarget(target, predicate);

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

  // Handle row click to toggle selection
  const handleRowClick = (e: React.MouseEvent) => {
    // Don't toggle if clicking on interactive elements
    const target = e.target as HTMLElement;
    if (
      target.closest("button") ||
      target.closest("vscode-checkbox") ||
      target.closest("vscode-single-select")
    ) {
      return;
    }
    onSelectionChange(!isSelected);
  };

  const handleDelete = () => {
    onDelete?.();
    setShowDeleteModal(false);
  };

  // Format labels for display
  const labelsText = formatLabels(labels);

  return (
    <div
      className={`${styles.card} ${isSelected ? styles.selected : ""}`}
      style={gridStyle}
      onClick={handleRowClick}
    >
      {/* Checkbox column */}
      <div className={styles.checkbox}>
        <VscodeCheckbox checked={isSelected} onChange={handleCheckboxChange} />
      </div>

      {/* Transcript column (ID + details) */}
      <div className={styles.transcriptCell}>
        <button
          className={styles.idLink}
          onClick={handleNavigateToTranscript}
          disabled={!transcriptsDir}
          title={
            transcriptsDir ? "View transcript" : "No transcripts directory"
          }
        >
          Transcript ID: {idText}
        </button>
        {transcript ? (
          <div className={styles.detailsRow}>
            {buildTranscriptDetails(transcript)}
          </div>
        ) : (
          <div className={styles.notFoundRow}>
            <i className={ApplicationIcons.logging.warning} />
            <span>Not found in project transcripts</span>
          </div>
        )}
      </div>

      {/* Labels column (conditional) */}
      {showLabels && <div className={styles.labelsCell}>{labelsText}</div>}

      {/* Target column (conditional) */}
      {showTarget && <div className={styles.targetCell}>{targetElement}</div>}

      {/* Split column */}
      {onSplitChange ? (
        <ValidationSplitSelector
          value={split ?? null}
          existingSplits={existingSplits}
          onChange={onSplitChange}
          disabled={isUpdating}
          className={styles.splitSelect}
          noSplitLabel="(No split)"
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
