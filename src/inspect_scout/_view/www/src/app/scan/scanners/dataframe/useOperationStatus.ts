import { useCallback, useEffect, useRef, useState } from "react";

/** Transient status for copy/download operations */
export type OperationStatus = "idle" | "success" | "error" | "empty";

/** Duration to show success/error feedback before resetting to idle */
const FEEDBACK_DURATION_MS = 2000;

/**
 * Hook for managing transient operation status with auto-reset.
 * Handles cleanup on unmount to prevent state updates after unmount.
 */
export const useOperationStatus = () => {
  const [status, setStatus] = useState<OperationStatus>("idle");
  const timeoutRef = useRef<number | null>(null);
  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  const setTransientStatus = useCallback((newStatus: OperationStatus) => {
    if (!isMountedRef.current) return;

    setStatus(newStatus);

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }

    if (newStatus !== "idle") {
      timeoutRef.current = window.setTimeout(() => {
        if (isMountedRef.current) {
          setStatus("idle");
        }
      }, FEEDBACK_DURATION_MS);
    }
  }, []);

  return [status, setTransientStatus] as const;
};
