import { AsyncData } from "../../utils/asyncData";
import { useServerScanDataframeInput } from "../server/hooks";
import { ScanResultInputData } from "../types";

import { useScanRoute } from "./useScanRoute";
import { useSelectedScanner } from "./useSelectedScanner";

export const useSelectedScanResultInputData =
  (): AsyncData<ScanResultInputData> => {
    const { location, scanResultUuid } = useScanRoute();
    const scanner = useSelectedScanner();

    return useServerScanDataframeInput(location, scanner.data, scanResultUuid);
  };
