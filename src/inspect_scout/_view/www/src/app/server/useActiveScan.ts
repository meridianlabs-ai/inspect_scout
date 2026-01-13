import { useCallback } from "react";

import { useMapAsyncData } from "../../hooks/useMapAsyncData";
import {
  ActiveScanInfo,
  ScanStatusWithActiveInfo,
} from "../../types/api-types";
import { AsyncData } from "../../utils/asyncData";

import { useServerScans } from "./useServerScans";

export const useActiveScan = (
  scanId: string | undefined
): AsyncData<ActiveScanInfo | undefined> => {
  const transform = useCallback(
    (scans: ScanStatusWithActiveInfo[]) => {
      if (!scanId) return undefined;
      const scan = scans.find((s) => s.spec.scan_id === scanId);
      return scan?.active_scan_info ?? undefined;
    },
    [scanId]
  );

  return useMapAsyncData(useServerScans(), transform);
};
