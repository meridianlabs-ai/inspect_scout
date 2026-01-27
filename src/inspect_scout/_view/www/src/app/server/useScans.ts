import { useQueryClient } from "@tanstack/react-query";

import { useApi } from "../../state/store";
import { ScanStatusWithActiveInfo } from "../../types/api-types";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";
import { toRelativePath } from "../../utils/path";

// Lists the available scans from the server and stores in state
export const useScans = (
  scansDir: string
): AsyncData<ScanStatusWithActiveInfo[]> => {
  const api = useApi();
  const queryClient = useQueryClient();

  return useAsyncDataFromQuery({
    queryKey: ["scans", scansDir],
    queryFn: async () => {
      const response = await api.getScans(scansDir);
      for (const scan of response.items) {
        queryClient.setQueryData(
          ["scan", scansDir, toRelativePath(scan.location, scansDir)],
          scan
        );
      }
      return response.items;
    },
    staleTime: 5000,
    refetchInterval: 5000,
  });
};
