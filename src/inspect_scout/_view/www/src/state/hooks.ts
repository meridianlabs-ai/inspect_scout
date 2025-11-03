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


export const useCollapsedState = (
  id: string,
  defaultValue?: boolean,
  scope?: string,
): [boolean, (value: boolean) => void] => {
  const stateId = scope ? `${scope}-${id}` : id;

  const collapsed = useStore((state) =>
    state.getCollapsed(stateId, defaultValue),
  );
  const setCollapsed = useStore((state) => state.setCollapsed);

  return useMemo(() => {
    const set = (value: boolean) => {
      setCollapsed(stateId, value);
    };
    return [collapsed, set];
  }, [collapsed, setCollapsed, stateId]);
};

