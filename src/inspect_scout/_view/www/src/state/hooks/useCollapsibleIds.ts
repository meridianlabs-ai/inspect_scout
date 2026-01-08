import { useCallback, useMemo } from "react";

import { useStore } from "../store";

export const useCollapsibleIds = (
  key: string
): [
  Record<string, boolean>,
  (id: string, value: boolean) => void,
  () => void,
] => {
  const collapsedIds = useStore((state) => state.collapsedBuckets[key]);

  const setCollapsed = useStore((state) => state.setCollapsed);
  const collapseId = useCallback(
    (id: string, value: boolean) => {
      setCollapsed(key, id, value);
    },
    [key, setCollapsed]
  );

  const clearCollapsedIds = useStore((state) => state.clearCollapsed);
  const clearIds = useCallback(() => {
    clearCollapsedIds(key);
  }, [clearCollapsedIds, key]);

  return useMemo(() => {
    return [collapsedIds || {}, collapseId, clearIds];
  }, [collapsedIds, collapseId, clearIds]);
};
