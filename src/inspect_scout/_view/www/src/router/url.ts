// Route URL patterns
export const kScansRouteUrlPattern = "/scans";
export const kScansWithPathRouteUrlPattern = "/scans/*";
export const kScanRouteUrlPattern = "/scan/*";

// Regex pattern for valid scan IDs (22 characters: alphanumeric, underscore, dot, or dash)
export const kScanIdPattern = /scan_id=[a-zA-Z0-9_.-]{22}$/;

// Helper functions to generate routes
export const scanRoute = (relativePath: string) => {
  // Split the path and encode each segment separately to preserve slashes
  const segments = relativePath.split("/").map(encodeURIComponent);
  return `/scan/${segments.join("/")}`;
};

export const scansRoute = (relativePath?: string) => {
  if (relativePath) {
    return `/scans/${encodeURIComponent(relativePath)}`;
  } else {
    return "/scans";
  }
};

/**
 * Validates if a path matches the scan_id pattern.
 * The path must end with scan_id=[22 characters of alphanumeric, underscore, dot, or dash]
 *
 * @param path - The path to validate
 * @returns true if the path is valid, false otherwise
 */
export const isValidScanPath = (path: string): boolean => {
  path = path.startsWith("/") ? path : "/" + path;
  return kScanIdPattern.test(path);
};

/**
 * Extracts the relative path from route params.
 * Use this with useParams() when you're on a /scan/* route.
 *
 * @example
 * const params = useParams<{ "*": string }>();
 * const relativePath = getRelativePathFromParams(params);
 */
export const getRelativePathFromParams = (
  params: Readonly<Partial<{ "*": string }>>
): string => {
  return params["*"] || "";
};
