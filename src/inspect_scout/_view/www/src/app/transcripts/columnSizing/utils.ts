import { TranscriptColumn } from "../columns";

import {
  ColumnSizeConstraints,
  DEFAULT_MAX_SIZE,
  DEFAULT_MIN_SIZE,
  DEFAULT_SIZE,
} from "./types";

/**
 * Extract size constraints from column definitions.
 */
export function getColumnConstraints(
  columns: TranscriptColumn[]
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
export function getColumnId(column: TranscriptColumn): string {
  return column.id || (column as { accessorKey?: string }).accessorKey || "";
}
