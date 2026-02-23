import { skipToken } from "@tanstack/react-query";

import { AsyncData } from "../../utils/asyncData";
import { useScanDataframeInput } from "../server/useScanDataframeInput";
import { ScanResultInputData } from "../types";

import { useScanRoute } from "./useScanRoute";
import { useSelectedScanner } from "./useSelectedScanner";

export const useSelectedScanResultInputData = (
  scanUuid?: string
): AsyncData<ScanResultInputData> => {
  const { resolvedScansDir, scanPath } = useScanRoute();

  const scanner = useSelectedScanner();

  return useScanDataframeInput(
    resolvedScansDir && scanPath && scanner.data && scanUuid
      ? {
          scansDir: resolvedScansDir,
          scanPath,
          scanner: scanner.data,
          uuid: scanUuid,
        }
      : skipToken
  );
};
