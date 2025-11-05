import { FC } from "react";

import styles from "./ScanResults.module.css";
import clsx from "clsx";
import { ScanResultsTOC } from "./ScanResultsTOC";
import { ScanResultsBody } from "./ScanResultsBody";

export const ScanResults: FC = () => {
  return (
    <div className={clsx(styles.container)}>
      <ScanResultsTOC />
      <ScanResultsBody />
    </div>
  );
};
