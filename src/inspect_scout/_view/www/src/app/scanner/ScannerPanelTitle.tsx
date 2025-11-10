import clsx from "clsx";
import { FC } from "react";

import { CopyButton } from "../../components/CopyButton";
import { useStore } from "../../state/store";
import { formatDateTime } from "../../utils/format";
import { toRelativePath } from "../../utils/path";
import { prettyDirUri } from "../../utils/uri";
import { useSelectedResults } from "../hooks";

import styles from "./ScannerPanelTitle.module.css";

export const ScannerPanelTitle: FC = () => {
  const selectedResults = useSelectedResults();
  const resultsDir = useStore((state) => state.resultsDir);
  const errorCount = selectedResults?.errors.length || 0;
  const status =
    selectedResults === undefined
      ? ""
      : selectedResults.complete
        ? "Complete"
        : "Incomplete";
  const scanJobName =
    selectedResults?.spec.scan_name === "job"
      ? "scan"
      : selectedResults?.spec.scan_name;

  const transcriptCount = selectedResults?.spec.transcripts.count || 0;
  return (
    <div className={clsx(styles.scanTitleView)}>
      <div className={clsx(styles.leftColumn)}>
        <h1>{scanJobName}:</h1>
        <div className={clsx(styles.secondaryRow)}>
          <h2>{toRelativePath(selectedResults?.location || "", resultsDir)}</h2>
          {selectedResults?.location && (
            <CopyButton
              className={clsx("text-size-small")}
              value={prettyDirUri(selectedResults?.location)}
            />
          )}
        </div>
        <div></div>
        <h3 className={clsx(styles.subtitle, "text-style-secondary")}>
          {selectedResults?.spec.timestamp
            ? formatDateTime(new Date(selectedResults?.spec.timestamp))
            : ""}
        </h3>
      </div>

      <div className={clsx(styles.rightColumn, "text-size-smaller")}>
        <div>{transcriptCount} Transcripts</div>

        <div>{status}</div>
        <div>
          {errorCount === 1
            ? `${errorCount} Error`
            : errorCount > 1
              ? `${errorCount} Errors`
              : ""}
        </div>
      </div>
    </div>
  );
};
