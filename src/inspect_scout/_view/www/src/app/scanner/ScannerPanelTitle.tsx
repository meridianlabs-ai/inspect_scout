import clsx from "clsx";
import { FC } from "react";

import { CopyButton } from "../../components/CopyButton";
import { useStore } from "../../state/store";
import { Status } from "../../types";
import { formatDateTime } from "../../utils/format";
import { toRelativePath } from "../../utils/path";
import { prettyDirUri } from "../../utils/uri";
import { ApplicationIcons } from "../appearance/icons";

import styles from "./ScannerPanelTitle.module.css";

export const ScannerPanelTitle: FC = () => {
  const selectedStatus = useStore((state) => state.selectedScanStatus);
  const resultsDir = useStore((state) => state.resultsDir);
  const scanJobName =
    selectedStatus?.spec.scan_name === "job"
      ? "scan"
      : selectedStatus?.spec.scan_name;

  const scannerModel = selectedStatus?.spec.model.model;

  const transcriptCount = selectedStatus?.spec.transcripts?.count || 0;
  return (
    <div className={clsx(styles.scanTitleView)}>
      <div className={clsx(styles.leftColumn)}>
        <h1>{scanJobName}:</h1>
        <div className={clsx(styles.secondaryRow)}>
          <h2>
            {toRelativePath(selectedStatus?.location || "", resultsDir || "")}
            {scannerModel ? ` (${scannerModel})` : ""}
          </h2>
          {selectedStatus?.location && (
            <CopyButton
              title="Copy Scan Path"
              className={clsx("text-size-small")}
              value={prettyDirUri(selectedStatus?.location)}
            />
          )}
        </div>
        <div></div>
        <div className={clsx(styles.subtitle, "text-style-secondary")}>
          <StatusDisplay status={selectedStatus} />
          <div>—</div>
          <div>{transcriptCount} Transcripts </div>
          <div>—</div>
          <div>
            {selectedStatus?.spec.timestamp
              ? formatDateTime(new Date(selectedStatus?.spec.timestamp))
              : ""}
          </div>
        </div>
      </div>

      <div className={clsx(styles.rightColumn, "text-size-smaller")}></div>
    </div>
  );
};

const StatusDisplay: FC<{ status?: Status }> = ({ status }) => {
  const errorCount = status?.errors.length || 0;

  if (errorCount > 0) {
    const errorStr =
      errorCount === 1
        ? `${errorCount} Error`
        : errorCount > 1
          ? `${errorCount} Errors`
          : "";

    return (
      <div>
        <i className={ApplicationIcons.error} /> {errorStr}
      </div>
    );
  }

  const statusStr =
    status === undefined ? "" : status.complete ? "Complete" : "Incomplete";
  const statusIcon =
    status === undefined
      ? ApplicationIcons.running
      : status.complete
        ? ApplicationIcons.successSubtle
        : ApplicationIcons.pendingTaskSubtle;

  return (
    <div>
      <i className={statusIcon} /> {statusStr}
    </div>
  );
};
