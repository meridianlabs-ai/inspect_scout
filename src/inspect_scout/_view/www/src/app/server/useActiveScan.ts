import { useCallback } from "react";

import { useMapAsyncData } from "../../hooks/useMapAsyncData";
import { ActiveScanInfo } from "../../types/api-types";
import { AsyncData } from "../../utils/asyncData";

import { useActiveScans } from "./useActiveScans";

export const useActiveScan = (
  _scansDir: string,
  scanId: string | undefined
): AsyncData<ActiveScanInfo | undefined> =>
  useMapAsyncData(
    useActiveScans(),
    useCallback(
      (activeScans: Record<string, ActiveScanInfo>) => {
        if (!scanId) return undefined;
        return activeScans[scanId] ?? undefined;
      },
      [scanId]
    )
  );
