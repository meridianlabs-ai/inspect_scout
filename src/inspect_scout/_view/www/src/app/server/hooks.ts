import {
  InfiniteData,
  keepPreviousData,
  useInfiniteQuery,
  UseInfiniteQueryResult,
  useQueryClient,
} from "@tanstack/react-query";
import { SortingState } from "@tanstack/react-table";
import { ColumnTable } from "arquero";
import { useMemo } from "react";

import type { Condition, OrderByModel } from "../../query";
import { useApi } from "../../state/store";
import { Status } from "../../types";
import { Transcript, TranscriptsResponse } from "../../types/api-types";
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

/**
 * Returns transcripts dir for use in components after data loaded globally.
 *
 * Use this hook in regular components throughout the app. Assumes the async
 * data has already been loaded at app initialization via useServerTranscriptsDirAsync.
 * Throws if data not yet available.
 *
 * @throws Error if transcripts dir not loaded
 */
export const useServerTranscriptsDir = (): string => {
  const { data } = useServerTranscriptsDirAsync();
  if (!data) throw new Error(`Must find transcripts dir`);
  return data;
};

/**
 * Loads transcripts dir asynchronously at app initialization.
 *
 * Use this hook only at the top of the app before rendering to load the
 * transcripts dir data globally. After this completes, all other components
 * should use useServerTranscriptsDir to access the loaded value synchronously.
 *
 * @returns AsyncData with loading states for initial data fetch
 */
export const useServerTranscriptsDirAsync = (): AsyncData<string> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey: ["transcripts-dir"],
    queryFn: async () => await api.getTranscriptsDir(),
    staleTime: 10000,
    placeholderData: keepPreviousData,
  });
};

export const useServerTranscripts = (
  location: string,
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

export const useServerTranscript = (
  location: string | undefined,
  id: string | undefined
): AsyncData<Transcript> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey: ["transcript", location, id],
    queryFn: () => api.getTranscript(location!, id!),
    enabled: !!location && !!id,
    staleTime: Infinity,
  });
};

export const useServerTranscriptsInfinite = (
  location?: string,
  pageSize: number = 50,
  filter?: Condition,
  sorting?: SortingState
): UseInfiniteQueryResult<
  InfiniteData<TranscriptsResponse, { [key: string]: unknown } | undefined>,
  Error
> => {
  const api = useApi();

  const orderBy = useMemo(
    () => (sorting ? sortingStateToOrderBy(sorting) : undefined),
    [sorting]
  );

  return useInfiniteQuery({
    queryKey: ["transcripts-infinite", location, filter, orderBy, pageSize],
    queryFn: async ({ pageParam }) => {
      const pagination = pageParam
        ? { limit: pageSize, cursor: pageParam, direction: "forward" as const }
        : { limit: pageSize, cursor: null, direction: "forward" as const };

      return await api.getTranscripts(
        location ?? "",
        filter,
        orderBy,
        pagination
      );
    },
    initialPageParam: undefined as undefined | { [key: string]: unknown },
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    staleTime: 10 * 60 * 1000,
    refetchInterval: 10 * 60 * 1000,
    enabled: !!location,
    placeholderData: keepPreviousData,
  });
};
