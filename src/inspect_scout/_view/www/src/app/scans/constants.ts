/**
 * Configuration for infinite scroll loading in the Scans grid.
 */
export const SCANS_INFINITE_SCROLL_CONFIG = {
  /** Number of items to fetch per page */
  pageSize: 50,
  /** Distance from bottom (in px) at which to trigger next page fetch */
  threshold: 500,
} as const;
