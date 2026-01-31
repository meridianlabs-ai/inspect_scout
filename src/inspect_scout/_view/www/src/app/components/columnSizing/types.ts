/**
 * Generic column sizing types for data grids.
 * These types are used by the column sizing strategies and hooks.
 */

import { ColumnSizingState } from "@tanstack/react-table";

import { ExtendedColumnDef, BaseColumnMeta } from "../columnTypes";

/**
 * Size constraints for a column.
 */
export interface ColumnSizeConstraints {
  /** Default size in pixels */
  size: number;
  /** Minimum allowed size in pixels */
  minSize: number;
  /** Maximum allowed size in pixels */
  maxSize: number;
}

/** Default minimum column size in pixels */
export const DEFAULT_MIN_SIZE = 40;

/** Default maximum column size in pixels */
export const DEFAULT_MAX_SIZE = 600;

/** Default column size in pixels when not specified */
export const DEFAULT_SIZE = 150;

/**
 * Context provided to sizing strategies for computing column sizes.
 * Generic over TData (row data type).
 */
export interface SizingStrategyContext<TData> {
  /** The table element for DOM measurements (may be null) */
  tableElement: HTMLTableElement | null;
  /** Column definitions */
  columns: ExtendedColumnDef<TData, BaseColumnMeta>[];
  /** Current data for content measurement */
  data: TData[];
  /** Pre-computed constraints for each column */
  constraints: Map<string, ColumnSizeConstraints>;
}

/**
 * Interface for column sizing strategies.
 * Each strategy computes column sizes differently.
 * Generic over TData (row data type).
 */
export interface SizingStrategy<TData = unknown> {
  /** Compute sizes for all columns */
  computeSizes(context: SizingStrategyContext<TData>): ColumnSizingState;
}

/**
 * Available sizing strategy keys.
 * - "default": Uses the column's defined `size` property
 * - "fit-content": Measures content and sizes columns to fit within min/max constraints
 */
export type ColumnSizingStrategyKey = "default" | "fit-content";

/**
 * Clamp a size value to min/max constraints.
 */
export function clampSize(
  size: number,
  constraints: ColumnSizeConstraints
): number {
  return Math.max(constraints.minSize, Math.min(constraints.maxSize, size));
}

/**
 * Get the column ID from a column definition.
 */
export function getColumnId<TData>(
  column: ExtendedColumnDef<TData, BaseColumnMeta>
): string {
  return column.id || (column as { accessorKey?: string }).accessorKey || "";
}

/**
 * Extract size constraints from column definitions.
 */
export function getColumnConstraints<TData>(
  columns: ExtendedColumnDef<TData, BaseColumnMeta>[]
): Map<string, ColumnSizeConstraints> {
  const constraints = new Map<string, ColumnSizeConstraints>();

  for (const column of columns) {
    const id = getColumnId(column);
    if (id) {
      constraints.set(id, {
        size: column.size ?? DEFAULT_SIZE,
        minSize: column.minSize ?? DEFAULT_MIN_SIZE,
        maxSize: column.maxSize ?? DEFAULT_MAX_SIZE,
      });
    }
  }

  return constraints;
}
