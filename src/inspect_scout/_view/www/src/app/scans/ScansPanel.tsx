import clsx from "clsx";
import React, { useEffect } from "react";
import { useSearchParams } from "react-router-dom";

import { ActivityBar } from "../../components/ActivityBar";
import { ExtendedFindProvider } from "../../components/ExtendedFindProvider";
import { getScannerParam } from "../../router/url";
import { useStore } from "../../state/store";
import { Navbar } from "../components/Navbar";
import {
  useServerScanDataframe,
  useServerScan,
  useServerScans,
} from "../server/hooks";

import styles from "./ScansPanel.module.css";
import { ScansPanelBody } from "./ScansPanelBody";
import { ScansPanelTitle } from "./ScansPanelTitle";

export const ScansPanel: React.FC = () => {
  // Load server data
  const scansData = useServerScans();
  const scanData = useServerScan();
  const dataframeData = useServerScanDataframe();

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

  // Render only if we have selected scan
  const selectedScanStatus = scanData.data;
  return (
    <div className={clsx(styles.root)}>
      <Navbar resultsDir={scansData.data?.resultsDir} />
      <ActivityBar animating={scansData.loading || scanData.loading} />
      {selectedScanStatus && (
        <>
          <ScansPanelTitle
            selectedStatus={selectedScanStatus}
            resultsDir={scansData.data?.resultsDir}
          />
          <ExtendedFindProvider>
            <ScansPanelBody
              selectedStatus={selectedScanStatus}
              dataframeData={dataframeData}
            />
          </ExtendedFindProvider>
        </>
      )}
    </div>
  );
};
