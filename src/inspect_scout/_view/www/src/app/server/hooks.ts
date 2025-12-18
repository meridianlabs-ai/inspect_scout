import { useEffect } from "react";
import { useParams } from "react-router-dom";

import {
  getRelativePathFromParams,
  parseScanResultPath,
} from "../../router/url";
import { useApi, useStore } from "../../state/store";
import { TranscriptInfo } from "../../types";
import { decodeArrowBytes } from "../../utils/arrow";
import { join } from "../../utils/uri";
import { useSelectedScanner } from "../hooks";
import { expandResultsetRows } from "../utils/arrow";

// Lists the available scans from the server and stores in state
export const useServerScans = () => {
  // api
  const api = useApi();

  // state
  const resultsDir = useStore((state) => state.resultsDir);

  // setters
  const setScans = useStore((state) => state.setScans);
  const setResultsDir = useStore((state) => state.setResultsDir);
  const setLoading = useStore((state) => state.setLoading);
  const setError = useStore((state) => state.setError);
  const clearError = useStore((state) => state.clearError);

  useEffect(() => {
    const fetchScans = async () => {
      // Update loading and error state
      clearError("scanjobs");
      setLoading(true);

      try {
        // Fetch the data
        const scansInfo = await api.getScans();
        if (scansInfo) {
          // Update state
          setResultsDir(scansInfo.results_dir);
          setScans(scansInfo.scans);
        }
      } catch (e) {
        // Notify app of error
        setError("scanjobs", e?.toString());
      } finally {
        // Stop loading
        setLoading(false);
      }
    };

    // Only fetch if we don't already have data retrieved
    if (!resultsDir) {
      void fetchScans();
    }
  }, [api, resultsDir, setScans, setResultsDir]);
};

// Fetches the selected scan status from the server and stores in state
export const useServerScan = () => {
  // api
  const api = useApi();

  // Path information
  const params = useParams<{ "*": string }>();
  const relativePath = getRelativePathFromParams(params);
  const { scanPath } = parseScanResultPath(relativePath);

  // State
  const resultsDir = useStore((state) => state.resultsDir);
  const selectedStatus = useStore((state) => state.selectedScanStatus);
  const scans = useStore((state) => state.scans);

  // Setters
  const setSelectedScanLocation = useStore(
    (state) => state.setSelectedScanLocation
  );
  const setSelectedScanStatus = useStore(
    (state) => state.setSelectedScanStatus
  );
  const setLoading = useStore((state) => state.setLoading);
  const setError = useStore((state) => state.setError);
  const clearError = useStore((state) => state.clearError);

  useEffect(() => {
    if (scanPath && !selectedStatus) {
      // Clear any existing errors
      clearError("scanner");

      // Check the list of scans that are already loaded
      const location = join(scanPath, resultsDir);
      const scansInfo = scans.find((s) => s.location === location);
      if (scansInfo) {
        // Already in store, use it
        setSelectedScanStatus(scansInfo);
      } else {
        // Fetch from server if not in store
        const fetchScan = async () => {
          setLoading(true);
          try {
            const status = await api.getScan(location);
            setSelectedScanStatus(status);
          } catch (e) {
            setError("scanner", e?.toString());
          } finally {
            setLoading(false);
          }
        };
        void fetchScan();
      }

      // Select this scan
      setSelectedScanLocation(scanPath);
    }
  }, [
    relativePath,
    api,
    setSelectedScanStatus,
    scanPath,
    selectedStatus,
    scans,
    resultsDir,
  ]);
};

// Fetch scanner dataframe from the server and stores in state
export const useServerScanDataframe = () => {
  // api
  const api = useApi();

  // Path information
  const params = useParams<{ "*": string }>();
  const relativePath = getRelativePathFromParams(params);
  const { scanPath } = parseScanResultPath(relativePath);

  // State
  const singleFileMode = useStore((state) => state.singleFileMode);
  const resultsDir = useStore((state) => state.resultsDir);
  const selectedScanner = useSelectedScanner();

  // Setters
  const setLoadingData = useStore((state) => state.setLoadingData);
  const setSelectedScanResultData = useStore(
    (state) => state.setSelectedScanResultData
  );
  const getSelectedScanResultData = useStore(
    (state) => state.getSelectedScanResultData
  );
  const setError = useStore((state) => state.setError);
  const clearError = useStore((state) => state.clearError);

  useEffect(() => {
    const fetchScannerDataframe = async () => {
      // Clear any existing errors
      clearError("dataframe");

      // See if we already have data
      const existingData = getSelectedScanResultData(selectedScanner);
      if (!scanPath || !selectedScanner || existingData) {
        return;
      }

      // Start loading (since we are going to fetch)
      setLoadingData(true);
      try {
        // If resultsDir is used, send an absolute path
        let location = scanPath;
        if (resultsDir) {
          location = join(scanPath, resultsDir);
        }

        // Request the raw data from the server
        const arrayBuffer = await api.getScannerDataframe(
          location,
          selectedScanner
        );

        // Pre-process result set rows to explode the results
        const table = decodeArrowBytes(arrayBuffer);

        const expandedTable = await expandResultsetRows(table);

        // Store in state
        setSelectedScanResultData(selectedScanner, expandedTable);
      } catch (e) {
        // Notify app of error
        setError("dataframe", e?.toString());
      } finally {
        // Stop progress
        setLoadingData(false);
      }
    };
    void fetchScannerDataframe();
  }, [
    api,
    scanPath,
    selectedScanner,
    resultsDir,
    singleFileMode,
    setLoadingData,
    setSelectedScanResultData,
    getSelectedScanResultData,
  ]);
};

