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
import { ScansResponse } from "../../types/api-types";

import { CursorType, sortingStateToOrderBy } from ".";

export const useScansInfinite = (
  pageSize: number = 50,
  filter?: Condition,
  sorting?: SortingState
): UseInfiniteQueryResult<
  InfiniteData<ScansResponse, CursorType | undefined>,
  Error
> => {
  const api = useApi();

  const orderBy = useMemo(
    () => (sorting ? sortingStateToOrderBy(sorting) : undefined),
    [sorting]
  );

  return useInfiniteQuery<
    ScansResponse,
    Error,
    InfiniteData<ScansResponse, CursorType | undefined>,
    QueryKey,
    CursorType | undefined
  >({
    queryKey: ["scans-infinite", filter, orderBy, pageSize],
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
