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

  return (
    <div className={clsx(styles.scanTitleView)}>
      <div className={clsx(styles.leftColumn)}>
        <h1>{selectedResults?.spec.scan_name}</h1>
        <h2>{selectedResults?.spec.scan_id}</h2>
        <div></div>
        <h3 className={clsx(styles.subtitle, "text-style-secondary")}>
          {selectedResults?.spec.scan_file}
        </h3>
      </div>

      <div className={clsx(styles.rightColumn)}>
        <div className={"text-size-smaller"}>{status}</div>
        <div className={"text-size-smaller"}>
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
