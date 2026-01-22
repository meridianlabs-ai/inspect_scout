import { clsx } from "clsx";
import { FC, useState } from "react";

import { useScansDir } from "../utils/useScansDir";

import { ActiveScanView } from "./ActiveScanView";
import { DefineScannerSection } from "./DefineScannerSection";
import styles from "./RunScanPanel.module.css";

export const RunScanPanel: FC = () => {
  const [scanId, setScanId] = useState<string>();
  const { resolvedScansDir } = useScansDir();
  return (
    <div className={clsx(styles.container)}>
      <DefineScannerSection onScanStarted={setScanId} />
      <ActiveScanView scansDir={resolvedScansDir} scanId={scanId} />
    </div>
  );
};
