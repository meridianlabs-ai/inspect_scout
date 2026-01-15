import { ProjectConfigInput } from "../../types/api-types";

/**
 * Deep equality check for config objects using JSON serialization.
 */
export function configsEqual(
  a: Partial<ProjectConfigInput> | null,
  b: Partial<ProjectConfigInput> | null
): boolean {
  if (a === b) return true;
  if (!a || !b) return false;
  return JSON.stringify(a) === JSON.stringify(b);
}

/**
 * Check if a value is "empty" (null, undefined, or empty object/array).
 */
export function isEmpty(value: unknown): boolean {
  if (value === null || value === undefined) return true;
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === "object") return Object.keys(value).length === 0;
  return false;
}

/**
 * Deep copy an object using JSON serialization.
 */
export function deepCopy<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}

/**
 * Clean nested config (cache/batch) for saving.
 * Handles boolean, number, object, null, and undefined values.
 */
function cleanNestedConfig(
  edited: Record<string, unknown> | boolean | number | null | undefined,
  original: Record<string, unknown> | boolean | number | null | undefined
): Record<string, unknown> | boolean | number | null | undefined {
  // Preserve boolean and number values as-is
  if (typeof edited === "boolean" || typeof edited === "number") {
    return edited;
  }

  // If edited is empty, return null if original had content
  if (edited === null || edited === undefined) {
    if (original !== null && original !== undefined) {
      return null;
    }
    return undefined;
  }

  const result: Record<string, unknown> = {};
  const originalObj =
    typeof original === "object" && original !== null ? original : {};

  for (const [key, value] of Object.entries(edited)) {
    const origValue = originalObj[key];
    const valueChanged = JSON.stringify(value) !== JSON.stringify(origValue);

    if (valueChanged) {
      result[key] = value;
    } else if (!isEmpty(value)) {
      result[key] = value;
    }
  }

  // If result is empty but original had content, return true (enabled state)
  if (Object.keys(result).length === 0) {
    if (original !== null && original !== undefined) {
      return true;
    }
    return undefined;
  }

  return result;
}

/**
 * Clean generate_config for saving.
 * Handles nested cache/batch configs and removes empty values.
 */
function cleanGenerateConfig(
  edited: Record<string, unknown> | null | undefined,
  original: Record<string, unknown> | null | undefined,
  _server: Record<string, unknown> | null | undefined
): Record<string, unknown> | null | undefined {
  // Handle empty edited config
  if (
    edited === null ||
    edited === undefined ||
    (typeof edited === "object" && Object.keys(edited).length === 0)
  ) {
    const originalHasContent =
      original !== null &&
      original !== undefined &&
      typeof original === "object" &&
      Object.keys(original).length > 0;
    if (originalHasContent) {
      return null;
    }
    return undefined;
  }

  const result: Record<string, unknown> = {};
  const originalObj = original ?? {};

  for (const key of Object.keys(edited)) {
    const editedValue = edited[key];
    const originalValue = originalObj[key];

    // Handle nested cache/batch configs
    if (key === "cache" || key === "batch") {
      const cleanedNested = cleanNestedConfig(
        editedValue as
          | Record<string, unknown>
          | boolean
          | number
          | null
          | undefined,
        originalValue as
          | Record<string, unknown>
          | boolean
          | number
          | null
          | undefined
      );
      if (cleanedNested !== undefined) {
        result[key] = cleanedNested;
      }
      continue;
    }

    // Handle null/undefined values
    if (editedValue === null || editedValue === undefined) {
      const originalHadContent =
        originalValue !== null &&
        originalValue !== undefined &&
        (typeof originalValue !== "object" ||
          Object.keys(originalValue).length > 0);
      if (originalHadContent) {
        result[key] = null;
      }
      continue;
    }

    result[key] = editedValue;
  }

  if (Object.keys(result).length === 0) {
    return undefined;
  }

  return result;
}

/**
 * Compute the config to save by comparing edited values against original server state.
 * Only includes values that have changed or have content.
 */
export function computeConfigToSave(
  edited: Partial<ProjectConfigInput>,
  original: Partial<ProjectConfigInput>,
  serverConfig: ProjectConfigInput
): ProjectConfigInput {
  const result: Record<string, unknown> = {};

  const allKeys = new Set([
    ...Object.keys(edited),
    ...Object.keys(serverConfig),
  ]);

  for (const key of allKeys) {
    const editedValue = edited[key as keyof ProjectConfigInput];
    const originalValue = original[key as keyof ProjectConfigInput];
    const serverValue = serverConfig[key as keyof ProjectConfigInput];

    // Handle generate_config specially
    if (key === "generate_config") {
      const cleanedGenConfig = cleanGenerateConfig(
        editedValue as Record<string, unknown> | null | undefined,
        originalValue as Record<string, unknown> | null | undefined,
        serverValue as Record<string, unknown> | null | undefined
      );
      if (cleanedGenConfig !== undefined) {
        result[key] = cleanedGenConfig;
      }
      continue;
    }

    const valueChanged =
      JSON.stringify(editedValue) !== JSON.stringify(originalValue);

    if (valueChanged) {
      result[key] = editedValue;
    } else if (!isEmpty(editedValue)) {
      result[key] = editedValue;
    }
  }

  return result as ProjectConfigInput;
}

/**
 * Initialize edited config from server config.
 * Extracts the relevant fields for editing.
 */
export function initializeEditedConfig(
  serverConfig: ProjectConfigInput
): Partial<ProjectConfigInput> {
  return {
    transcripts: serverConfig.transcripts,
    filter: serverConfig.filter,
    scans: serverConfig.scans,
    max_transcripts: serverConfig.max_transcripts,
    max_processes: serverConfig.max_processes,
    limit: serverConfig.limit,
    shuffle: serverConfig.shuffle,
    tags: serverConfig.tags,
    metadata: serverConfig.metadata,
    log_level: serverConfig.log_level,
    model: serverConfig.model,
    model_base_url: serverConfig.model_base_url,
    model_args: serverConfig.model_args,
    generate_config: serverConfig.generate_config ?? null,
  };
}
