import { clsx } from "clsx";
import { FC, useState } from "react";

import { useDocumentTitle } from "../../hooks/useDocumentTitle";

import { ActiveScanView } from "./ActiveScanView";
import { DefineScannerSection } from "./DefineScannerSection";
import styles from "./RunScanPanel.module.css";

export const RunScanPanel: FC = () => {
  useDocumentTitle("Run Scan");

  const [scanId, setScanId] = useState<string>();
  return (
    <div className={clsx(styles.container)}>
      <DefineScannerSection onScanStarted={setScanId} />
      <ActiveScanView scanId={scanId} />
    </div>
  );
};
