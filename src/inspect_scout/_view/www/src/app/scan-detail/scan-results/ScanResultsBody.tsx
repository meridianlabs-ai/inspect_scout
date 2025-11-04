import { FC } from "react";

import styles from "./ScanResultsBody.module.css";
import clsx from "clsx";
import { useSelectedScanner } from "./hooks";
import { useStore } from "../../../state/store";
import { ScannerHeading } from "./ScannerHeading";
import { ScannerDetail } from "./ScannerDetail";

export const ScanResultsBody: FC = () => {
  const selectedScanner = useSelectedScanner();
  const selectedResults = useStore((state) => state.selectedResults);
  const scanner = selectedResults?.spec.scanners[selectedScanner || ""];
  const scannerDetail = selectedResults?.scanners[selectedScanner || ""];

  return (
    <div className={clsx(styles.body)}>
      {scanner && <ScannerHeading scanner={scanner} />}
      {scannerDetail && <ScannerDetail scanner={scannerDetail} />}
    </div>
  );
};
