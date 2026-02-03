import {
  UseInfiniteQueryResult,
  InfiniteData,
  useInfiniteQuery,
  QueryKey,
  keepPreviousData,
  skipToken,
} from "@tanstack/react-query";
import { SortingState } from "@tanstack/react-table";
import { useMemo } from "react";

import { Condition } from "../../query";
import { useApi } from "../../state/store";
import { TranscriptsResponse } from "../../types/api-types";

import { CursorType, sortingStateToOrderBy } from ".";

type ServerTranscriptsInfiniteParams = {
  location: string;
  pageSize?: number;
  filter?: Condition;
  sorting?: SortingState;
};

export const useServerTranscriptsInfinite = (
  params: ServerTranscriptsInfiniteParams | typeof skipToken
): UseInfiniteQueryResult<
  InfiniteData<TranscriptsResponse, CursorType | undefined>,
  Error
> => {
  const api = useApi();

  const orderBy = useMemo(
    () =>
      params !== skipToken && params.sorting
        ? sortingStateToOrderBy(params.sorting)
        : undefined,
    [params]
  );

  const pageSize = params !== skipToken ? (params.pageSize ?? 50) : 50;

  return useInfiniteQuery<
    TranscriptsResponse,
    Error,
    InfiniteData<TranscriptsResponse, CursorType | undefined>,
    QueryKey,
    CursorType | undefined
  >({
    queryKey:
      params === skipToken
        ? [skipToken]
        : [
            "transcripts-infinite",
            "project-config",
            params.location,
            params.filter,
            orderBy,
            pageSize,
          ],
    queryFn:
      params === skipToken
        ? skipToken
        : async ({ pageParam }) => {
            const pagination = pageParam
              ? {
                  limit: pageSize,
                  cursor: pageParam,
                  direction: "forward" as const,
                }
              : {
                  limit: pageSize,
                  cursor: null,
                  direction: "forward" as const,
                };

            return await api.getTranscripts(
              params.location,
              params.filter,
              orderBy,
              pagination
            );
          },
    initialPageParam: undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    staleTime: 10 * 60 * 1000,
    refetchInterval: 10 * 60 * 1000,
    placeholderData: keepPreviousData,
  });
};
