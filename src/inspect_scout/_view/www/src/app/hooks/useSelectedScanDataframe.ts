import { ColumnTable } from "arquero";

import { AsyncData } from "../../utils/asyncData";
import { useScanDataframe } from "../server/useScanDataframe";

import { useScanRoute } from "./useScanRoute";
import { useSelectedScanner } from "./useSelectedScanner";

export const useSelectedScanDataframe = (): AsyncData<ColumnTable> => {
  const { location } = useScanRoute();
  const scanner = useSelectedScanner();

  return useScanDataframe(location, scanner.data);
};
