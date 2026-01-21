import { useApi } from "../../state/store";
import { ScannerInfo } from "../../types/api-types";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";

export const useScanners = (): AsyncData<ScannerInfo[]> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey: ["scanners"],
    queryFn: async () => (await api.getScanners()).items,
    staleTime: 10000,
  });
};
