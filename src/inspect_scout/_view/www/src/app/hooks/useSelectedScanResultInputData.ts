import { skipToken } from "@tanstack/react-query";

import { ScannerInput } from "../../types/api-types";
import { AsyncData } from "../../utils/asyncData";
import { useScanDataframeInput } from "../server/useScanDataframeInput";

import { useScanRoute } from "./useScanRoute";
import { useSelectedScanner } from "./useSelectedScanner";

export const useSelectedScanResultInputData = (
  scanUuid?: string
): AsyncData<ScannerInput> => {
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
