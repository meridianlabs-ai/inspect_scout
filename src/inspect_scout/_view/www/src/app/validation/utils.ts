import type { ValidationCase } from "../../types/api-types";

/**
 * Converts a validation case ID to a display string.
 * Handles both single string IDs and composite (array) IDs.
 */
export const getIdText = (id: string | string[]): string => {
  return Array.isArray(id) ? id.join(", ") : id;
};

/**
 * Converts a validation case ID to a unique key for use in Maps/Sets.
 * Uses "|" as separator for composite IDs.
 */
export const getCaseKey = (id: string | string[]): string => {
  return Array.isArray(id) ? id.join("|") : id;
};

/**
 * Extracts unique split values from a list of validation cases.
 * Returns sorted array of non-empty split values.
 */
export const extractUniqueSplits = (cases: ValidationCase[]): string[] => {
  const splitSet = new Set<string>();
  for (const c of cases) {
    if (c.split) {
      splitSet.add(c.split);
    }
  }
  return Array.from(splitSet).sort();
};

/**
 * Extracts the filename from a URI/path.
 * @param uri - The full URI or path
 * @param stripExtension - If true, removes common validation file extensions
 */
export const getFilenameFromUri = (
  uri: string,
  stripExtension = false
): string => {
  const filename = uri.split("/").pop() ?? uri;
  if (stripExtension) {
    return filename.replace(/\.(csv|json|yaml|yml)$/i, "");
  }
  return filename;
};
