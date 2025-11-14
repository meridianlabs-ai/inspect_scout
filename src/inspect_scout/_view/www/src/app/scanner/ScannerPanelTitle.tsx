import clsx from "clsx";
import { FC } from "react";

import { CopyButton } from "../../components/CopyButton";
import { useStore } from "../../state/store";
import { formatDateTime } from "../../utils/format";
import { toRelativePath } from "../../utils/path";
import { prettyDirUri } from "../../utils/uri";

import styles from "./ScannerPanelTitle.module.css";

export const ScannerPanelTitle: FC = () => {
  const selectedStatus = useStore((state) => state.selectedScanStatus);
  const resultsDir = useStore((state) => state.resultsDir);
  const errorCount = selectedStatus?.errors.length || 0;
  const status =
    selectedStatus === undefined
      ? ""
      : selectedStatus.complete
        ? "Complete"
        : "Incomplete";
  const scanJobName =
    selectedStatus?.spec.scan_name === "job"
      ? "scan"
      : selectedStatus?.spec.scan_name;

  const transcriptCount = selectedStatus?.spec.transcripts.count || 0;
  return (
    <div className={clsx(styles.scanTitleView)}>
      <div className={clsx(styles.leftColumn)}>
        <h1>{scanJobName}:</h1>
        <div className={clsx(styles.secondaryRow)}>
          <h2>
            {toRelativePath(selectedStatus?.location || "", resultsDir || "")}
          </h2>
          {selectedStatus?.location && (
            <CopyButton
              className={clsx("text-size-small")}
              value={prettyDirUri(selectedStatus?.location)}
            />
          )}
        </div>
        <div></div>
        <h3 className={clsx(styles.subtitle, "text-style-secondary")}>
          {selectedStatus?.spec.timestamp
            ? formatDateTime(new Date(selectedStatus?.spec.timestamp))
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
