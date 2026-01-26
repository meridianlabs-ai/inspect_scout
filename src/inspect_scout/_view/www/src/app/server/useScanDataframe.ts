import { skipToken } from "@tanstack/react-query";
import { ColumnTable } from "arquero";

import { useApi } from "../../state/store";
import { decodeArrowBytes } from "../../utils/arrow";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";
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
        ? ["scanDataframe", skipToken, skipToken, skipToken]
        : ["scanDataframe", params.scansDir, params.scanPath, params.scanner],
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
