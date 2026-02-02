/**
 * Infinite Scroll Tuning
 *
 * Goal: user never hits bottom while waiting for next page.
 *
 * Formula: threshold >= scroll_speed × fetch_duration
 *
 * Assumptions:
 *   row_height = 29px
 *   fetch_duration = 300-1000ms (variable with fixed overhead)
 *   max_scroll_speed = 1500px/s (typical fast scroller)
 *
 * Check at typical speed (1500px/s):
 *   runway_time = 2000px / 1500px/s = 1333ms
 *   worst_case_fetch = 1000ms
 *   margin = 333ms ✓
 *
 * Check at extreme speed (5000px/s):
 *   runway_time = 2000px / 5000px/s = 400ms
 *   median_fetch = ~350ms
 *   margin = 50ms (tight but ok) ✓
 *
 * Why large pageSize? Fetch duration is mostly fixed overhead, so larger
 * pages = fewer fetches = fewer stall opportunities. 500 rows gives ~9.7s
 * of scrolling per page at 1500px/s.
 *
 * Note: If threshold > pageSize_px, the next page is prefetched immediately
 * after the current page loads. This is fine for maximum smoothness.
 */
export const SCANS_INFINITE_SCROLL_CONFIG = {
  /** Number of rows to fetch per page (500 rows = 14,500px at 29px/row) */
  pageSize: 500,
  /** Distance from bottom (in px) at which to trigger fetch (~69 rows) */
  threshold: 2000,
} as const;
