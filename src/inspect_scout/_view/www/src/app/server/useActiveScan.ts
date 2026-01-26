import { useCallback } from "react";

import { useMapAsyncData } from "../../hooks/useMapAsyncData";
import {
  ActiveScanInfo,
  ScanStatusWithActiveInfo,
} from "../../types/api-types";
import { AsyncData } from "../../utils/asyncData";

import { useScans } from "./useScans";

export const useActiveScan = (
  scansDir: string,
  scanId: string | undefined
): AsyncData<ActiveScanInfo | undefined> =>
  useMapAsyncData(
    useScans(scansDir),
    useCallback(
      (scans: ScanStatusWithActiveInfo[]) => {
        if (!scanId) return undefined;
        const scan = scans.find((s) => s.spec.scan_id === scanId);
        return scan?.active_scan_info ?? undefined;
      },
      [scanId]
    )
  );
