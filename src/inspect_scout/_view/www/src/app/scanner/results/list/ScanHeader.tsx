import clsx from "clsx";
import { FC } from "react";

import styles from "./ScanHeader.module.css";
import { GridDescriptor } from "./ScanResultsList";

interface ScanResultsHeaderProps {
  gridDescriptor: GridDescriptor;
}
export const ScanResultsHeader: FC<ScanResultsHeaderProps> = ({
  gridDescriptor,
}) => {
  const hasExplanation = gridDescriptor.columns.includes("explanation");
  const hasLabel = gridDescriptor.columns.includes("label");
  return (
    <div
      style={gridDescriptor.gridStyle}
      className={clsx(
        styles.header,
        "text-size-smallestest",
        "text-style-label",
        "text-style-secondary",
        hasExplanation ? "" : styles.noExplanation
      )}
    >
      <div>Id</div>
      {hasExplanation && <div>Explanation</div>}
      {hasLabel && <div>Label</div>}
      <div className={clsx(styles.value)}>Value</div>
    </div>
  );
};
