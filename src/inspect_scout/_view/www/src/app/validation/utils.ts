import type { ValidationCase } from "../../types/api-types";

/** Valid file extensions for validation set files */
export const VALIDATION_SET_EXTENSIONS = [
  ".csv",
  ".json",
  ".jsonl",
  ".yml",
  ".yaml",
];

/**
 * Check if a filename has a valid validation set extension.
 */
export const hasValidationSetExtension = (name: string): boolean => {
  const lower = name.toLowerCase();
  return VALIDATION_SET_EXTENSIONS.some((ext) => lower.endsWith(ext));
};

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
 * Extracts unique label keys from a list of validation cases.
 * Returns sorted array of label key names.
 */
export const extractUniqueLabels = (cases: ValidationCase[]): string[] => {
  const labelKeys = new Set<string>();
  for (const c of cases) {
    if (c.labels) {
      for (const key of Object.keys(c.labels)) {
        labelKeys.add(key);
      }
    }
  }
  return Array.from(labelKeys).sort();
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
    return filename.replace(/\.(csv|json|jsonl|yaml|yml)$/i, "");
  }
  return filename;
};

/**
 * Extracts the directory portion of a URI (everything before the filename).
 * @param uri - The full URI (e.g., "file:///path/to/file.csv")
 * @returns The directory URI without trailing slash
 */
export const getDirFromUri = (uri: string): string => {
  const parts = uri.split("/");
  parts.pop(); // Remove filename
  return parts.join("/");
};

/**
 * Generates a new file URI in the same directory as the source with given name.
 * @param sourceUri - The source file URI
 * @param newName - The new filename (without extension)
 * @returns New file URI with .csv extension
 */
export const generateNewSetUri = (
  sourceUri: string,
  newName: string
): string => {
  const dir = getDirFromUri(sourceUri);
  return `${dir}/${newName}.csv`;
};

/** Characters that are not allowed in filenames */
const INVALID_FILENAME_CHARS = /[/\\:*?"<>|]/;

/**
 * Validates a filename for invalid characters.
 * @param name - The filename to validate (without extension)
 * @returns Object with isValid and optional error message
 */
export const isValidFilename = (
  name: string
): { isValid: boolean; error?: string } => {
  if (!name.trim()) {
    return { isValid: false, error: "Name cannot be empty" };
  }

  if (INVALID_FILENAME_CHARS.test(name)) {
    return {
      isValid: false,
      error: 'Name contains invalid characters: / \\ : * ? " < > |',
    };
  }

  if (name.startsWith(".")) {
    return { isValid: false, error: "Name cannot start with a dot" };
  }

  if (name.length > 255) {
    return { isValid: false, error: "Name is too long (max 255 characters)" };
  }

  return { isValid: true };
};
