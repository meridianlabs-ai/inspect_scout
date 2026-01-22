import { skipToken } from "@tanstack/react-query";

import { useApi } from "../../state/store";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";
import { ScanResultInputData } from "../types";

type ScanDataframeInputParams = {
  scansDir: string;
  scanPath: string;
  scanner: string;
  uuid: string;
};

export const useScanDataframeInput = (
  params: ScanDataframeInputParams | typeof skipToken
): AsyncData<ScanResultInputData> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey: ["scanDataframeInput", params],
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