export const useServerScanDataframeInput = () => {
  // api
  const api = useApi();

  // Path information
  const params = useParams<{ "*": string }>();
  const relativePath = getRelativePathFromParams(params);
  const { scanPath } = parseScanResultPath(relativePath);
  const { scanResultUuid } = parseScanResultPath(relativePath);

  // State
  const singleFileMode = useStore((state) => state.singleFileMode);
  const resultsDir = useStore((state) => state.resultsDir);
  const selectedScanner = useSelectedScanner();

  // Setters
  const setLoadingData = useStore((state) => state.setLoadingData);
  const setSelectedScanResultInputData = useStore(
    (state) => state.setSelectedScanResultInputData
  );
  const getSelectedScanResultInput = useStore(
    (state) => state.getSelectedScanResultInputData
  );
  const setError = useStore((state) => state.setError);
  const clearError = useStore((state) => state.clearError);

  useEffect(() => {
    const fetchScannerDataframeInput = async () => {
      // Clear any existing errors
      clearError("dataframe_input");

      // Not enough context to load
      if (!scanPath || !selectedScanner || !scanResultUuid) {
        return;
      }

      // See if we already have data
      const existingData = getSelectedScanResultInput(scanResultUuid);
      if (existingData) {
        return;
      }

      // Start loading (since we are going to fetch)
      setLoadingData(true);

      try {
        // If resultsDir is used, send an absolute path
        let location = scanPath;
        if (resultsDir) {
          location = join(scanPath, resultsDir);
        }

        // Request the raw data from the server
        const dfInput = await api.getScannerDataframeInput(
          location,
          selectedScanner,
          scanResultUuid
        );

        // Store in state
        setSelectedScanResultInputData(scanResultUuid, dfInput);
      } catch (e) {
        // Notify app of error
        setError("dataframe_input", e?.toString());
      } finally {
        // Stop progress
        setLoadingData(false);
      }
    };
    void fetchScannerDataframeInput();
  }, [
    api,
    scanPath,
    selectedScanner,
    resultsDir,
    singleFileMode,
    scanResultUuid,
    setLoadingData,
    setSelectedScanResultInputData,
    getSelectedScanResultInput,
  ]);
};

export const useServerTranscripts = () => {
  // api
  const api = useApi();

  // Transcripts
  const transcripts = useStore((state) => state.transcripts);
  const setTranscripts = useStore((state) => state.setTranscripts);

  // The loaded path to the transcripts directory
  const transcriptsDir = useStore((state) => state.transcriptsDir);
  const setTranscriptsDir = useStore((state) => state.setTranscriptsDir);

  // The user path to the transcripts database
  const transcriptsDatabasePath = useStore(
    (state) => state.transcriptsDatabasePath
  );
  const setTranscriptsDatabasePath = useStore(
    (state) => state.setTranscriptsDatabasePath
  );

  // Status/Error
  const setLoadingData = useStore((state) => state.setLoadingData);
  const setError = useStore((state) => state.setError);
  const clearError = useStore((state) => state.clearError);

  useEffect(() => {
    const fetchScannerDataframeInput = async () => {
      // Clear any existing errors
      clearError("transcripts");

      // See if we already have data
      if (
        transcripts === undefined ||
        transcriptsDir !== transcriptsDatabasePath
      ) {
        // Start loading (since we are going to fetch)
        setLoadingData(true);

        try {
          // Get the transcripts directory
          let queryTranscriptDir = transcriptsDatabasePath;
          if (!queryTranscriptDir) {
            queryTranscriptDir = await api.getTranscriptsDir();
            setTranscriptsDatabasePath(queryTranscriptDir);
          }

          // Request the raw data from the server
          const serverTranscripts =
            await api.getTranscripts(queryTranscriptDir);

          // TODO: 'convert' transcripts if needed.

          setTranscripts(serverTranscripts as TranscriptInfo[]);
          setTranscriptsDir(queryTranscriptDir);
        } catch (e) {
          // Notify app of error
          setError("transcripts", e?.toString());
        } finally {
          // Stop progress
          setLoadingData(false);
        }
      }
    };

    void fetchScannerDataframeInput();
  }, [
    api,
    transcriptsDatabasePath,
    transcriptsDir,
    transcripts,
    setLoadingData,
    setTranscripts,
    setError,
    clearError,
  ]);
};
