import { skipToken } from "@tanstack/react-query";
import { ColumnTable } from "arquero";

import { AsyncData } from "../../utils/asyncData";
import { useScanDataframe } from "../server/useScanDataframe";

import { useScanRoute } from "./useScanRoute";
import { useSelectedScanner } from "./useSelectedScanner";

export const useSelectedScanDataframe = (): AsyncData<ColumnTable> => {
  const { resolvedScansDir, scanPath } = useScanRoute();
  const scanner = useSelectedScanner();

  return useScanDataframe(
    resolvedScansDir && scanPath && scanner.data
      ? { scansDir: resolvedScansDir, scanPath, scanner: scanner.data }
      : skipToken
  );
};
