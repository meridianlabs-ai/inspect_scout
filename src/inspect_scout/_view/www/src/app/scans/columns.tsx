import { clsx } from "clsx";

import { ApplicationIcons } from "../../components/icons";
import { FilterType } from "../../state/store";
import type { ScanStatusWithActiveInfo } from "../../types/api-types";
import { ExtendedColumnDef, BaseColumnMeta } from "../components/columnTypes";

import styles from "./columns.module.css";

/**
 * Extended scan row type with computed fields for grid display.
 * Adds flattened/computed values for columns that need them.
 */
export type ScanRow = ScanStatusWithActiveInfo & {
  /** Relative path from results directory */
  relativeLocation: string;
};

// Define the keys that correspond to our scan columns
// These match the database column names for filtering to work
export type ScanColumnKey =
  | "complete" // Status column (computed display, but can filter on complete)
  | "scan_name" // Name column
  | "scanners"
  | "scan_id"
  | "model"
  | "location" // Path column
  | "timestamp"; // Time column

// Column type for scan grid
export type ScanColumn = ExtendedColumnDef<ScanRow, BaseColumnMeta>;

// Column headers for display (used in column picker and add filter dropdown)
export const COLUMN_LABELS: Record<ScanColumnKey, string> = {
  complete: "Status",
  scan_name: "Name",
  scanners: "Scanners",
  scan_id: "Scan ID",
  model: "Model",
  location: "Path",
  timestamp: "Time",
};

// Column header tooltips
export const COLUMN_HEADER_TITLES: Record<ScanColumnKey, string> = {
  complete: "Scan completion status (complete, in progress, or error)",
  scan_name: "Name of the scan configuration",
  scanners: "List of scanners used in this scan",
  scan_id: "Unique identifier for the scan",
  model: "Model used for scanning",
  location: "Path to the scan results",
  timestamp: "Timestamp when the scan was started",
};

// Helper to get status value from scan row
function getStatusValue(scan: ScanRow): string {
  if (scan.active_scan_info) return "active";
  if (scan.errors.length > 0) return "error";
  return scan.complete ? "complete" : "incomplete";
}

// Helper to get scanners as comma-separated string
function getScannersValue(scan: ScanRow): string {
  const scanners = scan.spec.scanners;
  return scanners ? Object.keys(scanners).join(", ") : "-";
}

// Helper to get status display (icon and color) for a scan
function getStatusDisplay(scan: ScanRow): {
  icon: string;
  colorClass: string | undefined;
} {
  if (scan.complete) {
    return { icon: ApplicationIcons.success, colorClass: styles.green };
  }
  if (scan.errors.length > 0) {
    return { icon: ApplicationIcons.error, colorClass: styles.red };
  }
  return { icon: ApplicationIcons.pendingTask, colorClass: styles.yellow };
}

// All available columns, keyed by their ID (using database column names)
const ALL_COLUMNS: Record<ScanColumnKey, ScanColumn> = {
  complete: {
    id: "complete",
    accessorFn: getStatusValue,
    header: "✓",
    headerTitle: COLUMN_HEADER_TITLES.complete,
    size: 70,
    minSize: 70,
    maxSize: 70,
    meta: {
      align: "center",
      filterable: true,
      filterType: "boolean",
    },
    cell: (info) => {
      const scan = info.row.original;
      const activeScan = scan.active_scan_info;

      if (activeScan) {
        const pct =
          activeScan.total_scans > 0
            ? Math.round(
                (activeScan.metrics.completed_scans / activeScan.total_scans) *
                  100
              )
            : 0;
        return (
          <span className={styles.blue}>
            <i className={ApplicationIcons["play-circle"]}></i> {pct}%
          </span>
        );
      }

      const { icon, colorClass } = getStatusDisplay(scan);
      return <i className={clsx(icon, colorClass)}></i>;
    },
    textValue: () => null,
  },
  scan_name: {
    id: "scan_name",
    accessorFn: (row) => row.spec.scan_name ?? "-",
    header: "Name",
    headerTitle: COLUMN_HEADER_TITLES.scan_name,
    size: 120,
    minSize: 80,
    maxSize: 300,
    meta: {
      filterable: true,
      filterType: "string",
    },
  },
  scanners: {
    id: "scanners",
    accessorFn: getScannersValue,
    header: "Scanners",
    headerTitle: COLUMN_HEADER_TITLES.scanners,
    size: 120,
    minSize: 80,
    maxSize: 400,
    meta: {
      filterable: true,
      filterType: "string",
    },
  },
  scan_id: {
    id: "scan_id",
    accessorFn: (row) => row.spec.scan_id ?? "-",
    header: "Scan ID",
    headerTitle: COLUMN_HEADER_TITLES.scan_id,
    size: 150,
    minSize: 100,
    maxSize: 400,
    meta: {
      filterable: true,
      filterType: "string",
    },
  },
  model: {
    id: "model",
    accessorFn: (row) => row.spec.model?.model ?? "-",
    header: "Model",
    headerTitle: COLUMN_HEADER_TITLES.model,
    size: 150,
    minSize: 80,
    maxSize: 400,
    meta: {
      filterable: true,
      filterType: "string",
    },
  },
  location: {
    id: "location",
    accessorKey: "relativeLocation",
    header: "Path",
    headerTitle: COLUMN_HEADER_TITLES.location,
    size: 200,
    minSize: 100,
    maxSize: 500,
    meta: {
      filterable: true,
      filterType: "string",
    },
  },
  timestamp: {
    id: "timestamp",
    accessorFn: (row) => row.spec.timestamp ?? "",
    header: "Time",
    headerTitle: COLUMN_HEADER_TITLES.timestamp,
    size: 180,
    minSize: 120,
    maxSize: 300,
    meta: {
      filterable: true,
      filterType: "datetime",
    },
    cell: (info) => {
      const timestamp = info.getValue() as string;
      if (!timestamp) return "-";
      return new Date(timestamp).toLocaleString();
    },
    textValue: (value) => {
      if (!value) return "-";
      return new Date(value as string).toLocaleString();
    },
  },
};

// Default column order
export const DEFAULT_COLUMN_ORDER: ScanColumnKey[] = [
  "complete",
  "scan_name",
  "scanners",
  "scan_id",
  "model",
  "location",
  "timestamp",
];

// Default visible columns - currently matches column order; can be subset if needed
export const DEFAULT_VISIBLE_COLUMNS: ScanColumnKey[] = DEFAULT_COLUMN_ORDER;

/**
 * Get columns for the ScansGrid.
 * @param visibleColumnKeys - Optional list of column keys to display. If not provided, returns all columns in default order.
 * @returns Array of column definitions in the order specified or default order.
 */
export function getScanColumns(
  visibleColumnKeys?: ScanColumnKey[]
): ScanColumn[] {
  if (!visibleColumnKeys) {
    return DEFAULT_COLUMN_ORDER.map((key) => ALL_COLUMNS[key]);
  }

  return visibleColumnKeys.map((key) => ALL_COLUMNS[key]);
}

/**
 * Get the filter type for a given column ID.
 * @param columnId - The column ID to look up
 * @returns The filter type for the column, or "string" as default
 */
export function getFilterTypeForColumn(columnId: string): FilterType {
  const column = ALL_COLUMNS[columnId as ScanColumnKey];
  return column?.meta?.filterType ?? "string";
}
