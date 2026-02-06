import type { ActiveScanInfo } from "../types/api-types";

export function createActiveScanInfo(
  overrides: Partial<ActiveScanInfo> & { scan_id: string }
): ActiveScanInfo {
  return {
    config: "default",
    last_updated: 1704067200,
    location: `/scans/${overrides.scan_id}`,
    metrics: {
      batch_failures: 0,
      batch_pending: 0,
      buffered_scanner_jobs: 0,
      completed_scans: 0,
      memory_usage: 0,
      process_count: 0,
      task_count: 0,
      tasks_idle: 0,
      tasks_parsing: 0,
      tasks_scanning: 0,
    },
    scanner_names: [],
    start_time: 1704067200,
    summary: { complete: true, scanners: {} },
    title: overrides.scan_id,
    total_scans: 0,
    ...overrides,
  };
}
