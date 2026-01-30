import { ColumnDef } from "@tanstack/react-table";

import type { FilterType } from "../../state/store";

/**
 * Common column metadata properties shared across all data grids.
 */
export interface BaseColumnMeta {
  /** Text alignment for the column */
  align?: "left" | "center" | "right";
  /** Whether the column can be filtered */
  filterable?: boolean;
  /** Filter type for the column */
  filterType?: FilterType;
}

/**
 * Extended column definition with custom properties for data grids.
 * Extends TanStack Table's ColumnDef with additional rendering helpers.
 */
export type ExtendedColumnDef<
  TData,
  TMeta extends BaseColumnMeta = BaseColumnMeta,
> = ColumnDef<TData> & {
  meta?: TMeta;
  /** Returns string for tooltip display */
  titleValue?: (value: unknown) => string;
  /** Returns string representation for column width measurement. Return null to skip content measurement. */
  textValue?: (value: unknown) => string | null;
  /** Minimum column width in pixels */
  minSize?: number;
  /** Maximum column width in pixels */
  maxSize?: number;
  /** Tooltip text for the column header */
  headerTitle?: string;
};

/**
 * Configuration for the column picker component.
 */
export interface ColumnInfo {
  /** Column identifier */
  id: string;
  /** Display label for the column */
  label: string;
  /** Optional tooltip for the column header */
  headerTitle?: string;
}

/**
 * Extract title value for tooltip from a cell.
 * Uses custom titleValue function if provided, otherwise falls back to default formatting.
 */
export function getCellTitleValue<TData>(
  value: unknown,
  columnDef: ExtendedColumnDef<TData>
): string {
  // Use custom titleValue function if provided
  if (columnDef.titleValue) {
    return columnDef.titleValue(value);
  }

  // Default fallback
  if (value === undefined || value === null) {
    return "";
  }
  if (typeof value === "object") {
    return JSON.stringify(value, null, 2);
  }
  return String(value);
}
