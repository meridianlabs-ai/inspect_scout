import { ColumnTable } from "arquero";

import { AsyncData } from "../../utils/asyncData";
import { useServerScanDataframe } from "../server/hooks";

import { useScanRoute } from "./useScanRoute";
import { useSelectedScanner } from "./useSelectedScanner";

export const useSelectedScanDataframe = (): AsyncData<ColumnTable> => {
  const { location } = useScanRoute();
  const scanner = useSelectedScanner();

  return useServerScanDataframe(location, scanner.data);
};
