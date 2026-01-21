import clsx from "clsx";
import React, { useEffect } from "react";
import { useSearchParams } from "react-router-dom";

import { ExtendedFindProvider } from "../../components/ExtendedFindProvider";
import { LoadingBar } from "../../components/LoadingBar";
import { getScannerParam } from "../../router/url";
import { useStore } from "../../state/store";
import { ScansNavbar } from "../components/ScansNavbar";
import { useSelectedScan } from "../hooks/useSelectedScan";
import { useConfig } from "../server/useConfig";
import { useScans } from "../server/useScans";

import styles from "./ScanPanel.module.css";
import { ScanPanelBody } from "./ScanPanelBody";
import { ScanPanelTitle } from "./ScanPanelTitle";

export const ScanPanel: React.FC = () => {
  // Load server data
  const { loading: scansLoading } = useScans();
  const config = useConfig();
  const scansDir = config.scans_dir.dir;
  const { loading: scanLoading, data: selectedScan } = useSelectedScan();

  const userScansDir = useStore((state) => state.userScansDir);
  const setUserScansDir = useStore((state) => state.setUserScansDir);

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
      <ScansNavbar
        scansDir={userScansDir || scansDir}
        setScansDir={setUserScansDir}
      />
      <LoadingBar loading={!!loading} />
      {selectedScan && (
        <>
          <ScanPanelTitle resultsDir={scansDir} selectedScan={selectedScan} />
          <ExtendedFindProvider>
            <ScanPanelBody selectedScan={selectedScan} />
          </ExtendedFindProvider>
        </>
      )}
    </div>
  );
};
