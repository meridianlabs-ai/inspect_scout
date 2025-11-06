import clsx from "clsx";
import { FC } from "react";

import styles from "./ScanHeader.module.css";

export const ScanResultsHeader: FC = () => (
  <div
    className={clsx(
      styles.header,
      "text-size-smallestest",
      "text-style-label",
      "text-style-secondary"
    )}
  >
    <div>Id</div>
    <div>Explanation</div>
    <div className={clsx(styles.value)}>Value</div>
  </div>
);
