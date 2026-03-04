import { useAsyncDataFromQuery } from "@tsmono/react/hooks";
import { AsyncData } from "@tsmono/util";

import { useApi } from "../../state/store";
import { ScannerInfo } from "../../types/api-types";

export const useScanners = (): AsyncData<ScannerInfo[]> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey: ["scanners"],
    queryFn: async () => (await api.getScanners()).items,
    staleTime: 10000,
  });
};
