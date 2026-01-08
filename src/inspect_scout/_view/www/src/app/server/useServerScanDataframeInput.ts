import { useApi } from "../../state/store";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";
import { ScanResultInputData } from "../types";

export const useServerScanDataframeInput = (
  location: string | undefined,
  scanner: string | undefined,
  uuid: string | undefined
): AsyncData<ScanResultInputData> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey: ["scanDataframeInput", location, scanner, uuid],
    queryFn: () => api.getScannerDataframeInput(location!, scanner!, uuid!),
    enabled: !!location && !!scanner && !!uuid,
    staleTime: Infinity,
  });
};
