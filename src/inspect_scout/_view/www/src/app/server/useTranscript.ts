import { skipToken } from "@tanstack/react-query";

import { useAsyncDataFromQuery } from "@tsmono/react/hooks";
import { AsyncData } from "@tsmono/util";

import { useApi } from "../../state/store";
import { Transcript } from "../../types/api-types";

type TranscriptParams = {
  location: string;
  id: string;
};

export const useTranscript = (
  params: TranscriptParams | typeof skipToken
): AsyncData<Transcript> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey: params === skipToken ? [skipToken] : ["transcript", params],
    queryFn:
      params === skipToken
        ? skipToken
        : () => api.getTranscript(params.location, params.id),
    staleTime: Infinity,
  });
};
