import { skipToken } from "@tanstack/react-query";

import { useApi } from "../../state/store";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";

type HasTranscriptParams = {
  location: string;
  id: string;
};

export const useHasTranscript = (
  params: HasTranscriptParams | typeof skipToken
): AsyncData<boolean> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey: params === skipToken ? [skipToken] : ["has_transcript", params],
    queryFn:
      params === skipToken
        ? skipToken
        : () => api.hasTranscript(params.location, params.id),
    staleTime: Infinity,
  });
};
