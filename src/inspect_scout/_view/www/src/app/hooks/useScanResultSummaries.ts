import { ColumnTable } from "arquero";
import { useState, useMemo, useEffect } from "react";

import { ScanResultSummary } from "../types";
import { parseScanResultSummaries } from "../utils/arrowHelpers";

export const useScanResultSummaries = (columnTable?: ColumnTable) => {
  const [scanResultSummaries, setScanResultsSummaries] = useState<
    ScanResultSummary[]
  >([]);
  const [isLoading, setIsLoading] = useState(false);

  const rowData = useMemo(() => columnTable?.objects(), [columnTable]);

  useEffect(() => {
    if (!rowData || rowData.length === 0) {
      // TODO: lint react-hooks/set-state-in-effect - consider if fixing this violation makes sense
      /* eslint-disable react-hooks/set-state-in-effect */
      setScanResultsSummaries([]);
      setIsLoading(false);
      /* eslint-enable react-hooks/set-state-in-effect */
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
