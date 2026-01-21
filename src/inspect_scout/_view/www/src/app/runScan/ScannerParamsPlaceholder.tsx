import { FC } from "react";

import styles from "./RunScanPanel.module.css";

interface Props {
  scannerName: string;
}

export const ScannerParamsPlaceholder: FC<Props> = ({ scannerName }) => (
  <div className={styles.paramsPlaceholder}>
    No parameter editor available for <strong>{scannerName}</strong>
  </div>
);
