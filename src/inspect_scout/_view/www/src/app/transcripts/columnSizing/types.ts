/**
 * Column sizing types for TranscriptsGrid.
 */

import { ColumnSizingState } from "@tanstack/react-table";

import { TranscriptInfo } from "../../../types/api-types";
import { TranscriptColumn } from "../columns";

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
 */
export interface SizingStrategyContext {
  /** The table element for DOM measurements (may be null) */
  tableElement: HTMLTableElement | null;
  /** Column definitions */
  columns: TranscriptColumn[];
  /** Current data for content measurement */
  data: TranscriptInfo[];
  /** Pre-computed constraints for each column */
  constraints: Map<string, ColumnSizeConstraints>;
}

/**
 * Interface for column sizing strategies.
 * Each strategy computes column sizes differently.
 */
export interface SizingStrategy {
  /** Compute sizes for all columns */
  computeSizes(context: SizingStrategyContext): ColumnSizingState;
}

/**
 * Available sizing strategy keys.
 * - "default": Uses the column's defined `size` property
 * - "fit-content": Measures content and sizes columns to fit within min/max constraints
 */
export type ColumnSizingStrategyKey = "default" | "fit-content";
