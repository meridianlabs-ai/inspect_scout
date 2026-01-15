import { useCallback, useMemo } from "react";

/**
 * Filter out null/undefined values from an object.
 */
function filterNullValues<T extends Record<string, unknown>>(
  obj: T
): Partial<T> {
  return Object.fromEntries(
    Object.entries(obj).filter(([, v]) => v !== null && v !== undefined)
  ) as Partial<T>;
}

/**
 * Hook for managing nested config sections like cache and batch.
 *
 * These configs can be:
 * - null/undefined (disabled)
 * - true (enabled with defaults)
 * - number (for batch: simple size value)
 * - object (enabled with specific settings)
 *
 * @param configValue The current config value (from parent generate_config)
 * @param updateParent Function to update the parent config with new nested value
 */
export function useNestedConfig<T extends Record<string, unknown>>(
  configValue: T | boolean | number | null | undefined,
  updateParent: (value: T | boolean | null) => void
) {
  const enabled = configValue !== null && configValue !== undefined && configValue !== false;

  const config: Partial<T> = useMemo(() => {
    if (typeof configValue === "object" && configValue !== null) {
      return configValue;
    }
    return {} as Partial<T>;
  }, [configValue]);

  const setEnabled = useCallback(
    (newEnabled: boolean) => {
      if (newEnabled) {
        updateParent(true);
      } else {
        updateParent(null);
      }
    },
    [updateParent]
  );

  const updateConfig = useCallback(
    (updates: Partial<T>) => {
      const existingConfig =
        typeof configValue === "object" && configValue !== null
          ? filterNullValues(configValue)
          : {};
      updateParent({
        ...existingConfig,
        ...updates,
      } as T);
    },
    [configValue, updateParent]
  );

  return {
    enabled,
    config,
    setEnabled,
    updateConfig,
  };
}

/**
 * Hook specifically for batch config which can also be a simple number (size).
 */
export function useBatchConfig<T extends Record<string, unknown>>(
  configValue: T | boolean | number | null | undefined,
  updateParent: (value: T | boolean | null) => void
) {
  const base = useNestedConfig(configValue, updateParent);

  const simpleBatchSize = typeof configValue === "number" ? configValue : null;

  const updateConfig = useCallback(
    (updates: Partial<T>) => {
      const existingConfig =
        typeof configValue === "object" && configValue !== null
          ? filterNullValues(configValue)
          : {};
      const size =
        typeof configValue === "number"
          ? configValue
          : (existingConfig as Record<string, unknown>).size;
      updateParent({
        ...(size !== undefined ? { size } : {}),
        ...existingConfig,
        ...updates,
      } as T);
    },
    [configValue, updateParent]
  );

  const currentBatchSize = useMemo(() => {
    if (typeof configValue === "object" && configValue !== null) {
      return (configValue as Record<string, unknown>).size as number | undefined;
    }
    return simpleBatchSize ?? undefined;
  }, [configValue, simpleBatchSize]);

  return {
    ...base,
    updateConfig,
    currentBatchSize,
  };
}
