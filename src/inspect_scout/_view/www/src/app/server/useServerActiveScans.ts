import { useApi } from "../../state/store";
import { ActiveScanInfo } from "../../types/api-types";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";

export const useServerActiveScans = (): AsyncData<
  Record<string, ActiveScanInfo>
> => {
  const api = useApi();
  return useAsyncDataFromQuery({
    queryKey: ["active-scans"],
    queryFn: async () => (await api.getActiveScans()).items,
    refetchInterval: 5000,
  });
};
