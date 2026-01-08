import {
  UseInfiniteQueryResult,
  InfiniteData,
  useInfiniteQuery,
  QueryKey,
  keepPreviousData,
} from "@tanstack/react-query";
import { SortingState } from "@tanstack/react-table";
import { useMemo } from "react";

import { Condition } from "../../query";
import { useApi } from "../../state/store";
import { TranscriptsResponse } from "../../types/api-types";

import { CursorType, sortingStateToOrderBy } from ".";

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
