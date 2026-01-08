import { useApi } from "../../state/store";
import { Status } from "../../types/api-types";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";

// Fetches scan status from the server by location
export const useServerScan = (
  location: string | undefined
): AsyncData<Status> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey: ["scan", location],
    queryFn: () => api.getScan(location!), // The ! is safe because of enabled below
    enabled: !!location,
    staleTime: 10000,
    // TODO: We need to think through refetchInterval. If the specific scan was retrieved
    // by the scans hook above, it'll already have a refresh. If it was not, however,
    // we'll still want it to refresh, but we don't want the hooks to compete. Hmmm.
  });
};
