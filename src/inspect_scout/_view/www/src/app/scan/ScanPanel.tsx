import clsx from "clsx";
import React, { useEffect } from "react";
import { useSearchParams } from "react-router-dom";

import { ErrorPanel } from "../../components/ErrorPanel";
import { ExtendedFindProvider } from "../../components/ExtendedFindProvider";
import { LoadingBar } from "../../components/LoadingBar";
import { useDocumentTitle } from "../../hooks/useDocumentTitle";
import { getScannerParam } from "../../router/url";
import { useStore } from "../../state/store";
import { ScansNavbar } from "../components/ScansNavbar";
import { useSelectedScan } from "../hooks/useSelectedScan";
import { useAppConfig } from "../server/useAppConfig";
import { useScans } from "../server/useScans";
import { getScanDisplayName } from "../utils/scan";
import { useScansDir } from "../utils/useScansDir";

import styles from "./ScanPanel.module.css";
import { ScanPanelBody } from "./ScanPanelBody";
import { ScanPanelTitle } from "./ScanPanelTitle";

export const ScanPanel: React.FC = () => {
  const config = useAppConfig();
  const scansDir = config.scans.dir;
  const {
    displayScansDir,
    resolvedScansDir,
    resolvedScansDirSource,
    setScansDir,
  } = useScansDir(true);
  // Load server data
  const { loading: scansLoading } = useScans(resolvedScansDir);
  const { loading: scanLoading, data: selectedScan, error } = useSelectedScan();

  const loading = scansLoading || scanLoading;

  // Set document title with scan location
  useDocumentTitle(getScanDisplayName(selectedScan, scansDir), "Scans");

  // Clear scan state from the store on mount
  const clearScanState = useStore((state) => state.clearScanState);
  useEffect(() => {
    clearScanState();
    // TODO: lint react-hooks/exhaustive-deps - should we just add clearScanState to the dependencies
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
        scansDir={displayScansDir}
        scansDirSource={resolvedScansDirSource}
        setScansDir={setScansDir}
      />
      <LoadingBar loading={!!loading} />
      {error && <ErrorPanel title="Error Loading Scan" error={error} />}
      {!error && selectedScan && (
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
