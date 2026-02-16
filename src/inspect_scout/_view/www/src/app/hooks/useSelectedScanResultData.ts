import { ColumnTable } from "arquero";
import { useEffect, useMemo, useState } from "react";

import { AsyncData, data, loading } from "../../utils/asyncData";
import { ScanResultData } from "../types";
import { parseScanResultData } from "../utils/arrowHelpers";

import { useSelectedScanDataframe } from "./useSelectedScanDataframe";

export const useSelectedScanResultData = (
  scanResultUuid: string | undefined
): AsyncData<ScanResultData | undefined> => {
  const { data: columnTable } = useSelectedScanDataframe();
  return useScanResultData(columnTable, scanResultUuid);
};

const useScanResultData = (
  // TODO: We need `| undefined` both on the input param as well as on the output
  // in order to honor the rules of hooks when the caller doesn't YET have the uuid.
  // Better would be to refactor the parent so that it doesn't even render until
  // it has the params so that it can avoid the hook call altogether.
  columnTable: ColumnTable | undefined,
  rowIdentifier: string | undefined
): AsyncData<ScanResultData | undefined> => {
  const [scanResultData, setScanResultData] = useState<
    ScanResultData | undefined
  >(undefined);
  const [isLoading, setIsLoading] = useState(false);

  const filtered = useMemo((): ColumnTable | undefined => {
    // Not a valid index
    if (!rowIdentifier || !columnTable) {
      return undefined;
    }

    // Empty table
    if (columnTable.columnNames().length === 0) {
      return undefined;
    }

    const filtered = columnTable
      .params({ targetUuid: rowIdentifier })
      .filter(
        (d: { _rowIdentifier: string }, $: { targetUuid: string }) =>
          d._rowIdentifier === $.targetUuid
      );

    if (filtered.numRows() === 0) {
      return undefined;
    }

    return filtered;
  }, [columnTable, rowIdentifier]);

  useEffect(() => {
    if (!filtered) {
      // TODO: lint react-hooks/set-state-in-effect - consider if fixing this violation makes sense
      /* eslint-disable react-hooks/set-state-in-effect */
      setScanResultData(undefined);
      setIsLoading(false);
      /* eslint-enable react-hooks/set-state-in-effect */
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
