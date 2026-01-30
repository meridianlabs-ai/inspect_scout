/**
 * Column sizing types for TranscriptsGrid.
 * Re-exports shared types and provides transcript-specific type aliases.
 */

// Re-export shared types and utilities
export {
  DEFAULT_MAX_SIZE,
  DEFAULT_MIN_SIZE,
  DEFAULT_SIZE,
} from "../../components/columnSizing";

export type {
  ColumnSizeConstraints,
  ColumnSizingStrategyKey,
} from "../../components/columnSizing";

// Import for transcript-specific types
import { TranscriptInfo } from "../../../types/api-types";
import {
  SizingStrategy as GenericSizingStrategy,
  SizingStrategyContext as GenericSizingStrategyContext,
} from "../../components/columnSizing";
import { TranscriptColumn } from "../columns";

/**
 * Context provided to sizing strategies for computing column sizes.
 * Uses transcript-specific column and data types.
 */
export interface SizingStrategyContext extends Omit<
  GenericSizingStrategyContext<TranscriptInfo>,
  "columns"
> {
  /** Column definitions */
  columns: TranscriptColumn[];
}

/**
 * Interface for column sizing strategies.
 * Each strategy computes column sizes differently.
 */
export type SizingStrategy = GenericSizingStrategy<TranscriptInfo>;
