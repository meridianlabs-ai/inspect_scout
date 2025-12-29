import { ColumnTable } from "arquero";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { useMapAsyncData } from "../hooks/useMapAsyncData";
import {
  getRelativePathFromParams,
  parseScanResultPath,
  parseTranscriptParams,
} from "../router/url";
import { useStore } from "../state/store";
import { Status } from "../types";
import { AsyncData, data, loading } from "../utils/asyncData";
import { join } from "../utils/uri";

import { parseScanResultData, parseScanResultSummaries } from "./arrowHelpers";
import {
  useServerScansDir,
  useServerScan,
  useServerScanDataframe,
  useServerScanDataframeInput,
} from "./server/hooks";
import {
  ScanResultData,
  ScanResultInputData,
  ScanResultSummary,
} from "./types";

const useSelectedScanLocation = () => {
  const params = useParams<{ "*": string }>();
  const relativePath = getRelativePathFromParams(params);
  const { scanPath } = parseScanResultPath(relativePath);
  const { data: resultsDir } = useServerScansDir();
  const location = join(scanPath, resultsDir);
  // E.g.:
  //  scanPath:   "scan_id=3G7xoo4YV3KffYkZEtWqGw"
  //  resultsDir: "/Users/me/project/scans"
  //  location:   "/Users/me/project/scans/scan_id=3G7xoo4YV3KffYkZEtWqGw"

  return { location, scanPath };
};

export const useSelectedScan = (): AsyncData<Status> => {
  const { location, scanPath } = useSelectedScanLocation();

  // Set selectedScanLocation for nav restoration
  const setSelectedScanLocation = useStore(
    (state) => state.setSelectedScanLocation
  );
  useEffect(() => {
    if (scanPath) {
      setSelectedScanLocation(scanPath);
    }
  }, [scanPath, setSelectedScanLocation]);

  return useServerScan(location);
};

export const useSelectedScanner = (): AsyncData<string> => {
  const selectedScanner = useStore((state) => state.selectedScanner);
  // TODO: This is a little bogus since we really don't need to do the server fetch
  // if we found the selectedScanner from zustand. Alas, the rules of hooks.
  const defaultScanner = useMapAsyncData(
    useSelectedScan(),
    _get_default_scanner
  );

  const selectedScannerAsyncData = useMemo(
    () => (selectedScanner ? data(selectedScanner) : undefined),
    [selectedScanner]
  );

  return selectedScannerAsyncData ?? defaultScanner;
};

const _get_default_scanner = (s: Status): string => {
  const result = s.summary.scanners
    ? Object.keys(s.summary.scanners)[0]
    : undefined;
  if (!result) {
    throw new Error("Scan must have a scanner");
  }
  return result;
};
export const useSelectedScanDataframe = (): AsyncData<ColumnTable> => {
  const { location } = useSelectedScanLocation();
  const scanner = useSelectedScanner();

  return useServerScanDataframe(location, scanner.data);
};

export const useSelectedScanResultData = (
  scanResultUuid: string | undefined
): AsyncData<ScanResultData | undefined> => {
  const { data: columnTable } = useSelectedScanDataframe();
  return useScanResultData(columnTable, scanResultUuid);
};

export const useSelectedScanResultInputData =
  (): AsyncData<ScanResultInputData> => {
    const { location } = useSelectedScanLocation();
    const scanner = useSelectedScanner();
    const params = useParams<{ "*": string }>();
    const relativePath = getRelativePathFromParams(params);
    const { scanResultUuid } = parseScanResultPath(relativePath);

    return useServerScanDataframeInput(location, scanner.data, scanResultUuid);
  };

export const useTranscriptRoute = (): {
  transcriptsDir?: string;
  transcriptId?: string;
} => {
  const params = useParams<{ transcriptsDir?: string; transcriptId?: string }>();
  const setUserTranscriptsDir = useStore(
    (state) => state.setUserTranscriptsDir
  );

  const route = useMemo(() => parseTranscriptParams(params), [params]);

  useEffect(() => {
    if (route.transcriptsDir) {
      setUserTranscriptsDir(route.transcriptsDir);
    }
  }, [route.transcriptsDir, setUserTranscriptsDir]);

  return route;
};

export const useScanResultSummaries = (columnTable?: ColumnTable) => {
  const [scanResultSummaries, setScanResultsSummaries] = useState<
    ScanResultSummary[]
  >([]);
  const [isLoading, setIsLoading] = useState(false);

  const rowData = useMemo(() => columnTable?.objects(), [columnTable]);

  useEffect(() => {
    if (!rowData || rowData.length === 0) {
      setScanResultsSummaries([]);
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    setIsLoading(true);

    const run = async () => {
      try {
        const result = await parseScanResultSummaries(rowData);
        if (!cancelled) {
          setScanResultsSummaries(result);
          setIsLoading(false);
        }
      } catch (error) {
        if (!cancelled) {
          console.error("Error parsing scanner previews:", error);
          setScanResultsSummaries([]);
          setIsLoading(false);
        }
      }
    };

    void run();

    return () => {
      cancelled = true;
    };
  }, [rowData]);

  return { data: scanResultSummaries, isLoading };
};

const useScanResultData = (
  // TODO: We need `| undefined` both on the input param as well as on the output
  // in order to honor the rules of hooks when the caller doesn't YET have the uuid.
  // Better would be to refactor the parent so that it doesn't even render until
  // it has the params so that it can avoid the hook call altogether.
  columnTable: ColumnTable | undefined,
  scanResultUuid: string | undefined
): AsyncData<ScanResultData | undefined> => {
  const [scanResultData, setScanResultData] = useState<
    ScanResultData | undefined
  >(undefined);
  const [isLoading, setIsLoading] = useState(false);

  const filtered = useMemo((): ColumnTable | undefined => {
    // Not a valid index
    if (!scanResultUuid || !columnTable) {
      return undefined;
    }

    // Empty table
    if (columnTable.columnNames().length === 0) {
      return undefined;
    }

    const filtered = columnTable
      .params({ targetUuid: scanResultUuid })
      .filter(
        (d: { uuid: string }, $: { targetUuid: string }) =>
          d.uuid === $.targetUuid
      );

    if (filtered.numRows() === 0) {
      return undefined;
    }

    return filtered;
  }, [columnTable, scanResultUuid]);

  useEffect(() => {
    if (!filtered) {
      setScanResultData(undefined);
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    setIsLoading(true);

    const run = async () => {
      try {
        const result = await parseScanResultData(filtered);
        if (!cancelled) {
          setScanResultData(result);
          setIsLoading(false);
        }
      } catch (error) {
        if (!cancelled) {
          console.error("Error parsing scanner data:", error);
          setScanResultData(undefined);
          setIsLoading(false);
        }
      }
    };

    void run();

    return () => {
      cancelled = true;
    };
  }, [filtered]);

  return isLoading ? loading : data(scanResultData);
};
