import clsx from "clsx";
import React, { useEffect } from "react";
import { useSearchParams } from "react-router-dom";

import { ActivityBar } from "../../components/ActivityBar";
import { ExtendedFindProvider } from "../../components/ExtendedFindProvider";
import { getScannerParam } from "../../router/url";
import { useStore } from "../../state/store";
import { useServerScanner, useServerScans } from "../hooks";
import { Navbar } from "../navbar/Navbar";

import styles from "./ScannerPanel.module.css";
import { ScannerPanelBody } from "./ScannerPanelBody";
import { ScannerPanelTitle } from "./ScannerPanelTitle";

export const ScannerPanel: React.FC = () => {
  useServerScans();
  useServerScanner();
  const loading = useStore((state) => state.loading);
  const setSelectedScanner = useStore((state) => state.setSelectedScanner);
  const [searchParams] = useSearchParams();
  const selectedResults = useStore((state) => state.selectedResults);

  // Sync URL query param with store state
  useEffect(() => {
    const scannerParam = getScannerParam(searchParams);
    if (scannerParam) {
      setSelectedScanner(scannerParam);
    }
  }, [searchParams, setSelectedScanner]);

  const clearScansState = useStore((state) => state.clearScansState);
  useEffect(() => {
    return () => {
      clearScansState();
    };
  }, [clearScansState]);

  return (
    <div className={clsx(styles.root)}>
      <Navbar />
      <ActivityBar animating={!!loading} />
      {selectedResults && (
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
