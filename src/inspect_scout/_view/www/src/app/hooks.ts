import { useEffect } from "react";

import { useStore } from "../state/store";
import { useParams } from "react-router-dom";
import { getRelativePathFromParams } from "../router/url";

export const useServerScans = () => {
  const api = useStore((state) => state.api);
  const setScans = useStore((state) => state.setScans);
  const setResultsDir = useStore((state) => state.setResultsDir);

  useEffect(() => {
    const fetchScans = async () => {
      const scansInfo = await api?.getScans();
      if (scansInfo) {
        setResultsDir(scansInfo.results_dir);
        setScans(scansInfo.scans);
      }
    };
    void fetchScans();
  }, [api, setScans, setResultsDir]);
};

export const useServerScanner = () => {
  const params = useParams<{ "*": string }>();
  const relativePath = getRelativePathFromParams(params);

  const setSelectedScan = useStore((state) => state.setSelectedResults);
  const api = useStore((state) => state.api);

  useEffect(() => {
    const fetchScans = async () => {
      const scansInfo = await api?.getScan(relativePath);
      if (scansInfo) {
        setSelectedScan(scansInfo);
      }
    };
    void fetchScans();
  }, [relativePath, api, setSelectedScan]);
};
