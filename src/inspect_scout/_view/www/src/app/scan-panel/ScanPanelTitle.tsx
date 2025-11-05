import { FC } from "react";
import { useStore } from "../../state/store";

import styles from "./ScanPanelTitle.module.css";
import clsx from "clsx";

export const ScanPanelTitle: FC = () => {
  const selectedResults = useStore((state) => state.selectedResults);
  const errorCount = selectedResults?.errors.length || 0;
  const status =
    selectedResults === undefined
      ? ""
      : selectedResults.complete
        ? "Complete"
        : "Incomplete";

  // Total tokens
  // # transcripts

  const transcriptCount = selectedResults?.spec.transcripts.count || 0;
  console.log({ selectedResults });

  return (
    <div className={clsx(styles.scanTitleView)}>
      <div className={clsx(styles.leftColumn)}>
        <h1>{selectedResults?.spec.scan_name}</h1>
        <h2>{selectedResults?.spec.model.model}</h2>
        <div></div>
        <h3 className={clsx(styles.subtitle, "text-style-secondary")}>
          {selectedResults?.spec.timestamp}
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
