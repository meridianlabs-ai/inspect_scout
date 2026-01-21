import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import { useConfigVersion } from "./useConfigVersion";

/**
 * Monitors server config version and invalidates dependent queries on change.
 *
 * Detects when server restarts or project config is modified, then invalidates
 * all queries tagged with "serverConfig" in their query key.
 *
 * Call once at app root level.
 */
export const useServerConfigInvalidation = (): void => {
  const queryClient = useQueryClient();
  const { data: version } = useConfigVersion();
  const prevVersionRef = useRef<string | undefined>(undefined);

  useEffect(() => {
    if (version === undefined) return;

    if (
      prevVersionRef.current !== undefined &&
      prevVersionRef.current !== version
    ) {
      void queryClient.invalidateQueries({
        predicate: (query) => query.queryKey.includes("serverConfig"),
      });
    }

    prevVersionRef.current = version;
  }, [version, queryClient]);
};
