import { useQueryClient } from "@tanstack/react-query";

import { useApi } from "../../state/store";
import { Status } from "../../types/api-types";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";

// Lists the available scans from the server and stores in state
export const useServerScans = (): AsyncData<Status[]> => {
  const api = useApi();
  const queryClient = useQueryClient();

  return useAsyncDataFromQuery({
    queryKey: ["scans"],
    queryFn: async () => {
      const response = await api.getScans();
      for (const scan of response.items) {
        queryClient.setQueryData(["scan", scan.location], scan);
      }
      return response.items;
    },
    staleTime: 10000,
    refetchInterval: 10000,
  });
};
