import clsx from "clsx";

import { ApplicationIcons } from "../../components/icons";
import type { ScanRow as ApiScanRow } from "../../types/api-types";
import { formatNumber } from "../../utils/format";
import { printObject } from "../../utils/object";
import type { AvailableColumn } from "../components/columnFilter";
import { ExtendedColumnDef, BaseColumnMeta } from "../components/columnTypes";

import styles from "./columns.module.css";

/**
 * Scan row type for grid display.
 * Extends the API ScanRow with a client-computed relativeLocation.
 */
export type ScanRow = ApiScanRow & {
  /** Relative path from results directory (computed client-side) */
  relativeLocation: string;
};

// Define the keys that correspond to our scan columns
// These match the database column names for filtering to work
export type ScanColumnKey =
  // Original columns
  | "status" // Status column
  | "scan_name" // Name column
  | "scanners"
  | "scan_id"
  | "model"
  | "location" // Path column
  | "timestamp" // Time column
  // New columns from spec
  | "scan_file"
  | "tags"
  | "revision_version"
  | "revision_commit"
  | "revision_origin"
  | "packages"
  | "metadata"
  | "scan_args"
  // Aggregated summary columns
  | "total_results"
  | "total_errors"
  | "total_tokens";

// Column type for scan grid
export type ScanColumn = ExtendedColumnDef<ScanRow, BaseColumnMeta>;

// Column headers for display (used in column picker and add filter dropdown)
export const COLUMN_LABELS: Record<ScanColumnKey, string> = {
  // Original columns
  status: "Status",
  scan_name: "Name",
  scanners: "Scanners",
  scan_id: "Scan ID",
  model: "Model",
  location: "Path",
  timestamp: "Time",
  // New columns from spec
  scan_file: "Scan File",
  tags: "Tags",
  revision_version: "Version",
  revision_commit: "Commit",
  revision_origin: "Origin",
  packages: "Packages",
  metadata: "Metadata",
  scan_args: "Scan Args",
  // Aggregated summary columns
  total_results: "Total Results",
  total_errors: "Scanner Errors",
  total_tokens: "Total Tokens",
};

// Column header tooltips
export const COLUMN_HEADER_TITLES: Record<ScanColumnKey, string> = {
  // Original columns
  status: "Scan completion status (complete, in progress, or error)",
  scan_name: "Name of the scan configuration",
  scanners: "List of scanners used in this scan",
  scan_id: "Unique identifier for the scan",
  model: "Model used for scanning",
  location: "Path to the scan results",
  timestamp: "Timestamp when the scan was started",
  // New columns from spec
  scan_file: "Source file path for the scan job",
  tags: "Tags associated with this scan",
  revision_version: "Git version of the scan code",
  revision_commit: "Git commit hash of the scan code",
  revision_origin: "Git origin URL of the scan code",
  packages: "Package versions used in this scan",
  metadata: "Custom metadata for this scan",
  scan_args: "Arguments passed to the scan",
  // Aggregated summary columns
  total_results: "Total number of results across all scanners",
  total_errors: "Errors reported by scanners while processing transcripts",
  total_tokens: "Total tokens used across all scanners",
};

// Helper to get status display (icon and color) for a scan
function getStatusDisplay(scan: ScanRow): {
  icon: string;
  colorClass: string | undefined;
} {
  switch (scan.status) {
    case "complete":
      return { icon: ApplicationIcons.success, colorClass: styles.green };
    case "error":
      return { icon: ApplicationIcons.error, colorClass: styles.red };
    case "active":
    case "incomplete":
    default:
      return { icon: ApplicationIcons.pendingTask, colorClass: styles.yellow };
  }
}

// Helper to format object values for display
function formatObjectValue(
  value: Record<string, unknown> | null | undefined,
  maxLength: number = 1000
): string {
  if (!value || Object.keys(value).length === 0) {
    return "-";
  }
  try {
    return printObject(value, maxLength);
  } catch {
    return "-";
  }
}

// Helper to get full JSON for tooltip
function getObjectTitleValue(
  value: Record<string, unknown> | null | undefined
): string {
  if (!value || Object.keys(value).length === 0) {
    return "";
  }
  return JSON.stringify(value, null, 2);
}

