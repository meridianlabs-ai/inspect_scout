import { decodeBase64Url, encodeBase64Url } from "../utils/base64url";

// Route URL patterns
export const kScansRootRouteUrlPattern = "/scans";
export const kScansRouteUrlPattern = "/scans/:scansDir";
export const kScansWithPathRouteUrlPattern = "/scans/:scansDir/*";
export const kScanRouteUrlPattern = "/scan/:scansDir/*";
export const kScanResultRouteUrlPattern = "/scan/:scansDir/*/*";
export const kTranscriptsRouteUrlPattern = "/transcripts";
export const kProjectRouteUrlPattern = "/project";
export const kTranscriptDetailRoute =
  "/transcripts/:transcriptsDir/:transcriptId";
export const kTranscriptDetailRouteUrlPattern =
  /\/transcripts\/[^\s/]+\/[^\s/]+$/;

// Regex pattern for valid scan IDs (22 characters: alphanumeric, underscore, dot, or dash)
export const kScanIdPattern = /scan_id=[a-zA-Z0-9_.-]{22}$/;

// Query parameter constants
export const kScannerQueryParam = "scanner";

// Helper functions to generate routes
export const scanRoute = (
  scansDir: string,
  relativePath: string,
  searchParams?: URLSearchParams
) => {
  const encodedDir = encodeBase64Url(scansDir);
  const route = `/scan/${encodedDir}/${relativePath}`;
  searchParams?.delete("tab");

  return searchParams?.toString()
    ? `${route}?${searchParams.toString()}`
    : route;
};

export const scansRoute = (
  scansDir: string,
  relativePath?: string,
  searchParams?: URLSearchParams
) => {
  const encodedDir = encodeBase64Url(scansDir);
  const baseRoute = `/scans/${encodedDir}`;
  const route = relativePath ? `${baseRoute}/${relativePath}` : baseRoute;
  return searchParams?.toString()
    ? `${route}?${searchParams.toString()}`
    : route;
};

export const scanResultRoute = (
  scansDir: string,
  scanRelativePath: string,
  scanResultId?: string,
  searchParams?: URLSearchParams
) => {
  const encodedDir = encodeBase64Url(scansDir);
  const route = `/scan/${encodedDir}/${scanRelativePath}/${scanResultId}`;
  return searchParams?.toString()
    ? `${route}?${searchParams.toString()}`
    : route;
};

export const transcriptsRoute = (searchParams?: URLSearchParams) => {
  const route = `/transcripts`;
  return searchParams?.toString()
    ? `${route}?${searchParams.toString()}`
    : route;
};

export const projectRoute = () => "/project";

export const transcriptRoute = (
  transcriptsDir: string,
  transcriptId: string,
  searchParams?: URLSearchParams
) => {
  const encodedDir = encodeBase64Url(transcriptsDir);
  const route = `/transcripts/${encodedDir}/${transcriptId}`;
  return searchParams?.toString()
    ? `${route}?${searchParams.toString()}`
    : route;
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

export const isValidTranscriptPath = (path: string): boolean => {
  return kTranscriptDetailRouteUrlPattern.test(path);
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

export const parseTranscriptParams = (
  params: Readonly<Partial<{ transcriptsDir: string; transcriptId: string }>>
): { transcriptsDir?: string; transcriptId?: string } => {
  const transcriptId = params.transcriptId;
  const encodedDir = params.transcriptsDir;
  if (!encodedDir) {
    return { transcriptId };
  }

  try {
    return { transcriptsDir: decodeBase64Url(encodedDir), transcriptId };
  } catch {
    return { transcriptId };
  }
};

export const parseScanParams = (
  params: Readonly<Partial<{ scansDir: string; "*": string }>>
): {
  scansDir?: string;
  relativePath: string;
  scanPath: string;
  scanResultUuid?: string;
} => {
  const relativePath = getRelativePathFromParams(params);
  const { scanPath, scanResultUuid } = parseScanResultPath(relativePath);
  const encodedDir = params.scansDir;

  if (!encodedDir) {
    return { relativePath, scanPath, scanResultUuid };
  }

  try {
    return {
      scansDir: decodeBase64Url(encodedDir),
      relativePath,
      scanPath,
      scanResultUuid,
    };
  } catch {
    return { relativePath, scanPath, scanResultUuid };
  }
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
