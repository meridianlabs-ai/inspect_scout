// Route URL patterns
export const kScansRouteUrlPattern = "/scans";
export const kScansWithPathRouteUrlPattern = "/scans/*";
export const kScanRouteUrlPattern = "/scan/*";
export const kScanResultRouteUrlPattern = "/scan/*/*";

// Regex pattern for valid scan IDs (22 characters: alphanumeric, underscore, dot, or dash)
export const kScanIdPattern = /scan_id=[a-zA-Z0-9_.-]{22}$/;

// Query parameter constants
export const kScannerQueryParam = "scanner";

// Helper functions to generate routes
export const scanRoute = (relativePath: string) => {
  return `/scan/${relativePath}`;
};

export const scansRoute = (relativePath?: string) => {
  if (relativePath) {
    return `/scans/${relativePath}`;
  } else {
    return "/scans";
  }
};

export const scanResultRoute = (
  scanRelativePath: string,
  scanResultId: string
) => {
  return `/scan/${scanRelativePath}/${scanResultId}`;
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

// Extracts the scanPath and scanResultUuid from a full path.
// const { scanPath, scanResultUuid } = parseScanResultPath("old_scans/scan_id=3oUGqQCpPQ9WSNPV4oy7Fe/8B90F1605892");
//   scanPath: "old_scans/scan_id=3oUGqQCpPQ9WSNPV4oy7Fe"
//   scanResultUuid: "8B90F1605892"
//
export const parseScanResultPath = (
  fullPath: string
): { scanPath: string; scanResultUuid?: string } => {
  // Find the scan_id pattern in the path
  const scanIdMatch = fullPath.match(/scan_id=[a-zA-Z0-9_.-]{22}/);

  if (!scanIdMatch || scanIdMatch.index === undefined) {
    // No valid scan_id found
    return { scanPath: fullPath };
  }

  // Extract everything up to and including the scan_id
  const scanIdEndIndex = scanIdMatch.index + scanIdMatch[0].length;
  const scanPath = fullPath.slice(0, scanIdEndIndex);
  const remainingPath = fullPath.slice(scanIdEndIndex);

  // Check if there's a scan result UUID after the scan_id
  if (remainingPath && remainingPath.length > 1) {
    const scanResultUuid = remainingPath.startsWith("/")
      ? remainingPath.slice(1)
      : remainingPath;
    return { scanPath, scanResultUuid };
  }

  return { scanPath };
};

// Updates the scanner parameter in URL search params.
export const updateScannerParam = (
  searchParams: URLSearchParams,
  scanner: string
): URLSearchParams => {
  const newParams = new URLSearchParams(searchParams);
  newParams.set(kScannerQueryParam, scanner);
  return newParams;
};

// Retrieves the scanner parameter from URL search params.
export const getScannerParam = (
  searchParams: URLSearchParams
): string | undefined => {
  return searchParams.get(kScannerQueryParam) || undefined;
};
