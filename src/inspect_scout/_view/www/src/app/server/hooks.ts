import { keepPreviousData, useQueryClient } from "@tanstack/react-query";
import { SortingState } from "@tanstack/react-table";
import { ColumnTable } from "arquero";
import { useMemo } from "react";

import type { Condition, OrderByModel } from "../../query";
import { useApi } from "../../state/store";
import { Status } from "../../types";
import { TranscriptsResponse } from "../../types/api-types";
import { decodeArrowBytes } from "../../utils/arrow";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";
import { ScanResultInputData } from "../types";
import { expandResultsetRows } from "../utils/arrow";

const sortingStateToOrderBy = (sorting: SortingState): OrderByModel[] =>
  sorting.map((s) => ({ column: s.id, direction: s.desc ? "DESC" : "ASC" }));

// Returns the server's configured scans directory
export const useServerScansDir = (): AsyncData<string> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey: ["scans-dir"],
    queryFn: async () => await api.getScansDir(),
    staleTime: Infinity,
  });
};

// Lists the available scans from the server and stores in state
export const useServerScans = (): AsyncData<Status[]> => {
  const api = useApi();
  const queryClient = useQueryClient();
  const { data: scansDir } = useServerScansDir();

  return useAsyncDataFromQuery({
    queryKey: ["scans", scansDir],
    queryFn: async () => {
      const scans = await api.getScans(scansDir);
      for (const scan of scans) {
        queryClient.setQueryData(["scan", scan.location], scan);
      }
      return scans;
    },
    enabled: scansDir !== undefined,
    staleTime: 10000,
    refetchInterval: 10000,
  });
};

// Fetches scan status from the server by location
export const useServerScan = (
  location: string | undefined
): AsyncData<Status> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey: ["scan", location],
    queryFn: () => api.getScan(location!), // The ! is safe because of enabled below
    enabled: !!location,
    staleTime: 10000,
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
  location?: string,
  filter?: Condition,
  sorting?: SortingState
): AsyncData<TranscriptsResponse> => {
  const api = useApi();

  const orderBy = useMemo(
    () => (sorting ? sortingStateToOrderBy(sorting) : undefined),
    [sorting]
  );

  return useAsyncDataFromQuery({
    queryKey: ["transcripts", location, filter, orderBy],
    queryFn: async () => await api.getTranscripts(location, filter, orderBy),
    staleTime: 10 * 60 * 1000,
    refetchInterval: 10 * 60 * 1000,
    placeholderData: keepPreviousData,
  });
};
