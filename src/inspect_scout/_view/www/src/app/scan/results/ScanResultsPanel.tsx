import clsx from "clsx";
import { FC } from "react";

import { ScanResultsBody } from "./ScanResultsBody";
import { ScanResultsOutline } from "./ScanResultsOutline";
import styles from "./ScanResultsPanel.module.css";

export const ScanResultsPanel: FC = () => {
  return (
    <div className={clsx(styles.container)}>
      <ScanResultsOutline />
      <ScanResultsBody />
    </div>
  );
};
