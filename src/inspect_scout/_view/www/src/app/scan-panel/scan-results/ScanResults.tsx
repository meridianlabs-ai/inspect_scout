import { FC } from "react";

import styles from "./ScanResults.module.css";
import clsx from "clsx";
import { ScanResultsOutline } from "./ScanResultsOutline";
import { ScanResultsBody } from "./ScanResultsBody";

export const ScanResults: FC = () => {
  return (
    <div className={clsx(styles.container)}>
      <ScanResultsOutline />
      <ScanResultsBody />
    </div>
  );
};
