import clsx from "clsx";
import { FC } from "react";

import { useStore } from "../../../state/store";

import { useSelectedScanner } from "./hooks";
import { ScannerDetail } from "./ScannerDetail";
import styles from "./ScanResultsBody.module.css";

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
