import { useQueryClient } from "@tanstack/react-query";
import { ColumnTable } from "arquero";

import { useMapAsyncData } from "../../hooks/useMapAsyncData";
import { useApi } from "../../state/store";
import { Scans, Status } from "../../types";
import { decodeArrowBytes } from "../../utils/arrow";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";
import { ScanResultInputData } from "../types";
import { expandResultsetRows } from "../utils/arrow";

// Lists the available scans from the server and stores in state
export const useServerScans = (): AsyncData<Scans> => {
  const api = useApi();
  const queryClient = useQueryClient();

  return useAsyncDataFromQuery({
    queryKey: ["scans"],
    queryFn: async () => {
      const scans = await api.getScans();
      for (const scan of scans.scans) {
        queryClient.setQueryData(["scan", scan.location], scan);
      }
      return scans;
    },
    staleTime: 5000,
    refetchInterval: 5000,
  });
};

// TODO: This implementation is temporary until we break results_dir out from the
// scans endpoint
export const useResultsDir = (): AsyncData<string | undefined> =>
  useMapAsyncData(useServerScans(), (x) => x.results_dir);

// Fetches scan status from the server by location
export const useServerScan = (
  location: string | undefined
): AsyncData<Status> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey: ["scan", location],
    queryFn: () => api.getScan(location!), // The ! is safe because of enabled below
    enabled: !!location,
    staleTime: 5000,
    // TODO: We need to think through refetchInterval. If the specific scan was retrieved
    // by the scans hook above, it'll already have a refresh. If it was not, however,
    // we'll still want it to refresh, but we don't want the hooks to compete. Hmmm.
  });
};

// Fetches scanner dataframe from the server by location and scanner
export const useServerScanDataframe = (
  location: string | undefined,
  scanner: string | undefined
): AsyncData<ColumnTable> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey: ["scanDataframe", location, scanner],
    queryFn: async () =>
      expandResultsetRows(
        decodeArrowBytes(await api.getScannerDataframe(location!, scanner!))
      ),
    enabled: !!location && !!scanner,
    staleTime: Infinity,
  });
};

export const useServerScanDataframeInput = (
  location: string | undefined,
  scanner: string | undefined,
  uuid: string | undefined
): AsyncData<ScanResultInputData> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey: ["scanDataframeInput", location, scanner, uuid],
    queryFn: () => api.getScannerDataframeInput(location!, scanner!, uuid!),
    enabled: !!location && !!scanner && !!uuid,
    staleTime: Infinity,
  });
};

export const useServerTranscriptsDir = (): AsyncData<string> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey: ["transcripts-dir"],
    queryFn: async () => await api.getTranscriptsDir(),
    staleTime: 10000,
  });
};

export const useServerTranscripts = (
  location: string | undefined
): AsyncData<unknown[]> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey: ["transcripts", location],
    queryFn: async () => await api.getTranscripts(location),
    staleTime: 10 * 60 * 1000,
    refetchInterval: 10 * 60 * 1000,
  });
};
