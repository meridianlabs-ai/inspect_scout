import { skipToken } from "@tanstack/react-query";

import { useAsyncDataFromQuery } from "@tsmono/react/hooks";
import { AsyncData } from "@tsmono/util";

import { useApi } from "../../state/store";
import { Status } from "../../types/api-types";

type ScanParams = {
  scansDir: string;
  scanPath: string;
};

// Fetches scan status from the server by location
export const useScan = (
  params: ScanParams | typeof skipToken
): AsyncData<Status> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey:
      params === skipToken
        ? [skipToken]
        : ["scan", params.scansDir, params.scanPath, "scans-inv"],
    queryFn:
      params === skipToken
        ? skipToken
        : () => api.getScan(params.scansDir, params.scanPath),
    staleTime: 10000,
  });
};
