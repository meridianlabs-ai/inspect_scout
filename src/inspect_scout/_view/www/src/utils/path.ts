/**
 * Extracts the filename without extension from a given path.
 */
export const filename = (path: string): string => {
  if (!path) {
    return "";
  }
  path = path.endsWith("/") ? path.slice(0, -1) : path;

  const pathparts = path.split("/");
  const basename = pathparts.slice(-1)[0];

  if (!basename) {
    return "";
  }

  // Special case for .hidden files
  if (basename.startsWith(".") && !basename.substring(1).includes(".")) {
    return basename;
  }

  const match = basename.match(/(.*)\.\S+$/);
  if (match) {
    return match[1] ?? "";
  } else {
    return path;
  }
};

export const basename = (path: string): string => {
  if (!path) {
    return "";
  }
  path = path.endsWith("/") ? path.slice(0, -1) : path;
  const pathparts = path.split("/");
  return pathparts.slice(-1)[0] ?? "";
};

/**
 * Extracts the directory name from a given path.
 */
export const dirname = (path: string): string => {
  path = path.endsWith("/") ? path.slice(0, -1) : path;

  const pathparts = path.split("/");

  // If the path ends with a filename (or no slashes), remove the last part (filename)
  if (pathparts.length > 1) {
    pathparts.pop();
    // Join the remaining parts to form the directory path
    return pathparts.join("/");
  }

  // If no slashes, return empty string (no directory)
  return "";
};

/**
 * Tests whether the given path is in the specified directory.
 */
export const isInDirectory = (path: string, directory: string): boolean => {
  directory = directory.endsWith("/") ? directory.slice(0, -1) : directory;

  return dirname(path) === directory;
};

export const ensureTrailingSlash = (path?: string): string => {
  if (!path) {
    return "";
  }
  return path.endsWith("/") ? path : path + "/";
};

/**
 * Converts an absolute path to a relative path based on the results directory.
 * Handles nested subdirectories within the results directory.
 * For example: "/Users/user/scans/subdir/scan_id=123" -> "subdir/scan_id=123"
 */
export const toRelativePath = (
  absolutePath: string,
  basePath: string
): string => {
  const normalizedResultsDir = ensureTrailingSlash(basePath).replace(
    "file://",
    ""
  );
  const normalizedPath = absolutePath.startsWith("file://")
    ? decodeURIComponent(absolutePath.replace("file://", ""))
    : absolutePath;

  if (normalizedPath.startsWith(normalizedResultsDir)) {
    return normalizedPath.substring(normalizedResultsDir.length);
  }

  // If path doesn't start with resultsDir, return the full path as-is
  return normalizedPath;
};

/**
 * Converts a relative path to an absolute path based on the results directory.
 * For example: "subdir/scan_id=123" + "/Users/user/scans/" -> "/Users/user/scans/subdir/scan_id=123"
 */
export const toAbsolutePath = (
  relativePath: string,
  baseDir: string
): string => {
  const normalizedResultsDir = ensureTrailingSlash(baseDir);
  return normalizedResultsDir + relativePath;
};
