import { skipToken } from "@tanstack/react-query";

import { useApi } from "../../state/store";
import { Transcript } from "../../types/api-types";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";

type TranscriptParams = {
  location: string;
  id: string;
};

export const useTranscript = (
  params: TranscriptParams | typeof skipToken
): AsyncData<Transcript> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey: ["transcript", params],
    queryFn:
      params === skipToken
        ? skipToken
        : () => api.getTranscript(params.location, params.id),
    staleTime: Infinity,
  });
};
