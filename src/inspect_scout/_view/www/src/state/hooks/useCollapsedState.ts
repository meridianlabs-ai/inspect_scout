import { useMemo } from "react";

import { useStore } from "../store";

export const useCollapsedState = (
  id: string,
  defaultValue?: boolean,
  scope?: string
): [boolean, (value: boolean) => void] => {
  const resolvedScope = scope || "collapse-state-scope";

  const collapsed = useStore(
    (state) => state.collapsedBuckets[resolvedScope]?.[id]
  );
  const setCollapsed = useStore((state) => state.setCollapsed);

  return useMemo(() => {
    const set = (value: boolean) => {
      setCollapsed(resolvedScope, id, value);
    };
    return [collapsed ?? defaultValue ?? false, set];
  }, [collapsed, resolvedScope, defaultValue, setCollapsed, id]);
};
