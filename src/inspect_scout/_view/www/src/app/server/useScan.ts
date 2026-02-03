import { skipToken } from "@tanstack/react-query";

import { useApi } from "../../state/store";
import { Status } from "../../types/api-types";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";

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
        : ["scan", params.scansDir, params.scanPath],
    queryFn:
      params === skipToken
        ? skipToken
        : () => api.getScan(params.scansDir, params.scanPath),
    staleTime: 10000,
  });
};
