import clsx from "clsx";
import React, { useEffect } from "react";
import { useSearchParams } from "react-router-dom";

import { ExtendedFindProvider } from "../../components/ExtendedFindProvider";
import { LoadingBar } from "../../components/LoadingBar";
import { getScannerParam } from "../../router/url";
import { useStore } from "../../state/store";
import { ScansNavbar } from "../components/ScansNavbar";
import {
  useServerScan,
  useServerScanDataframe,
  useServerScans,
} from "../server/hooks";

import styles from "./ScansPanel.module.css";
import { ScansPanelBody } from "./ScansPanelBody";
import { ScansPanelTitle } from "./ScansPanelTitle";

export const ScansPanel: React.FC = () => {
  // Load server data
  useServerScans();
  useServerScan();
  useServerScanDataframe();
  const loading = useStore((state) => state.loading);
  const resultsDir = useStore((state) => state.resultsDir);

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

  // Render only if we have selected results
  const selectedScan = useStore((state) => state.selectedScanStatus);
  return (
    <div className={clsx(styles.root)}>
      <ScansNavbar />
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
