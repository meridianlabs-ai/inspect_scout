import { useCallback, useEffect, useMemo, useState } from "react";

import { useStore } from "./store";

export function useProperty<T>(
  id: string,
  propertyName: string,
  options?: {
    defaultValue?: T;
    cleanup?: boolean;
  }
): [T | undefined, (value: T) => void, () => void] {
  const defaultValue = options?.defaultValue;
  const cleanup = options?.cleanup ?? true;

  const setPropertyValue = useStore((state) => state.setPropertyValue);
  const removePropertyValue = useStore((state) => state.removePropertyValue);
  const propertyValue = useStore(
    useCallback(
      (state) => state.getPropertyValue(id, propertyName, defaultValue),
      [id, propertyName, defaultValue]
    )
  );

  const setValue = useCallback(
    (value: T) => {
      setPropertyValue(id, propertyName, value);
    },
    [id, propertyName, setPropertyValue]
  );

  const removeValue = useCallback(() => {
    removePropertyValue(id, propertyName);
  }, [id, propertyName, removePropertyValue]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (cleanup) {
        removePropertyValue(id, propertyName);
      }
    };
  }, [id, propertyName, removePropertyValue, cleanup]);

  return [propertyValue, setValue, removeValue];
}

export const usePrevious = <T>(value: T): T | undefined => {
  const [current, setCurrent] = useState<T>(value);
  const [previous, setPrevious] = useState<T | undefined>(undefined);

  if (value !== current) {
    setPrevious(current);
    setCurrent(value);
  }

  return previous;
};

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
