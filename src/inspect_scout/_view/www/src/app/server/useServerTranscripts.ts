import { keepPreviousData } from "@tanstack/react-query";
import { SortingState } from "@tanstack/react-table";
import { useMemo } from "react";

import { Condition } from "../../query";
import { useApi } from "../../state/store";
import { TranscriptsResponse } from "../../types/api-types";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";

import { sortingStateToOrderBy } from ".";

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