// All available columns, keyed by their ID (using database column names)
export const ALL_COLUMNS: Record<ScanColumnKey, ScanColumn> = {
  // ============================================
  // Original columns
  // ============================================
  status: {
    id: "status",
    accessorKey: "status",
    header: "✓",
    headerTitle: COLUMN_HEADER_TITLES.status,
    size: 70,
    minSize: 70,
    maxSize: 70,
    meta: {
      align: "center",
      filterable: true,
      filterType: "string",
    },
    cell: (info) => {
      const scan = info.row.original;

      if (scan.active_completion_pct != null) {
        return (
          <span className={styles.blue}>
            <i className={ApplicationIcons["play-circle"]}></i>{" "}
            {scan.active_completion_pct}%
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
    accessorKey: "scan_name",
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
    accessorKey: "scanners",
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
    accessorKey: "scan_id",
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
    accessorKey: "model",
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
    accessorKey: "timestamp",
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

  // ============================================
  // New columns from spec
  // ============================================
  scan_file: {
    id: "scan_file",
    accessorKey: "scan_file",
    header: "Scan File",
    headerTitle: COLUMN_HEADER_TITLES.scan_file,
    size: 200,
    minSize: 100,
    maxSize: 500,
    meta: {
      filterable: true,
      filterType: "string",
    },
    cell: (info) => {
      const value = info.getValue() as string | null;
      return value || "-";
    },
  },
  tags: {
    id: "tags",
    accessorKey: "tags",
    header: "Tags",
    headerTitle: COLUMN_HEADER_TITLES.tags,
    size: 150,
    minSize: 80,
    maxSize: 400,
    meta: {
      filterable: true,
      filterType: "string",
    },
    cell: (info) => {
      const value = info.getValue() as string;
      return value || "-";
    },
  },
  revision_version: {
    id: "revision_version",
    accessorKey: "revision_version",
    header: "Version",
    headerTitle: COLUMN_HEADER_TITLES.revision_version,
    size: 150,
    minSize: 80,
    maxSize: 300,
    meta: {
      filterable: true,
      filterType: "string",
    },
    cell: (info) => {
      const value = info.getValue() as string | null;
      return value || "-";
    },
  },
  revision_commit: {
    id: "revision_commit",
    accessorKey: "revision_commit",
    header: "Commit",
    headerTitle: COLUMN_HEADER_TITLES.revision_commit,
    size: 120,
    minSize: 80,
    maxSize: 300,
    meta: {
      filterable: true,
      filterType: "string",
    },
    cell: (info) => {
      const value = info.getValue() as string | null;
      if (!value) return "-";
      // Show first 7 characters of commit hash (standard git short hash)
      return value.slice(0, 7);
    },
    textValue: (value) => {
      if (!value) return "-";
      const strValue = value as string;
      return strValue.slice(0, 7);
    },
  },
  revision_origin: {
    id: "revision_origin",
    accessorKey: "revision_origin",
    header: "Origin",
    headerTitle: COLUMN_HEADER_TITLES.revision_origin,
    size: 200,
    minSize: 100,
    maxSize: 500,
    meta: {
      filterable: true,
      filterType: "string",
    },
    cell: (info) => {
      const value = info.getValue() as string | null;
      return value || "-";
    },
  },
  packages: {
    id: "packages",
    accessorKey: "packages",
    header: "Packages",
    headerTitle: COLUMN_HEADER_TITLES.packages,
    size: 200,
    minSize: 80,
    maxSize: 500,
    meta: {
      filterable: true,
      filterType: "string",
    },
    cell: (info) => {
      const value = info.getValue() as Record<string, string> | undefined;
      return formatObjectValue(value);
    },
    textValue: (value) => {
      return formatObjectValue(value as Record<string, string> | undefined);
    },
    titleValue: (value) => {
      return getObjectTitleValue(value as Record<string, string> | undefined);
    },
  },
  metadata: {
    id: "metadata",
    accessorKey: "metadata",
    header: "Metadata",
    headerTitle: COLUMN_HEADER_TITLES.metadata,
    size: 200,
    minSize: 80,
    maxSize: 500,
    meta: {
      filterable: true,
      filterType: "string",
    },
    cell: (info) => {
      const value = info.getValue() as Record<string, unknown> | undefined;
      return formatObjectValue(value);
    },
    textValue: (value) => {
      return formatObjectValue(value as Record<string, unknown> | undefined);
    },
    titleValue: (value) => {
      return getObjectTitleValue(value as Record<string, unknown> | undefined);
    },
  },
  scan_args: {
    id: "scan_args",
    accessorKey: "scan_args",
    header: "Scan Args",
    headerTitle: COLUMN_HEADER_TITLES.scan_args,
    size: 200,
    minSize: 80,
    maxSize: 500,
    meta: {
      filterable: true,
      filterType: "string",
    },
    cell: (info) => {
      const value = info.getValue() as Record<string, unknown> | undefined;
      return formatObjectValue(value);
    },
    textValue: (value) => {
      return formatObjectValue(value as Record<string, unknown> | undefined);
    },
    titleValue: (value) => {
      return getObjectTitleValue(value as Record<string, unknown> | undefined);
    },
  },

  // ============================================
  // Aggregated summary columns
  // ============================================
  total_results: {
    id: "total_results",
    accessorKey: "total_results",
    header: "Results",
    headerTitle: COLUMN_HEADER_TITLES.total_results,
    size: 100,
    minSize: 60,
    maxSize: 200,
    meta: {
      filterable: true,
      filterType: "number",
    },
    cell: (info) => {
      const value = info.getValue() as number;
      return formatNumber(value);
    },
    textValue: (value) => {
      return formatNumber(value as number);
    },
  },
  total_errors: {
    id: "total_errors",
    accessorKey: "total_errors",
    header: "Scanner Errors",
    headerTitle: COLUMN_HEADER_TITLES.total_errors,
    size: 100,
    minSize: 60,
    maxSize: 200,
    meta: {
      filterable: true,
      filterType: "number",
    },
    cell: (info) => {
      const value = info.getValue() as number;
      return formatNumber(value);
    },
    textValue: (value) => {
      return formatNumber(value as number);
    },
  },
  total_tokens: {
    id: "total_tokens",
    accessorKey: "total_tokens",
    header: "Tokens",
    headerTitle: COLUMN_HEADER_TITLES.total_tokens,
    size: 120,
    minSize: 60,
    maxSize: 200,
    meta: {
      filterable: true,
      filterType: "number",
    },
    cell: (info) => {
      const value = info.getValue() as number;
      return formatNumber(value);
    },
    textValue: (value) => {
      return formatNumber(value as number);
    },
  },
};

// Default column order - includes all columns
export const DEFAULT_COLUMN_ORDER: ScanColumnKey[] = [
  // Original columns first
  "status",
  "scan_name",
  "scanners",
  "scan_id",
  "model",
  "location",
  "timestamp",
  // Aggregated summary columns
  "total_results",
  "total_errors",
  "total_tokens",
  // New columns from spec
  "scan_file",
  "tags",
  "revision_version",
  "revision_commit",
  "revision_origin",
  "packages",
  "metadata",
  "scan_args",
];

// Default visible columns - the original 7 plus total_results
export const DEFAULT_VISIBLE_COLUMNS: ScanColumnKey[] = [
  "status",
  "scan_name",
  "scanners",
  "scan_id",
  "model",
  "location",
  "timestamp",
  "total_results",
];

/**
 * Get columns for the ScansGrid.
 * @param visibleColumnKeys - Optional list of column keys to display. If not provided, returns default visible columns.
 * @returns Array of column definitions in the order specified or default visible columns.
 */
export function getScanColumns(
  visibleColumnKeys?: ScanColumnKey[]
): ScanColumn[] {
  if (!visibleColumnKeys) {
    return DEFAULT_VISIBLE_COLUMNS.map((key) => ALL_COLUMNS[key]);
  }

  return visibleColumnKeys.map((key) => ALL_COLUMNS[key]);
}

// Columns available for filtering (used by Add Filter popover)
export const FILTER_COLUMNS: AvailableColumn[] = DEFAULT_COLUMN_ORDER.map(
  (columnId) => ({
    id: columnId,
    label: COLUMN_LABELS[columnId],
    filterType: ALL_COLUMNS[columnId].meta?.filterType ?? "string",
  })
);
