import { useCallback } from "react";

import { useMapAsyncData } from "@tsmono/react/hooks";
import { AsyncData } from "@tsmono/util";

import { ActiveScanInfo } from "../../types/api-types";

import { useActiveScans } from "./useActiveScans";

export const useActiveScan = (
  scanId: string | undefined
): AsyncData<ActiveScanInfo | undefined> =>
  useMapAsyncData(
    useActiveScans(),
    useCallback(
      (activeScans: Record<string, ActiveScanInfo>) =>
        scanId ? (activeScans[scanId] ?? undefined) : undefined,
      [scanId]
    )
  );
