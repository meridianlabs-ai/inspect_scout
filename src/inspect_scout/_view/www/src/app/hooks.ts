import { ColumnTable } from "arquero";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { getRelativePathFromParams, parseScanResultPath } from "../router/url";
import { useStore } from "../state/store";
import { AsyncData, data, loading } from "../utils/asyncData";

import { parseScanResultData, parseScanResultSummaries } from "./arrowHelpers";
import {
  ScanResultData,
  ScanResultInputData,
  ScanResultSummary,
} from "./types";

export const useSelectedScanner = () => {
  const selectedScanner = useStore((state) => state.selectedScanner);
  const selectedScan = useStore((state) => state.selectedScanStatus);
  const defaultScanner = useMemo(() => {
    if (selectedScan) {
      const scanners = Object.keys(selectedScan.summary.scanners);
      return scanners.length > 0 ? scanners[0] : undefined;
    }
  }, [selectedScan, selectedScan?.summary.scanners]);

  return selectedScanner || defaultScanner;
};

export const useSelectedScanResultData = (
  // TODO: We need `| undefined` both on the input param as well as on the output
  // in order to honor the rules of hooks when the caller doesn't YET have the uuid.
  // Better would be to refactor the parent so that it doesn't even render until
  // it has the params so that it can avoid the hook call altogether.
  scanResultUuid: string | undefined
): AsyncData<ScanResultData | undefined> => {
  const getSelectedScanResultData = useStore(
    (state) => state.getSelectedScanResultData
  );

  // Get the column data for the selected scanner
  const selectedScanner = useSelectedScanner();
  // TODO: In this case, it's not really that we may not have the data initially.
  // It's that the return type of getSelectedScanResultData is | undefined. We really
  // want to be able to assert that it had better be set if we're in this hook ...
  // rather than designing this hook to be able to "stall" until its needs are met.
  const selectedScanResultData = getSelectedScanResultData(selectedScanner);

  return useScanResultData(selectedScanResultData, scanResultUuid);
};

export const useSelectedScanResultInputData = ():
  | ScanResultInputData
  | undefined => {
  const params = useParams<{ "*": string }>();
  const relativePath = getRelativePathFromParams(params);
  const { scanResultUuid } = parseScanResultPath(relativePath);

  const getSelectedScanResultInput = useStore(
    (state) => state.getSelectedScanResultInputData
  );

  return scanResultUuid
    ? getSelectedScanResultInput(scanResultUuid)
    : undefined;
};

export const useScanResultSummaries = (columnTable?: ColumnTable) => {
  // First see if we've already decoded these
  const selectedScanner = useSelectedScanner();
  const getSelectedScanResultSummaries = useStore(
    (state) => state.getSelectedScanResultSummaries
  );
  const setSelectedScanResultSummaries = useStore(
    (state) => state.setSelectedScanResultSummaries
  );

  const [scanResultSummaries, setScanResultsSummaries] = useState<
    ScanResultSummary[]
  >([]);
  const [isLoading, setIsLoading] = useState(false);

  const rowData = useMemo(() => columnTable?.objects(), [columnTable]);

  useEffect(() => {
    // If empty, set empty and return
    if (rowData?.length === 0) {
      setScanResultsSummaries([]);
      setSelectedScanResultSummaries(selectedScanner, []);
      setIsLoading(false);
      return;
    }

    // Use the existing previews if available
    const existingPreviews = getSelectedScanResultSummaries(selectedScanner);
    if (existingPreviews) {
      setScanResultsSummaries(existingPreviews);
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    setIsLoading(true);

    const run = async () => {
      try {
        const result = await parseScanResultSummaries(rowData || []);
        if (!cancelled) {
          setScanResultsSummaries(result);
          setSelectedScanResultSummaries(selectedScanner, result);
          setIsLoading(false);
        }
      } catch (error) {
        if (!cancelled) {
          console.error("Error parsing scanner previews:", error);
          setScanResultsSummaries([]);
          setSelectedScanResultSummaries(selectedScanner, []);
          setIsLoading(false);
        }
      }
    };

    void run();

    return () => {
      cancelled = true;
    };
  }, [
    rowData,
    selectedScanner,
    getSelectedScanResultSummaries,
    setSelectedScanResultSummaries,
  ]);

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
