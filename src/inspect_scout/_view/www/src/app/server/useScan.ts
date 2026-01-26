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
        ? ["scan", skipToken, skipToken]
        : ["scan", params.scansDir, params.scanPath],
    queryFn:
      params === skipToken
        ? skipToken
        : () => api.getScan(params.scansDir, params.scanPath),
    staleTime: 10000,
    // TODO: We need to think through refetchInterval. If the specific scan was retrieved
    // by the scans hook above, it'll already have a refresh. If it was not, however,
    // we'll still want it to refresh, but we don't want the hooks to compete. Hmmm.
  });
};
