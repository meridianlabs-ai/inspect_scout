import clsx from "clsx";
import { FC } from "react";

import styles from "./ScanResults.module.css";
import { ScanResultsBody } from "./ScanResultsBody";
import { ScanResultsOutline } from "./ScanResultsOutline";

export const ScanResults: FC = () => {
  return (
    <div className={clsx(styles.container)}>
      <ScanResultsOutline />
      <ScanResultsBody />
    </div>
  );
};
