import { useMemo } from "react";

import { ActiveScanInfo } from "../../types/api-types";
import { AsyncData, loading } from "../../utils/asyncData";

import { useServerScans } from "./useServerScans";

export const useActiveScan = (
  scanId: string | undefined
): AsyncData<ActiveScanInfo | null> => {
  const { loading: isLoading, error, data: scans } = useServerScans();

  const activeScanInfo = useMemo(() => {
    if (!scans || !scanId) return null;
    const scan = scans.find((s) => s.spec.scan_id === scanId);
    return scan?.active_scan_info ?? null;
  }, [scans, scanId]);

  if (error) return { loading: false, error };
  if (isLoading) return loading;
  return { loading: false, data: activeScanInfo };
};
