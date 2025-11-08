import clsx from "clsx";
import { FC } from "react";

import styles from "./ScanHeader.module.css";

interface ScanResultsHeaderProps {
  hasExplanation: boolean;
}
export const ScanResultsHeader: FC<ScanResultsHeaderProps> = ({
  hasExplanation,
}) => (
  <div
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
