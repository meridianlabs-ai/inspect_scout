import { useApi } from "../../state/store";
import { Transcript } from "../../types/api-types";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";

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
