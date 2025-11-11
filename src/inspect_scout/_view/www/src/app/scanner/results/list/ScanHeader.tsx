import clsx from "clsx";
import { FC } from "react";

import styles from "./ScanHeader.module.css";

interface ScanResultsHeaderProps {
  hasExplanation: boolean;
  gridTemplateColumns: string;
}
export const ScanResultsHeader: FC<ScanResultsHeaderProps> = ({
  gridTemplateColumns,
  hasExplanation,
}) => (
  <div
    style={{ gridTemplateColumns }}
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
    <div className={clsx(styles.value)}>Value</div>
  </div>
);
