// Route URL patterns
export const kScansRouteUrlPattern = '/scans';
export const kScanRouteUrlPattern = '/scan/*';

// Helper functions to generate routes
export const scanRoute = (relativePath: string) => {
  // Split the path and encode each segment separately to preserve slashes
  const segments = relativePath.split('/').map(encodeURIComponent);
  return `/scan/${segments.join('/')}`;
};

export const scansRoute = (relativePath?: string) => {
  if (relativePath) {
    return `/scans/${encodeURIComponent(relativePath)}`;
  } else {
    return '/scans';
  }
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
  params: Readonly<Partial<{ '*': string }>>
): string => {
  return params['*'] || '';
};
