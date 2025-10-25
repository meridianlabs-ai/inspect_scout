// Route URL patterns
export const kScansRouteUrlPattern = "/scans";
export const kScanRouteUrlPattern = "/scan/:scan_location";

// Helper functions to generate routes
export const scanRoute = (scanLocation: string) => `/scan/${encodeURIComponent(scanLocation)}`;
export const scansRoute = () => "/scans";
