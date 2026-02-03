import { useApi } from "../../state/store";
import { ScanRow } from "../../types/api-types";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";

// Lists the available scans from the server and stores in state
export const useScans = (scansDir: string): AsyncData<ScanRow[]> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey: ["scans", scansDir],
    queryFn: async () => (await api.getScans(scansDir)).items,
    staleTime: 5000,
    refetchInterval: 5000,
  });
};
