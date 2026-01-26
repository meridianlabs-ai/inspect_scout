import { skipToken } from "@tanstack/react-query";

import { AsyncData } from "../../utils/asyncData";
import { useScanDataframeInput } from "../server/useScanDataframeInput";
import { ScanResultInputData } from "../types";

import { useScanRoute } from "./useScanRoute";
import { useSelectedScanner } from "./useSelectedScanner";

export const useSelectedScanResultInputData =
  (): AsyncData<ScanResultInputData> => {
    const { resolvedScansDir, scanPath, scanResultUuid } = useScanRoute();
    const scanner = useSelectedScanner();

    return useScanDataframeInput(
      resolvedScansDir && scanPath && scanner.data && scanResultUuid
        ? {
            scansDir: resolvedScansDir,
            scanPath,
            scanner: scanner.data,
            uuid: scanResultUuid,
          }
        : skipToken
    );
  };
