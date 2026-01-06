import {
  InfiniteData,
  keepPreviousData,
  QueryKey,
  useInfiniteQuery,
  UseInfiniteQueryResult,
  useQueryClient,
} from "@tanstack/react-query";
import { SortingState } from "@tanstack/react-table";
import { ColumnTable } from "arquero";
import { useMemo } from "react";

import type { Condition, OrderByModel } from "../../query";
import { useApi } from "../../state/store";
import {
  AppConfig,
  Status,
  ScanJobsResponse,
  Transcript,
  TranscriptsResponse,
} from "../../types/api-types";
import { decodeArrowBytes } from "../../utils/arrow";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";
import { ScanResultInputData } from "../types";
import { expandResultsetRows } from "../utils/arrow";

const sortingStateToOrderBy = (sorting: SortingState): OrderByModel[] =>
  sorting.map((s) => ({ column: s.id, direction: s.desc ? "DESC" : "ASC" }));

/**
 * Loads app config asynchronously at app initialization.
 *
 * Use this hook only at the top of the app before rendering to load config
 * data globally. After this completes, all other components should use
 * useConfig to access the loaded value synchronously.
 */
export const useConfigAsync = (): AsyncData<AppConfig> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey: ["config"],
    queryFn: () => api.getConfig(),
    staleTime: Infinity,
  });
};

/**
 * Returns app config for use in components after data loaded globally.
 *
 * Use this hook in regular components throughout the app. Assumes the async
 * data has already been loaded at app initialization via useConfigAsync.
 * Throws if data not yet available.
 */
export const useConfig = (): AppConfig => {
  const { data } = useConfigAsync();
  if (!data) throw new Error("Config not loaded");
  return data;
};

/** Returns the server's configured scans directory. */
export const useServerScansDir = (): string | undefined =>
  useConfig().scans_dir ?? undefined;

/** Returns transcripts dir for use in components after data loaded globally. */
export const useServerTranscriptsDir = (): string | undefined | null =>
  useConfig().transcripts_dir;

// Lists the available scans from the server and stores in state
export const useServerScans = (): AsyncData<Status[]> => {
  const api = useApi();
  const queryClient = useQueryClient();

  return useAsyncDataFromQuery({
    queryKey: ["scanjobs"],
    queryFn: async () => {
      const response = await api.getScans();
      for (const scan of response.items) {
        queryClient.setQueryData(["scanjob", scan.location], scan);
      }
      return response.items;
    },
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
    queryKey: ["scanjob", location],
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
    queryKey: ["scanjobDataframe", location, scanner],
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
    queryKey: ["scanjobDataframeInput", location, scanner, uuid],
    queryFn: () => api.getScannerDataframeInput(location!, scanner!, uuid!),
    enabled: !!location && !!scanner && !!uuid,
    staleTime: Infinity,
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
  location: string | undefined | null,
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

type CursorType = { [key: string]: unknown };

export const useServerTranscriptsInfinite = (
  location?: string | null,
  pageSize: number = 50,
  filter?: Condition,
  sorting?: SortingState
): UseInfiniteQueryResult<
  InfiniteData<TranscriptsResponse, CursorType | undefined>,
  Error
> => {
  const api = useApi();

  const orderBy = useMemo(
    () => (sorting ? sortingStateToOrderBy(sorting) : undefined),
    [sorting]
  );

  return useInfiniteQuery<
    TranscriptsResponse,
    Error,
    InfiniteData<TranscriptsResponse, CursorType | undefined>,
    QueryKey,
    CursorType | undefined
  >({
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
    initialPageParam: undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    staleTime: 10 * 60 * 1000,
    refetchInterval: 10 * 60 * 1000,
    enabled: !!location,
    placeholderData: keepPreviousData,
  });
};

export const useServerScansInfinite = (
  pageSize: number = 50,
  filter?: Condition,
  sorting?: SortingState
): UseInfiniteQueryResult<
  InfiniteData<ScanJobsResponse, CursorType | undefined>,
  Error
> => {
  const api = useApi();

  const orderBy = useMemo(
    () => (sorting ? sortingStateToOrderBy(sorting) : undefined),
    [sorting]
  );

  return useInfiniteQuery<
    ScanJobsResponse,
    Error,
    InfiniteData<ScanJobsResponse, CursorType | undefined>,
    QueryKey,
    CursorType | undefined
  >({
    queryKey: ["scanjobs-infinite", filter, orderBy, pageSize],
    queryFn: async ({ pageParam }) => {
      const pagination = pageParam
        ? { limit: pageSize, cursor: pageParam, direction: "forward" as const }
        : { limit: pageSize, cursor: null, direction: "forward" as const };

      return await api.getScans(filter, orderBy, pagination);
    },
    initialPageParam: undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    staleTime: 10000,
    refetchInterval: 10000,
    placeholderData: keepPreviousData,
  });
};
