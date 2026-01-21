import { useApi } from "../../state/store";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";

/**
 * Polls the server config version for cache invalidation.
 * Returns an opaque version string that changes when server restarts
 * or project config is modified.
 */
export const useConfigVersion = (): AsyncData<string> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey: ["config-version"],
    queryFn: () => api.getConfigVersion(),
    staleTime: 5000,
    refetchInterval: 5000,
  });
};
