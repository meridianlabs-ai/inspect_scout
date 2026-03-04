import { skipToken } from "@tanstack/react-query";
import { ColumnTable } from "arquero";

import { useAsyncDataFromQuery } from "@tsmono/react/hooks";
import { decodeArrowBytes, AsyncData } from "@tsmono/util";

import { useApi } from "../../state/store";
import { expandResultsetRows } from "../utils/arrow";

type ScanDataframeParams = {
  scansDir: string;
  scanPath: string;
  scanner: string;
};

// Fetches scanner dataframe from the server by location and scanner
export const useScanDataframe = (
  params: ScanDataframeParams | typeof skipToken
): AsyncData<ColumnTable> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey:
      params === skipToken
        ? [skipToken]
        : [
            "scanDataframe",
            params.scansDir,
            params.scanPath,
            params.scanner,
            "scans-inv",
          ],
    queryFn:
      params === skipToken
        ? skipToken
        : async () =>
            expandResultsetRows(
              decodeArrowBytes(
                await api.getScannerDataframe(
                  params.scansDir,
                  params.scanPath,
                  params.scanner
                )
              )
            ),
    staleTime: Infinity,
  });
};
