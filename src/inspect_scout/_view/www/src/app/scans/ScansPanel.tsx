import clsx from "clsx";
import React, { useEffect } from "react";
import { useSearchParams } from "react-router-dom";

import { ExtendedFindProvider } from "../../components/ExtendedFindProvider";
import { LoadingBar } from "../../components/LoadingBar";
import { getScannerParam } from "../../router/url";
import { useStore } from "../../state/store";
import { ScansNavbar } from "../components/ScansNavbar";
import { useSelectedScan } from "../hooks";
import { useServerScansDir, useServerScans } from "../server/hooks";

import styles from "./ScansPanel.module.css";
import { ScansPanelBody } from "./ScansPanelBody";
import { ScansPanelTitle } from "./ScansPanelTitle";

export const ScansPanel: React.FC = () => {
  // Load server data
  const { loading: scansLoading } = useServerScans();
  const { data: resultsDir } = useServerScansDir();
  const { loading: scanLoading, data: selectedScan } = useSelectedScan();

  const loading = scansLoading || scanLoading;

  // Clear scan state from the store on mount
  const clearScanState = useStore((state) => state.clearScanState);
  useEffect(() => {
    clearScanState();
  }, []);

  // Sync URL query param with store state
  const [searchParams] = useSearchParams();
  const setSelectedScanner = useStore((state) => state.setSelectedScanner);
  useEffect(() => {
    const scannerParam = getScannerParam(searchParams);
    if (scannerParam) {
      setSelectedScanner(scannerParam);
    }
  }, [searchParams, setSelectedScanner]);
  return (
    <div className={clsx(styles.root)}>
      <ScansNavbar resultsDir={resultsDir} />
      <LoadingBar loading={!!loading} />
      {selectedScan && (
        <>
          <ScansPanelTitle
            resultsDir={resultsDir}
            selectedScan={selectedScan}
          />
          <ExtendedFindProvider>
            <ScansPanelBody selectedScan={selectedScan} />
          </ExtendedFindProvider>
        </>
      )}
    </div>
  );
};
