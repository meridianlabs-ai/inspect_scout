import { FC } from "react";

import styles from "./ScanResultsBody.module.css";
import clsx from "clsx";
import { useSelectedScanner } from "./hooks";
import { useStore } from "../../../state/store";
import { ScannerDetail } from "./ScannerDetail";

export const ScanResultsBody: FC = () => {
  const selectedScanner = useSelectedScanner();
  const selectedResults = useStore((state) => state.selectedResults);
  const scannerDetail = selectedResults?.scanners[selectedScanner || ""];

  return (
    <div className={clsx(styles.body)}>
      {scannerDetail && <ScannerDetail scanner={scannerDetail} />}
    </div>
  );
};
