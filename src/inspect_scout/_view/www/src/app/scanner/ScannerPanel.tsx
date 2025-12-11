import clsx from "clsx";
import React, { useEffect } from "react";
import { useSearchParams } from "react-router-dom";

import { ActivityBar } from "../../components/ActivityBar";
import { ExtendedFindProvider } from "../../components/ExtendedFindProvider";
import { getScannerParam } from "../../router/url";
import { useStore } from "../../state/store";
import { Navbar } from "../navbar/Navbar";
import {
  useServerScanner,
  useServerScannerDataframe,
  useServerScans,
} from "../server/hooks";

import styles from "./ScannerPanel.module.css";
import { ScannerPanelBody } from "./ScannerPanelBody";
import { ScannerPanelTitle } from "./ScannerPanelTitle";

export const ScannerPanel: React.FC = () => {
  // Load server data
  useServerScans();
  useServerScanner();
  useServerScannerDataframe();
  const loading = useStore((state) => state.loading);

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
  const selectedStatus = useStore((state) => state.selectedScanStatus);
  return (
    <div className={clsx(styles.root)}>
      <Navbar />
      <ActivityBar animating={!!loading} />
      {selectedStatus && (
        <>
          <ScannerPanelTitle />
          <ExtendedFindProvider>
            <ScannerPanelBody />
          </ExtendedFindProvider>
        </>
      )}
    </div>
  );
};
