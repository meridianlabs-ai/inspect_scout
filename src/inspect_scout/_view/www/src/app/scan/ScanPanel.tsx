import clsx from "clsx";
import React, { useEffect } from "react";
import { useParams } from "react-router-dom";

import { ActivityBar } from "../../components/ActivityBar";
import { ExtendedFindProvider } from "../../components/ExtendedFindProvider";
import { getRelativePathFromParams } from "../../router/url";
import { useStore } from "../../state/store";
import { Navbar } from "../navbar/Navbar";

import styles from "./ScanPanel.module.css";
import { ScanPanelBody } from "./ScanPanelBody";
import { ScanPanelTitle } from "./ScanPanelTitle";

export const ScanPanel: React.FC = () => {
  const params = useParams<{ "*": string }>();
  const relativePath = getRelativePathFromParams(params);
  const singleFileMode = useStore((state) => state.singleFileMode);

  const resultsDir = useStore((state) => state.resultsDir);
  const setResultsDir = useStore((state) => state.setResultsDir);

  const setSelectedScan = useStore((state) => state.setSelectedResults);
  const clearScanState = useStore((state) => state.clearScanState);

  const setScans = useStore((state) => state.setScans);
  const api = useStore((state) => state.api);
  const loading = useStore((state) => state.loading);

  useEffect(() => {
    const fetchScans = async () => {
      if (resultsDir === undefined) {
        const scansInfo = await api?.getScans();
        if (scansInfo) {
          setResultsDir(scansInfo.results_dir);
          setScans(scansInfo.scans);
        }
      }

      const scansInfo = await api?.getScan(relativePath);
      if (scansInfo) {
        setSelectedScan(scansInfo);
      }
    };
    void fetchScans();
  }, [resultsDir, relativePath, api, setSelectedScan, setResultsDir, setScans]);

  useEffect(() => {
    return () => {
      clearScanState();
    };
  }, []);

  return (
    <div className={clsx(styles.root)}>
      {singleFileMode || <Navbar />}
      <ActivityBar animating={!!loading} />
      <ScanPanelTitle />
      <ExtendedFindProvider>
        <ScanPanelBody />
      </ExtendedFindProvider>
    </div>
  );
};
