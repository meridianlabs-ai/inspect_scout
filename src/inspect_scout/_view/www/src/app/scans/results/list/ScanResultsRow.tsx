import clsx from "clsx";
import { FC, memo } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import { MarkdownReference } from "../../../../components/MarkdownDivWithReferences";
import {
  getRelativePathFromParams,
  scanResultRoute,
} from "../../../../router/url";
import { useStore } from "../../../../state/store";
import { Error } from "../../../components/Error";
import { Explanation } from "../../../components/Explanation";
import { TaskName } from "../../../components/TaskName";
import { ValidationResult } from "../../../components/ValidationResult";
import { Value } from "../../../components/Value";
import { ScanResultSummary } from "../../../types";
import { useMarkdownRefs } from "../../../utils/refs";

import { GridDescriptor } from "./ScanResultsList";
import styles from "./ScanResultsRow.module.css";

interface ScanResultsRowProps {
  index: number;
  summary: ScanResultSummary;
  gridDescriptor: GridDescriptor;
}

const ScanResultsRowComponent: FC<ScanResultsRowProps> = ({
  summary,
  gridDescriptor,
}) => {
  // Path information
  const params = useParams<{ "*": string }>();
  const relativePath = getRelativePathFromParams(params);
  const [searchParams] = useSearchParams();

  // selected scan result
  const selectedScanResult = useStore((state) => state.selectedScanResult);
  const setSelectedScanResult = useStore(
    (state) => state.setSelectedScanResult
  );

  // Generate the route to the scan result using the current scan path and the entry's uuid
  const isNavigable = summary.uuid !== undefined;
  const scanResultUrl = isNavigable
    ? scanResultRoute(relativePath, summary.uuid, searchParams)
    : "";
  const navigate = useNavigate();

  // Information about the row
  const hasExplanation = gridDescriptor.columns.includes("result");
  const hasLabel = gridDescriptor.columns.includes("label");
  const hasErrors = gridDescriptor.columns.includes("error");
  const hasValidations = gridDescriptor.columns.includes("validations");

  // refs
  const refs: MarkdownReference[] = useMarkdownRefs(summary);

  // Task information
  const taskSet = summary.transcriptTaskSet;
  const taskId = summary.transcriptTaskId;
  const taskRepeat = summary.transcriptTaskRepeat;

  const grid = (
    <div
      style={gridDescriptor.gridStyle}
      className={clsx(
        styles.row,
        !isNavigable ? styles.disabled : "",
        selectedScanResult === summary.uuid ? styles.selected : "",
        hasExplanation ? "" : styles.noExplanation
      )}
      onClick={() => {
        if (summary.uuid) {
          setSelectedScanResult(summary.uuid);
        }
      }}
    >
      {hasExplanation && (
        <div className={clsx(styles.result, "text-size-smaller")}>
          <div className={clsx(styles.id, "text-size-smallest")}>
            <TaskName
              taskSet={taskSet}
              taskId={taskId}
              taskRepeat={taskRepeat}
            />
          </div>
          <div className={clsx(styles.model, "text-size-smallest")}>
            {summary.transcriptModel || ""}
          </div>

          <div className={clsx(styles.explanation, "text-size-smaller")}>
            <Explanation summary={summary} references={refs} />
          </div>
        </div>
      )}
      {hasLabel && (
        <div
          className={clsx(
            styles.label,
            "text-size-smallest",
            "text-style-label",
            "text-style-secondary"
          )}
        >
          {summary.label || (
            <span className={clsx(styles.label, "text-style-secondary")}>
              —
            </span>
          )}
        </div>
      )}

      <div className={clsx(styles.value, "text-size-smaller")}>
        {!summary.scanError && (
          <Value summary={summary} style="inline" references={refs} />
        )}
      </div>
      {hasValidations && (
        <div className={clsx("text-size-smaller")}>
          <ValidationResult result={summary.validationResult} />
        </div>
      )}
      {hasErrors && (
        <div className={clsx(styles.error, "text-size-smallest")}>
          {summary.scanError && (
            <Error
              error={summary.scanError || "unknown error"}
              refusal={!!summary.scanErrorRefusal}
            />
          )}
        </div>
      )}
    </div>
  );

  const handleClick = (e: React.MouseEvent) => {
    // Don't navigate if clicking an inner link
    if ((e.target as HTMLElement).closest("a")) {
      return;
    }
    void navigate(scanResultUrl);
  };

  return isNavigable ? (
    <div
      className={clsx(styles.link)}
      onClick={handleClick}
      style={{ cursor: "pointer" }}
    >
      {grid}
    </div>
  ) : (
    grid
  );
};

// memoize the component to avoid unnecessary re-renders (esp of things which may involve markdown rendering)
export const ScanResultsRow = memo(ScanResultsRowComponent);
