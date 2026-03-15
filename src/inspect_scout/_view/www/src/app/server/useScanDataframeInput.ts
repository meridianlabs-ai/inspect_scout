import { skipToken } from "@tanstack/react-query";

import { useApi } from "../../state/store";
import { ScannerInput } from "../../types/api-types";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";

type ScanDataframeInputParams = {
  scansDir: string;
  scanPath: string;
  scanner: string;
  uuid: string;
};

export const useScanDataframeInput = (
  params: ScanDataframeInputParams | typeof skipToken
): AsyncData<ScannerInput> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey:
      params === skipToken
        ? [skipToken]
        : ["scanDataframeInput", params, "scans-inv"],
    queryFn:
      params === skipToken
        ? skipToken
        : () =>
            api.getScannerDataframeInput(
              params.scansDir,
              params.scanPath,
              params.scanner,
              params.uuid
            ),
    staleTime: Infinity,
  });
};
