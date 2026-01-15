import { AsyncData } from "../../utils/asyncData";
import { useScanDataframeInput } from "../server/useScanDataframeInput";
import { ScanResultInputData } from "../types";

import { useScanRoute } from "./useScanRoute";
import { useSelectedScanner } from "./useSelectedScanner";

export const useSelectedScanResultInputData =
  (): AsyncData<ScanResultInputData> => {
    const { location, scanResultUuid } = useScanRoute();
    const scanner = useSelectedScanner();

    return useScanDataframeInput(location, scanner.data, scanResultUuid);
  };
