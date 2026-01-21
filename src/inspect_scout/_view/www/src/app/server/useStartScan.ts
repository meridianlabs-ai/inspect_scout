import {
  DefaultError,
  useMutation,
  UseMutationResult,
} from "@tanstack/react-query";

import { useApi } from "../../state/store";
import { ScanJobConfig, Status } from "../../types/api-types";

export const useStartScan = (): UseMutationResult<
  Status,
  DefaultError,
  ScanJobConfig
> => {
  const api = useApi();
  return useMutation({ mutationFn: (config) => api.startScan(config) });
};
