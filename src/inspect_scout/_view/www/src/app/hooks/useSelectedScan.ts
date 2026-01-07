import { useEffect } from "react";

import { useStore } from "../../state/store";
import { Status } from "../../types/api-types";
import { AsyncData } from "../../utils/asyncData";
import { useServerScan } from "../server/hooks";

import { useScanRoute } from "./useScanRoute";

export const useSelectedScan = (): AsyncData<Status> => {
  const { location, scanPath } = useScanRoute();

  // Set selectedScanLocation for nav restoration
  const setSelectedScanLocation = useStore(
    (state) => state.setSelectedScanLocation
  );
  useEffect(() => {
    if (scanPath) {
      setSelectedScanLocation(scanPath);
    }
  }, [scanPath, setSelectedScanLocation]);

  return useServerScan(location);
};
