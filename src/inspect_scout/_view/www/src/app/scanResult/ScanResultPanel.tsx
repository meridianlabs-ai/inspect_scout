import { clsx } from "clsx";
import { FC, useEffect } from "react";
import { useParams } from "react-router-dom";

import { ActivityBar } from "../../components/ActivityBar";
import {
  getRelativePathFromParams,
  parseScanResultPath,
} from "../../router/url";
import { useStore } from "../../state/store";
import { Navbar } from "../navbar/Navbar";

import styles from "./ScanResultPanel.module.css";

export const ScanResultPanel: FC = () => {
  const params = useParams<{ "*": string }>();
  const relativePath = getRelativePathFromParams(params);
  const { scanPath, scanResultUuid } = parseScanResultPath(relativePath);

  const singleFileMode = useStore((state) => state.singleFileMode);
  const loading = useStore((state) => state.loading);

  const resultsDir = useStore((state) => state.resultsDir);
  const setResultsDir = useStore((state) => state.setResultsDir);

  const setScans = useStore((state) => state.setScans);
  const api = useStore((state) => state.api);

  useEffect(() => {
    const fetchScans = async () => {
      if (resultsDir === undefined) {
        const scansInfo = await api?.getScans();
        if (scansInfo) {
          setResultsDir(scansInfo.results_dir);
          setScans(scansInfo.scans);
        }
      }
    };
    void fetchScans();
  }, [resultsDir, relativePath, api, setResultsDir, setScans]);

  return (
    <div className={clsx(styles.root)}>
      {singleFileMode || <Navbar />}
      <ActivityBar animating={!!loading} />
      <div>Scan Result UUID: {scanResultUuid || "None"}</div>
      <div>Scan Path: {scanPath}</div>
    </div>
  );
};
